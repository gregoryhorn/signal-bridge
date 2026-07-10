# Repo-wide Void Tactical UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved Pilot Info Mockup A design language consistently to every Signal Bridge desktop and LAN UI surface without changing product behavior.

**Architecture:** Keep Python 3.12 and Tkinter. Make `sb_ui.theme`, shared components, and window helpers the only visual primitives; extract Settings page layout from `signal_bridge_gui.py` as each page is restyled. Export the same semantic theme contract to `web_lan` so desktop and phone views share identity without sharing widget code.

**Tech Stack:** Python 3.12, Tkinter/ttk, HTML/CSS/JavaScript for the LAN viewer, pytest, Pillow `ImageGrab` for Windows screenshot verification.

## Global Constraints

- Visual sources of truth are `docs/images/signal-bridge-v0.7-theme-mockup-a.png`, `docs/images/pilot-info-v0.7-mockup-a.png`, and `docs/superpowers/specs/2026-07-10-v0.7-void-tactical-theme.md`.
- Include all desktop surfaces and `web_lan`; light mode and alternate themes remain out of scope.
- Keep parsing, translation, ESI, zKill, monitoring, add-on, tab-state, and LAN security behavior unchanged.
- Never perform network or blocking disk work on the Tk render path.
- No hard-coded UI hex colors outside `sb_ui/theme.py`; user-editable appearance preset values are data and remain allowed in `signal_bridge_gui.py`.
- Use the spacing scale `4 / 8 / 12 / 16 / 24` and semantic type roles from the approved theme spec.
- One cyan scan line marks the active locus on a surface. Do not add cyan decoration to every section.
- Use color plus text or icon for status. Never communicate threat, error, or success by color alone.
- Preserve keyboard operation, visible focus, Windows scaling, minimum-window behavior, and screen clamping.
- Child windows open beside the main feed when space exists; modal dialogs may overlap their parent but must remain fully visible.
- Re-rendering content may resize a window but must preserve the user-moved position.
- `signal_bridge_gui.py` remains wiring. Extract a UI builder before materially restyling a large inline widget tree.
- Do not change `APP_VERSION` or rebuild the portable package until a separate release task is approved.
- Every visual task produces before/after evidence under `docs/images/ui-review/` and a short result in the surface matrix.
- Every task ends with focused tests, `python -X utf8 scripts/check-fixtures.py`, and `python -m pytest tests/ -q`.

---

## Approved design contract

### Visual identity

- **Surfaces:** deep void background, restrained elevated navy panels, thin blue-gray separators.
- **Active signature:** one cyan scan line with a soft endpoint glow.
- **Information hierarchy:** identity or task title, status ribbon, primary data, supporting detail, fixed actions.
- **Typography:** Segoe UI for interface copy; Consolas for timestamps, IDs, counts, and compact operational data.
- **Entity colors:** systems gold, ships orange, pilots coral, links blue, counts violet.
- **Density:** compact operational layouts with deliberate breathing room; no large empty canvases or repeated card grids.
- **Actions:** one obvious primary action, up to two visible secondary actions, overflow for tertiary actions.
- **States:** loading, empty, error, warning, disabled, syncing, success, and disconnected states each explain the next action.

### Surface inventory

1. Main window: menu, title/status chrome, channel tabs, feed, translated sublines, context menus, footer status.
2. Pilot Info: summary, local sightings, zKill states, flags, activity subview, footer actions.
3. Settings Center: shell plus 16 pages.
4. Standalone windows: hidden-tab restore, channel chooser, feed-font chooser, prompt, Appearance, ESI/OAuth, Recognition Rules, Help, About.
5. System feedback: message boxes, warnings, confirmations, update notice, empty and failed states.
6. LAN viewer: header, connection status, filters, feed rows, empty/disconnected states, footer.

---

### Task 1: Freeze the UI surface contract and baseline evidence

**Files:**
- Create: `docs/ui/void-tactical-surface-matrix.md`
- Create: `scripts/capture_ui_review.py`
- Create: `tests/test_ui_surface_contract.py`
- Reference: `docs/images/pilot-info-v0.7-mockup-a.png`

**Interfaces:**
- Produces `SURFACE_CASES: tuple[SurfaceCase, ...]` in `scripts/capture_ui_review.py`.
- Each `SurfaceCase` contains `key`, `open_surface(app)`, `target_size`, and `output_name`.
- The matrix records owner file, states, minimum size, primary action, screenshot path, and approval status.

