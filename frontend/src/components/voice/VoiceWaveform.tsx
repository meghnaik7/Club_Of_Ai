import React from 'react';

interface VoiceWaveformProps {
  state: 'idle' | 'recording' | 'processing' | 'playing';
  barCount?: number;
  height?: number;
}

export default function VoiceWaveform({
  state,
  barCount = 20,
  height = 40,
}: VoiceWaveformProps) {
  const isRecording = state === 'recording';
  const isPlaying = state === 'playing';
  const isProcessing = state === 'processing';

  const bars = Array.from({ length: barCount }, (_, i) => i);

  return (
    <div
      className="flex items-center justify-center gap-1 px-4 py-2"
      style={{ height: `${height}px` }}
      aria-label={`Audio status: ${state}`}
    >
      {bars.map((index) => {
        // Compute pseudo-random heights or animated heights based on index
        const delay = (index % 5) * 0.15;
        const duration = 0.6 + ((index % 4) * 0.15);

        let colorClasses = 'bg-slate-700';
        let barHeight = '15%';

        if (isRecording) {
          colorClasses = 'bg-gradient-to-t from-rose-500 to-amber-400 animate-pulse';
          // Calculate varied wave heights for natural voice look
          const sinFactor = Math.sin((index / barCount) * Math.PI);
          barHeight = `${Math.max(25, sinFactor * 90)}%`;
        } else if (isPlaying) {
          colorClasses = 'bg-gradient-to-t from-indigo-500 to-cyan-400';
          const sinFactor = Math.sin(((index + 3) / barCount) * Math.PI);
          barHeight = `${Math.max(20, sinFactor * 85)}%`;
        } else if (isProcessing) {
          colorClasses = 'bg-gradient-to-t from-violet-500 to-indigo-400';
          barHeight = `${20 + ((index % 3) * 25)}%`;
        }

        return (
          <div
            key={index}
            className={`w-1 rounded-full transition-all duration-200 ${colorClasses}`}
            style={{
              height: barHeight,
              animationDuration: isRecording || isPlaying || isProcessing ? `${duration}s` : undefined,
              animationDelay: `${delay}s`,
            }}
          />
        );
      })}
    </div>
  );
}
