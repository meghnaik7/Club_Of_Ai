import base64
import logging
from typing import Optional, Tuple
from app.voice.config import DEFAULT_VOICES, DEFAULT_LANGUAGE, MAX_TTS_CHARS
from app.voice.language_service import normalize_language
from app.voice.sarvam_client import SarvamClient
from app.voice.schemas import TTSResponse
from app.voice.exceptions import TextToSpeechError

logger = logging.getLogger(__name__)


class TTSService:
    """Service layer orchestrating text-to-speech synthesis."""

    def __init__(self, client: Optional[SarvamClient] = None):
        self.client = client or SarvamClient()

    def _select_voice(self, language: str, explicit_voice: Optional[str] = None) -> str:
        if explicit_voice and explicit_voice.strip():
            return explicit_voice.strip()
        return DEFAULT_VOICES.get(language, "shubh")

    def _truncate_text(self, text: str, max_chars: int = MAX_TTS_CHARS) -> str:
        """Truncates text safely at a sentence or word boundary if over the max length."""
        cleaned = text.strip()
        if len(cleaned) <= max_chars:
            return cleaned

        truncated = cleaned[:max_chars - 3]
        last_punct = max(truncated.rfind(". "), truncated.rfind("! "), truncated.rfind("? "), truncated.rfind("। "))
        if last_punct > max_chars * 0.7:
            return truncated[:last_punct + 1]
        return truncated + "..."

    async def synthesize_speech(
        self,
        text: str,
        language: str = DEFAULT_LANGUAGE,
        voice: Optional[str] = None,
        pace: float = 1.0
    ) -> TTSResponse:
        """
        Synthesizes spoken audio from text using Sarvam TTS.
        Returns TTSResponse with base64 audio payload and metadata.
        """
        if not text or not text.strip():
            raise TextToSpeechError("Cannot synthesize speech from empty text.")

        # Normalize target language
        target_lang = normalize_language(language, allow_auto=False) or DEFAULT_LANGUAGE
        speaker = self._select_voice(target_lang, explicit_voice=voice)
        processed_text = self._truncate_text(text)

        logger.info(
            f"[TTSService] Synthesizing text_len={len(processed_text)}, "
            f"lang='{target_lang}', voice='{speaker}'"
        )

        result = await self.client.text_to_speech(
            text=processed_text,
            language_code=target_lang,
            speaker=speaker,
            pace=pace
        )

        return TTSResponse(
            audio_base64=result["audio_base64"],
            content_type=result.get("content_type", "audio/wav"),
            language=target_lang,
            voice=speaker,
            duration_seconds=None
        )

    async def synthesize_speech_bytes(
        self,
        text: str,
        language: str = DEFAULT_LANGUAGE,
        voice: Optional[str] = None,
        pace: float = 1.0
    ) -> Tuple[bytes, str]:
        """Synthesize and return raw binary audio bytes + content_type."""
        resp = await self.synthesize_speech(text=text, language=language, voice=voice, pace=pace)
        raw_bytes = base64.b64decode(resp.audio_base64)
        return raw_bytes, resp.content_type
