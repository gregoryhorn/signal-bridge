"""Protect/restore entity tokens around free machine translation."""

from __future__ import annotations

import re


def make_protect_token(index: int) -> str:
    return f"SBX{index}"


def reattach_untranslated_source_tokens(original: str, translated: str, extracted_source: str = "") -> str:
    """Reattach English/EVE tokens left out when only a CJK span was translated/cached.

    Example: original ``能塌吗？Buffering``, extracted source ``能塌吗``, translation
    ``Can it collapse?`` → ``Can it collapse? Buffering``.
    """
    full = str(original or "").strip()
    out = str(translated or "").strip()
    if not full or not out:
        return out
    extracted = str(extracted_source or "").strip()
    remainder = ""
    if extracted and extracted in full and extracted != full:
        idx = full.find(extracted)
        remainder = (full[:idx] + full[idx + len(extracted) :]).strip()
    elif extracted and extracted != full:
        # Fallback: drop CJK runs from original
        remainder = re.sub(r"[\u3400-\u9fff\uf900-\ufaff]+", " ", full)
        remainder = re.sub(r"[？！。，、：；…]+", " ", remainder)
        remainder = re.sub(r"\s+", " ", remainder).strip()
    if not remainder:
        return out
    if remainder.casefold() in out.casefold():
        return out
    missing: list[str] = []
    seen: set[str] = set()
    # Pilot-like / ship-like latin tokens and system codes
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9'*.-]{1,}|[A-Z0-9]{1,6}-[A-Z0-9]{1,4}", remainder):
        key = tok.casefold()
        if key in seen:
            continue
        if key in out.casefold():
            continue
        seen.add(key)
        missing.append(tok)
    if missing:
        return f"{out} {' '.join(missing)}".strip()
    # Non-empty remainder that is not just punctuation
    cleaned = re.sub(r"[\s\W_]+", "", remainder, flags=re.U)
    if cleaned and cleaned.casefold() not in re.sub(r"[\s\W_]+", "", out, flags=re.U).casefold():
        return f"{out} {remainder}".strip()
    return out


def restore_protected_translation_tokens(translated: str, protected: list[tuple[str, str]]) -> str:
    """Put protected terms back after MT; re-append any tokens the engine dropped.

    Google free translate often deletes opaque placeholders like SBX0. When a
    token is missing and the original term is not already present, append it so
    English pilot names / systems after Chinese text are not lost.
    """
    out = str(translated or "")
    missing: list[str] = []
    for token, original in protected:
        token = str(token or "")
        original = str(original or "")
        if not token or not original:
            continue
        patterns = [
            rf"\b{re.escape(token)}\b",
            re.escape(token),
            # MT sometimes inserts a space: SBX 0
            re.escape(token[:3]) + r"\s*" + re.escape(token[3:]) if token.startswith("SBX") and len(token) > 3 else None,
        ]
        restored = False
        for pat in patterns:
            if not pat:
                continue
            if re.search(pat, out, flags=re.I):
                out = re.sub(pat, original, out, count=1, flags=re.I)
                restored = True
                break
        if restored:
            continue
        # Already present as plain text (engine "translated" name to itself)
        if original in out:
            continue
        # Case-insensitive presence
        if re.search(re.escape(original), out, flags=re.I):
            continue
        # Do not re-append CJK-only protected terms (e.g. 天鹤级 -> "Crane").
        # Those were placeholders for content the engine should translate, not keep.
        if re.search(r"[\u3400-\u9fff\uf900-\ufaff]", original) and not re.search(r"[A-Za-z]{2,}", original):
            continue
        missing.append(original)
    if missing:
        out = (out.rstrip() + " " + " ".join(missing)).strip()
    return out.strip()
