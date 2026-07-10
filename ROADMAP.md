# Signal Bridge Roadmap — path to 1.0

**Status:** Direction set 2026-07-10 (post-v0.6)  
**Current public release:** v0.6  
**Next public cut:** **v0.7** = all four pillars below  
**Implementation plan:** [`docs/superpowers/plans/2026-07-10-v0.7-four-pillars.md`](docs/superpowers/plans/2026-07-10-v0.7-four-pillars.md) (modular file map + task phases)  
**Later:** v0.8+ harden · **v1.0** = recommendable / no P0 caveats

This file is the **product** forward plan. Historical release notes live in `CHANGELOG.md`.

---

## Guiding principles (unchanged)

- Lightweight, portable Windows side-panel tool  
- Never block live chat rendering (no network/MT on the Tk UI thread)  
- Live-only monitoring by default  
- Network features opt-in and visible  
- Prefer local EVE data for EVE terms; machine translation for free text only  

---

## v0.7 product pillars (decided)

These four items are **the v0.7 release scope**. They also define the product bar toward 1.0; post-0.7 is harden/polish, not a second round of these pillars.

### 1. Full look-and-feel update

**Problem:** Current UI does not meet modern desktop standards (dense prototype chrome, inconsistent density, dated feed/chrome).

**Goal:** A cohesive visual system for the **main shell**, feed, tabs, dialogs, and Settings — not another partial Settings polish only.

| In scope | Out of scope for 1.0 |
|----------|----------------------|
| Typography, spacing, surfaces, elevation/borders | Full Tauri/web rewrite |
| Main window chrome (header, status, feed) | Theme marketplace |
| Shared `sb_ui` theme as single source of truth | Click-through game overlay |
| Dark tactical aesthetic that still reads in fleet | Per-channel themes |
| New screenshots for README/release | Pixel-perfect OS native controls |

**Acceptance (v0.7):**

- One visual language across main feed, tabs, Pilot surfaces, Settings, and dialogs  
- No “random hex / ad-hoc packing” on new surfaces  
- README screenshot reflects the new look  
- Visual review pass (before/after) required for the main shell  

**Approach:** Keep Python/Tk stack; invest in `sb_ui/theme` + layout components + main-shell redesign (same decision as the 2026-07 UI foundation: rebuild on foundation, don’t migrate frameworks for 1.0).

---

### 2. Tabs that act like tabs

**Problem:** Channel “tabs” / mobile channel bar do not behave like real tab controls (selection, order, close, overflow, unread, keyboard expectations).

**Goal:** Channel switching feels like a normal multi-document tab strip (or a deliberate, polished compact strip that still **behaves** correctly).

| Required behavior |
|-------------------|
| Clear active / inactive / hover / unread states |
| Click selects; active channel owns the feed view |
| **All** stays pinned first when present |
| Close channel, close others, close all (context menu) |
| Drag reorder (persist `tab_order`) |
| Overflow when many channels (scroll or overflow menu — pick one, implement fully) |
| Long names truncate with tooltip / full name on hover |
| Hidden-tab restore still works |
| No layout jank when adding/removing channels during live monitor |

**Acceptance (v0.7):**

- Manual smoke: open many channels, reorder, close, restore, unread badges, All vs single channel  
- No tab-bar reflow bugs that steal clicks from the feed  

---

### 3. Pilot intel as a first-class feature

**Problem:** Pilot Info / Intel History still feel like add-on-adjacent extras, not a core fleet tool.

**Goal:** Pilot intelligence is a **primary product surface**, not a bolted-on card.

| First-class means |
|-------------------|
| Obvious entry points from feed (click / right-click) with reliable targeting |
| Dedicated Pilot / Intel area in IA (menu and/or Settings nav — not buried only under Add-ons) |
| Coherent model: local snapshot + flags + sightings + zKill sync story |
| Intel History treated as core capability in v0.7 (may still use add-on package plumbing, but product language is first-class) |
| Empty, loading, error, and offline states are designed, not afterthoughts |
| Hot-drop / watchlist flags visible and explainable in the feed |

**Likely work packages:**

- Product IA: “Pilot Intel” in menus/Settings; reduce “optional add-on only” messaging for default-bundled history  
- Pilot Info card quality (already redesigned once — lift to match new look-and-feel)  
- Intel History reliability: sightings, flags, DNT, auto hot-drop tuning in Settings  
- Import/export intel packs (if needed for “first-class”; otherwise polish path + clear data location)  
- Help topics updated for Pilot Intel as a primary workflow  

**Acceptance (v0.7):**

- New user can open pilot intel from the feed without reading add-on docs  
- One roam-session smoke: sighting → flag → reopen card → zKill sync path understood  
- Bundled by default on portable installs (already true for code; make **product** match)  

---

