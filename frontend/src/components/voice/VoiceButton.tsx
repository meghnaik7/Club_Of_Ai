import React from 'react';
import { Mic, Square, Loader2 } from 'lucide-react';

interface VoiceButtonProps {
  isRecording: boolean;
  isProcessing: boolean;
  onStartRecording: () => void;
  onStopRecording: () => void;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export default function VoiceButton({
  isRecording,
  isProcessing,
  onStartRecording,
  onStopRecording,
  disabled = false,
  size = 'md',
  label,
}: VoiceButtonProps) {
  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled || isProcessing) return;
    if (isRecording) {
      onStopRecording();
    } else {
      onStartRecording();
    }
  };

  const sizeClasses = {
    sm: 'w-10 h-10',
    md: 'w-14 h-14',
    lg: 'w-20 h-20',
  }[size];

  const iconSizes = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  }[size];

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative flex items-center justify-center">
        {/* Pulsing ring during recording */}
        {isRecording && (
          <div className="absolute inset-0 rounded-full bg-rose-500/30 animate-ping pointer-events-none scale-125" />
        )}
        {isRecording && (
          <div className="absolute inset-0 rounded-full bg-rose-500/20 animate-pulse scale-110 pointer-events-none" />
        )}

        <button
          type="button"
          onClick={handleClick}
          disabled={disabled || isProcessing}
          aria-label={isRecording ? 'Stop voice recording' : 'Start voice recording'}
          className={`relative z-10 cursor-pointer rounded-full flex items-center justify-center shadow-xl transition-all duration-300 ${sizeClasses} ${
            isRecording
              ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-900/60 scale-105 ring-4 ring-rose-500/40'
              : isProcessing
              ? 'bg-slate-800 text-violet-400 border border-violet-500/40 cursor-wait'
              : 'bg-violet-600 hover:bg-violet-500 text-white shadow-violet-900/50 hover:scale-105 active:scale-95 ring-2 ring-violet-400/30'
          } disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100`}
        >
          {isProcessing ? (
            <Loader2 className={`${iconSizes} animate-spin text-violet-300`} />
          ) : isRecording ? (
            <Square className={`${iconSizes} fill-current text-white`} />
          ) : (
            <Mic className={`${iconSizes} text-white`} />
          )}
        </button>
      </div>

      {label && (
        <span className="text-xs font-semibold text-slate-300 select-none">
          {isProcessing ? 'Processing speech...' : isRecording ? 'Recording (Click to stop)' : label}
        </span>
      )}
    </div>
  );
}
