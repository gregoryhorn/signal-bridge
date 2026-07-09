# Contracts Foundation + Backlog Issues Implementation Plan

> **Status (2026-07-10):** **Implemented on branch `feature/contracts-and-backlog`.** Core tasks (0–14 product/modules) are done; remaining follow-ups are PR merge, manual live smoke, full Settings design pass, and further god-file extraction (ESI/parse/free_text). Checkbox steps below are historical execution notes.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the six documented target contracts real, testable runtime types; close every still-open `ISSUES.md` backlog item; and while doing so, **extract every system we touch into small, isolated modules** so work no longer requires regular edits to the ~7k-line `signal_bridge_gui.py` god file.

**Architecture:** Logic lives in focused packages/modules (`sb_contracts/`, `sb_channels.py`, `sb_monitor.py`, `sb_translation/`, `sb_filters.py`, `sb_highlight.py`, `sb_diagnostics.py`, `sb_paths.py`, `sb_ui/*` page helpers). `signal_bridge_gui.py` becomes a **wiring shell**: Tk app lifecycle, menus, queue drain, and thin calls into modules. New features must not add substantial business logic to the GUI file.

**Tech Stack:** Python 3.12, Tkinter, pytest, existing SQLite caches, no new runtime dependencies.

---

## Global Constraints

### Product / runtime (from `docs/INVARIANTS.md`)

- Tk UI thread must not block.
- Render path must not perform network, machine translation, Argos import/probe, ESI hydration, or large cache scans.
- ESI is optional and cache-first; network work is queued, bounded, rate-limited.
- Diagnostics must never include OAuth tokens, client secrets, API keys, or auth headers.
- Add-ons fail isolated and must not block the live feed.
- Portable ZIP stays lightweight; no admin/dev-tool requirements.
- Do not start Tauri/v3 work.

### Modularity (mandatory for this plan)

These rules override any earlier “leave business logic in the monolith” notes for **systems this plan touches**.

1. **One concern per module.** A module owns one subsystem (channels, monitor, filters, translation detect, highlight classification, etc.). No grab-bag “utils” dumps.
2. **Size budget.** Prefer **≤ ~400 lines** per new module; split before a file grows past **~500 lines**. Packages (`sb_contracts/`, `sb_translation/`) use multiple small files.
3. **GUI is wiring only.** When implementing a backlog feature, put pure logic + non-Tk I/O in a module first. `signal_bridge_gui.py` may only:
   - import and call module APIs
   - bind Tk widgets / Settings page shells
   - pass settings/state into modules
   - **not** gain new multi-screen business algorithms, parsers, or policy engines
4. **Extract-before-extend.** If a task needs code that currently lives in `signal_bridge_gui.py`, **move that code into a module in the same task (or a prerequisite task)** before changing behavior. Temporary re-exports in the GUI file are allowed for one transition commit, then call sites should import from the module.
5. **Dependency direction.**  
   `sb_contracts` ← pure domain modules ← optional I/O modules ← `signal_bridge_gui` / `sb_ui`  
   Never import `signal_bridge_gui` from a library module (no circular god import).
6. **Pure where possible.** Prefer stdlib-only pure functions for policy (filters, spam, highlight kind, language detect, channel catalog merge). Tk and network stay at edges.
7. **Tests live with the module.** `tests/test_<area>.py` imports the new module directly — not via spinning up `SignalBridgeGui` unless testing wiring.
8. **Do not expand systems we are not touching.** Leave `EveCatalog` / full `EsiResolver` / full `TranslationCache` in the monolith **until** a task needs them; if a task needs them, extract the **slice** used (not a 2k-line drive-by refactor).
9. **One logical commit per Task** (message given in the task). Prefer: `test → extract → behavior → wire UI` inside the task when needed.
10. After every task run:
    - `python -X utf8 -m py_compile` on every new/changed `.py`
    - `python -X utf8 scripts/check-fixtures.py`
    - `python -m pytest tests/ -q`
11. Update `ISSUES.md` + `CHANGELOG.md` when a user-facing issue closes.
12. Target product release after backlog: **v0.7**. Contracts alone are not a marketing bump.

---

## Status of related prior work

| Batch | Status | Notes |
|---|---|---|
| Phase 1–2 UI foundation | Done in v0.6 | `sb_ui/*`, SettingsShell, Pilot Info, Help/About |
| Phase 3.1 translation cache model | Done | stay in place; only extract helpers if Task 7 needs them |
| Phase 3.2–3.7 + channel + mojibake | Open | this plan |
| Target contracts | Spec only | Phase A–B |

