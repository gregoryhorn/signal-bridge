"""Language detection helpers for free translation."""

from __future__ import annotations


def has_cjk(text: str) -> bool:
    return any("\u3400" <= ch <= "\u9fff" for ch in text)


def has_english_letters(text: str) -> bool:
    return any(("A" <= ch <= "Z") or ("a" <= ch <= "z") for ch in text)


def has_non_english_signal(text: str) -> bool:
    ranges = (
        (0x0370, 0x03FF),  # Greek
        (0x0400, 0x052F),  # Cyrillic
        (0x0590, 0x05FF),  # Hebrew
        (0x0600, 0x06FF),  # Arabic
        (0x0750, 0x077F),
        (0x08A0, 0x08FF),
        (0x0900, 0x097F),
        (0x0980, 0x09FF),
        (0x0A00, 0x0A7F),
        (0x0A80, 0x0AFF),
        (0x0B00, 0x0B7F),
        (0x0B80, 0x0BFF),
        (0x0C00, 0x0C7F),
        (0x0C80, 0x0CFF),
        (0x0D00, 0x0D7F),
        (0x0E00, 0x0E7F),
        (0x0E80, 0x0EFF),
        (0x3040, 0x30FF),
        (0x3400, 0x9FFF),
        (0xAC00, 0xD7AF),
        (0xF900, 0xFAFF),
    )
    for ch in text:
        code = ord(ch)
        if code == 0xFFFD or code < 0x20 or 0x7F <= code <= 0x9F:
            continue
        if any(start <= code <= end for start, end in ranges):
            return True
    return False


def pick_google_source_lang(text: str, direction: str = "zh-en") -> str:
    """Choose Google sl= parameter for free translate."""
    d = str(direction or "zh-en").casefold()
    if d in {"en-zh", "en->zh", "en_zh"}:
        return "en"
    if has_cjk(text):
        return "zh-CN"
    if has_non_english_signal(text):
        return "auto"
    return "auto"
