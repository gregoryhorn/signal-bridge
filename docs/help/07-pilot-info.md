# Pilot Info

**Pilot Intel** is a core Signal Bridge feature (menu **Pilot Intel**, Settings **Pilot Intel**).

Right-click a pilot name in the feed and choose **Open Pilot Info** to open the
compact pilot card.

## Layout (at a glance)

- **Identity**: name, threat ribbon (HIGH / MED / QUIET / NOT SYNCED), corp · alliance, last sighting line, character ID.
- **Snapshot**: flags and hot systems / ships / signals (empty groups are omitted).
- **Local**: short timeline of recent local sightings (when any exist).
- **zKill**: sync CTA when cold; stats + short kill/loss lists when synced.
- **Footer**: primary action first (Sync or Open zKill), then Flags, Activity, Copy, Close.

There is no full zKill URL dump in the header — use **Open zKill**.

## Actions

- **Sync zKill**: fetch a 30-day summary in the background (cached locally; never blocks the card).
- **Open zKill**: pilot page in your browser.
- **Flags**: manual flags (Watchlist, FC, Scout, Hot Dropper, threat levels…) with optional note. Use **← Summary** to return.
- **Activity**: full local sightings list.
- **Copy**: copyable pilot summary text.

## Notes

- The card renders **cached** Intel History + zKill data only.
- Priority uses recent zKill activity and same-ship matches when available.
- Kill lists prefer small-gang engagements first.
