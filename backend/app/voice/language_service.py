from typing import Optional, Dict
from app.voice.config import SUPPORTED_LANGUAGES
from app.voice.exceptions import UnsupportedLanguageError

# Alias normalization table
LANGUAGE_ALIASES: Dict[str, str] = {
    # English
    "en": "en-IN",
    "eng": "en-IN",
    "english": "en-IN",
    "en-in": "en-IN",
    "en_in": "en-IN",
    # Hindi
    "hi": "hi-IN",
    "hin": "hi-IN",
    "hindi": "hi-IN",
    "hi-in": "hi-IN",
    "hi_in": "hi-IN",
    # Gujarati
    "gu": "gu-IN",
    "guj": "gu-IN",
    "gujarati": "gu-IN",
    "gu-in": "gu-IN",
    "gu_in": "gu-IN",
}


def normalize_language(lang_str: Optional[str], allow_auto: bool = True) -> Optional[str]:
    """
    Normalizes a user or API language string into a canonical BCP-47 Sarvam code:
    'en-IN', 'hi-IN', or 'gu-IN'.

    If lang_str is None, empty, or 'auto' (and allow_auto=True), returns None (triggering auto-detection).
    Raises UnsupportedLanguageError if the language is not recognized or supported.
    """
    if not lang_str or not lang_str.strip():
        return None if allow_auto else "en-IN"

    cleaned = lang_str.strip().lower()

    if cleaned in ("auto", "detect", "auto-detect", "autodetect"):
        if allow_auto:
            return None
        return "en-IN"

    # Check direct canonical match
    for code in SUPPORTED_LANGUAGES:
        if cleaned == code.lower():
            return code

    # Check alias map
    if cleaned in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[cleaned]

    # Unsupported language
    raise UnsupportedLanguageError(
        language=lang_str,
        supported=list(SUPPORTED_LANGUAGES.keys())
    )


def is_language_supported(lang_code: str) -> bool:
    """Check if the normalized code is currently supported."""
    return lang_code in SUPPORTED_LANGUAGES


def get_language_display_name(lang_code: str) -> str:
    """Return friendly display name for language code."""
    return SUPPORTED_LANGUAGES.get(lang_code, lang_code)
