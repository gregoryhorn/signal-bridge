"""Entity highlight classification (ship vs module vs ess)."""

from __future__ import annotations


def highlight_kind_for_term(
    term: str,
    *,
    ship_terms: set[str] | None = None,
    module_terms: set[str] | None = None,
    ess_terms: set[str] | None = None,
) -> str:
    """Return 'ship' | 'module' | 'ess' | 'other'. Ships win over module."""
    key = str(term or "").strip().casefold()
    if not key:
        return "other"
    ships = {str(x).casefold() for x in (ship_terms or set())}
    modules = {str(x).casefold() for x in (module_terms or set())}
    ess = {str(x).casefold() for x in (ess_terms or set())}
    if key in ships:
        return "ship"
    if key in ess:
        return "ess"
    if key in modules:
        return "module"
    # Word-level membership for multi-word ship names
    if any(key == s or key in s.split() or s in key for s in ships if len(s) >= 3):
        for s in ships:
            if key == s or key == s.casefold():
                return "ship"
            if s.startswith(key + " ") or s.endswith(" " + key) or f" {key} " in f" {s} ":
                # Prefer exact multi-word later; single token that is whole ship name:
                pass
        if key in ships:
            return "ship"
        for s in ships:
            if s == key:
                return "ship"
    if key in {s for s in ships}:
        return "ship"
    # Direct membership already handled; also match known ship display names casefold exact only
    return "other"


def term_is_ship(term: str, ship_terms: set[str]) -> bool:
    key = str(term or "").strip().casefold()
    ships = {str(x).strip().casefold() for x in ship_terms if str(x).strip()}
    if key in ships:
        return True
    # Plural soft match
    if key.endswith("s") and key[:-1] in ships:
        return True
    return False
