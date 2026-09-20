from typing import Optional, Dict, Any

class VoiceError(Exception):
    """Base exception for all voice module errors."""
    def __init__(self, message: str, code: str = "VOICE_ERROR", status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                **({"details": self.details} if self.details else {})
            }
        }


class VoiceUploadError(VoiceError):
    """Raised when an audio upload is invalid, empty, or corrupted."""
    def __init__(self, message: str = "Audio upload is invalid or empty.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="VOICE_UPLOAD_INVALID", status_code=400, details=details)


class UnsupportedAudioFormatError(VoiceError):
    """Raised when the uploaded audio MIME type or extension is not supported."""
    def __init__(self, message: str = "Unsupported audio format. Please provide WAV, WebM, MP3, or OGG audio.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="UNSUPPORTED_AUDIO_FORMAT", status_code=415, details=details)


class AudioTooLargeError(VoiceError):
    """Raised when the uploaded audio file exceeds the maximum allowed size."""
    def __init__(self, message: str = "Audio file size exceeds the allowed limit.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="AUDIO_TOO_LARGE", status_code=413, details=details)


class UnsupportedLanguageError(VoiceError):
    """Raised when an unsupported language is requested."""
    def __init__(self, language: str, supported: Optional[list] = None):
        details = {
            "requested_language": language,
            "supported_languages": supported or ["en-IN", "hi-IN", "gu-IN"]
        }
        super().__init__(
            message=f"Unsupported language '{language}'. Supported languages: {', '.join(details['supported_languages'])}.",
            code="UNSUPPORTED_LANGUAGE",
            status_code=400,
            details=details
        )


class SarvamAuthenticationError(VoiceError):
    """Raised when Sarvam API credentials are missing, invalid, or expired."""
    def __init__(self, message: str = "Authentication failed with voice provider."):
        # Never leak the actual key or sensitive upstream body
        super().__init__(message, code="VOICE_AUTH_FAILED", status_code=502)


class SarvamRateLimitError(VoiceError):
    """Raised when Sarvam API rate limit has been reached."""
    def __init__(self, message: str = "Voice service rate limit exceeded. Please wait a moment and try again."):
        super().__init__(message, code="VOICE_RATE_LIMIT_EXCEEDED", status_code=429)


class SarvamTimeoutError(VoiceError):
    """Raised when a request to Sarvam times out."""
    def __init__(self, message: str = "Voice processing timed out. Please try again with shorter speech."):
        super().__init__(message, code="VOICE_TIMEOUT", status_code=504)


class SarvamUnavailableError(VoiceError):
    """Raised when Sarvam service is unavailable or returning 5xx errors."""
    def __init__(self, message: str = "Voice service is temporarily unavailable. Please try again shortly."):
        super().__init__(message, code="VOICE_SERVICE_UNAVAILABLE", status_code=503)


class SpeechRecognitionError(VoiceError):
    """Raised when speech recognition fails to produce a valid transcript."""
    def __init__(self, message: str = "I couldn't understand the audio. Please try speaking clearly again.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="SPEECH_RECOGNITION_FAILED", status_code=422, details=details)


class TextToSpeechError(VoiceError):
    """Raised when voice synthesis fails."""
    def __init__(self, message: str = "Failed to generate speech audio.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="TEXT_TO_SPEECH_FAILED", status_code=502, details=details)


class VoiceProcessingError(VoiceError):
    """Generic error during voice pipeline orchestration."""
    def __init__(self, message: str = "An unexpected error occurred during voice processing.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="VOICE_PROCESSING_FAILED", status_code=500, details=details)
