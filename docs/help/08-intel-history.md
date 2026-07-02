# Intel History

Signal Bridge keeps a local history of pilot sightings parsed from the
channels you track. This history powers the Pilot Info card.

## What is recorded

- Pilot sightings with timestamp, system, ship/status, and source channel.
- Aggregates per pilot: report counts, first/last seen, top systems and ships.
- Manual flags you set on pilots.

## Where it lives

All history is stored locally in the app's data folder — nothing is
uploaded anywhere. Clearing or resetting local data (Settings, page
**Cache & Data**) removes it.

Duplicate reports of the same sighting are collapsed with a multiplier
(for example `x3`) instead of flooding the history.
