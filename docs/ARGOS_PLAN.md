# Argos Offline Translation Plan

## Current state

Direct in-process Argos integration is disabled. The GUI must not import, probe, install, or call `argostranslate` directly because imports/model scans can hang or take several seconds and freeze the Tkinter app.

Current safe paths:

- compact EVE catalog/localized aliases
- curated translation cache
- Google online translation only where safe/precomputed/backgrounded

## Required future design

Argos must run through a helper process:

```text
Signal Bridge GUI
  -> argos_helper.py / argos_helper.exe
      -> imports Argos
      -> checks models
      -> translates
      -> returns JSON
```

## Helper commands

- `status`
- `list-models`
- `self-test`
- `translate`
- `install-models`

Every call must use:

- subprocess isolation
- hard timeout
- kill-on-timeout
- JSON result/error
- diagnostic logging
- cached status in the GUI

## Settings behavior

Translation settings should show cached Argos state immediately. Buttons may queue background helper jobs, but must never block the UI thread.

## Re-enable criteria

Argos can become a preferred engine only after:

1. helper status probe is timeout-safe
2. helper test translation is timeout-safe
3. model install/repair is app-local and verifiable
4. GUI translation jobs are background-only
5. render path cannot call Argos under any condition
