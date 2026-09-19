import { Globe } from 'lucide-react';

export interface LanguageOption {
  code: string;
  label: string;
  nativeLabel: string;
}

export const LANGUAGE_OPTIONS: LanguageOption[] = [
  { code: 'auto', label: 'Auto Detect', nativeLabel: '✨ Auto' },
  { code: 'en-IN', label: 'English', nativeLabel: 'English (India)' },
  { code: 'hi-IN', label: 'Hindi', nativeLabel: 'हिन्दी' },
  { code: 'gu-IN', label: 'Gujarati', nativeLabel: 'ગુજરાતી' },
];

interface LanguageSelectorProps {
  selectedLanguage: string;
  onChange: (languageCode: string) => void;
  disabled?: boolean;
  compact?: boolean;
}

export default function LanguageSelector({
  selectedLanguage,
  onChange,
  disabled = false,
  compact = false,
}: LanguageSelectorProps) {
  return (
    <div className={`relative flex items-center ${compact ? 'text-xs' : 'text-sm'}`}>
      <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900/90 border border-slate-700/70 hover:border-slate-600 rounded-xl transition-colors shadow-inner">
        <Globe className={`text-violet-400 shrink-0 ${compact ? 'w-3.5 h-3.5' : 'w-4 h-4'}`} />
        <select
          value={selectedLanguage}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer pr-2 disabled:opacity-50 disabled:cursor-not-allowed appearance-none"
        >
          {LANGUAGE_OPTIONS.map((opt) => (
            <option
              key={opt.code}
              value={opt.code}
              className="bg-slate-900 text-slate-200 py-1"
            >
              {opt.nativeLabel} ({opt.label})
            </option>
          ))}
        </select>
        <span className="text-[10px] text-slate-500 pointer-events-none">▼</span>
      </div>
    </div>
  );
}