- [ ] **Step 1: Write the failing contract test.** Assert that the registry covers `main`, `pilot-empty`, `pilot-synced`, `settings-general`, all 16 Settings page keys, each standalone window, `lan-connected`, and `lan-disconnected`.
- [ ] **Step 2: Run the contract test.**

  Run: `python -m pytest tests/test_ui_surface_contract.py -q`

  Expected: FAIL because `SURFACE_CASES` and the matrix do not exist.

- [ ] **Step 3: Add the registry and matrix.** The capture script must instantiate the GUI without starting `mainloop`, open a named surface using fixture data, call `update_idletasks()`, and capture only the target window with Pillow `ImageGrab`.
- [ ] **Step 4: Capture the current baseline.**

  Run: `python -X utf8 scripts/capture_ui_review.py --all --output docs/images/ui-review/before`

  Expected: one PNG per registered desktop surface and an explicit `SKIPPED` record only for a surface that requires unavailable OS state.

- [ ] **Step 5: Verify and commit.**

  Run: `python -m pytest tests/test_ui_surface_contract.py -q`

  Commit: `test(ui): inventory surfaces and capture visual baseline`

---

### Task 2: Complete the semantic theme and component foundation

**Files:**
- Modify: `sb_ui/theme.py`
- Modify: `sb_ui/components.py`
- Modify: `sb_ui/markdown_view.py`
- Create: `tests/test_ui_theme_contract.py`
- Create: `tests/test_ui_components.py`

**Interfaces:**
- `theme.semantic_color(role: str) -> str`
- `components.section(parent, title, note=None, tone="normal")`
- `components.status_ribbon(parent, text, tone="info")`
- `components.chip(parent, text, kind="neutral")`
- `components.empty_state(parent, title, guidance, action_text=None, command=None)`
- `components.toolbar(parent)` and `components.footer(parent)`
- `components.data_table(parent, columns, rows=())`

- [ ] **Step 1: Write failing theme tests.** Require semantic roles for focus, disabled, info, success, warning, error, threat-high, threat-medium, system, ship, pilot, link, and count; require `export_theme_dict()` to expose the same roles.
- [ ] **Step 2: Write failing component smoke tests.** Build every shared component under Tk and assert labels, tone text, focus highlight, and primary-action placement.
- [ ] **Step 3: Run focused tests.**

  Run: `python -m pytest tests/test_ui_theme_contract.py tests/test_ui_components.py -q`

  Expected: FAIL on missing roles and builders.

- [ ] **Step 4: Implement the semantic API.** Extend the approved palette rather than introducing a second palette. Replace the markdown link literal with `entity_link`.
- [ ] **Step 5: Migrate existing `card`, `danger_card`, buttons, tables, labels, chips, and ribbon builders onto the new primitives while preserving their public call signatures.
- [ ] **Step 6: Add a source check.** Fail when a new UI hex literal appears outside `sb_ui/theme.py`, excluding serialized user appearance preset dictionaries.
- [ ] **Step 7: Verify and commit.**

  Run: `python -m pytest tests/test_ui_theme_contract.py tests/test_ui_components.py tests/test_appearance_defaults.py -q`

  Commit: `style(ui): establish Void Tactical semantic components`

---

### Task 3: Standardize window chrome, placement, and resizing

**Files:**
- Modify: `sb_ui/windows.py`
- Modify: `signal_bridge_gui.py` thin wrapper `polish_window`
- Modify: `tests/test_windows.py`

**Interfaces:**
- `WindowPlacementPolicy = Literal["beside_parent", "center_parent", "remember"]`
- `polish_window(..., placement="beside_parent", preserve_position=False)`
- `fit_to_content(..., preserve_position=True)`
- `place_beside_parent(win, parent, preferred=("right", "left", "below")) -> tuple[int, int]`

- [ ] **Step 1: Add failing geometry tests.** Cover right-side placement, left fallback, same-monitor clamping, modal centering, and position preservation after `fit_to_content`.
- [ ] **Step 2: Run the focused test.**

  Run: `python -m pytest tests/test_windows.py -q`

  Expected: FAIL because placement policies do not exist and current autosizing recenters.

- [ ] **Step 3: Implement placement as pure geometry calculations plus thin Tk application.** Keep monitor bounds injectable so tests do not depend on the developer desktop.
- [ ] **Step 4: Make non-modal companion windows use `beside_parent`; keep destructive confirmations and prompts centered and modal.
- [ ] **Step 5: Verify the Pilot Info sync path keeps the moved coordinates before, during, and after sync render callbacks.
- [ ] **Step 6: Verify and commit.**

  Run: `python -m pytest tests/test_windows.py tests/test_pilot_info_ui.py -q`

  Commit: `fix(ui): unify child-window placement and preserve moved geometry`

---

