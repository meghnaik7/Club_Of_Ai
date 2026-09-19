import React, { useState, useRef, useEffect, useCallback } from 'react';
import { X, Mic, Volume2, AlertCircle, Sparkles, RefreshCw } from 'lucide-react';
import LanguageSelector from './LanguageSelector';
import VoiceButton from './VoiceButton';
import VoiceWaveform from './VoiceWaveform';
import VoiceTranscript from './VoiceTranscript';
import VoiceResponse from './VoiceResponse';
import VoiceService from '../../services/voice.service';
import type { VoiceChatResponse } from '../../services/voice.service';

interface VoiceAssistantProps {
  isOpen: boolean;
  onClose: () => void;
  activeEventId?: number;
  initialThreadId?: string;
  onTurnComplete?: (res: VoiceChatResponse) => void;
}

export default function VoiceAssistant({
  isOpen,
  onClose,
  activeEventId,
  initialThreadId,
  onTurnComplete,
}: VoiceAssistantProps) {
  const [selectedLanguage, setSelectedLanguage] = useState<string>('auto');
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [threadId, setThreadId] = useState<string | undefined>(initialThreadId);
  const [lastTurn, setLastTurn] = useState<VoiceChatResponse | null>(null);
  const [statusState, setStatusState] = useState<'idle' | 'recording' | 'processing' | 'playing'>('idle');

  // Audio recording refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  // Stop recording & cleanup on unmount or close
  const cleanupRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsRecording(false);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      cleanupRecording();
    }
  }, [isOpen, cleanupRecording]);

  const startRecording = async () => {
    setErrorMessage(null);
    audioChunksRef.current = [];

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Microphone access is not supported by your browser or connection is not secure.');
      }

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
      } catch {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      }
      streamRef.current = stream;

      // Select supported mime type
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : MediaRecorder.isTypeSupported('audio/ogg')
        ? 'audio/ogg'
        : '';

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        // Stop audio tracks after recorder has completed flushing
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
        }

        const audioBlob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });

        if (audioBlob.size > 100) {
          await handleAudioSubmit(audioBlob);
        } else {
          setErrorMessage('Recording was too short or silent. Please click and speak clearly.');
          setStatusState('idle');
          setIsProcessing(false);
        }
      };

      recorder.start(100);
      setIsRecording(true);
      setStatusState('recording');
    } catch (err: any) {
      console.error('Microphone error:', err);
      setErrorMessage(
        err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError'
          ? 'Microphone permission denied. Please allow microphone access in your browser settings.'
          : err.message || 'Unable to access microphone.'
      );
      setStatusState('idle');
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setStatusState('processing');
  };

  const handleAudioSubmit = async (audioBlob: Blob) => {
    setIsProcessing(true);
    setStatusState('processing');
    setErrorMessage(null);

    try {
      const response = await VoiceService.voiceChat(audioBlob, {
        threadId,
        eventId: activeEventId,
        language: selectedLanguage,
      });

      setLastTurn(response);
      if (response.thread_id) {
        setThreadId(response.thread_id);
      }
      setStatusState(response.audio_url ? 'playing' : 'idle');

      if (onTurnComplete) {
        onTurnComplete(response);
      }
    } catch (err: any) {
      console.error('Voice chat error:', err);
      const detail =
        err.response?.data?.error?.message ||
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        err.message;
      setErrorMessage(
        typeof detail === 'string'
          ? detail
          : "I couldn't process the voice request. Please try speaking again."
      );
      setStatusState('idle');
    } finally {
      setIsProcessing(false);
    }
  };


  const handleConfirmProposal = async (proposalId: number) => {
    // Send confirmation to backend
    setIsProcessing(true);
    setStatusState('processing');
    try {
      // Use existing text confirmation via speech synthesize or execute command
      const AIService = (await import('../../services/ai.service')).default;
      const res = await AIService.confirmProposal(proposalId, activeEventId);
      
      // Synthesize confirmation spoken response
      const synth = await VoiceService.synthesize({
        text: res.response,
        language: lastTurn?.language || 'en-IN',
      });

      setLastTurn({
        transcript: `Confirm proposal #${proposalId}`,
        response_text: res.response,
        language: lastTurn?.language || 'en-IN',
        audio_url: `data:${synth.content_type};base64,${synth.audio_base64}`,
        thread_id: threadId,
        proposals: [],
        status: res.status,
      });
      setStatusState('playing');
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to apply proposal.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRejectProposal = async (proposalId: number) => {
    setIsProcessing(true);
    setStatusState('processing');
    try {
      const AIService = (await import('../../services/ai.service')).default;
      const res = await AIService.rejectProposal(proposalId, activeEventId);
      setLastTurn((prev) =>
        prev
          ? {
              ...prev,
              response_text: `Proposal #${proposalId} rejected.`,
              proposals: [],
            }
          : null
      );
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to reject proposal.');
    } finally {
      setIsProcessing(false);
      setStatusState('idle');
    }
  };

  const handleSimulatedVoice = async (promptText: string, lang: string) => {
    setIsProcessing(true);
    setStatusState('processing');
    setErrorMessage(null);
    try {
      const synth = await VoiceService.synthesize({ text: promptText, language: lang });
      const byteChars = atob(synth.audio_base64);
      const byteNumbers = new Array(byteChars.length);
      for (let i = 0; i < byteChars.length; i++) {
        byteNumbers[i] = byteChars.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: synth.content_type || 'audio/wav' });
      await handleAudioSubmit(blob);
    } catch (err: any) {
      console.error('Test voice error:', err);
      setErrorMessage(err.message || 'Error running voice test.');
      setStatusState('idle');
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md overflow-y-auto"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative z-10 bg-slate-950 border border-slate-800 rounded-3xl w-full max-w-lg shadow-2xl shadow-violet-950/50 flex flex-col overflow-hidden my-auto"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-violet-600 flex items-center justify-center shadow-md shadow-violet-950">
              <Mic className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                ClubOps AI Voice
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/30">
                  Sarvam AI
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">English • हिन्दी • ગુજરાતી</p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close voice assistant"
            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Controls Bar: Language Selector */}
        <div className="px-6 py-3 border-b border-slate-800/50 flex items-center justify-between bg-slate-900/30">
          <span className="text-xs font-medium text-slate-400">Speech Language:</span>
          <LanguageSelector
            selectedLanguage={selectedLanguage}
            onChange={setSelectedLanguage}
            disabled={isRecording || isProcessing}
            compact
          />
        </div>

        {/* Body & Dialogue Area */}
        <div className="p-6 flex-1 max-h-[360px] overflow-y-auto space-y-4">
          {/* Error banner */}
          {errorMessage && (
            <div className="flex items-start gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs animate-in fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
              <p className="flex-1">{errorMessage}</p>
            </div>
          )}

          {/* If no interaction yet, show friendly prompt & 1-click test buttons */}
          {!lastTurn && !isRecording && !isProcessing && (
            <div className="text-center py-4 px-2 flex flex-col items-center">
              <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-violet-400 mb-3 shadow-inner">
                <Sparkles className="w-6 h-6" />
              </div>
              <h4 className="text-base font-semibold text-white mb-1">Speak Naturally</h4>
              <p className="text-xs text-slate-400 max-w-sm mb-4">
                Click the microphone to speak, or click any sample prompt below to test immediately:
              </p>

              {/* 1-Click Multilingual Test Prompts */}
              <div className="flex flex-col gap-2 w-full max-w-xs">
                <button
                  type="button"
                  onClick={() => handleSimulatedVoice('રાહુલ માટે વેન્યુ તૈયાર કરવાનો ટાસ્ક બનાવો.', 'gu-IN')}
                  className="px-3 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-violet-500/50 rounded-xl text-left text-xs text-slate-200 transition-all flex items-center justify-between cursor-pointer group shadow-sm"
                >
                  <span className="truncate">🚩 "રાહુલ માટે ટાસ્ક બનાવો"</span>
                  <span className="text-[10px] text-violet-400 group-hover:text-violet-300 ml-2 shrink-0">ગુજરાતી ▶</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleSimulatedVoice('राहुल के लिए वेन्यू तैयार करने का एक टास्क बनाओ।', 'hi-IN')}
                  className="px-3 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-violet-500/50 rounded-xl text-left text-xs text-slate-200 transition-all flex items-center justify-between cursor-pointer group shadow-sm"
                >
                  <span className="truncate">🇮🇳 "राहुल के लिए टास्क बनाओ"</span>
                  <span className="text-[10px] text-amber-400 group-hover:text-amber-300 ml-2 shrink-0">हिन्दी ▶</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleSimulatedVoice('Create a task for Rahul to prepare venue tomorrow.', 'en-IN')}
                  className="px-3 py-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-violet-500/50 rounded-xl text-left text-xs text-slate-200 transition-all flex items-center justify-between cursor-pointer group shadow-sm"
                >
                  <span className="truncate">🇬🇧 "Create task for Rahul"</span>
                  <span className="text-[10px] text-emerald-400 group-hover:text-emerald-300 ml-2 shrink-0">English ▶</span>
                </button>
              </div>
            </div>
          )}

          {/* User Speech Transcript */}
          {lastTurn && (
            <VoiceTranscript
              transcript={lastTurn.transcript}
              language={lastTurn.language}
              confidence={lastTurn.confidence}
            />
          )}

          {/* AI Voice & Text Response */}
          {lastTurn && (
            <VoiceResponse
              responseText={lastTurn.response_text}
              audioUrl={lastTurn.audio_url}
              language={lastTurn.language}
              proposals={lastTurn.proposals}
              citations={lastTurn.details?.citations}
              onConfirmProposal={handleConfirmProposal}
              onRejectProposal={handleRejectProposal}
            />
          )}
        </div>

        {/* Bottom Waveform & Speak Controls */}
        <div className="p-6 bg-slate-900/90 border-t border-slate-800/80 flex flex-col items-center gap-3">
          {/* Animated Waveform */}
          <VoiceWaveform state={statusState} barCount={24} height={36} />

          {/* Voice Record Button */}
          <VoiceButton
            isRecording={isRecording}
            isProcessing={isProcessing}
            onStartRecording={startRecording}
            onStopRecording={stopRecording}
            size="lg"
            label={isRecording ? 'Click to finish' : 'Click to speak'}
          />
        </div>
      </div>
    </div>
  );
}

