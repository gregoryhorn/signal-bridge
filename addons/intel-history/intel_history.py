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
        self.flag_rules_path = self.module_dir / "rules" / "flag_rules.json"
        self.flag_rules = self._load_flag_rules()
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


    def _load_flag_rules(self) -> dict:
        default = {
            "hot_drop_risk": {
                "enabled": True,
                "duration_minutes": 120,
                "flag": "Hot Drop Risk",
                "label": "Hot Drop Risk",
                "icon": "🔥",
                "high_confidence_classes": {
                    "force_recon_cruiser": ["Arazu", "Rapier", "Falcon", "Pilgrim"],
                    "expedition_frigate": ["Prospect", "Endurance"],
                },
            }
        }
        try:
            if self.flag_rules_path.exists():
                loaded = json.loads(self.flag_rules_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    return loaded
        except Exception as exc:
            self.last_error = f"flag_rules {type(exc).__name__}: {exc}"
        return default

    def _hot_drop_ship_class(self, ship: str) -> str:
        ship_key = str(ship or "").strip().casefold()
        if not ship_key:
            return ""
        rule = self.flag_rules.get("hot_drop_risk") or {}
        classes = rule.get("high_confidence_classes") or {}
        for class_name, ships in classes.items():
            for item in ships or []:
                if ship_key == str(item).strip().casefold():
                    return str(class_name).replace("_", " ").title()
        return ""

    def _upsert_auto_flag(self, con: sqlite3.Connection, pilot_id: int, label: str, icon: str, reason: str, now: str, expires_at: str | None):
        con.execute("""
            update pilot_flags
               set active=0
             where pilot_id=? and source='auto' and label=? and active=1
        """, (int(pilot_id), label))
        con.execute("""
            insert into pilot_flags(pilot_id, flag, label, icon, source, confidence, reason, created_at, expires_at, active)
            values(?,?,?,?,?,?,?,?,?,1)
        """, (int(pilot_id), label, label, icon, "auto", "high", reason, now, expires_at))

    def _row_has_cyno_signal(self, row: dict, ship: str) -> bool:
        terms = []
        terms.extend(row.get("assets") or [])
        terms.extend(row.get("ships") or [])
        terms.append(ship or "")
        terms.append(row.get("text") or "")
        for term in terms:
            if "cyno" in str(term or "").casefold():
                return True
        return False

    def _maybe_cyno_hotdrop_flag(self, con: sqlite3.Connection, pilot_id: int, system: str, timestamp: str, now: str):
        rule = self.flag_rules.get("hot_drop_risk") or {}
        if not rule.get("enabled", True):
            return
        minutes = int(rule.get("duration_minutes") or 120)
        expires_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + minutes * 60))
        label = str(rule.get("label") or rule.get("flag") or "Hot Drop Risk")
        icon = str(rule.get("icon") or "HOT")
        reason = f"Reported with cyno intel, likely hotdropper, in {system or 'unknown'} at {timestamp}."
        self._upsert_auto_flag(con, pilot_id, label, icon, reason, now, expires_at)

    def _maybe_hot_drop_auto_flag(self, con: sqlite3.Connection, pilot_id: int, ship: str, system: str, timestamp: str, now: str):
        rule = self.flag_rules.get("hot_drop_risk") or {}
        if not rule.get("enabled", True):
            return
        ship_class = self._hot_drop_ship_class(ship)
        if not ship_class:
            return
        minutes = int(rule.get("duration_minutes") or 120)
        expires_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + minutes * 60))
        label = str(rule.get("label") or rule.get("flag") or "Hot Drop Risk")
        icon = str(rule.get("icon") or "HOT")
        reason = f"Reported in {ship}, a {ship_class}, likely cyno-capable, in {system or 'unknown'} at {timestamp}."
        self._upsert_auto_flag(con, pilot_id, label, icon, reason, now, expires_at)

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
            if self._is_do_not_track(pilot_id):
                continue
            pilot_name = ent.get("name") or ent.get("query") or str(pilot_id)
            for system in systems[:3]:
                for ship in ships[:3]:
                    self._record_sighting(pilot_id, pilot_name, timestamp, system or "", ship or "", channel, ent.get("confidence") or "high", now, ent)
                    if self._row_has_cyno_signal(row, ship):
                        self._maybe_cyno_hotdrop_flag(con, pilot_id, system or "", timestamp, now)

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
            self._maybe_hot_drop_auto_flag(con, pilot_id, ship, system, timestamp, now)
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


    def get_active_flags(self, pilot_id: int) -> list[dict]:
        """Return active flags for feed badges and quick UI actions."""
        if not self.db_path.exists():
            return []
        try:
            with sqlite3.connect(self.db_path) as con:
                con.row_factory = sqlite3.Row
                rows = con.execute("""
                    select id, flag, label, icon, source, confidence, reason, created_at, expires_at, active
                    from pilot_flags
                    where pilot_id=? and active=1 and (expires_at is null or expires_at='' or expires_at>?)
                    order by source='manual' desc, created_at desc, flag
                """, (int(pilot_id), time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))).fetchall()
                return [dict(r) for r in rows]
        except Exception as exc:
            self.last_error = f"active_flags {type(exc).__name__}: {exc}"
            return []

    def _is_do_not_track(self, pilot_id: int) -> bool:
        for flag in self.get_active_flags(int(pilot_id)):
            label = str(flag.get("label") or flag.get("flag") or "").casefold()
            if label == "do not track":
                return True
        return False

    def get_pilot_profile(self, pilot_id: int | None = None, name: str | None = None) -> dict:
        """Return a compact profile for the Pilot Info card."""
        if not self.db_path.exists():
            return {"found": False, "error": "database not initialized"}
        try:
            with sqlite3.connect(self.db_path) as con:
                con.row_factory = sqlite3.Row
                if pilot_id:
                    pilot = con.execute("select * from pilots where pilot_id=?", (int(pilot_id),)).fetchone()
                else:
                    pilot = con.execute("select * from pilots where lower(name)=lower(?) order by last_seen desc limit 1", (name or "",)).fetchone()
                if not pilot:
                    return {"found": False, "pilot_id": pilot_id, "name": name or ""}
                pid = int(pilot["pilot_id"])
                stat = con.execute("select * from pilot_stats where pilot_id=?", (pid,)).fetchone()
                recent = [dict(r) for r in con.execute("""
                    select timestamp, system_name, ship_name, duplicate_count, source, channel
                    from sightings where pilot_id=? order by timestamp desc limit 25
                """, (pid,)).fetchall()]
                top_ships = [dict(r) for r in con.execute("""
                    select ship_name as name, count(*) as sightings, sum(duplicate_count) as reports,
                           min(timestamp) as first_seen, max(timestamp) as last_seen
                    from sightings where pilot_id=? and ship_name<>''
                    group by ship_name order by reports desc, sightings desc, ship_name limit 25
                """, (pid,)).fetchall()]
                top_systems = [dict(r) for r in con.execute("""
                    select system_name as name, count(*) as sightings, sum(duplicate_count) as reports,
                           min(timestamp) as first_seen, max(timestamp) as last_seen
                    from sightings where pilot_id=? and system_name<>''
                    group by system_name order by reports desc, sightings desc, system_name limit 25
                """, (pid,)).fetchall()]
                flags = [dict(r) for r in con.execute("""
                    select id, flag, label, icon, source, confidence, reason, created_at, expires_at, active
                    from pilot_flags where pilot_id=? order by active desc, created_at desc, flag
                """, (pid,)).fetchall()]
                report_count = int(stat["report_count"] if stat else 0)
                if not report_count:
                    row = con.execute("select count(*) from sightings where pilot_id=?", (pid,)).fetchone()
                    report_count = int(row[0] if row else 0)
                return {
                    "found": True,
                    "pilot": dict(pilot),
                    "stats": dict(stat) if stat else {},
                    "report_count": report_count,
                    "recent_sightings": recent,
                    "top_ships": top_ships,
                    "top_systems": top_systems,
                    "flags": flags,
                }
        except Exception as exc:
            self.last_error = f"profile {type(exc).__name__}: {exc}"
            return {"found": False, "error": self.last_error, "pilot_id": pilot_id, "name": name or ""}

    def set_manual_flags(self, pilot_id: int, flags: list[dict]) -> dict:
        """Replace active manual flags for a pilot. Keeps inactive rows as history."""
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            with sqlite3.connect(self.db_path) as con:
                con.execute("update pilot_flags set active=0 where pilot_id=? and source='manual' and active=1", (int(pilot_id),))
                for item in flags:
                    flag = str(item.get("flag") or item.get("label") or "").strip()
                    if not flag:
                        continue
                    con.execute("""
                        insert into pilot_flags(pilot_id, flag, label, icon, source, confidence, reason, created_at, expires_at, active)
                        values(?,?,?,?,?,?,?,?,?,1)
                    """, (int(pilot_id), flag, str(item.get("label") or flag), str(item.get("icon") or ""), "manual", "high", str(item.get("reason") or ""), now, None))
            return {"ok": True}
        except Exception as exc:
            self.last_error = f"flags {type(exc).__name__}: {exc}"
            return {"ok": False, "error": self.last_error}

    def copyable_pilot_summary(self, pilot_id: int) -> str:
        profile = self.get_pilot_profile(pilot_id=pilot_id)
        if not profile.get("found"):
            return "No Intel History profile found."
        pilot = profile.get("pilot") or {}
        flags = [f.get("label") or f.get("flag") for f in profile.get("flags", []) if f.get("active")]
        recent = profile.get("recent_sightings", [])[:10]
        top_ships = profile.get("top_ships", [])[:5]
        top_systems = profile.get("top_systems", [])[:5]
        last = recent[0] if recent else {}
        lines = [
            f"Pilot: {pilot.get('name','')}",
            f"Corp: {pilot.get('corp_name') or 'unknown'}",
            f"Alliance: {pilot.get('alliance_name') or 'none'}",
            f"Character ID: {pilot.get('pilot_id')}",
            f"Flags: {', '.join(flags) if flags else 'none'}",
            f"Reports: {profile.get('report_count', 0)}",
            f"First seen: {pilot.get('first_seen') or 'unknown'}",
            f"Last seen: {pilot.get('last_seen') or 'unknown'}",
            f"Last sighting: {last.get('timestamp','unknown')} — {last.get('system_name') or '-'} — {last.get('ship_name') or '-'}",
            "",
            "Top ships:",
        ]
        lines.extend([f"- {r.get('name')}: {r.get('reports') or r.get('sightings')}" for r in top_ships] or ["- none"])
        lines.append("")
        lines.append("Top systems:")
        lines.extend([f"- {r.get('name')}: {r.get('reports') or r.get('sightings')}" for r in top_systems] or ["- none"])
        lines.append("")
        lines.append("Recent sightings:")
        lines.extend([f"- {r.get('timestamp')} {r.get('system_name') or '-'} {r.get('ship_name') or '-'} x{r.get('duplicate_count', 1)}" for r in recent] or ["- none"])
        return "\n".join(lines)

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
