#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Promote curated EVE phrase fixes into durable phrase_overrides and purge machine cache.

Translation layers (highest trust first):
  1. data/phrase_overrides.json     — shipped curated fixes (this script syncs into here)
  2. translation_overrides (SQLite) — user manual corrections in Settings
  3. translation_cache (SQLite)     — ephemeral Google/Argos machine cache

Typical workflow
----------------
1. Review live bad MT in the feed or machine cache::

     python -X utf8 scripts/promote_eve_translations.py report

2. Add a good EVE mapping to ``data/eve_phrase_promotions.json``
   (source Chinese/phrase → target EVE English).

3. Apply promotions + purge matching machine-cache rows::

     python -X utf8 scripts/promote_eve_translations.py sync

4. Restart Signal Bridge so phrase overrides reload.

Idempotent: re-running ``sync`` only adds missing sources (or updates targets
with ``--update``) and re-purges matching cache rows.

Examples
--------
  python -X utf8 scripts/promote_eve_translations.py report
  python -X utf8 scripts/promote_eve_translations.py report --limit 30
  python -X utf8 scripts/promote_eve_translations.py sync
  python -X utf8 scripts/promote_eve_translations.py sync --update
  python -X utf8 scripts/promote_eve_translations.py sync --purge-all-overrides
  python -X utf8 scripts/promote_eve_translations.py purge
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMOTIONS_PATH = ROOT / "data" / "eve_phrase_promotions.json"
OVERRIDES_PATH = ROOT / "data" / "phrase_overrides.json"
CACHE_PATH = ROOT / "cache" / "translation_cache.sqlite"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_promotions() -> list[dict]:
    data = _load_json(PROMOTIONS_PATH)
    items = data.get("promotions") or data.get("overrides") or []
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        src = str(item.get("source") or "").strip()
        tgt = str(item.get("target") or "").strip()
        if not src or not tgt:
            continue
        out.append(
            {
                "source": src,
                "target": tgt,
                "direction": str(item.get("direction") or "zh-en"),
                "enabled": bool(item.get("enabled", True)),
                "note": str(item.get("note") or "EVE phrase promotion"),
            }
        )
    return out


def load_overrides() -> list[dict]:
    data = _load_json(OVERRIDES_PATH)
    items = data.get("overrides") or []
    return [x for x in items if isinstance(x, dict) and str(x.get("source") or "").strip()]


def save_overrides(items: list[dict]) -> None:
    # Longest sources first so compounds win at apply-time even if callers do not sort.
    items = sorted(items, key=lambda x: len(str(x.get("source") or "")), reverse=True)
    _save_json(
        OVERRIDES_PATH,
        {"schema_version": 1, "overrides": items},
    )


def merge_promotions(update_existing: bool = False) -> tuple[int, int, int]:
    """Merge promotions into phrase_overrides. Returns (added, updated, unchanged)."""
    promotions = load_promotions()
    overrides = load_overrides()
    by_source = {str(x.get("source") or "").strip(): x for x in overrides}
    added = updated = unchanged = 0
    for promo in promotions:
        src = promo["source"]
        if src not in by_source:
            by_source[src] = dict(promo)
            added += 1
            continue
        existing = by_source[src]
        if update_existing and (
            str(existing.get("target") or "") != promo["target"]
            or str(existing.get("direction") or "zh-en") != promo["direction"]
            or bool(existing.get("enabled", True)) != promo["enabled"]
        ):
            existing["target"] = promo["target"]
            existing["direction"] = promo["direction"]
            existing["enabled"] = promo["enabled"]
            if promo.get("note"):
                existing["note"] = promo["note"]
            updated += 1
        else:
            unchanged += 1
    save_overrides(list(by_source.values()))
    return added, updated, unchanged


def purge_cache_sources(sources: set[str], also_bad_substrings: list[str] | None = None) -> int:
    if not CACHE_PATH.exists():
        print(f"No machine cache at {CACHE_PATH} (nothing to purge).")
        return 0
    con = sqlite3.connect(str(CACHE_PATH))
    deleted = 0
    try:
        for src in sorted(sources, key=len, reverse=True):
            if not src:
                continue
            # Exact source match
            cur = con.execute("delete from translation_cache where source_text = ?", (src,))
            deleted += int(cur.rowcount or 0)
            # Compound lines that embed the promoted phrase (e.g. 本地低安超大洞，图尔隔壁)
            if len(src) >= 2:
                cur = con.execute(
                    "delete from translation_cache where source_text like ?",
                    (f"%{src}%",),
                )
                deleted += int(cur.rowcount or 0)
        for needle in also_bad_substrings or []:
            if not needle:
                continue
            cur = con.execute(
                "delete from translation_cache where translated_text like ?",
                (f"%{needle}%",),
            )
            deleted += int(cur.rowcount or 0)
        con.commit()
    finally:
        con.close()
    return deleted


