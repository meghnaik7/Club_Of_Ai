import time
import logging
from typing import Optional, Dict, Any, List
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.voice.stt_service import STTService
from app.voice.tts_service import TTSService
from app.voice.schemas import VoiceChatResponse
from app.models.chat_history import RAGChatHistory
from app.voice.exceptions import VoiceProcessingError

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Coordinates the full voice pipeline:
    User Voice -> Sarvam STT -> Text -> Existing ClubOps AI Agent -> Text Response -> Sarvam TTS -> Spoken Audio.

    Crucially, voice acts strictly as an I/O modality. The existing text-based AI agent
    is the sole source of intelligence, proposals, authorization, RAG, and execution.
    """

    def __init__(
        self,
        stt_service: Optional[STTService] = None,
        tts_service: Optional[TTSService] = None
    ):
        self.stt_service = stt_service or STTService()
        self.tts_service = tts_service or TTSService()

    async def process_voice_chat(
        self,
        audio_file: UploadFile,
        user_id: int,
        active_event_id: Optional[int] = None,
        thread_id: Optional[str] = None,
        language: Optional[str] = None,
        voice: Optional[str] = None,
        db: Optional[Session] = None
    ) -> VoiceChatResponse:
        """
        Executes the end-to-end voice chat interaction:
        1. Transcribes audio via Sarvam STT (auto-detecting or using explicit language).
        2. Routes transcript to the existing ClubOps AI agent.
        3. Preserves proposals, approvals, conversation context (thread_id), and RAG.
        4. Synthesizes agent response via Sarvam TTS in the interaction language.
        5. Saves interaction to RAGChatHistory.
        6. Returns structured response with base64 audio and metadata.
        """
        total_start = time.perf_counter()
        effective_thread_id = thread_id or f"voice-user-{user_id}"

        # -------------------------------------------------------------------
        # Step 1: Speech-to-Text (Sarvam STT)
        # -------------------------------------------------------------------
        stt_start = time.perf_counter()
        stt_result = await self.stt_service.transcribe_audio(
            audio_file=audio_file,
            language=language
        )
        stt_duration_ms = (time.perf_counter() - stt_start) * 1000
        transcript = stt_result.text
        interaction_language = stt_result.language
        confidence = stt_result.confidence

        logger.info(
            f"[Voice Pipeline] STT Success ({stt_duration_ms:.1f}ms): "
            f"user_id={user_id}, lang={interaction_language}, transcript='{transcript}'"
        )

        # -------------------------------------------------------------------
        # Step 2: Route through Existing ClubOps AI Agent
        # -------------------------------------------------------------------
        agent_start = time.perf_counter()
        proposals: List[int] = []
        status_val = "COMPLETED"
        answer_text = ""
        agent_raw_result: Dict[str, Any] = {}

        try:
            from ai.tools.command_tool import execute_command
            res = execute_command.invoke({
                "command": transcript,
                "active_event_id": active_event_id,
                "user_id": user_id,
                "confirm_proposal_id": None,
                "auto_confirm": False,
                "thread_id": effective_thread_id
            })

            agent_raw_result = res if isinstance(res, dict) else {"result": res}

            if agent_raw_result.get("proposal_id"):
                proposals.append(agent_raw_result["proposal_id"])
            elif agent_raw_result.get("result") and isinstance(agent_raw_result["result"], dict) and agent_raw_result["result"].get("proposals"):
                proposals = agent_raw_result["result"]["proposals"]

            answer_text = (
                agent_raw_result.get("message")
                or str(agent_raw_result.get("result", "Command executed successfully."))
            )
            status_val = agent_raw_result.get("status", "COMPLETED")
            if agent_raw_result.get("thread_id"):
                effective_thread_id = agent_raw_result["thread_id"]

        except Exception as e:
            logger.error(f"[Voice Pipeline] AI Agent execution error: {e}", exc_info=True)
            answer_text = f"I encountered an issue processing your request: {str(e)}"
            status_val = "ERROR"

        agent_duration_ms = (time.perf_counter() - agent_start) * 1000
        logger.info(
            f"[Voice Pipeline] Agent Completed ({agent_duration_ms:.1f}ms): "
            f"status={status_val}, proposals={proposals}, answer_len={len(answer_text)}"
        )

        # -------------------------------------------------------------------
        # Step 3: Text-to-Speech (Sarvam TTS)
        # -------------------------------------------------------------------
        tts_start = time.perf_counter()
        tts_response = None
        audio_b64 = None
        data_uri = None

        try:
            tts_response = await self.tts_service.synthesize_speech(
                text=answer_text,
                language=interaction_language,
                voice=voice
            )
            audio_b64 = tts_response.audio_base64
            data_uri = f"data:{tts_response.content_type};base64,{audio_b64}"
        except Exception as e:
            logger.warning(f"[Voice Pipeline] TTS synthesis failed: {e}. Returning text-only response.")
            # Fallback: Voice pipeline does not crash completely if TTS has a transient error

        tts_duration_ms = (time.perf_counter() - tts_start) * 1000
        total_duration_ms = (time.perf_counter() - total_start) * 1000

        logger.info(
            f"[Voice Pipeline Summary] Total={total_duration_ms:.1f}ms (STT={stt_duration_ms:.1f}ms, "
            f"Agent={agent_duration_ms:.1f}ms, TTS={tts_duration_ms:.1f}ms), thread={effective_thread_id}"
        )

        # -------------------------------------------------------------------
        # Step 4: Persist Chat History
        # -------------------------------------------------------------------
        if db is not None and hasattr(db, "add") and hasattr(db, "commit"):
            try:
                history_entry = RAGChatHistory(
                    user_id=user_id,
                    event_id=active_event_id,
                    question=transcript,
                    answer=answer_text,
                    status=status_val,
                    proposal_ids=proposals
                )
                db.add(history_entry)
                db.commit()
            except Exception as e:
                logger.warning(f"Could not persist chat history: {e}")
                if hasattr(db, "rollback"):
                    db.rollback()

        return VoiceChatResponse(
            transcript=transcript,
            response_text=answer_text,
            language=interaction_language,
            audio_base64=audio_b64,
            audio_url=data_uri,
            thread_id=effective_thread_id,
            proposals=proposals,
            status=status_val,
            details=agent_raw_result,
            confidence=confidence
        )
