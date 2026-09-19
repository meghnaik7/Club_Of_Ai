import React from 'react';
import { User, Volume2, Sparkles } from 'lucide-react';
import { LANGUAGE_OPTIONS } from './LanguageSelector';

interface VoiceTranscriptProps {
  transcript: string;
  language?: string;
  confidence?: number | null;
  timestamp?: Date;
}

export default function VoiceTranscript({
  transcript,
  language,
  confidence,
  timestamp = new Date(),
}: VoiceTranscriptProps) {
  if (!transcript) return null;

  const langMatch = LANGUAGE_OPTIONS.find(
    (l) => l.code === language || l.code.toLowerCase() === language?.toLowerCase()
  );
  const langLabel = langMatch ? `${langMatch.nativeLabel} (${langMatch.label})` : language;

  return (
    <div className="flex gap-3 flex-row-reverse animate-in fade-in slide-in-from-bottom-2 duration-300">
      <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0 shadow-md shadow-indigo-950">
        <User className="w-4 h-4 text-white" />
      </div>

      <div className="max-w-[85%] items-end flex flex-col gap-1.5">
        <div className="rounded-2xl rounded-tr-sm px-4 py-3 bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-md text-sm leading-relaxed">
          <p className="font-normal whitespace-pre-wrap">{transcript}</p>
        </div>

        <div className="flex items-center gap-2 text-[10px] text-slate-400">
          {language && (
            <span className="flex items-center gap-1 bg-slate-800/80 px-2 py-0.5 rounded-full border border-slate-700/60 font-medium text-indigo-300">
              <Sparkles className="w-2.5 h-2.5 text-indigo-400" />
              {langLabel}
            </span>
          )}

          {confidence !== null && confidence !== undefined && (
            <span className="text-slate-500">
              Confidence: {Math.round(confidence * 100)}%
            </span>
          )}

          <span className="text-slate-500">
            {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    </div>
  );
}