### Task 4: Apply the concept to the main shell, feed, tabs, and menus

**Files:**
- Modify: `sb_ui/shell/main_chrome.py`
- Modify: `sb_ui/shell/layout.py`
- Modify: `sb_ui/feed/text_tags.py`
- Modify: `sb_ui/tabs/strip.py`
- Modify: `sb_ui/tabs/menu.py`
- Modify: `sb_ui/tabs/overflow.py`
- Modify: `signal_bridge_gui.py` wiring and context-menu style only
- Create: `tests/test_shell_layout.py`
- Modify: `tests/test_tabs_ui.py`

**Interfaces:**
- `build_header_bar()` exposes title, mode, monitoring state, and status handles.
- `build_main_layout()` exposes header, tabs, feed, and footer/status hosts.
- `TabStrip.set_tabs()` remains the only tab rendering entry point.

- [ ] **Step 1: Add failing shell tests.** Assert one active scan line, readable monitoring state, footer fields for LAN/channel count/translation mode, and no duplicate status string.
- [ ] **Step 2: Add failing tab tests.** Assert active underline, inactive unread badge, close affordance only when closable, overflow, and keyboard focus.
- [ ] **Step 3: Restyle the shell to match Mockup A.** Keep the feed dominant, remove decorative boxes, and use entity colors only inside feed semantics.
- [ ] **Step 4: Render translated sublines with an indented left scan edge and muted text while preserving copy behavior.
- [ ] **Step 5: Route feed and tab context menus through shared menu colors; remove inline menu literals.
- [ ] **Step 6: Capture `main-empty`, `main-live`, `tabs-overflow`, and `translated-dual-line` after screenshots.
- [ ] **Step 7: Verify and commit.**

  Run: `python -m pytest tests/test_shell_layout.py tests/test_tabs_ui.py tests/test_tabs_state.py -q`

  Commit: `style(ui): apply Void Tactical hierarchy to shell feed and tabs`

---

### Task 5: Implement the approved Pilot Info Mockup A

**Files:**
- Modify: `sb_ui/pilot/card.py`
- Modify: `sb_ui/pilot/sections.py`
- Modify: `sb_ui/pilot_info.py` pure formatting helpers only
- Modify: `tests/test_pilot_info_ui.py`
- Modify: `tests/test_pilot_domain.py`
- Modify: `docs/help/07-pilot-info.md`
- Reference: `docs/images/pilot-info-v0.7-mockup-a.png`

**Interfaces:**
- `render_identity_header()` produces name, corp/alliance, ID, threat ribbon, and one last-sighting line.
- `render_snapshot_strip()` omits empty groups.
- `render_local_timeline(limit=3)` renders aligned time/system/ship/note columns.
- `render_zkill_block()` renders explicit not-synced, syncing, failed, or synced states.
- `render_footer()` exposes one primary, two secondary, overflow, and Close.

- [ ] **Step 1: Add failing structure tests.** Assert the default summary contains one threat ribbon, no raw zKill URL, no duplicate Summary/Patterns blocks, maximum three local rows, and a single primary action.
- [ ] **Step 2: Add failing state tests.** Cover empty, syncing, failed, and synced zKill data; confirm each state contains useful guidance and no empty list headers.
- [ ] **Step 3: Implement the approved information hierarchy exactly.** Use the mockup text density and palette but bind real view-model values.
- [ ] **Step 4: Keep Flags and Activity as in-window subviews with a chrome-level back control; do not create another Toplevel.
- [ ] **Step 5: Use Task 3 placement and preserve coordinates through Sync zKill.
- [ ] **Step 6: Capture empty and synced screenshots and compare against the approved mockup for hierarchy, not pixel identity.
- [ ] **Step 7: Verify and commit.**

  Run: `python -m pytest tests/test_pilot_info_ui.py tests/test_pilot_domain.py -q`

  Commit: `feat(ui): implement approved Void Tactical Pilot Info card`

---

### Task 6: Rebuild the Settings shell around task-focused navigation

**Files:**
- Modify: `sb_ui/settings_center.py`
- Create: `sb_ui/settings/__init__.py`
- Create: `sb_ui/settings/registry.py`
- Modify: `signal_bridge_gui.py` Settings wiring only
- Modify: `tests/test_settings_center.py`
- Create: `tests/test_settings_registry.py`

**Interfaces:**
```python
@dataclass(frozen=True)
class SettingsPageSpec:
    key: str
    title: str
    description: str
    group: str
    render: Callable

def build_settings_page_specs(app) -> tuple[SettingsPageSpec, ...]: ...
```

