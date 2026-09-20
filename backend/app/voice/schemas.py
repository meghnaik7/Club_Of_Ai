from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class TranscriptionResponse(BaseModel):
    text: str = Field(..., description="Recognized speech text")
    language: str = Field(..., description="Normalized language code, e.g. 'en-IN', 'hi-IN', 'gu-IN'")
    confidence: Optional[float] = Field(None, description="Confidence score if provided by provider, else null")
    request_id: Optional[str] = Field(None, description="Sarvam request ID for traceability")


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2500, description="Text to synthesize into voice audio")
    language: str = Field("en-IN", description="Language code (en-IN, hi-IN, gu-IN)")
    voice: Optional[str] = Field(None, description="Voice speaker name (e.g. 'shubh')")
    pace: Optional[float] = Field(1.0, ge=0.5, le=2.0, description="Speech rate from 0.5 to 2.0")


class TTSResponse(BaseModel):
    audio_base64: str = Field(..., description="Base64-encoded audio WAV/MP3")
    content_type: str = Field("audio/wav", description="Audio MIME type")
    language: str = Field(..., description="Language synthesized")
    voice: str = Field(..., description="Speaker voice used")
    duration_seconds: Optional[float] = Field(None, description="Estimated or reported duration")


class VoiceChatResponse(BaseModel):
    transcript: str = Field(..., description="User voice transcription")
    response_text: str = Field(..., description="ClubOps AI agent text response")
    language: str = Field(..., description="Detected or configured interaction language")
    audio_base64: Optional[str] = Field(None, description="Base64 encoded speech audio response")
    audio_url: Optional[str] = Field(None, description="Optional playback URL or data URI")
    thread_id: Optional[str] = Field(None, description="LangGraph conversational thread ID")
    proposals: List[int] = Field(default_factory=list, description="IDs of any proposals created or referenced")
    status: str = Field("COMPLETED", description="Status of the interaction")
    details: Optional[Dict[str, Any]] = Field(None, description="Execution details, proposals, or citations")
    confidence: Optional[float] = Field(None, description="STT confidence score if available")


class LanguageListResponse(BaseModel):
    languages: Dict[str, str] = Field(..., description="Map of code to display name")
    default_language: str = Field("en-IN", description="Default configured language")
