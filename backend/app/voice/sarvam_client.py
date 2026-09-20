import time
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
import httpx

from app.voice.config import (
    SARVAM_API_KEY,
    SARVAM_STT_ENDPOINT,
    SARVAM_TTS_ENDPOINT,
    SARVAM_STT_MODEL,
    SARVAM_TTS_MODEL,
    VOICE_TIMEOUT_SECONDS,
)
from app.voice.exceptions import (
    SarvamAuthenticationError,
    SarvamRateLimitError,
    SarvamTimeoutError,
    SarvamUnavailableError,
    SpeechRecognitionError,
    TextToSpeechError,
)

logger = logging.getLogger(__name__)


class SarvamClient:
    """
    Asynchronous client for Sarvam AI Speech Services.
    Encapsulates STT (Saaras) and TTS (Bulbul) API communication, authentication,
    rate-limit handling, exponential-backoff retries, and error mapping.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = VOICE_TIMEOUT_SECONDS,
        max_retries: int = 2
    ):
        self.api_key = api_key or SARVAM_API_KEY
        self.timeout = timeout
        self.max_retries = max_retries

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise SarvamAuthenticationError(
                "Sarvam API key is not configured. Please set SARVAM_API_KEY in environment."
            )
        return {
            "api-subscription-key": self.api_key,
        }

    async def speech_to_text(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        content_type: str = "audio/wav",
        language_code: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends audio bytes to Sarvam STT API (`/speech-to-text`).
        If language_code is None, Sarvam automatically detects the language.
        Returns dict containing transcript, language_code, confidence/probability, and request_id.
        """
        model_name = model or SARVAM_STT_MODEL
        headers = self._get_headers()

        data_fields: Dict[str, Any] = {
            "model": model_name,
        }
        if language_code:
            data_fields["language_code"] = language_code

        files = {
            "file": (filename, audio_bytes, content_type)
        }

        start_time = time.perf_counter()
        attempt = 0
        backoff_sec = 0.5

        while attempt <= self.max_retries:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.info(
                        f"[Sarvam STT] Requesting transcription (attempt {attempt}/{self.max_retries + 1}), "
                        f"audio_size={len(audio_bytes)} bytes, lang={language_code or 'auto'}, model={model_name}"
                    )
                    resp = await client.post(
                        SARVAM_STT_ENDPOINT,
                        headers=headers,
                        data=data_fields,
                        files=files
                    )
                    duration_ms = (time.perf_counter() - start_time) * 1000

                    if resp.status_code == 200:
                        body = resp.json()
                        transcript = body.get("transcript", "")
                        detected_lang = body.get("language_code") or language_code or "en-IN"
                        prob = body.get("language_probability") or body.get("confidence")

                        logger.info(
                            f"[Sarvam STT Success] status=200, duration={duration_ms:.1f}ms, "
                            f"lang={detected_lang}, chars={len(transcript)}"
                        )
                        return {
                            "transcript": transcript,
                            "language_code": detected_lang,
                            "confidence": float(prob) if prob is not None else None,
                            "request_id": body.get("request_id")
                        }

                    # Handle HTTP Errors
                    self._handle_http_error(resp, attempt=attempt, operation="STT")

            except httpx.TimeoutException as exc:
                if attempt <= self.max_retries:
                    logger.warning(f"[Sarvam STT Timeout] Retrying in {backoff_sec}s... ({exc})")
                    await asyncio.sleep(backoff_sec)
                    backoff_sec *= 2
                    continue
                raise SarvamTimeoutError("Sarvam STT request timed out.") from exc

            except httpx.RequestError as exc:
                if attempt <= self.max_retries:
                    logger.warning(f"[Sarvam STT Network Error] Retrying in {backoff_sec}s... ({exc})")
                    await asyncio.sleep(backoff_sec)
                    backoff_sec *= 2
                    continue
                raise SarvamUnavailableError(f"Network error connecting to Sarvam STT: {str(exc)}") from exc

        raise SpeechRecognitionError("Failed to transcribe audio after multiple attempts.")

    async def text_to_speech(
        self,
        text: str,
        language_code: str = "en-IN",
        speaker: Optional[str] = None,
        pace: float = 1.0,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends text to Sarvam TTS API (`/text-to-speech`).
        Returns dict with base64 audio string, content_type, request_id, and duration estimate.
        """
        if not text or not text.strip():
            raise TextToSpeechError("Cannot synthesize empty text.")

        model_name = model or SARVAM_TTS_MODEL
        voice_speaker = speaker or "shubh"
        headers = self._get_headers()
        headers["Content-Type"] = "application/json"

        payload = {
            "text": text[:2500],
            "language_code": language_code,
            "speaker": voice_speaker,
            "model": model_name,
            "pace": max(0.5, min(2.0, pace))
        }

        start_time = time.perf_counter()
        attempt = 0
        backoff_sec = 0.5

        while attempt <= self.max_retries:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.info(
                        f"[Sarvam TTS] Requesting synthesis (attempt {attempt}/{self.max_retries + 1}), "
                        f"text_len={len(text)}, lang={language_code}, speaker={voice_speaker}"
                    )
                    resp = await client.post(
                        SARVAM_TTS_ENDPOINT,
                        headers=headers,
                        json=payload
                    )
                    duration_ms = (time.perf_counter() - start_time) * 1000

                    if resp.status_code == 200:
                        body = resp.json()
                        audios = body.get("audios") or []
                        if not audios:
                            raise TextToSpeechError("Sarvam TTS returned no audio streams in response.")

                        audio_b64 = audios[0]
                        logger.info(
                            f"[Sarvam TTS Success] status=200, duration={duration_ms:.1f}ms, "
                            f"b64_len={len(audio_b64)}, speaker={voice_speaker}"
                        )
                        return {
                            "audio_base64": audio_b64,
                            "content_type": "audio/wav",
                            "language_code": language_code,
                            "speaker": voice_speaker,
                            "request_id": body.get("request_id")
                        }

                    # Handle HTTP Errors
                    self._handle_http_error(resp, attempt=attempt, operation="TTS")

            except httpx.TimeoutException as exc:
                if attempt <= self.max_retries:
                    logger.warning(f"[Sarvam TTS Timeout] Retrying in {backoff_sec}s... ({exc})")
                    await asyncio.sleep(backoff_sec)
                    backoff_sec *= 2
                    continue
                raise SarvamTimeoutError("Sarvam TTS request timed out.") from exc

            except httpx.RequestError as exc:
                if attempt <= self.max_retries:
                    logger.warning(f"[Sarvam TTS Network Error] Retrying in {backoff_sec}s... ({exc})")
                    await asyncio.sleep(backoff_sec)
                    backoff_sec *= 2
                    continue
                raise SarvamUnavailableError(f"Network error connecting to Sarvam TTS: {str(exc)}") from exc

        raise TextToSpeechError("Failed to synthesize speech after multiple attempts.")

    def _handle_http_error(self, resp: httpx.Response, attempt: int, operation: str) -> None:
        """Categorize Sarvam HTTP errors, deciding whether to back off or raise immediately."""
        status = resp.status_code
        logger.error(
            f"[Sarvam {operation} Error] status={status}, attempt={attempt}, body={resp.text[:300]}"
        )

        if status in (401, 403):
            # Invalid API key - DO NOT RETRY
            raise SarvamAuthenticationError(
                "Invalid or expired Sarvam API subscription key. Please verify SARVAM_API_KEY."
            )

        if status == 429:
            # Rate limited
            if attempt <= self.max_retries:
                return  # allow loop to backoff & retry
            raise SarvamRateLimitError("Sarvam rate limit exceeded. Please try again in a few seconds.")

        if 500 <= status <= 599:
            # Upstream server error
            if attempt <= self.max_retries:
                return  # allow loop to backoff & retry
            raise SarvamUnavailableError(f"Sarvam service error (HTTP {status}).")

        # 400 Bad Request or 422 Unprocessable Entity - DO NOT RETRY
        if operation == "STT":
            raise SpeechRecognitionError(f"Speech recognition rejected: {resp.text[:200]}")
        else:
            raise TextToSpeechError(f"Speech synthesis rejected: {resp.text[:200]}")
