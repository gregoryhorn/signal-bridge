"""Typed JSON settings store with per-key validation and non-silent failures."""

import copy
import json
import os
from pathlib import Path


def _noop(_msg: str) -> None:
    pass


class SettingsStore:
    def __init__(self, path, schema, log=None):
        self.path = Path(path)
        self.schema = schema
        self.log = log or _noop
        self.warnings: list[str] = []

    def defaults(self) -> dict:
        out = {}
        for key, (_type, default) in self.schema.items():
            out[key] = default() if callable(default) else copy.deepcopy(default)
        return out

    def _warn(self, msg: str) -> None:
        self.warnings.append(msg)
        self.log(msg)

    def _validate(self, key, value, expected_type, default):
        if expected_type is bool:
            if isinstance(value, bool):
                return value
        elif expected_type is int:
            if isinstance(value, int) and not isinstance(value, bool):
                return value
        elif isinstance(value, expected_type):
            return value
        try:
            coerced = expected_type(value)
            if expected_type is int and isinstance(value, bool):
                raise TypeError("bool is not an int setting")
            self._warn(f"settings: coerced {key}={value!r} to {expected_type.__name__}")
            return coerced
        except Exception:
            self._warn(f"settings: invalid {key}={value!r}, using default {default!r}")
            return default

    def load(self) -> dict:
        self.warnings = []
        settings = self.defaults()
        if not self.path.exists():
            return settings
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            self._warn(f"settings: failed to read {self.path.name}: {exc}; using defaults")
            return settings
        if not isinstance(loaded, dict):
            self._warn(f"settings: {self.path.name} is not a JSON object; using defaults")
            return settings
        for key, value in loaded.items():
            if key in self.schema:
                expected_type, _ = self.schema[key]
                settings[key] = self._validate(key, value, expected_type, settings[key])
            else:
                settings[key] = value
        return settings

    def save(self, settings: dict) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(settings, indent=2, ensure_ascii=False),
                           encoding="utf-8")
            os.replace(tmp, self.path)
            return True
        except Exception as exc:
            self.log(f"settings: save to {self.path} failed: {exc}")
            return False
