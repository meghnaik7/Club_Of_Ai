import logging
from typing import Optional
from fastapi import UploadFile

from app.voice.audio_utils import validate_audio_upload
from app.voice.language_service import normalize_language
from app.voice.sarvam_client import SarvamClient
from app.voice.schemas import TranscriptionResponse
from app.voice.exceptions import SpeechRecognitionError

logger = logging.getLogger(__name__)


class STTService:
    """Service layer orchestrating speech-to-text processing."""

    def __init__(self, client: Optional[SarvamClient] = None):
        self.client = client or SarvamClient()

    async def transcribe_audio(
        self,
        audio_file: UploadFile,
        language: Optional[str] = None
    ) -> TranscriptionResponse:
        """
        Validates, normalizes, and transcribes incoming speech audio.
        Supports explicit language ('en-IN', 'hi-IN', 'gu-IN') or automatic detection (None).
        """
        # 1. Validate audio upload (size, MIME, magic bytes)
        content, filename, content_type = await validate_audio_upload(audio_file)

        # 2. Normalize requested language if specified
        normalized_lang = normalize_language(language, allow_auto=True)

        logger.info(
            f"[STTService] Transcribing file='{filename}', size={len(content)}B, "
            f"type='{content_type}', requested_language='{normalized_lang or 'auto'}'"
        )

        # 3. Call Sarvam STT API
        result = await self.client.speech_to_text(
            audio_bytes=content,
            filename=filename,
            content_type=content_type,
            language_code=normalized_lang
        )

        transcript = result.get("transcript", "").strip()
        detected_lang = result.get("language_code") or normalized_lang or "en-IN"
        confidence = result.get("confidence")  # None if unavailable, do not fabricate

        if not transcript:
            raise SpeechRecognitionError(
                "I couldn't hear or recognize any clear speech in the audio. Please try again."
            )

        # Re-normalize detected language to canonical code
        final_lang = normalize_language(detected_lang, allow_auto=False) or "en-IN"

        logger.info(
            f"[STTService Completed] transcript='{transcript[:60]}...', "
            f"lang='{final_lang}', confidence={confidence}"
        )

        return TranscriptionResponse(
            text=transcript,
            language=final_lang,
            confidence=confidence,
            request_id=result.get("request_id")
        )
