# Void Tactical Surface Matrix

This matrix is the visual acceptance record for the v0.7 UI rollout. Captures
are retained alongside this record; states that require a live interactive or
web harness remain explicitly marked as such.

| Surface | Owner | Key states | Primary action | Before | After | Status |
|---|---|---|---|---|---|---|
| Main feed and tabs | `sb_ui/shell`, `sb_ui/tabs` | empty, live, translated, overflow | Start monitoring | `before/main.png` | `after/{main.png,main-live-translated.png}` | live and translated rows exercised and reviewed |
| Pilot Info | `sb_ui/pilot` | empty, syncing, failed, synced | Open zKill / Sync zKill | `before/pilot-*.png` | approved concept plus `after/pilot-*.png` | approved and captured |
| Settings shell | `sb_ui/settings_center.py` | default, long page, save failed | Apply | `before/settings-*.png` | `after/settings-*.png`, `after/settings-save-failed.png` | save-failure path exercised without writing settings |
| Settings pages | `signal_bridge_gui.py`, `sb_ui/*` | all 16 page keys | page-specific | `before/settings-*.png` | `after/settings-*.png` | all page keys captured |
| Standalone dialogs | `signal_bridge_gui.py` | empty, validation, modal | context-specific | `before/{hidden-tabs,channel-chooser,font-chooser,appearance-dialog,esi-oauth,recognition-rules}.png` | corresponding `after/*.png`, `after/simple-prompt.png` | prompt and OAuth missing-secret validation exercised |
| Help and About | `sb_ui/settings_center.py`, `signal_bridge_gui.py` | topic navigation, external-link copy | Close | `before/{help,about}.png` | `after/{help,about}.png` | captured |
| LAN viewer | `web_lan/` | connected, reconnecting, disconnected, empty | filter channel | code and fixture coverage | `after/{lan-connected.png,lan-disconnected.png}` | browser checked with real rows, SSE, filters, and server-loss reconnect state |

## Capture registry

`scripts/capture_ui_review.py --list` prints every registered surface.
Desktop captures write under `docs/images/ui-review/before/` and
`docs/images/ui-review/after/`. The automatic desktop harness skips
`simple-prompt` and LAN connection states; their live review captures are
added alongside the automated output.
