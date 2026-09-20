from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.voice.config import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from app.voice.schemas import (
    TranscriptionResponse,
    TTSRequest,
    TTSResponse,
    VoiceChatResponse,
    LanguageListResponse,
)
from app.voice.stt_service import STTService
from app.voice.tts_service import TTSService
from app.voice.service import VoiceService
from app.voice.exceptions import VoiceError

router = APIRouter()

# Instantiate singletons for services
_stt_service = STTService()
_tts_service = TTSService()
_voice_service = VoiceService(stt_service=_stt_service, tts_service=_tts_service)


@router.get("/languages", response_model=LanguageListResponse)
def get_supported_languages() -> LanguageListResponse:
    """
    Returns the list of supported multilingual speech processing languages
    along with their human-readable labels.
    """
    return LanguageListResponse(
        languages=SUPPORTED_LANGUAGES,
        default_language=DEFAULT_LANGUAGE
    )


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_speech(
    audio: UploadFile = File(..., description="Uploaded audio file (WAV, WebM, MP3, OGG)"),
    language: Optional[str] = Form(None, description="Optional language hint (en-IN, hi-IN, gu-IN, or auto)"),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> TranscriptionResponse:
    """
    Transcribes audio into text using Sarvam AI Speech-to-Text.
    Supports English, Hindi, and Gujarati with automatic language detection when omitted.
    """
    try:
        return await _stt_service.transcribe_audio(audio_file=audio, language=language)
    except VoiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict()["error"])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "SPEECH_RECOGNITION_FAILED", "message": f"Transcription error: {str(e)}"}
        )


@router.post("/synthesize")
async def synthesize_speech(
    request: TTSRequest,
    raw: bool = Query(False, description="If true, returns binary audio/wav directly instead of JSON"),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
):
    """
    Synthesizes speech audio from input text using Sarvam Bulbul TTS.
    Returns JSON with base64 audio by default, or raw binary audio when ?raw=true.
    """
    try:
        if raw:
            audio_bytes, content_type = await _tts_service.synthesize_speech_bytes(
                text=request.text,
                language=request.language,
                voice=request.voice,
                pace=request.pace or 1.0
            )
            return Response(content=audio_bytes, media_type=content_type)
        else:
            return await _tts_service.synthesize_speech(
                text=request.text,
                language=request.language,
                voice=request.voice,
                pace=request.pace or 1.0
            )
    except VoiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict()["error"])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "TEXT_TO_SPEECH_FAILED", "message": f"Synthesis error: {str(e)}"}
        )


@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(
    audio: UploadFile = File(..., description="Audio recording of user voice command"),
    thread_id: Optional[str] = Form(None, description="Conversational thread ID to preserve context"),
    event_id: Optional[int] = Form(None, description="Active event ID for context filtering"),
    language: Optional[str] = Form(None, description="Preferred language code or auto"),
    voice: Optional[str] = Form(None, description="Optional voice speaker override"),
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> VoiceChatResponse:
    """
    Full multimodal voice pipeline:
    1. Transcribes incoming audio via Sarvam STT.
    2. Sends the recognized text to the existing ClubOps AI LangGraph agent.
    3. Retains all safety guards, approval proposals, permissions, and thread state.
    4. Synthesizes the agent's textual response using Sarvam TTS in the user's language.
    5. Returns both the text and spoken audio together with any staged proposals.
    """
    effective_user_id = current_user.id if current_user else 1
    try:
        return await _voice_service.process_voice_chat(
            audio_file=audio,
            user_id=effective_user_id,
            active_event_id=event_id,
            thread_id=thread_id,
            language=language,
            voice=voice,
            db=db
        )
    except VoiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict()["error"])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "VOICE_PROCESSING_FAILED", "message": f"Voice chat failed: {str(e)}"}
        )