- [ ] **Step 1: Add failing registry tests.** Require all 16 existing pages exactly once and group them as `Monitor`, `Translation`, `Intel`, `Data`, and `Support`.
- [ ] **Step 2: Add failing shell tests.** Require group labels, active scan line, fixed footer, visible dirty/saved/failed status, scroll restoration per page, and keyboard navigation.
- [ ] **Step 3: Replace parallel page/description/renderer dictionaries with `SettingsPageSpec` while preserving old deep links such as `Exclusions` to `Recognition Rules`.
- [ ] **Step 4: Apply the Pilot mockup hierarchy to Settings: title and status first, one primary task per page, restrained sections, destructive actions isolated at the end.
- [ ] **Step 5: Capture default 860×620 and minimum 640×480 screenshots for navigation and a long page.
- [ ] **Step 6: Verify and commit.**

  Run: `python -m pytest tests/test_settings_center.py tests/test_settings_registry.py tests/test_settings_pages_smoke.py -q`

  Commit: `refactor(ui): introduce task-focused Void Tactical Settings shell`

---

### Task 7: Migrate all 16 Settings pages in three verified batches

**Files:**
- Create: `sb_ui/settings/general.py`, `channels.py`, `appearance.py`
- Create: `sb_ui/settings/translation.py`, `translation_cache.py`, `filters.py`, `recognition.py`
- Create: `sb_ui/settings/catalog.py`, `aliases.py`, `esi.py`, `addons.py`, `data.py`, `diagnostics.py`, `support.py`
- Reuse: `sb_ui/pilot/settings_page.py`, `sb_ui/lan_page.py`
- Modify: `signal_bridge_gui.py` delegates only
- Modify: `tests/test_settings_pages_smoke.py`

**Interfaces:**
- Every module exports `render_page(body, shell, app) -> None`.
- Page modules may call app callbacks but may not perform network work or persistence directly during render.

- [ ] **Step 1: Batch A tests and migration.** Move General, Channels, and Appearance; assert each page has one primary task, one status area, and no local style literals.
- [ ] **Step 2: Batch A verification and commit.**

  Commit: `refactor(settings): migrate monitor and appearance pages`

- [ ] **Step 3: Batch B tests and migration.** Move Translation, Translation Cache, Filters, and Recognition Rules. Preserve cache/correction behavior and keep English correction visually primary.
- [ ] **Step 4: Batch B verification and commit.**

  Commit: `refactor(settings): migrate translation and recognition pages`

- [ ] **Step 5: Batch C tests and migration.** Move Catalog, Aliases, ESI, Pilot Intel, LAN Viewer, Add-ons, Cache & Data, Diagnostics, and About / Support. Keep destructive actions in danger sections and make live status readable before actions.
- [ ] **Step 6: Batch C verification and commit.**

  Commit: `refactor(settings): migrate intel data and support pages`

- [ ] **Step 7: Run all Settings smoke tests and capture every page at default size.**

  Run: `python -m pytest tests/test_settings_center.py tests/test_settings_registry.py tests/test_settings_pages_smoke.py -q`

  Expected: 16 pages rendered, no exceptions, no missing registry entries.

---

### Task 8: Unify standalone dialogs, Help, About, prompts, and feedback states

**Files:**
- Create: `sb_ui/dialogs.py`
- Modify: `sb_ui/markdown_view.py`
- Modify: `signal_bridge_gui.py` dialog delegates
- Create: `tests/test_dialogs.py`
- Modify: `tests/test_help_content.py`

**Interfaces:**
- `open_list_dialog(...)`, `open_form_dialog(...)`, `open_confirmation(...)`, and `open_status_dialog(...)` own common chrome and footer hierarchy.
- Existing public app methods remain as thin delegates so menu callbacks do not change.

- [ ] **Step 1: Add failing dialog tests.** Cover title hierarchy, modal behavior, one primary action, Escape/Enter bindings, minimum geometry, focus order, and beside-parent versus centered policy.
- [ ] **Step 2: Migrate hidden tabs, channel chooser, font chooser, simple prompt, Appearance, ESI/OAuth, Recognition Rules, Help, and About without changing callback semantics.
- [ ] **Step 3: Replace vague message text with action-oriented states while preserving meaning: identify what happened and the next safe action.
- [ ] **Step 4: Route all menu and dialog styling through theme/components; leave user appearance color values untouched.
- [ ] **Step 5: Capture every dialog from the Task 1 registry, including minimum-size and validation-error states.
- [ ] **Step 6: Verify and commit.**

  Run: `python -m pytest tests/test_dialogs.py tests/test_help_content.py tests/test_settings_pages_smoke.py -q`

  Commit: `style(ui): unify dialogs help and feedback states`

---