## Open ISSUES.md items covered

| ID | Issue | Priority | Closed by | Primary module(s) |
|---|---|---|---|---|
| C1 | Contracts not runtime types | architecture | Tasks 1–5 | `sb_contracts/` |
| B1 | Channel chooser / tracking restore | high | Task 6 | `sb_channels.py` |
| B2 | Google auto-detect non-English | high | Task 7 | `sb_translation/` |
| B3 | Content + sender filters | high | Task 8 | `sb_filters.py` |
| B4 | Local spam / ASCII-art limits | high | Task 9 | `sb_filters.py` (spam section) or `sb_spam.py` if >400 lines |
| B5 | Backlog chat ingest | medium | Task 10 | `sb_monitor.py` |
| B6 | Ships purple on first load | medium | Task 11 | `sb_highlight.py` |
| B7 | Purple modules off by default | medium | Task 12 | `sb_appearance.py` |
| B8 | Mojibake literals | low | Task 13 | extract strip helpers → `sb_text.py` then fix |
| R1 | Absolute `DEFAULT_DB_PATH` | bug | Task 14 | `sb_paths.py` |
| R2 | Unbounded monitor `seen` | bug | Task 14 | `sb_monitor.py` |

---

## Locked modular file structure

Target layout after this plan (new or heavily used):

```text
sb_paths.py                      # APP/USER dirs, DEFAULT_DB_PATH, path helpers (no Tk)
sb_diagnostics.py                # write_log, write_jsonl, record_event/error, redaction bridge
sb_text.py                       # normalize/clean/strip helpers (fix mojibake once here)

sb_contracts/                    # pure display/domain contracts (stdlib only)
  __init__.py                    # re-exports only; keep thin
  intel_segment.py
  translation_decision.py
  render_row.py
  diagnostic_event.py            # redact + event shape
  addon_event.py
  pilot_info_snapshot.py
  adapters.py                    # legacy Row duck-type → contracts

sb_channels.py                   # discover, normalize, catalog merge, status labels
sb_monitor.py                    # MonitorThread, backlog window, bounded dedupe
sb_parse.py                      # OPTIONAL extract if Task 10/11 needs parse_rows without GUI
                                 # only create if monitor extract pulls parse with it

sb_translation/                  # translation edge (no Tk)
  __init__.py
  detect.py                      # has_cjk, has_non_english_signal, source lang choice
  google_free.py                 # google_translate_free (network, timeout)
  free_text.py                   # translate_free_text* orchestration using detect + cache APIs
  # Do NOT move entire TranslationCache class unless a later task requires it;
  # free_text may call into existing cache functions via injected callables or
  # a thin sb_translation/cache_api.py façade if import cycles appear.

sb_filters.py                    # FeedFilter model, row_is_filtered, settings normalize
sb_spam.py                       # SpamPolicy + SpamLimiter (split from filters if crowded)
sb_feed_admit.py                 # pure: should_admit_row(row, filters, limiter) → AdmitResult
                                 # single place queue-drain calls — keeps GUI thin

sb_highlight.py                  # highlight_kind_for_term, ship vs module vs ess
sb_appearance.py                 # DEFAULT_APPEARANCE, normalize_appearance, highlight_modules default

sb_ui/                           # existing + small page modules when UI is non-trivial
  theme.py / components.py / windows.py / settings_center.py / markdown_view.py
  filters_page.py                # Task 8–9 Settings Filters/Hygiene page builders
  channels_dialog.py             # Task 6 chooser dialog (optional if keeps GUI smaller)

signal_bridge_render_model.py    # pure visible_lines helpers (keep)
signal_bridge_gui.py             # Tk shell + wiring ONLY for touched features
sb_settings.py                   # existing SettingsStore
sb_help.py / sb_zkill.py         # existing

tests/
  test_contracts_*.py
  test_channels.py
  test_monitor.py
  test_translation_detect.py
  test_filters.py
  test_spam.py
  test_feed_admit.py
  test_highlight.py
  test_appearance_defaults.py
  test_paths.py
  test_text_mojibake.py
  fixtures/feed_cases.json
```

### What may stay in `signal_bridge_gui.py` (for now)

