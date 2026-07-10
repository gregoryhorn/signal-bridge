# Pilot Info Card — Design / Look & Feel Pass

> **Status:** implemented in source (`sb_ui/pilot_info.py`, wired from `show_pilot_info_card`).  
> **For agentic workers:** implement after approval with `superpowers:subagent-driven-development` or `superpowers:executing-plans`.  
> **Scope:** visual hierarchy, density, and wasted space — **not** ESI/zKill correctness (already Phase 2.3).  
> **Constraint:** keep network work off the render path (`docs/INVARIANTS.md`). No `APP_VERSION` bump unless packaging.

---

## Visual review (current state)

Source of truth: `signal_bridge_gui.py` → `show_pilot_info_card` (~6685–7072).  
There is **no dedicated Pilot Info screenshot** in `docs/images/` (only main feed). Review is from layout code + structure.

### What the card does today

```text
┌─ Header (fixed dark bar) ─────────────────────────────────────┐
│ PilotName (large)                                             │
│ Corp · Alliance                                               │
│ Character ID: 123…  zKill: https://zkillboard.com/…           │
│ Last: … · System · N reports · zKill: not synced              │
├─ Body (scroll canvas) ────────────────────────────────────────┤
│ [chip strip: flags + systems + ships + signals + status]      │
│ ┌ Summary ──────────────────────────────────────────────────┐ │
│ │ Reports / First / Last / System / Ship / Status (2-col)   │ │
│ └───────────────────────────────────────────────────────────┘ │
│ ┌ Recent Activity ──────────────────────────────────────────┐ │
│ │ mono-ish lines of last 4 sightings                        │ │
│ └───────────────────────────────────────────────────────────┘ │
│ ┌ Patterns ─────────────────────────────────────────────────┐ │
│ │ Ships: chips   Status: chips   Signals: chips   Systems:  │ │
│ └───────────────────────────────────────────────────────────┘ │
│ ┌ zKill ────────────────────────────────────────────────────┐ │
│ │ long pipe-delimited status line                           │ │
│ │ long ISK / signals line                                   │ │
│ │ Recent kills… / Recent losses…                            │ │
│ └───────────────────────────────────────────────────────────┘ │
├─ Footer (fixed) ──────────────────────────────────────────────┤
│ [Copy][Flags][Activity][Sync zKill][Open zKill][Close]        │
└───────────────────────────────────────────────────────────────┘
```

Default open size: **720×620**, min **640×520** — large for a companion overlay next to EVE.

### Findings (severity-ordered)

| # | Issue | Why it feels ugly / wasteful |
|---|--------|------------------------------|
| **P0** | **Triple-redundant data** | Same facts appear in (1) header “Last: …”, (2) chip strip, (3) Summary grid, (4) Patterns rows. Brain has to re-parse the same pilot three times. |
| **P0** | **Empty / sparse sections always expand** | “No local sightings”, “Not synced”, Patterns with all “None/Unknown” still consume full section blocks and vertical padding. |
| **P1** | **Hardcoded hex everywhere** | `#0b0f14`, `#111821`, `#1c2835`… bypass `sb_ui.theme` / components — inconsistent with Settings design pass; chips/buttons look off-brand. |
| **P1** | **Header is a dump zone** | Full zKill URL + Character ID as gray body text is console-like, not card-like. Meta line is one long cyan sentence. |
| **P1** | **Chip strip is unsorted noise** | Flags, systems, ships, signals, status share one pack row with no labels — wraps into a candy bar of unrelated tags. |
| **P1** | **zKill intro is a wall of text** | Two long `|`-joined labels before useful kill/loss lists. Priority (HIGH/MED) is buried mid-sentence. |
| **P1** | **Activity lines fake monospace** | `f"{tm:<10}  {sysname:<8}"` in proportional fonts misaligns and looks broken. |
| **P2** | **Footer has six equal flat buttons** | No primary action (Sync when not synced / Open zKill when synced). Dense and “toolbar soup”. |
| **P2** | **Oversized chrome for empty pilots** | New pilot with 0 reports + not synced still opens a tall window → large empty black canvas. |
| **P2** | **Subviews replace entire body** | Flags/Activity re-render header+body; “&lt; Back” sits inside content, not chrome — disorienting. |
| **P2** | **God-method (~400 lines)** | Nested closures, local hex helpers — hard to iterate design without regressions. |

### What still works (keep)

- Footer packed before body → actions stay visible (Phase 2.3 fix).
- Cache-first zKill; Sync is background-only.
- Priority logic (HIGH/MED/QUIET) and ranked small-gang kills are useful.
- Separate Flags / full Activity drill-downs are the right *features*, wrong *chrome*.

---

## Design direction

### Product job (one sentence)

**“In one glance, know who this pilot is, how hot they are right now, and what to do next.”**

Not: dump every field from Intel History + zKill.

### Aesthetic

Match Signal Bridge **tactical side-panel** language (already on feed/Settings):

