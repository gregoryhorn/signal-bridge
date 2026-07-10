# Signal Bridge Public Issue List

This file tracks current open issues for the public repository. Signal Bridge v0.6 is the current public release; these open items were reported during the v0.7 review.

Resolved and superseded records from v0.4 through v0.6 are preserved in the [historical issue archive](docs/archive/ISSUES-v0.4-v0.6.md).

## Active issues

## Open: Pilot Info Sync zKill jumps the window back to its original position

- Status: open
- Priority: high
- Area: Pilot Info / zKill sync / window geometry
- Type: bug / UX
- Reported: 2026-07-10 (v0.7 review)

### Reported behavior

- User opens Pilot Info and may move the card to a convenient place on screen.
- Clicking **Sync zKill** causes the window to jump/move back to its original open position (and/or re-layout as if freshly opened).
- Disrupts fleet use when the card was deliberately placed beside the client or main app.

### Likely cause areas

- `fit_window` / `fit_to_content` / `polish_window` re-run after sync completes and re-centers or re-applies initial geometry.
- Full re-render of the card (`render_summary` / header-body rebuild) calling autosize placement again.
- `sb_ui/windows.py` placement helpers treating every layout pass as a first open.

### Desired behavior

- Sync zKill updates card content only.
- Window **position stays where the user left it**.
- Size may grow slightly if needed for new content, but should not snap back to the initial open location.

### Acceptance criteria

- Open Pilot Info, drag window away from default position, click Sync zKill, wait for sync finish.
- Window remains at the dragged position (within a few pixels).
- Content updates (syncing → synced / failed) without a full “re-open” feel.
- Visual check before/after.


## Open: Child windows open on top of the main feed instead of beside it

- Status: open
- Priority: high
- Area: window placement / Pilot Info / Settings / dialogs
- Type: UX
- Reported: 2026-07-10 (v0.7 review)

### Reported behavior

- Pilot Info, Settings, and other child windows open centered on (or over) the main Signal Bridge window.
- They block the live chat/intel feed while open — bad for a side-panel fleet tool.

### Desired behavior

- Prefer placing new windows **next to** the main window (prefer right, then left, then below) so the feed stays visible.
- Clamp to the current monitor work area; if there is not enough room beside, fall back without covering the entire main window when possible.
- Apply consistently for Pilot Info first; extend to Settings and other `polish_window` children.

### Implementation direction

- Extend `sb_ui/windows.py` (`polish_window` / placement helper) with a `place_beside_parent` policy.
- Record parent geometry; compute sibling position; optional sticky preference later.

### Acceptance criteria

- With main window on a free desktop area, open Pilot Info: feed remains largely visible beside the card.
- Open Settings: same beside-parent behavior (or documented exception if modal).
- Multi-monitor: window stays on the same monitor as the main app when practical.
- Visual inspection before/after.


## Open: Pilot Info visual design still feels prototype / ugly (v0.7 Void Tactical not fully applied)

- Status: open
- Priority: high
- Area: Pilot Info / `sb_ui/pilot` / look-and-feel
- Type: design / UX
- Reported: 2026-07-10 (v0.7 review)

### Reported behavior

- Pilot Info was modularized (`sb_ui/pilot/card.py`) and product IA made first-class, but the **visual design did not advance enough**.
- Card still feels dense, dated, and inconsistent with the approved **Void Tactical** shell mockup (`docs/images/signal-bridge-v0.7-theme-mockup-a.png`).
- Not up to modern side-panel / tactical card standards for fleet use.

### Desired behavior

- Pilot Info matches Void Tactical: clearer hierarchy, spacing scale, surfaces, threat ribbon, footer actions, empty/loading/error states.
- Feels like a deliberate product surface, not a debug dump of sections.
- Same visual language as main shell tabs/chrome (tokens from `sb_ui/theme.py` only).

### Design direction

- Treat as a **design pass** on `sb_ui/pilot/` (card + sections), not more data fields.
- Reference: Void Tactical mockup + compact tactical card goals in `docs/superpowers/plans/2026-07-10-pilot-info-design-pass.md` (refresh as needed).
- Before/after screenshots required.

### Acceptance criteria

- Visual review against Void Tactical mockup.
- No hard-coded one-off hex outside theme tokens on the card.
- Empty, syncing, failed, and synced states are intentional.
- Feed remains usable while the card is open (pairs with beside-parent placement issue above).

## Reporting template

When reporting an intel parsing or translation issue, include:

```text
Original chat line:
Displayed translation:
Expected output:
What was highlighted wrong or missing:
```

For Pilot Info or zKill issues, include:

```text
Clicked pilot name:
Expected character ID or zKill URL:
What Pilot Info showed instead:
```