- `SignalBridgeGui` class: menus, feed widget, queue drain loop, monitor start/stop **calls**
- Legacy types/code not yet extracted (`EveCatalog`, full ESI stack, full `TranslationCache`) until a task requires a slice
- Settings page methods that only compose `sb_ui` builders

### Hard rule for agents

> If your change would add **>30 lines of non-UI logic** to `signal_bridge_gui.py`, **stop** and put it in the module listed above (create the module if missing).

### Import graph (allowed)

```text
sb_paths
sb_text
sb_contracts  (no project deps except optional signal_bridge_render_model for render_row)
sb_diagnostics → sb_contracts.diagnostic_event, sb_paths
sb_channels → sb_paths (optional)
sb_highlight  (pure)
sb_appearance (pure)
sb_filters / sb_spam / sb_feed_admit (pure)
sb_translation.* → sb_contracts.translation_decision; may call injected cache
sb_monitor → sb_channels helpers, parse entrypoints, sb_paths
sb_ui.* → sb_ui.theme/components only (+ callbacks)
signal_bridge_gui → all of the above
```

Forbidden: `sb_*` importing `signal_bridge_gui`.

---

## Design rules for contracts

1. Contract modules are **pure**: stdlib + typing only (exception: `render_row` may import `signal_bridge_render_model` only).
2. Builders accept duck-typed rows (`getattr`) so `Row` need not move on day one.
3. `schema_version: int = 1` on every serializable contract.
4. `build_render_row(...)` must not call network/MT/ESI.
5. Serialization helpers return JSON-friendly `dict`s.

---

## Phase 0 — Path + diagnostics extraction (unblocks clean modules)

### Task 0: `sb_paths` + `sb_diagnostics` (extract, no behavior change)

**Why first:** New modules need dirs/logging without importing the GUI.

**Files:**
- Create: `sb_paths.py`
- Create: `sb_diagnostics.py`
- Create: `tests/test_paths.py`
- Modify: `signal_bridge_gui.py` — re-export or replace definitions with imports from these modules (behavior identical)

**Interfaces:**

```python
# sb_paths.py
APP_DIR: Path
USER_DIR: Path
CONFIG_DIR, CACHE_DIR, DATA_DIR, LOG_DIR, MODULES_DIR, MODULE_DATA_DIR: Path
DEFAULT_DB_PATH: Path  # MUST be DATA_DIR / "translations.db" (fix absolute D:\ path here)

def ensure_app_dirs() -> None: ...

# sb_diagnostics.py
def write_log(message: str, exc: BaseException | None = None) -> None: ...
def write_jsonl(path: Path, event: dict) -> None: ...
def record_event(event_type: str, **data) -> None: ...
def record_error(context: str, exc: BaseException | None = None, **data) -> None: ...
```

- [ ] **Step 1: Write `tests/test_paths.py`**

```python
from sb_paths import DEFAULT_DB_PATH, DATA_DIR

def test_default_db_is_under_data_dir():
    assert DEFAULT_DB_PATH == DATA_DIR / "translations.db"
    assert not str(DEFAULT_DB_PATH).lower().startswith(r"d:\ai\rift")
```

- [ ] **Step 2: Implement modules by moving code; fix `DEFAULT_DB_PATH` to portable relative path (closes R1 early).**

- [ ] **Step 3: GUI imports from `sb_paths` / `sb_diagnostics`; delete duplicate bodies.**

- [ ] **Step 4: Full suite green.**

- [ ] **Step 5: Commit**

```text
refactor: extract sb_paths and sb_diagnostics; portable default DB path
```

---

## Phase A — Contract types (pure)

### Task 1: `sb_contracts` — IntelSegment + TranslationDecision

**Files:**
- Create: `sb_contracts/__init__.py`
- Create: `sb_contracts/intel_segment.py`
- Create: `sb_contracts/translation_decision.py`
- Create: `tests/test_contracts_intel_segment.py`
- Create: `tests/test_contracts_translation_decision.py`
- Modify: `signal_bridge_gui.py` — **only** if needed for a one-line compatibility alias; prefer **not** redefining `IntelSegment` yet (adapters use duck typing). Optional later: `from sb_contracts import IntelSegment as ContractIntelSegment`.

**Interfaces:**
- `@dataclass class IntelSegment` per `docs/contracts/intel-segment.md`
- `intel_segment_to_dict` / `intel_segment_from_legacy`
- `@dataclass class TranslationDecision` + `make_translation_decision` + `translation_decision_to_dict`

- [ ] **Step 1: Failing tests**

