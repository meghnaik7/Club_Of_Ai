import React, { useState, useRef, useEffect } from 'react';
import { Bot, Play, Pause, RotateCcw, CheckCircle, XCircle, Volume2, Sparkles, FileText } from 'lucide-react';
import VoiceWaveform from './VoiceWaveform';

interface VoiceResponseProps {
  responseText: string;
  audioUrl?: string;
  language?: string;
  proposals?: number[];
  citations?: Array<{ title?: string; source?: string }>;
  onConfirmProposal?: (id: number) => void;
  onRejectProposal?: (id: number) => void;
  autoPlay?: boolean;
}

export default function VoiceResponse({
  responseText,
  audioUrl,
  language,
  proposals = [],
  citations = [],
  onConfirmProposal,
  onRejectProposal,
  autoPlay = true,
}: VoiceResponseProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

  // Play audio when audioUrl changes
  useEffect(() => {
    if (audioUrl && autoPlay && audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => {
          console.warn('Auto-play was prevented by browser policy:', err);
          setIsPlaying(false);
        });
    }
  }, [audioUrl, autoPlay]);

  const togglePlayPause = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current
        .play()
        .then(() => setIsPlaying(true))
        .catch((err) => console.error('Playback error:', err));
    }
  };

  const handleReplay = () => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = 0;
    audioRef.current
      .play()
      .then(() => setIsPlaying(true))
      .catch((err) => console.error('Replay error:', err));
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    const current = audioRef.current.currentTime;
    const total = audioRef.current.duration || 1;
    setProgress((current / total) * 100);
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setProgress(0);
  };

  return (
    <div className="flex gap-3 flex-row animate-in fade-in slide-in-from-bottom-2 duration-300">
      {/* Hidden HTML5 audio element */}
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onTimeUpdate={handleTimeUpdate}
          onEnded={handleEnded}
        />
      )}

      {/* Bot Avatar */}
      <div className="w-8 h-8 rounded-full bg-violet-600/30 border border-violet-500/30 flex items-center justify-center shrink-0 shadow-md">
        <Bot className="w-4 h-4 text-violet-400" />
      </div>

      <div className="max-w-[85%] items-start flex flex-col gap-2.5 w-full">
        {/* Main Response Bubble */}
        <div className="rounded-2xl rounded-tl-sm px-4 py-3 bg-slate-800/90 text-slate-100 border border-slate-700/60 shadow-lg text-sm leading-relaxed w-full">
          <p className="whitespace-pre-wrap">{responseText}</p>

          {/* Audio Controls Bar */}
          {audioUrl && (
            <div className="mt-3 pt-2.5 border-t border-slate-700/50 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={togglePlayPause}
                    aria-label={isPlaying ? 'Pause spoken response' : 'Play spoken response'}
                    className="w-7 h-7 rounded-full bg-violet-600 hover:bg-violet-500 text-white flex items-center justify-center transition-colors shadow-sm"
                  >
                    {isPlaying ? (
                      <Pause className="w-3.5 h-3.5" />
                    ) : (
                      <Play className="w-3.5 h-3.5 ml-0.5" />
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={handleReplay}
                    aria-label="Replay audio"
                    className="w-7 h-7 rounded-full bg-slate-700 hover:bg-slate-600 text-slate-300 flex items-center justify-center transition-colors"
                  >
                    <RotateCcw className="w-3 h-3" />
                  </button>

                  <span className="text-xs text-slate-400 font-medium flex items-center gap-1">
                    <Volume2 className="w-3 h-3 text-violet-400" />
                    Sarvam Voice ({language || 'Multilingual'})
                  </span>
                </div>

                {isPlaying && (
                  <span className="text-[10px] bg-violet-500/20 text-violet-300 border border-violet-500/30 px-2 py-0.5 rounded-full font-medium animate-pulse">
                    Speaking
                  </span>
                )}
              </div>

              {/* Progress track */}
              <div className="w-full bg-slate-700/60 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-violet-500 to-indigo-500 h-full transition-all duration-100"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Proposals & Safety Confirmations */}
        {proposals && proposals.length > 0 && (
          <div className="flex flex-col gap-2 w-full">
            {proposals.map((pid) => (
              <div
                key={pid}
                className="bg-slate-850/90 border border-violet-500/30 rounded-xl p-3 shadow-md bg-slate-900"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-violet-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                    Proposal #{pid} Requires Confirmation
                  </span>
                  <span className="text-[10px] text-slate-500">Voice or Click</span>
                </div>

                <p className="text-xs text-slate-400 mb-3">
                  Say <span className="text-emerald-400 font-semibold">"Yes"</span> to apply, or{' '}
                  <span className="text-rose-400 font-semibold">"No"</span> to reject.
                </p>

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => onConfirmProposal && onConfirmProposal(pid)}
                    className="flex-1 flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors shadow-sm"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    Apply Proposal
                  </button>
                  <button
                    type="button"
                    onClick={() => onRejectProposal && onRejectProposal(pid)}
                    className="flex-1 flex items-center justify-center gap-1.5 bg-slate-800 hover:bg-red-600/60 text-slate-300 hover:text-red-200 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors border border-slate-700"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Citations from RAG if any */}
        {citations && citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-0.5">
            {citations.map((c, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 bg-slate-800/80 border border-slate-700/60 text-slate-400 text-[10px] px-2 py-0.5 rounded-md"
              >
                <FileText className="w-3 h-3 text-indigo-400" />
                {c.title || c.source || `Citation ${i + 1}`}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
