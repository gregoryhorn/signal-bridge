"""Translation helpers (detect + free engines). No Tk."""

from sb_translation.detect import has_cjk, has_english_letters, has_non_english_signal, pick_google_source_lang
from sb_translation.google_free import google_translate_free

__all__ = [
    "has_cjk",
    "has_english_letters",
    "has_non_english_signal",
    "pick_google_source_lang",
    "google_translate_free",
]