```python
# tests/test_contracts_intel_segment.py
from sb_contracts.intel_segment import IntelSegment, intel_segment_to_dict, intel_segment_from_legacy


def test_segment_defaults_and_dict():
    seg = IntelSegment(kind="kill", text="Akai Basilisk", systems=[], assets=["Basilisk"], pilots=["Akai"])
    d = intel_segment_to_dict(seg)
    assert d["kind"] == "kill"
    assert d["assets"] == ["Basilisk"]
    assert d["confidence"] == "medium"
    assert d["schema_version"] == 1


def test_from_legacy_duck_type():
    class Legacy:
        kind = "sighting"
        text = "Jita nv"
        systems = ["Jita"]
        assets = []
        pilots = []
        notes = ["VOICE"]
        status = ["NV"]
        confidence = "high"
    seg = intel_segment_from_legacy(Legacy())
    assert seg.kind == "sighting"
    assert seg.status == ["NV"]
```

```python
# tests/test_contracts_translation_decision.py
from sb_contracts.translation_decision import make_translation_decision, translation_decision_to_dict


def test_skipped_english_decision():
    d = make_translation_decision(
        decision="skipped", reason="english_only", engine="none",
        source_lang="en", target_lang="en",
    )
    out = translation_decision_to_dict(d)
    assert out["decision"] == "skipped"
    assert out["schema_version"] == 1
```

- [ ] **Step 2: Implement minimal pure modules (see prior plan detail — keep each file <150 lines).**

- [ ] **Step 3: Tests pass; commit**

```text
feat(contracts): add IntelSegment and TranslationDecision pure types
```

---

### Task 2: `sb_contracts` — RenderRow builder

**Files:**
- Create: `sb_contracts/render_row.py`
- Create: `sb_contracts/adapters.py`
- Create: `tests/test_contracts_render_row.py`
- Modify: `sb_contracts/__init__.py`
- **Do not** put builder logic in `signal_bridge_gui.py`.

**Interfaces:**
- `@dataclass class RenderRow` per `docs/contracts/render-row.md`
- `build_render_row(row, *, translated_only: bool, normalize) -> RenderRow`
- `row_id` = `r_` + sha1(channel|received_at|sender|text|file)[:16]

- [ ] **Step 1: Failing test with FakeRow (no GUI import)**

```python
from sb_contracts.render_row import build_render_row

class FakeSeg:
    kind = "message"; text = "Jita Caracal"; systems = ["Jita"]; assets = ["Caracal"]
    pilots = []; notes = []; status = []; confidence = "medium"

class FakeRow:
    channel = "Intel"; received_at = "2026-07-10 12:00:00"; sender = "Scout"
    text = "Jita Caracal"; free_translation = "Jita Caracal"; translation = "Jita Caracal"
    systems = ["Jita"]; assets = ["Caracal"]; links = []; counts = []; esi_entities = []
    segments = [FakeSeg()]; translation_source = "catalog"; file = "Intel_x.txt"

def test_build_render_row():
    rr = build_render_row(FakeRow(), translated_only=True, normalize=lambda s: s.strip())
    assert rr.channel == "Intel" and rr.visible_lines and rr.schema_version == 1
```

- [ ] **Step 2: Implement using `signal_bridge_render_model.visible_body_lines` only.**

- [ ] **Step 3: Commit**

```text
feat(contracts): add pure RenderRow builder
```

---

### Task 3: DiagnosticEvent + AddonEvent + PilotInfoSnapshot

**Files:**
- Create: `sb_contracts/diagnostic_event.py`
- Create: `sb_contracts/addon_event.py`
- Create: `sb_contracts/pilot_info_snapshot.py`
- Create: `tests/test_contracts_events.py`
- Modify: `sb_diagnostics.py` — call `redact_context` from contracts (keeps privacy in one place)
- **No** new logic in GUI except optional re-export of `make_intel_history_event` → contracts

**Interfaces:**
- `make_diagnostic_event`, `redact_context`, secret key fragments
- `row_to_addon_event(row) -> dict` (schema_version + current Intel History fields)
- `empty_pilot_info_snapshot(name, pilot_id) -> dict`

- [ ] **Step 1: Tests for redaction + addon shape + snapshot**

- [ ] **Step 2: Implement; wire redaction into `sb_diagnostics.record_event`**

- [ ] **Step 3: Commit**

```text
feat(contracts): diagnostic redaction, AddonEvent, PilotInfoSnapshot
```