### 4. LAN phone viewer = replicate the tool display

**Problem:** Planned LAN viewer must not be a plain-text dump; it must **mirror what the desktop tool shows**.

**Goal:** Optional LAN web viewer for phone/tablet/second PC that streams the **same rendered feed** the operator sees (theme, highlights, translation mode, filters, channel selection as practical).

| Required behavior |
|-------------------|
| Opt-in only; Stop Sharing is obvious |
| LAN-only bind; tokenized URL by default; QR + copy URL |
| Read-only; no remote control, no settings/tokens/logs exposure |
| **Visual parity:** feed background, text, timestamps, sender, systems/ships/pilots/ESS/links, bold/highlight styles from Appearance |
| Respect Recognition Rules / exclusions so highlights match desktop |
| Same translation-facing text the tool shows (visible line / translated-only policy) |
| Channel filter: at least mirror active tab or simple channel picker on phone |
| Bounded recent buffer; SSE or equivalent; works offline from internet (LAN only) |
| Theme updates when Appearance changes (reload or live CSS variables) |

**Acceptance (v0.7):**

- Side-by-side: desktop feed vs phone browser look “the same tool”  
- Enable → scan QR → see live rows; disable → clients stop  
- Security warning shown once when enabling  

**Implementation note:** Prefer semantic spans / theme JSON export (already sketched in older LAN notes). May require finishing `RenderRow` span data so the browser can style like Tk tags.

---

## Supporting work (enables v0.7 / 1.0)

Not headline features, but required so the cut is shippable:

| Support item | Why |
|--------------|-----|
| Release CI (portable ZIP + SHA256) | Trust; no half-shipped releases |
| Update-check vs real Latest tag | Already burned by missing v0.6 once |
| Pre-release visual + live smoke checklist | Look-and-feel and tabs need eyes |
| Extract remaining ESI/parse hotspots if they block UI work | Safer main-shell rewrite |
| Diagnostic export (no secrets) | Support during redesign |
| Keep translation/phrase quality loops | Feed content quality still matters under new chrome |

**Explicitly post-v0.7 (unless pulled in later):**

- Offline Argos helper process  
- Intel Query / LLM  
- Code signing (aim if cheap; not a v0.7 pillar — document AV story)  
- Tauri/v3 rewrite  
- Cloud relay / accounts  

---

## Version ladder

| Version | Theme | Ships |
|---------|--------|--------|
| **v0.7** | **The four pillars** | (1) full look & feel, (2) tabs that act like tabs, (3) pilot intel first-class, (4) LAN phone viewer with display parity — all in one public cut |
| **v0.8+** | **Harden & extend** | Live feedback fixes, release CI, translation quality loops, optional Argos helper, signing story |
| **v1.0** | **Recommendable** | Stabilization, automated release path, smoke gates, docs/help aligned, no open P0 UI/trust bugs |

**Decision:** v0.7 is not “shell only.” It delivers the full set of 1.0 pillars above in one release train. Internal sequencing still builds look/tabs before LAN so the phone viewer clones the new UI.

---

## v0.7 execution order (internal)

1. **Visual system design** — theme tokens, type scale, density; reference for main shell + tabs + pilot + Settings  
2. **Tabs behavior rewrite** — real tab model (select, unread, close, reorder, overflow, All pinned), then skin  
3. **Main shell + feed + Settings restyle** — apply tokens end-to-end  
4. **Pilot intel first-class** — product IA, feed entry, history/flags/card coherent on new chrome  
5. **LAN phone viewer** — opt-in stream; theme + highlights + visible lines match desktop  
6. **v0.7 ship gate** — visual review, live smoke (tabs / pilot / LAN / translate), portable ZIP + README screenshot + CHANGELOG

---

## Out of scope for this roadmap revision

- Re-listing every completed v0.2–v0.6 item (see `CHANGELOG.md`)  
- Argos re-enable as a 1.0 gate  
- Rewriting the app outside Python/Tk for 1.0  

---

## Decision log

| Date | Decision |
|------|----------|
| 2026-07-10 | Path to 1.0 centers on: (1) full look-and-feel, (2) real tabs, (3) pilot intel first-class, (4) LAN phone viewer with display parity |
| 2026-07-10 | **All four pillars are the v0.7 scope** (single public cut); 0.8+ hardens; 1.0 is recommendable/stability |
| 2026-07-10 | **Theme: Void Tactical (Mockup A)** approved; Amber Fleet (B) rejected — spec `docs/superpowers/specs/2026-07-10-v0.7-void-tactical-theme.md` |
| 2026-07-10 | Framework stays Tk + `sb_ui` for 0.7/1.0; no Tauri migration as the vehicle for the visual update |
| 2026-07-02 | Earlier UI foundation (Settings shell, components) remains the base to extend — main shell was not fully modernized yet |
