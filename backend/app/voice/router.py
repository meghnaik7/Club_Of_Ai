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
    VoiceRAGResponse,
    VoiceRAGCitation,
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


@router.post("/rag-query", response_model=VoiceRAGResponse)
async def voice_rag_query(
    audio: UploadFile = File(..., description="Spoken question audio"),
    event_id: Optional[int] = Form(None, description="Optional event ID scope"),
    category: Optional[str] = Form(None, description="Optional document category filter"),
    language: Optional[str] = Form(None, description="Language hint (en-IN, hi-IN, gu-IN, or auto)"),
    voice: Optional[str] = Form(None, description="TTS speaker voice"),
    db: Session = Depends(deps.get_db),
    current_user: Optional[User] = Depends(deps.get_current_user_optional),
) -> VoiceRAGResponse:
    """
    Voice RAG Query:
    1. Transcribes spoken question via Sarvam STT.
    2. Executes end-to-end RAG pipeline (CRAG + Self-RAG + Re-Ranking).
    3. Synthesizes grounded answer to voice audio via Sarvam TTS.
    4. Persists the question and answer with citations in RAGChatHistory.
    """
    try:
        # 1. Speech to Text
        stt_result = await _stt_service.transcribe_audio(audio_file=audio, language=language)
        transcript = stt_result.text.strip()
        interaction_language = stt_result.language

        # 2. Execute RAG pipeline
        from ai.rag.pipeline import execute_rag_pipeline
        rag_resp = execute_rag_pipeline(
            db=db,
            query=transcript,
            event_id=event_id,
            category=category,
            top_k=5
        )

        if isinstance(rag_resp, dict):
            answer_text = rag_resp.get("answer", "")
            raw_citations = rag_resp.get("citations", [])
            confidence_val = rag_resp.get("confidence_score") or rag_resp.get("confidence")
        else:
            answer_text = getattr(rag_resp, "answer", "")
            raw_citations = getattr(rag_resp, "citations", [])
            confidence_val = getattr(rag_resp, "confidence_score", None) or getattr(rag_resp, "confidence", None)

        # 3. Text to Speech of the answer (synthesizes concise speech)
        speech_text = answer_text[:400] if len(answer_text) > 400 else answer_text
        tts_res = None
        try:
            tts_res = await _tts_service.synthesize_speech(
                text=speech_text,
                language=interaction_language,
                voice=voice
            )
        except Exception:
            pass

        # Normalize citations for response & persistence
        parsed_citations = []
        serializable_citations = []
        for c in raw_citations:
            if isinstance(c, dict):
                s_name = c.get("source", "Document")
                p = c.get("page")
                sec = c.get("section")
            elif hasattr(c, "model_dump"):
                d = c.model_dump()
                s_name = d.get("source", "Document")
                p = d.get("page")
                sec = d.get("section")
            else:
                s_name = getattr(c, "source", "Document")
                p = getattr(c, "page", None)
                sec = getattr(c, "section", None)

            parsed_citations.append(VoiceRAGCitation(source=s_name, page=p, section=sec))
            serializable_citations.append({"source": s_name, "page": p, "section": sec})

        # 4. Save to RAGChatHistory
        from app.models.chat_history import RAGChatHistory
        try:
            history_record = RAGChatHistory(
                user_id=current_user.id if current_user else None,
                event_id=str(event_id) if event_id else None,
                question=transcript,
                answer=answer_text,
                citations=serializable_citations,
                confidence=confidence_val
            )
            db.add(history_record)
            db.commit()
        except Exception:
            db.rollback()

        audio_url_val = (
            f"data:{tts_res.content_type};base64,{tts_res.audio_base64}"
            if tts_res and tts_res.audio_base64
            else None
        )

        return VoiceRAGResponse(
            transcript=transcript,
            answer=answer_text,
            language=interaction_language,
            confidence=confidence_val,
            citations=parsed_citations,
            audio_base64=tts_res.audio_base64 if tts_res else None,
            audio_url=audio_url_val,
            content_type=tts_res.content_type if tts_res else "audio/wav",
            status="SUCCESS"
        )
    except VoiceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.to_dict()["error"])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"code": "SPEECH_RECOGNITION_FAILED", "message": f"Transcription error: {str(e)}"}
        )