---

## Phase B — Wire contracts (thin GUI)

### Task 4: Bridge add-on events + translation decision attachment

**Files:**
- Modify: `signal_bridge_gui.py` — replace `make_intel_history_event` body with:

```python
from sb_contracts.addon_event import row_to_addon_event as make_intel_history_event
```

  or a 2-line wrapper. Move worker decision assignment to call `make_translation_decision` from contracts.
- Prefer extracting translation worker **decision assignment** into `sb_translation/decisions.py` if worker block is large:

```python
# sb_translation/decisions.py
def decision_for_result(*, used: bool, reason: str, engine: str, ...) -> TranslationDecision: ...
```

- Create: `tests/test_translation_decisions.py` if extracted
- **Do not** paste decision construction inline across GUI methods.

- [ ] **Step 1: Wire addon event**
- [ ] **Step 2: Attach `row.translation_decision` only off render path (worker / admit)**
- [ ] **Step 3: Suite + smoke**
- [ ] **Step 4: Commit**

```text
feat(contracts): wire AddonEvent and TranslationDecision at edges
```

---

### Task 5: Feed render consumes RenderRow (GUI draw only)

**Files:**
- Modify: `signal_bridge_gui.py` `_render_row` — call `build_render_row`, draw `visible_lines` (widget code stays in GUI)
- Create: `tests/test_render_row_display.py` — pure fixture → `build_render_row` assertions (no Tk)
- Expand: `tests/fixtures/feed_cases.json` only as needed

**Isolation note:** Tagging/highlight application can still live in GUI for this task; classification policy moves in Task 11 (`sb_highlight`). Do not reimplement segmentation in GUI.

- [ ] **Step 1: Fixture tests via `build_render_row`**
- [ ] **Step 2: `_render_row` uses RenderRow**
- [ ] **Step 3: Commit**

```text
feat(contracts): feed render draws from RenderRow
```

---

## Phase C — High-priority backlog (module-first)

### Task 6: Channels system → `sb_channels.py` + chooser

**Extract then fix.**

**Files:**
- Create: `sb_channels.py` (move from GUI: `channel_from_filename`, `channel_sort_key`, `normalize_channel_name`, `discover_channel_metadata`, `discover_channels`, `default_channels`, pure `build_channel_catalog(active, hidden, tab_order, discovered) -> dict`)
- Create: `tests/test_channels.py`
- Create (optional if dialog stays large): `sb_ui/channels_dialog.py` — builds Toplevel; callbacks for add/replace
- Modify: `signal_bridge_gui.py` — thin wrappers: `self.channel_catalog()` → `build_channel_catalog(...)`; start_monitor uses restored active set
- Update: `ISSUES.md`, help if labels change

**Interfaces:**

```python
def normalize_channel_name(name: str) -> str: ...
def discover_channel_metadata(chatlog_dir: Path, limit_files: int = 500) -> dict[str, dict]: ...
def build_channel_catalog(
    *,
    chatlog_dir: Path,
    active_channels: set[str],
    hidden_tab_ids: set[str],
    tab_order: list[str],
    discovered: dict[str, dict] | None = None,
) -> dict[str, dict]:
    """Merge discovered + persisted; set status: tracking | tracking, waiting for log | hidden | discovered | saved, missing log."""

def catalog_summary(catalog: dict) -> dict:  # counts for diagnostics
    ...
```

- [ ] **Step 1: Move pure functions + tests (behavior parity)**
- [ ] **Step 2: Fix restore / empty-discovery / chooser list using catalog API**
- [ ] **Step 3: Emit `record_event("channel_catalog_summary", **catalog_summary(...))` via diagnostics module**
- [ ] **Step 4: GUI only wires Settings/dialog**
- [ ] **Step 5: Commit**

```text
refactor(channels): extract sb_channels and fix restore/chooser
```

---

### Task 7: Multi-language translation → `sb_translation/`

**Extract language detect + Google free + free-text orchestration; then enable auto source.**

**Files:**
- Create: `sb_translation/__init__.py`
- Create: `sb_translation/detect.py` — move `has_cjk`, `has_english_letters`, `has_non_english_signal`, `pick_google_source_lang(text, direction) -> str`
- Create: `sb_translation/google_free.py` — move `google_translate_free` (support `source="auto"` → `sl=auto`)
- Create: `sb_translation/free_text.py` — move `translate_free_text` / cached variants **or** thin wrappers that take cache callables to avoid importing monolith `TranslationCache`
- Create: `tests/test_translation_detect.py`
- Modify: existing `tests/test_translation_cache_model.py` only if gate imports move (update imports to new module)
- Modify: `signal_bridge_gui.py` — import public functions; delete moved bodies
- Update: ISSUES, `docs/help/04-translation.md`

