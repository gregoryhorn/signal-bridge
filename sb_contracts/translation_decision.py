"""TranslationDecision contract — pure stdlib."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class TranslationDecision:
    decision: str  # used | skipped | queued | error
    reason: str
    engine: str = "none"  # catalog | cache | google | argos | none
    source_lang: str = ""
    target_lang: str = ""
    cache_hit: bool = False
    duration_ms: int = 0
    error: str = ""
    schema_version: int = 1


def make_translation_decision(
    *,
    decision: str,
    reason: str,
    engine: str = "none",
    source_lang: str = "",
    target_lang: str = "",
    cache_hit: bool = False,
    duration_ms: int = 0,
    error: str = "",
) -> TranslationDecision:
    return TranslationDecision(
        decision=decision,
        reason=reason,
        engine=engine,
        source_lang=source_lang,
        target_lang=target_lang,
        cache_hit=bool(cache_hit),
        duration_ms=int(duration_ms or 0),
        error=str(error or ""),
    )


def translation_decision_to_dict(d: TranslationDecision) -> dict:
    return asdict(d)
