import io
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile
from app.voice.config import (
    MAX_AUDIO_SIZE_BYTES,
    SUPPORTED_MIME_TYPES,
    SUPPORTED_EXTENSIONS
)
from app.voice.exceptions import (
    VoiceUploadError,
    AudioTooLargeError,
    UnsupportedAudioFormatError
)

MAGIC_SIGNATURES = [
    (b"RIFF", 0, "audio/wav"),
    (b"\x1a\x45\xdf\xa3", 0, "audio/webm"),     # EBML header (WebM/Matroska)
    (b"OggS", 0, "audio/ogg"),                 # Ogg bitstream
    (b"ID3", 0, "audio/mpeg"),                 # MP3 with ID3v2
    (b"\xff\xfb", 0, "audio/mpeg"),             # MP3 raw frame sync
    (b"\xff\xf3", 0, "audio/mpeg"),             # MP3 raw frame sync
    (b"\xff\xf2", 0, "audio/mpeg"),             # MP3 raw frame sync
    (b"ftyp", 4, "audio/mp4"),                 # MP4/M4A
]


def detect_audio_mime(content: bytes) -> str | None:
    """Check magic bytes of audio content to identify genuine audio format."""
    if len(content) < 8:
        return None
    for sig, offset, mime in MAGIC_SIGNATURES:
        if len(content) >= offset + len(sig):
            if content[offset:offset + len(sig)] == sig:
                return mime
    return None


async def validate_audio_upload(file: UploadFile) -> Tuple[bytes, str, str]:
    """
    Validates uploaded audio file for:
    1. Non-empty content
    2. File size within limit
    3. Supported MIME type and valid audio magic bytes

    Returns (audio_bytes, normalized_filename, content_type).
    """
    if not file or not file.filename:
        raise VoiceUploadError("No audio file provided.")

    # Read audio bytes
    content = await file.read()
    if not content or len(content) == 0:
        raise VoiceUploadError("Uploaded audio file is empty (0 bytes).")

    # Check size limit
    if len(content) > MAX_AUDIO_SIZE_BYTES:
        raise AudioTooLargeError(
            f"Audio file is too large ({len(content) / (1024 * 1024):.1f} MB). Maximum allowed is {MAX_AUDIO_SIZE_BYTES / (1024 * 1024):.0f} MB."
        )

    # Check reported MIME type & extension
    reported_mime = (file.content_type or "").lower().split(";")[0].strip()
    ext = Path(file.filename).suffix.lower()

    # Detect real MIME from content bytes
    detected_mime = detect_audio_mime(content)

    # Allow if either detected mime is valid or reported mime is recognized
    is_valid_mime = reported_mime in SUPPORTED_MIME_TYPES or (detected_mime and detected_mime in SUPPORTED_MIME_TYPES)
    is_valid_ext = ext in SUPPORTED_EXTENSIONS

    if not (is_valid_mime or is_valid_ext):
        raise UnsupportedAudioFormatError(
            f"Unsupported audio format (reported '{reported_mime}', extension '{ext}'). Supported formats: WAV, WebM, MP3, OGG, M4A."
        )

    # Standardize filename and content type
    effective_mime = detected_mime or reported_mime or "audio/wav"
    effective_filename = file.filename or "recording.wav"
    if not Path(effective_filename).suffix:
        ext_map = {
            "audio/wav": ".wav",
            "audio/webm": ".webm",
            "audio/ogg": ".ogg",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a"
        }
        effective_filename += ext_map.get(effective_mime, ".wav")

    return content, effective_filename, effective_mime