**Cycle avoidance:** If `free_text` needs `TranslationCache` still in GUI:

```python
# free_text.py accepts optional hooks
def translate_free_text(..., cache_lookup=None, cache_put=None, ...):
```

GUI passes bound methods. Do **not** import `signal_bridge_gui` from `sb_translation`.

- [ ] **Step 1: Extract detect + tests (Russian / English / CJK)**
- [ ] **Step 2: Extract google_free with `sl=auto` support + tests (mock urlopen)**
- [ ] **Step 3: Wire free_text to use `pick_google_source_lang`; attach TranslationDecision via contracts**
- [ ] **Step 4: Commit**

```text
feat(translation): extract sb_translation and auto-detect non-English
```

---

### Task 8: Content + sender filters → `sb_filters` + `sb_feed_admit` + UI page

**Files:**
- Create: `sb_filters.py` — `FeedFilter`, `normalize_filters`, `filters_to_settings`, `row_is_filtered`
- Create: `sb_feed_admit.py` — `AdmitResult`, `should_admit_row(sender, text, channel, filters, spam_limiter=None) -> AdmitResult`
- Create: `tests/test_filters.py`, `tests/test_feed_admit.py`
- Create: `sb_ui/filters_page.py` — builds Filters settings body (list, add, delete, enable); **no** business rules
- Modify: `sb_settings` schema usage in GUI / settings schema dict — add `feed_filters: (list, [])` where SETTINGS_SCHEMA lives (**if schema stays in GUI, only add keys**; optional Task: move SETTINGS_SCHEMA to `sb_settings_schema.py` only if you already touch it)
- Modify: `signal_bridge_gui.py` drain path: ~5 lines calling `should_admit_row`
- Update: ISSUES, help

**Interfaces:**

```python
@dataclass
class FeedFilter:
    id: str
    kind: str  # keyword | sender
    pattern: str
    enabled: bool = True
    match_mode: str = "contains"  # contains | exact
    case_insensitive: bool = True

@dataclass
class AdmitResult:
    admit: bool
    reason: str  # allow | filter_keyword | filter_sender | spam_* 

def should_admit_row(...) -> AdmitResult: ...
```

- [ ] **Step 1: Pure filter tests**
- [ ] **Step 2: Implement `sb_filters` + `sb_feed_admit`**
- [ ] **Step 3: `sb_ui/filters_page.py` + GUI registers page + schema key**
- [ ] **Step 4: Drain uses admit helper; diagnostics counts via `record_event`**
- [ ] **Step 5: Commit**

```text
feat(filters): modular content/sender filters and admit pipeline
```

---

### Task 9: Spam limiting → `sb_spam.py` (or section of filters if still small)

**Files:**
- Create: `sb_spam.py` if `sb_filters.py` would exceed ~400 lines; else keep in `sb_filters.py` and document
- Create: `tests/test_spam.py`
- Modify: `sb_feed_admit.py` — integrate limiter
- Modify: `sb_ui/filters_page.py` — hygiene section (settings only)
- Modify: GUI — construct `SpamLimiter` from settings once; pass into admit
- Update: ISSUES

**Interfaces:**

```python
@dataclass
class SpamPolicy:
    enabled: bool = True
    local_channels_only: bool = True
    per_channel_max_per_minute: int = 30
    repeat_sender_window_seconds: int = 8
    repeat_sender_max: int = 3
    ascii_art_min_lines: int = 6
    ascii_art_symbol_ratio: float = 0.45

class SpamLimiter:
    def allow(self, channel: str, sender: str, text: str, *, systems: list[str] | None = None, now: float | None = None) -> tuple[bool, str]: ...
```

Intel preservation: if `systems` non-empty, do not ascii-art suppress.

- [ ] **Step 1: Unit tests (burst, ascii, intel exception)**
- [ ] **Step 2: Implement + admit integration**
- [ ] **Step 3: Settings UI in filters_page only**
- [ ] **Step 4: Commit**

```text
feat(spam): Local rate limit and ASCII-art suppression module
```

---