| Token | Role | Suggested source |
|-------|------|------------------|
| `bg` `#0b0f14` | Window | `sb_theme.COLORS["bg"]` |
| `bg_panel` `#111821` | Header/footer/cards | `sb_theme.COLORS["bg_panel"]` |
| `fg` / `fg_muted` / `fg_bright` | Body / meta / name | theme |
| `accent` / cyan `#5ad7ff` | Links, secondary emphasis | theme / existing link |
| Threat **HIGH** | Soft red text + optional left bar | `COLORS["error"]` |
| Threat **MED** | Gold | `COLORS["warning"]` / system yellow family |
| Ship chips | Orange family | align feed ship highlight |
| System chips | Gold family | align feed system highlight |

**Signature element:** a single **Threat / Priority ribbon** under the name (HIGH · same ship today · or QUIET · not synced) — one place the eye lands. Everything else is quieter.

**Not** the generic “three black cards + neon green accent” AI default. Keep it dense, dark, intel-console — but **structured**, not a log paste.

### Information architecture (target)

```text
┌─ Identity ──────────────────────────────────────────┐
│ NAME                              [HIGH] ribbon     │
│ Corp · Alliance                                     │
│ Last sighting one-liner (time · system · ship)      │
│ optional: ID as small copyable muted (not URL wall) │
├─ Snapshot strip (one row, labeled groups) ──────────┤
│ Flags: …   ·   Hot: systems/ships/signals (top 2–3) │
├─ Local (only if reports > 0) ───────────────────────┤
│ Compact timeline: 3–5 rows max, table-like columns  │
├─ zKill ─────────────────────────────────────────────┤
│ [Sync needed] CTA  OR  stats strip + 2 short lists  │
│  kills (3) | losses (3) with zkill links            │
├─ Footer ────────────────────────────────────────────┤
│ Primary: Sync zKill / Open zKill   Secondary: …     │
└─────────────────────────────────────────────────────┘
```

**Remove from default view:**

- Full `https://zkillboard.com/character/…` string (keep **Open zKill** button).
- Entire **Patterns** section (merge into snapshot strip).
- **Summary** 6-field grid when it only repeats header + strip.
- Placeholder chips (“None”, “Unknown”) — omit the group instead.

**Collapse empty:**

- No sightings → one muted line under snapshot, no “Recent Activity” card.
- zKill not synced → one CTA card (“Sync for 30-day kills/losses”), no empty kill/loss headers.

### Density / size

| State | Target window (approx.) |
|-------|-------------------------|
| Empty / never seen / not synced | ~420–480 × 360–420 |
| Local data, zKill not synced | ~480 × 480–520 |
| Full data (synced + lists) | ~520 × 560–640 max |

Use `fit_to_content` after render with **lower min_size** (e.g. 420×360) than today’s 660×520.

Default width closer to feed panel (~430–520), not a second Settings window.

### Layout principles

1. **One primary column** — no competing multi-panels on open.
2. **Scan order:** Name → threat → last sighting → chips → lists → actions.
3. **Type scale:** Name 14–16 bold; section labels 9–10 muted uppercase or small bold; body 9–10; meta 8–9 muted.
4. **Lists as rows**, not freeform prose: `time | system | ship | note` with consistent column weights (use a small grid or fixed-width prefixes only if using Consolas for that row).
5. **Buttons:** max **3** primary/secondary in footer; overflow “More…” menu if needed (Copy, Flags, Activity, Close).
6. **Theme only** — no new hex literals in the pilot card module.

### Component structure (implementation)

Extract from god method into:

```text
sb_ui/pilot_info.py          # pure layout builders (Tk)
  - open_pilot_info_window(app, profile)
  - render_identity_header(...)
  - render_snapshot_strip(...)
  - render_local_timeline(...)
  - render_zkill_block(...)
  - render_footer(...)
signal_bridge_gui.py         # thin: open_pilot_info_card → sb_ui.pilot_info
```

Logic stays callable from GUI (zkill summary, intel history, friendly_datetime). Card module receives **prepared view-model dict** to avoid importing network code.

Optional pure prepare step:

```text
sb_pilot_card.py  # pure: profile + zkill_summary → PilotCardViewModel
```

---

## Wireframes

### A — Empty / new pilot (common today)

```text
┌─────────────────────────────────────┐
│ Buffering                    QUIET  │
│ Chaos arbiter · Fraternity.         │
│ No local sightings yet              │
├─────────────────────────────────────┤
│ zKill not synced                    │
│ [ Sync zKill ]  data stays local    │
├─────────────────────────────────────┤
│ [Sync zKill]  [Open zKill]  [Close] │
└─────────────────────────────────────┘
  ~ compact, little empty black
```

### B — Hot pilot (local + synced)

