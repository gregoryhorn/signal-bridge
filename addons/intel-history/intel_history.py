from __future__ import annotations

import json
import queue
import sqlite3
import threading
import time
import traceback
from pathlib import Path


class IntelHistoryModule:
    """Small, conservative MVP Intel History module.

    It records only ESI-confirmed character sightings from normalized Signal Bridge
    rows. All database work happens on a background thread so live chat rendering
    never waits on Intel History.
    """

    def __init__(self, context: dict):
        self.context = context
        self.data_dir = Path(context["data_dir"])
        self.module_dir = Path(context["module_dir"])
        self.db_path = self.data_dir / "intel_history.sqlite"
        self.schema_path = self.module_dir / "schema.sql"
        self.queue: queue.Queue = queue.Queue(maxsize=1000)
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.last_error = ""
        self.last_sighting = ""
        self.processed = 0
        self.inserted = 0
        self.duplicates = 0
        self.dropped = 0
        self.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def start(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self.worker = threading.Thread(target=self._run, name="IntelHistory", daemon=True)
        self.worker.start()

    def shutdown(self):
        self.stop_event.set()
        if self.worker:
            self.worker.join(timeout=2.0)

    def on_intel_row(self, row: dict):
        try:
            self.queue.put_nowait(row)
        except queue.Full:
            self.dropped += 1

    def get_health_status(self) -> dict:
        stats = self._db_stats()
        stats.update({
            "enabled": True,
            "db_path": str(self.db_path),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            "queue_size": self.queue.qsize(),
            "processed": self.processed,
            "inserted": self.inserted,
            "duplicates": self.duplicates,
            "dropped": self.dropped,
            "last_sighting": self.last_sighting or "none",
            "last_error": self.last_error or "none",
            "started_at": self.started_at,
        })
        return stats

    def _init_db(self):
        with sqlite3.connect(self.db_path) as con:
            if self.schema_path.exists():
                con.executescript(self.schema_path.read_text(encoding="utf-8"))
            else:
                con.execute("create table if not exists pilots(pilot_id integer primary key, name text not null, first_seen text, last_seen text)")
                con.execute("create table if not exists sightings(id integer primary key autoincrement, pilot_id integer, pilot_name text, timestamp text, system_name text, ship_name text, channel text, confidence text, source text, dedupe_key text unique, duplicate_count integer default 1, created_at text)")
                con.execute("create table if not exists pilot_stats(pilot_id integer primary key, report_count integer default 0, first_seen text, last_seen text, top_ships_json text, top_systems_json text, threat_level text, threat_reasons_json text, updated_at text)")

    def _run(self):
        while not self.stop_event.is_set():
            try:
                row = self.queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._process_row(row)
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
                try:
                    (self.data_dir / "intel_history_errors.log").write_text(traceback.format_exc(), encoding="utf-8")
                except Exception:
                    pass
            finally:
                self.queue.task_done()

    def _process_row(self, row: dict):
        characters = [c for c in row.get("characters", []) if c.get("entity_type") == "character" and c.get("entity_id")]
        if not characters:
            return
        systems = row.get("systems") or [""]
        ships = row.get("ships") or [""]
        timestamp = row.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        channel = row.get("channel") or ""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for ent in characters:
            pilot_id = int(ent.get("entity_id"))
            pilot_name = ent.get("name") or ent.get("query") or str(pilot_id)
            for system in systems[:3]:
                for ship in ships[:3]:
                    self._record_sighting(pilot_id, pilot_name, timestamp, system or "", ship or "", channel, ent.get("confidence") or "high", now, ent)

    def _bucket(self, timestamp: str) -> str:
        # Cheap stable bucket: exact minute rounded down to a 3-minute group when parseable.
        m = timestamp[:16]
        try:
            minute = int(m[-2:])
            return m[:-2] + f"{minute - (minute % 3):02d}"
        except Exception:
            return m

    def _record_sighting(self, pilot_id: int, pilot_name: str, timestamp: str, system: str, ship: str, channel: str, confidence: str, now: str, ent: dict):
        dedupe = "|".join([str(pilot_id), system.casefold(), ship.casefold(), channel.casefold(), self._bucket(timestamp)])
        with sqlite3.connect(self.db_path) as con:
            con.execute("""
                insert into pilots(pilot_id, name, corp_id, corp_name, alliance_id, alliance_name, first_seen, last_seen, created_at, updated_at)
                values(?,?,?,?,?,?,?,?,?,?)
                on conflict(pilot_id) do update set
                  name=excluded.name,
                  corp_id=excluded.corp_id,
                  corp_name=excluded.corp_name,
                  alliance_id=excluded.alliance_id,
                  alliance_name=excluded.alliance_name,
                  last_seen=excluded.last_seen,
                  updated_at=excluded.updated_at
            """, (pilot_id, pilot_name, ent.get("corporation_id"), ent.get("corporation_name") or "", ent.get("alliance_id"), ent.get("alliance_name") or "", timestamp, timestamp, now, now))
            cur = con.execute("""
                insert into sightings(pilot_id, pilot_name, timestamp, system_name, ship_name, channel, confidence, source, dedupe_key, duplicate_count, created_at)
                values(?,?,?,?,?,?,?,?,?,?,?)
                on conflict(dedupe_key) do update set duplicate_count=duplicate_count+1
            """, (pilot_id, pilot_name, timestamp, system, ship, channel, confidence, "signal-bridge-live", dedupe, 1, now))
            if cur.rowcount:
                # SQLite reports 1 for both insert and update; distinguish by duplicate count after write.
                dup = con.execute("select duplicate_count from sightings where dedupe_key=?", (dedupe,)).fetchone()[0]
                if int(dup) > 1:
                    self.duplicates += 1
                else:
                    self.inserted += 1
            con.execute("""
                insert into pilot_stats(pilot_id, report_count, first_seen, last_seen, top_ships_json, top_systems_json, threat_level, threat_reasons_json, updated_at)
                values(?, 1, ?, ?, ?, ?, 'Low', '[]', ?)
                on conflict(pilot_id) do update set
                  report_count=(select count(*) from sightings where pilot_id=?),
                  first_seen=(select min(timestamp) from sightings where pilot_id=?),
                  last_seen=(select max(timestamp) from sightings where pilot_id=?),
                  top_ships_json=?,
                  top_systems_json=?,
                  updated_at=?
            """, (pilot_id, timestamp, timestamp, self._top_json(con, pilot_id, "ship_name"), self._top_json(con, pilot_id, "system_name"), now, pilot_id, pilot_id, pilot_id, self._top_json(con, pilot_id, "ship_name"), self._top_json(con, pilot_id, "system_name"), now))
        self.processed += 1
        self.last_sighting = f"{pilot_name} {system or '-'} {ship or '-'} {timestamp}"

    def _top_json(self, con: sqlite3.Connection, pilot_id: int, column: str) -> str:
        if column not in {"ship_name", "system_name"}:
            return "[]"
        rows = con.execute(f"select {column}, count(*) c from sightings where pilot_id=? and {column}<>'' group by {column} order by c desc, {column} limit 5", (pilot_id,)).fetchall()
        total = sum(int(r[1]) for r in rows) or 1
        return json.dumps([{"name": r[0], "count": int(r[1]), "percent": round(int(r[1]) * 100 / total)} for r in rows], ensure_ascii=False)

    def _db_stats(self) -> dict:
        if not self.db_path.exists():
            return {"pilots": 0, "sightings": 0, "flags": 0}
        try:
            with sqlite3.connect(self.db_path) as con:
                return {
                    "pilots": con.execute("select count(*) from pilots").fetchone()[0],
                    "sightings": con.execute("select count(*) from sightings").fetchone()[0],
                    "flags": con.execute("select count(*) from pilot_flags").fetchone()[0],
                }
        except Exception as exc:
            self.last_error = f"stats {type(exc).__name__}: {exc}"
            return {"pilots": 0, "sightings": 0, "flags": 0}


def init(context: dict) -> IntelHistoryModule:
    module = IntelHistoryModule(context)
    module.start()
    return module