## Phase D — Medium backlog (module-first)

### Task 10: Monitor + backlog → `sb_monitor.py`

**Files:**
- Create: `sb_monitor.py` — move `MonitorThread`; implement `backlog_minutes: int = 0`, bounded dedupe (closes R2)
- Create: `tests/test_monitor.py` — dedupe eviction + backlog window selection with fake clocks/files where feasible
- If `parse_rows_from_text` must move with monitor: Create `sb_parse.py` for parse + row build **only as much as needed**; GUI re-exports for self_test
- Modify: GUI `start_monitor` passes settings; General settings controls for `replay_on_start` / `backlog_minutes`
- Update: ISSUES, help

**Interfaces:**

```python
class MonitorThread(threading.Thread):
    def __init__(self, outq, stop_event, status, channels, *, chatlog_dir: Path, db, backlog_minutes: int = 0, seen_limit: int = 5000): ...
```

Inject `chatlog_dir` and `db` — do not read GUI globals.

- [ ] **Step 1: Extract MonitorThread with injected deps + bounded seen tests**
- [ ] **Step 2: Backlog window + row cap (e.g. 200)**
- [ ] **Step 3: Settings wiring only in GUI / settings page**
- [ ] **Step 4: Commit**

```text
refactor(monitor): extract sb_monitor with backlog and bounded dedupe
```

---

### Task 11: Highlight classification → `sb_highlight.py`

**Files:**
- Create: `sb_highlight.py`
- Create: `tests/test_highlight.py`
- Modify: GUI render tagging path to call `highlight_kind_for_term(term, catalog_view)` — no classification if/else trees in GUI
- Update: ISSUES

**Interfaces:**

```python
def highlight_kind_for_term(term: str, *, ship_terms: set[str], module_terms: set[str], ess_terms: set[str] | None = None) -> str:
    """Return 'ship' | 'module' | 'ess' | 'other'. Ships win over module."""
```

Catalog view is plain sets injected from GUI/catalog — keep `sb_highlight` free of `EveCatalog` class dependency if possible.

- [ ] **Step 1: Tests Caracal/Retribution → ship not module**
- [ ] **Step 2: Implement + wire first paint path**
- [ ] **Step 3: Commit**

```text
fix(highlight): ship-vs-module classification module
```

---

### Task 12: Appearance defaults → `sb_appearance.py`

**Files:**
- Create: `sb_appearance.py` — `DEFAULT_APPEARANCE`, `normalize_appearance`, presets constants
- Create: `tests/test_appearance_defaults.py`
- Modify: GUI — import defaults; Appearance checkbox for `highlight_modules`
- Render path: if not `highlight_modules`, skip module tag
- Update: ISSUES

```python
DEFAULT_APPEARANCE = {
    ...
    "highlight_modules": False,
}
```

- [ ] **Step 1: Test missing key → False**
- [ ] **Step 2: Extract + wire**
- [ ] **Step 3: Commit**

```text
fix(appearance): extract defaults; modules highlight off by default
```

---

### Task 13: Mojibake → `sb_text.py`

**Files:**
- Create: `sb_text.py` — `strip_term_punctuation`, `truncate_label`, `normalize_feed_text` (move)
- Create: `tests/test_text_mojibake.py` — asserts correct curly quotes + ellipsis; scan GUI for `â€` / `\ufffd` if still present
- Modify: GUI — import helpers; fix any remaining literals by deletion
- Update: ISSUES

- [ ] **Step 1: Extract + fix strip sets to use `\u201c\u201d\u2018\u2019` and `…`**
- [ ] **Step 2: Repo scan test**
- [ ] **Step 3: Commit**

```text
fix(text): extract sb_text and repair mojibake literals
```

---

### Task 14: Paths/dedupe verification (if not fully done in 0 + 10)

**Files:**
- Verify: `sb_paths.DEFAULT_DB_PATH` portable
- Verify: `sb_monitor` bounded seen
- Create/adjust: `tests/test_paths.py`, `tests/test_monitor.py`
- Remove any leftover absolute path constants in GUI

- [ ] **Step 1: Grep for `D:\\AI\\Rift` and `translations.db` absolute paths — must be zero**
- [ ] **Step 2: Confirm tests cover eviction**
- [ ] **Step 3: Commit only if fixes remain**

```text
fix: ensure portable paths and bounded monitor dedupe
```

---

## Phase E — Docs + size audit

### Task 15: Documentation + modularity audit

