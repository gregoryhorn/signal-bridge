# Intel History / Pilot Intelligence Add-on

Planned optional Signal Bridge add-on for local pilot memory.

Current MVP skeleton:

- Creates a local SQLite database under `user_data/modules/intel-history/`.
- Records ESI-confirmed pilot sightings only.
- Dedupes repeated reports in a short time bucket.
- Maintains basic health/status counters.
- Never blocks the live feed; the core app queues rows and continues.

Future work is tracked in `docs/INTEL_HISTORY_ADDON_SPEC.md`.