```text
┌─────────────────────────────────────┐
│ Matek Bathana                 HIGH  │
│ Some Corp · Some Alliance           │
│ 12:42 · 4-HWWF · Sabre · No visual  │
├─────────────────────────────────────┤
│ ★ Watchlist   4-HWWF×3   Sabre×2    │
│ cyno×1                              │
├─────────────────────────────────────┤
│ LOCAL                               │
│ 12:42  4-HWWF   Sabre    nv         │
│ 11:01  Jita     Unknown  —          │
│ 10:50  4-HWWF   Crow     —          │
├─────────────────────────────────────┤
│ ZKILL  12k / 3l · 1.2b / 400m ISK  │
│ Kills (small gang first)            │
│  · yesterday  Sabre  80m  [solo] ↗  │
│ Losses                              │
│  · 3d ago     Caracal 12m [fleet] ↗ │
├─────────────────────────────────────┤
│ [Open zKill] [Sync] [Flags] [More▾]│
└─────────────────────────────────────┘
```

### C — Flags / Activity subviews

Keep as **in-body panels** with a **chrome back control** in header right (`← Summary`), not a text button inside the list. Same window size; don’t re-open.

---

## Implementation plan (tasks)

### Task 0 — Capture before/after

- Open Pilot Info on: (1) unknown pilot, (2) pilot with local history, (3) after zKill sync.
- Screenshot into `docs/images/pilot-info-before-*.png` (optional but ideal).

### Task 1 — Extract + theme tokens

- Create `sb_ui/pilot_info.py` using `sb_theme` + `sb_components` (`card`/`action_button`/`primary_button`/`info_label`).
- GUI becomes one-liner open.
- No visual change required beyond theme alignment.

### Task 2 — Identity header redesign

- Name + threat ribbon + corp/alliance.
- Single last-sighting line.
- Character ID as muted small text or “Copy ID” only — **remove raw zKill URL**.
- Drop duplicate “Last: … reports · zKill status” mega-line if covered by ribbon + last-sighting.

### Task 3 — Collapse Summary + Patterns into snapshot strip

- One labeled strip: Flags | Hot systems | Hot ships | Signals (omit empty groups).
- Delete default Patterns section and redundant Summary grid (or reduce Summary to one optional “Stats” line: `N reports · first seen …` only if useful).

### Task 4 — Local timeline density

- Show 3–5 rows by default; “Activity” opens full list.
- Consistent columns; use theme colors; drop fake monospace padding or use a real monospace font only for the timeline block.

### Task 5 — zKill block redesign

- **Not synced / failed / syncing:** short status + single primary CTA.
- **Synced:** one stats strip (K/L · ISK · priority badge), then two compact lists (cap 3 each on summary view; full lists stay after sync).
- Killmail link as subtle `↗` only (already mostly there).

### Task 6 — Footer hierarchy

- Primary: `Sync zKill` if not synced; else `Open zKill`.
- Secondary: `Sync` (if already synced), `Flags`, `Copy`.
- Tertiary: `Activity`, `Close` — or menu **More**.
- Use `primary_button` vs `action_button`.

### Task 7 — Sizing

- Lower `fit_to_content` min/max; set canvas height from body; re-run after each render_summary / subview.
- Ensure empty state does not open at 620px height.

### Task 8 — Docs + verify

- Update `docs/help/07-pilot-info.md` to match new layout.
- Optional after screenshots: `docs/images/pilot-info-after.png`.
- Tests: pure view-model helpers if extracted; smoke “open doesn’t throw” if feasible without full ESI.

---

## Out of scope

- Changing zKill API ranking rules (unless display-only caps).
- ESI portrait images (nice later; avoid dependency/network on open).
- Multi-column “dashboard” layouts that fight the side-panel mental model.
- APP_VERSION / portable rebuild.

---

## Success criteria

1. Opening Pilot Info on a never-seen pilot shows a **compact** card with clear Sync CTA — not a half-empty 620px window.
2. **No triple-repeat** of systems/ships/status on the default view.
3. Threat priority is **visible in &lt;1 second** without reading a pipe-delimited paragraph.
4. All colors/fonts from `sb_ui.theme` / components.
5. Footer actions always visible; primary action obvious.
6. Existing flows still work: Copy, Flags, Activity, Sync zKill, Open zKill, killmail links.
7. Invariants: no network on render.

---

## Effort estimate

| Task | Size |
|------|------|
| 1 Extract + theme | S–M |
| 2 Header | S |
| 3 Snapshot merge | M |
| 4 Timeline | S |
| 5 zKill block | M |
| 6 Footer | S |
| 7 Sizing | S |
| 8 Docs | S |

**Total:** ~1 focused session for extract+theme+header+collapse; second session for zKill polish + sizing + verify.

---

## Approval checkpoint

Please confirm:

1. **Compact side-panel density** (recommended) vs keeping a wide 720px card.
2. **Remove Patterns + Summary grid** in favor of one snapshot strip (recommended).
3. **Hide zKill URL** in favor of Open zKill button (recommended).
4. Optional: character portrait later (out of this pass).

After approval, implement Tasks 1–7 on the current feature branch without version bump.