**Files:**
- Modify: `docs/ARCHITECTURE.md` — module map + dependency rules
- Modify: `docs/PROJECT_MAP.md` — list new modules; version note
- Modify: `ROADMAP.md` — 3.2–3.7 / contracts status
- Modify: `docs/contracts/*.md` — “Implemented in `sb_contracts/...`”
- Modify: `CHANGELOG.md`, `ISSUES.md`
- Optional: add `docs/superpowers/specs/2026-07-10-module-map.md` one-pager if ARCHITECTURE is crowded

**Audit checklist (must pass):**

```powershell
# Rough line counts — flag any new module > 500 lines
Get-ChildItem sb_*.py,sb_contracts\*.py,sb_translation\*.py,sb_ui\filters_page.py,sb_ui\channels_dialog.py -ErrorAction SilentlyContinue |
  ForEach-Object { "{0,5} {1}" -f (Get-Content $_.FullName | Measure-Object -Line).Lines, $_.Name }

python -X utf8 -m py_compile signal_bridge_gui.py sb_paths.py sb_diagnostics.py sb_text.py sb_channels.py sb_monitor.py sb_filters.py sb_spam.py sb_feed_admit.py sb_highlight.py sb_appearance.py
python -X utf8 -m compileall sb_contracts sb_translation
python -X utf8 scripts/check-fixtures.py
python -m pytest tests/ -v
```

**GUI growth rule for PR review:** net new non-comment lines in `signal_bridge_gui.py` for this whole plan should trend **flat or down**. Feature work that only added lines to the GUI is a plan violation — extract before merge.

**Manual smoke:** channels restore, multi-lang translate, filters, spam, backlog, ship color, module default, Intel History events, diagnostics redaction.

- [ ] **Step 1: Docs**
- [ ] **Step 2: Audit + suite**
- [ ] **Step 3: Commit**

```text
docs: module map for contracts and v0.7 backlog
```

---

## Execution order

```text
Task 0          paths + diagnostics extract (enables clean imports)
Tasks 1 → 5     contracts (pure) + thin wire
Task 6          sb_channels
Task 7          sb_translation
Tasks 8 → 9     sb_filters / sb_spam / sb_feed_admit / sb_ui.filters_page
Task 10         sb_monitor (+ optional sb_parse)
Tasks 11 → 12   sb_highlight / sb_appearance
Task 13         sb_text mojibake
Task 14         verify R1/R2
Task 15         docs + audit
```

Parallel-safe after Task 0: Task 1–3 (contracts) || early extract of `sb_text` (Task 13) if needed.

## Out of scope

- Full extraction of `EveCatalog`, `EsiResolver`, entire `TranslationCache`, all Settings pages
- LAN viewer, Argos helper process, Tauri/v3
- Regex filter modes (API can extend later)
- Drive-by refactors of systems not listed above

## Success criteria

1. All six contract areas exist under `sb_contracts/` with direct unit tests.
2. Each touched backlog system has a **named module**; GUI only wires.
3. No new module > ~500 lines without a split.
4. `signal_bridge_gui.py` line count does not grow by feature logic (prefer decrease).
5. No `sb_*` imports of `signal_bridge_gui`.
6. All listed ISSUES closed with summaries.
7. `pytest` + fixtures green; portable DB path; bounded monitor dedupe.
8. ARCHITECTURE/PROJECT_MAP document the module map.

---

## Self-review

| Requirement | Module / Task |
|---|---|
| Keep files isolated & small | Global modularity rules + Phase 0 + per-task extract-first |
| Contracts runtime | Tasks 1–5, `sb_contracts/` |
| Channels issue | Task 6, `sb_channels.py` |
| Multi-lang | Task 7, `sb_translation/` |
| Filters / spam | Tasks 8–9, `sb_filters` / `sb_spam` / `sb_feed_admit` / `sb_ui/filters_page` |
| Backlog ingest | Task 10, `sb_monitor` |
| Ship purple / module default | Tasks 11–12, `sb_highlight` / `sb_appearance` |
| Mojibake | Task 13, `sb_text` |
| DB path / seen | Tasks 0, 10, 14 |
| Avoid god-file churn | “>30 lines non-UI logic → module” rule |

Types/names consistent: `FeedFilter`, `AdmitResult`, `SpamPolicy`, `SpamLimiter`, `RenderRow`, `TranslationDecision`, `build_channel_catalog`, `highlight_kind_for_term`.
