from typing import Dict, Set
from app.core.config import settings

# Base Sarvam AI Endpoints
SARVAM_BASE_URL: str = "https://api.sarvam.ai"
SARVAM_STT_ENDPOINT: str = f"{SARVAM_BASE_URL}/speech-to-text"
SARVAM_TTS_ENDPOINT: str = f"{SARVAM_BASE_URL}/text-to-speech"

# API Key & Models
SARVAM_API_KEY: str = settings.SARVAM_API_KEY
SARVAM_STT_MODEL: str = settings.SARVAM_STT_MODEL or "saaras:v3"
SARVAM_TTS_MODEL: str = settings.SARVAM_TTS_MODEL or "bulbul:v3"

# Audio Constraints
MAX_AUDIO_SIZE_BYTES: int = settings.VOICE_MAX_AUDIO_SIZE_MB * 1024 * 1024  # Default 25 MB
VOICE_TIMEOUT_SECONDS: float = settings.VOICE_TIMEOUT_SECONDS or 30.0

SUPPORTED_MIME_TYPES: Set[str] = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/webm",
    "audio/webm;codecs=opus",
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/m4a",
    "audio/mp4",
    "audio/x-m4a",
    "video/webm",  # Some browser MediaRecorder produce video/webm for audio blobs
}

SUPPORTED_EXTENSIONS: Set[str] = {
    ".wav",
    ".webm",
    ".ogg",
    ".mp3",
    ".m4a",
    ".aac",
    ".flac",
}

# Supported Languages for STT & TTS
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en-IN": "English",
    "hi-IN": "Hindi",
    "gu-IN": "Gujarati",
}

# Voice selection by language
DEFAULT_VOICES: Dict[str, str] = {
    "en-IN": settings.SARVAM_ENGLISH_VOICE or "shubh",
    "hi-IN": settings.SARVAM_HINDI_VOICE or "shubh",
    "gu-IN": settings.SARVAM_GUJARATI_VOICE or "shubh",
}

DEFAULT_LANGUAGE: str = settings.SARVAM_DEFAULT_LANGUAGE or "en-IN"
MAX_TTS_CHARS: int = 2500