def cmd_report(limit: int) -> int:
    print(f"Promotions catalog: {PROMOTIONS_PATH}")
    print(f"  entries: {len(load_promotions())}")
    print(f"Phrase overrides:  {OVERRIDES_PATH}")
    print(f"  entries: {len(load_overrides())}")
    print(f"Machine cache:     {CACHE_PATH}")
    if not CACHE_PATH.exists():
        print("  (missing)")
        return 0
    con = sqlite3.connect(str(CACHE_PATH))
    try:
        total = int(con.execute("select count(*) from translation_cache").fetchone()[0])
        print(f"  rows: {total}")
        print()
        print("=== machine translation_cache (for review) ===")
        rows = con.execute(
            """
            select source_text, translated_text, engine, hit_count, last_used_at
            from translation_cache
            order by hit_count desc, last_used_at desc
            limit ?
            """,
            (max(1, limit),),
        ).fetchall()
        promo_sources = {p["source"] for p in load_promotions()}
        override_sources = {str(x.get("source") or "") for x in load_overrides()}
        for src, dst, eng, hits, used in rows:
            flags = []
            if src in promo_sources:
                flags.append("IN_PROMOTIONS")
            if src in override_sources:
                flags.append("IN_OVERRIDES")
            tag = f" [{','.join(flags)}]" if flags else ""
            print(f"[{hits}] {src!r} => {dst!r}  ({eng}, used={used}){tag}")
        print()
        print("Tip: add good EVE mappings to data/eve_phrase_promotions.json, then run:")
        print("  python -X utf8 scripts/promote_eve_translations.py sync")
    finally:
        con.close()
    return 0


def cmd_sync(update_existing: bool, purge_all_overrides: bool) -> int:
    added, updated, unchanged = merge_promotions(update_existing=update_existing)
    print(f"Merged promotions into {OVERRIDES_PATH}")
    print(f"  added={added} updated={updated} unchanged={unchanged}")

    sources = {p["source"] for p in load_promotions()}
    if purge_all_overrides:
        sources |= {str(x.get("source") or "") for x in load_overrides()}
        print("  purge set: all phrase_overrides sources + promotions")
    else:
        print("  purge set: eve_phrase_promotions sources only")

    bad_substrings = [
        "deformation",
        "Great Voyage of the Serpent",
        "krypton gold",
        "flagship skill",
        "guitar brain",
    ]
    deleted = purge_cache_sources(sources, also_bad_substrings=bad_substrings)
    print(f"Purged {deleted} machine-cache row(s) from {CACHE_PATH}")
    print("Restart Signal Bridge to reload phrase overrides.")
    return 0


def cmd_purge(purge_all_overrides: bool) -> int:
    sources = {p["source"] for p in load_promotions()}
    if purge_all_overrides:
        sources |= {str(x.get("source") or "") for x in load_overrides()}
    deleted = purge_cache_sources(
        sources,
        also_bad_substrings=[
            "deformation",
            "Great Voyage of the Serpent",
            "krypton gold",
            "flagship skill",
            "guitar brain",
        ],
    )
    print(f"Purged {deleted} machine-cache row(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Promote curated EVE translations into durable phrase_overrides and purge machine cache.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="Show promotions/overrides counts and machine-cache rows for review")
    p_report.add_argument("--limit", type=int, default=100, help="Max machine-cache rows to print (default 100)")

    p_sync = sub.add_parser("sync", help="Merge promotions into phrase_overrides and purge matching machine cache")
    p_sync.add_argument(
        "--update",
        action="store_true",
        help="Update existing phrase_overrides targets from promotions when they differ",
    )
    p_sync.add_argument(
        "--purge-all-overrides",
        action="store_true",
        help="Also purge machine-cache rows for every phrase_overrides source (not only promotions)",
    )

    p_purge = sub.add_parser("purge", help="Only purge machine cache for promotion sources (no merge)")
    p_purge.add_argument(
        "--purge-all-overrides",
        action="store_true",
        help="Purge machine-cache rows for every phrase_overrides source",
    )

    args = parser.parse_args(argv)
    if args.command == "report":
        return cmd_report(args.limit)
    if args.command == "sync":
        return cmd_sync(update_existing=args.update, purge_all_overrides=args.purge_all_overrides)
    if args.command == "purge":
        return cmd_purge(purge_all_overrides=args.purge_all_overrides)
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