### Task 9: Bring the LAN viewer to visual and semantic parity

**Files:**
- Modify: `sb_ui/theme.py` export only
- Modify: `sb_lan/theme_css.py`
- Modify: `web_lan/index.html`
- Modify: `web_lan/styles.css`
- Modify: `web_lan/app.js`
- Modify: `tests/test_lan_theme_css.py`
- Modify: `tests/test_lan_serialize.py`

**Interfaces:**
- `export_theme_dict()` remains the single palette source.
- LAN row JSON continues to expose semantic classes for system, ship, pilot, link, count, sender, timestamp, and translated text.

- [ ] **Step 1: Add failing parity tests.** Require every exported semantic color as a CSS variable and require connected, reconnecting, disconnected, empty, and live states in markup or JavaScript.
- [ ] **Step 2: Apply the same hierarchy at phone density.** Keep feed-first composition, compact header/status, real channel filters, translated subline scan edge, and restrained footer.
- [ ] **Step 3: Preserve accessibility.** Provide visible focus, 44px touch targets for filters/actions, text labels for connection state, and reduced-motion behavior.
- [ ] **Step 4: Verify responsive widths at 360, 390, 768, and desktop 1280 CSS pixels using the local LAN server fixture.
- [ ] **Step 5: Verify and commit.**

  Run: `python -m pytest tests/test_lan_theme_css.py tests/test_lan_serialize.py tests/test_lan_server.py tests/test_lan_security.py -q`

  Commit: `style(lan): apply Void Tactical UI parity to phone viewer`

---

### Task 10: Accessibility, visual acceptance, documentation, and release gate

**Files:**
- Modify: `docs/ui/void-tactical-surface-matrix.md`
- Modify: `docs/superpowers/specs/2026-07-10-v0.7-void-tactical-theme.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `ISSUES.md`
- Create: `docs/images/ui-review/after/` screenshots

- [ ] **Step 1: Run the complete screenshot registry.**

  Run: `python -X utf8 scripts/capture_ui_review.py --all --output docs/images/ui-review/after`

  Expected: every desktop registry case captured with no clipping; any OS-dependent skip is recorded in the matrix with a manual verification result.

- [ ] **Step 2: Perform the visual acceptance checklist.** For every surface confirm one active scan line, clear primary action, no unexplained empty area, no clipped controls, readable status, and correct entity color semantics.
- [ ] **Step 3: Perform keyboard and scaling checks.** Verify Tab/Shift+Tab, Enter/Escape, 100% and 150% Windows scaling, default and minimum sizes, and high-contrast readability.
- [ ] **Step 4: Run source guards.** Confirm no new UI hex literals outside the theme and no direct large Tk layout trees were added to `signal_bridge_gui.py`.
- [ ] **Step 5: Update docs.** Record screenshot paths and approval results, replace stale UI screenshots, describe the new window placement, and close the three active Pilot Info/window issues only when their acceptance criteria have been live-proven.
- [ ] **Step 6: Run the full verification gate.**

  Run:

  ```powershell
  python -X utf8 -m py_compile signal_bridge_gui.py sb_ui\theme.py sb_ui\components.py sb_ui\windows.py
  python -X utf8 scripts/check-fixtures.py
  python -m pytest tests/ -q
  git diff --check
  ```

  Expected: all commands exit 0; the exact pytest pass count is recorded in the handoff.

- [ ] **Step 7: Commit.**

  Commit: `docs(ui): complete Void Tactical visual acceptance`

---

## Rollout order and approval gates

1. Tasks 1–3 establish evidence, components, and safe window behavior.
2. Task 4 modernizes the daily-use shell.
3. Task 5 implements the already-approved Pilot Info mockup.
4. Tasks 6–8 migrate Settings and every remaining desktop surface.
5. Task 9 aligns the LAN viewer after desktop semantics are stable.
6. Task 10 is the product-wide visual approval gate; packaging remains separate.

Stop after each numbered task for screenshot review. A rejected visual slice is corrected before later surfaces consume it.

## Definition of done

- Every surface in the matrix has an approved after screenshot.
- Desktop and LAN consume the same semantic theme export.
- The approved Pilot Info hierarchy is implemented without duplicated facts.
- The main feed remains visible when non-modal companion windows open.
- Content refreshes do not move user-positioned windows.
- All 16 Settings pages and standalone dialogs use shared components and action hierarchy.
- No new visual literals exist outside the theme source.
- Focus, keyboard, scaling, empty, loading, error, and disconnected states are verified.
- Full tests, fixture checks, compilation, and `git diff --check` pass.
- Version bump, packaging, and release publication remain a separately approved operation.
