import io
import json
import base64
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.api import deps
from app.models.user import User
from app.voice.language_service import normalize_language, UnsupportedLanguageError
from app.voice.audio_utils import detect_audio_mime, validate_audio_upload
from app.voice.exceptions import (
    VoiceUploadError,
    AudioTooLargeError,
    UnsupportedAudioFormatError,
    SarvamAuthenticationError,
    SarvamRateLimitError
)
from app.voice.sarvam_client import SarvamClient


def mock_get_current_user():
    user = MagicMock(spec=User)
    user.id = 1
    user.email = "test@clubops.ai"
    user.full_name = "Test Lead"
    user.role = "CLUB_LEAD"
    return user


class TestLanguageService(unittest.TestCase):
    def test_canonical_languages(self):
        self.assertEqual(normalize_language("en-IN"), "en-IN")
        self.assertEqual(normalize_language("hi-IN"), "hi-IN")
        self.assertEqual(normalize_language("gu-IN"), "gu-IN")

    def test_language_aliases(self):
        self.assertEqual(normalize_language("en"), "en-IN")
        self.assertEqual(normalize_language("english"), "en-IN")
        self.assertEqual(normalize_language("hi"), "hi-IN")
        self.assertEqual(normalize_language("hindi"), "hi-IN")
        self.assertEqual(normalize_language("gu"), "gu-IN")
        self.assertEqual(normalize_language("gujarati"), "gu-IN")

    def test_auto_detection(self):
        self.assertIsNone(normalize_language(None, allow_auto=True))
        self.assertIsNone(normalize_language("", allow_auto=True))
        self.assertIsNone(normalize_language("auto", allow_auto=True))
        self.assertEqual(normalize_language(None, allow_auto=False), "en-IN")

    def test_unsupported_language_raises_error(self):
        with self.assertRaises(UnsupportedLanguageError):
            normalize_language("french")
        with self.assertRaises(UnsupportedLanguageError):
            normalize_language("es-ES")


class TestAudioValidation(unittest.IsolatedAsyncioTestCase):
    def test_detect_magic_bytes(self):
        wav_header = b"RIFF\x24\x00\x00\x00WAVE"
        self.assertEqual(detect_audio_mime(wav_header), "audio/wav")

        webm_header = b"\x1a\x45\xdf\xa3\x01\x00\x00\x00"
        self.assertEqual(detect_audio_mime(webm_header), "audio/webm")

        mp3_header = b"ID3\x03\x00\x00\x00\x00\x00\x00"
        self.assertEqual(detect_audio_mime(mp3_header), "audio/mpeg")

    async def test_validate_empty_file(self):
        mock_upload = MagicMock()
        mock_upload.filename = "test.wav"
        mock_upload.read = AsyncMock(return_value=b"")

        with self.assertRaises(VoiceUploadError):
            await validate_audio_upload(mock_upload)

    async def test_validate_too_large_file(self):
        mock_upload = MagicMock()
        mock_upload.filename = "big.wav"
        # Return 26 MB (limit is 25 MB)
        mock_upload.read = AsyncMock(return_value=b"0" * (26 * 1024 * 1024))

        with self.assertRaises(AudioTooLargeError):
            await validate_audio_upload(mock_upload)

    async def test_validate_unsupported_format(self):
        mock_upload = MagicMock()
        mock_upload.filename = "bad.exe"
        mock_upload.content_type = "application/x-msdownload"
        mock_upload.read = AsyncMock(return_value=b"MZ\x90\x00\x03\x00\x00\x00")

        with self.assertRaises(UnsupportedAudioFormatError):
            await validate_audio_upload(mock_upload)

    async def test_validate_valid_wav(self):
        mock_upload = MagicMock()
        mock_upload.filename = "test.wav"
        mock_upload.content_type = "audio/wav"
        mock_upload.read = AsyncMock(return_value=b"RIFF$\x00\x00\x00WAVEfmt ")

        content, name, mime = await validate_audio_upload(mock_upload)
        self.assertTrue(len(content) > 0)
        self.assertEqual(name, "test.wav")
        self.assertEqual(mime, "audio/wav")


class TestSarvamClient(unittest.IsolatedAsyncioTestCase):
    @patch("httpx.AsyncClient.post")
    async def test_stt_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "transcript": "Hello world",
            "language_code": "en-IN",
            "language_probability": 0.98,
            "request_id": "req-123"
        }
        mock_post.return_value = mock_resp

        client = SarvamClient(api_key="test-key")
        result = await client.speech_to_text(b"RIFF...", filename="test.wav")

        self.assertEqual(result["transcript"], "Hello world")
        self.assertEqual(result["language_code"], "en-IN")
        self.assertEqual(result["confidence"], 0.98)

    @patch("httpx.AsyncClient.post")
    async def test_tts_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        fake_b64 = base64.b64encode(b"RIFFWAVE").decode("utf-8")
        mock_resp.json.return_value = {
            "audios": [fake_b64],
            "request_id": "req-456"
        }
        mock_post.return_value = mock_resp

        client = SarvamClient(api_key="test-key")
        result = await client.text_to_speech("નમસ્તે", language_code="gu-IN", speaker="shubh")

        self.assertEqual(result["audio_base64"], fake_b64)
        self.assertEqual(result["language_code"], "gu-IN")
        self.assertEqual(result["speaker"], "shubh")

    @patch("httpx.AsyncClient.post")
    async def test_no_retry_on_401_auth_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = '{"error": "Unauthorized"}'
        mock_post.return_value = mock_resp

        client = SarvamClient(api_key="bad-key")
        with self.assertRaises(SarvamAuthenticationError):
            await client.speech_to_text(b"RIFF...", filename="test.wav")

        # Must only call once (no retries on 401)
        self.assertEqual(mock_post.call_count, 1)


class TestVoiceEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[deps.get_current_user] = mock_get_current_user
        app.dependency_overrides[deps.get_current_user_optional] = mock_get_current_user
        app.dependency_overrides[deps.get_db] = lambda: MagicMock()

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_get_languages_endpoint(self):
        res = self.client.get("/api/v1/voice/languages")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("en-IN", data["languages"])
        self.assertIn("hi-IN", data["languages"])
        self.assertIn("gu-IN", data["languages"])
        self.assertEqual(data["languages"]["gu-IN"], "Gujarati")

    @patch("app.voice.stt_service.STTService.transcribe_audio")
    def test_transcribe_endpoint(self, mock_transcribe):
        from app.voice.schemas import TranscriptionResponse
        mock_transcribe.return_value = TranscriptionResponse(
            text="રાહુલ માટે વેન્યુ તૈયાર કરવાનો એક ટાસ્ક બનાવો",
            language="gu-IN",
            confidence=0.96,
            request_id="test-req"
        )

        dummy_audio = io.BytesIO(b"RIFF$\x00\x00\x00WAVEfmt ")
        res = self.client.post(
            "/api/v1/voice/transcribe",
            files={"audio": ("speech.wav", dummy_audio, "audio/wav")},
            data={"language": "gu-IN"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["text"], "રાહુલ માટે વેન્યુ તૈયાર કરવાનો એક ટાસ્ક બનાવો")
        self.assertEqual(data["language"], "gu-IN")
        self.assertEqual(data["confidence"], 0.96)

    @patch("app.voice.tts_service.TTSService.synthesize_speech")
    def test_synthesize_endpoint_json(self, mock_synth):
        from app.voice.schemas import TTSResponse
        fake_b64 = base64.b64encode(b"RIFFWAVE").decode("utf-8")
        mock_synth.return_value = TTSResponse(
            audio_base64=fake_b64,
            content_type="audio/wav",
            language="gu-IN",
            voice="shubh"
        )

        res = self.client.post(
            "/api/v1/voice/synthesize",
            json={"text": "કામ પૂર્ણ થયું છે", "language": "gu-IN"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["audio_base64"], fake_b64)
        self.assertEqual(data["language"], "gu-IN")

    @patch("app.voice.tts_service.TTSService.synthesize_speech_bytes")
    def test_synthesize_endpoint_raw(self, mock_synth_bytes):
        mock_synth_bytes.return_value = (b"RIFFWAVE_BINARY", "audio/wav")

        res = self.client.post(
            "/api/v1/voice/synthesize?raw=true",
            json={"text": "Hello world", "language": "en-IN"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "audio/wav")
        self.assertEqual(res.content, b"RIFFWAVE_BINARY")

    @patch("app.voice.stt_service.STTService.transcribe_audio")
    @patch("ai.tools.command_tool.execute_command")
    @patch("app.voice.tts_service.TTSService.synthesize_speech")
    def test_voice_chat_endpoint(self, mock_tts, mock_agent, mock_stt):
        from app.voice.schemas import TranscriptionResponse, TTSResponse
        # 1. STT mock
        mock_stt.return_value = TranscriptionResponse(
            text="Rahul ka task complete kar do",
            language="hi-IN",
            confidence=0.92,
            request_id="req-stt"
        )
        # 2. Agent mock
        mock_agent.invoke.return_value = {
            "status": "COMPLETED",
            "message": "Rahul ka task Venue Setup successfully mark ho gaya.",
            "proposal_id": 42,
            "thread_id": "thread-123"
        }
        # 3. TTS mock
        fake_b64 = base64.b64encode(b"RIFFWAVE").decode("utf-8")
        mock_tts.return_value = TTSResponse(
            audio_base64=fake_b64,
            content_type="audio/wav",
            language="hi-IN",
            voice="shubh"
        )

        dummy_audio = io.BytesIO(b"RIFF$\x00\x00\x00WAVEfmt ")
        res = self.client.post(
            "/api/v1/voice/chat",
            files={"audio": ("speech.wav", dummy_audio, "audio/wav")},
            data={"language": "hi-IN", "thread_id": "thread-123"}
        )

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["transcript"], "Rahul ka task complete kar do")
        self.assertEqual(data["language"], "hi-IN")
        self.assertIn("Venue Setup", data["response_text"])
        self.assertEqual(data["proposals"], [42])
        self.assertEqual(data["audio_base64"], fake_b64)
        self.assertTrue(data["audio_url"].startswith("data:audio/wav;base64,"))
        self.assertEqual(data["thread_id"], "thread-123")


if __name__ == "__main__":
    unittest.main()
