import React, { useState, useRef, useEffect } from 'react';
import { X, Send, Bot, User, Loader2, CheckCircle, XCircle, Sparkles, ChevronRight } from 'lucide-react';
import AIService from '../services/ai.service';
import type { ChatMessage, AICommandRequest } from '../services/ai.service';


interface AIChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
  activeEventId?: number;
}

const SUGGESTED_COMMANDS = [
  'List all upcoming events',
  'Show volunteers with low task load',
  'Generate an announcement for the next event',
  'What tasks are overdue?',
  'Summarize recent documents',
];

function MessageBubble({ msg, onConfirm, onReject }: {
  msg: ChatMessage;
  onConfirm: (id: number) => void;
  onReject: (id: number) => void;
}) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
        isUser ? 'bg-indigo-600 shadow-md shadow-indigo-600/30' : 'bg-violet-600/25 border border-violet-500/30 shadow-sm'
      }`}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-violet-400" />
        )}
      </div>

      <div className={`max-w-[85%] sm:max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-2`}>
        {/* Bubble */}
        <div className={`rounded-2xl px-4 py-2.5 sm:py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-indigo-600 text-white rounded-tr-sm shadow-sm'
            : 'bg-slate-800/90 text-slate-200 border border-slate-700/50 rounded-tl-sm shadow-sm'
        }`}>
          <p className="whitespace-pre-wrap">{msg.content}</p>
        </div>

        {/* Status badge */}
        {msg.status && msg.status !== 'COMPLETED' && (
          <span className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
            msg.status === 'PENDING_CONFIRMATION'
              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
              : msg.status === 'ERROR'
              ? 'bg-red-500/10 text-red-400 border border-red-500/20'
              : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
          }`}>
            {msg.status.replace('_', ' ')}
          </span>
        )}

        {/* Proposal actions */}
        {msg.proposals && msg.proposals.length > 0 && (
          <div className="flex flex-col gap-2.5 w-full mt-1">
            {msg.proposals.map(pid => (
              <div key={pid} className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-3.5 space-y-2.5 shadow-sm">
                <p className="text-xs text-slate-300 font-medium">Proposal #{pid} — awaiting confirmation</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => onConfirm(pid)}
                    className="flex-1 flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3 py-2 rounded-lg transition-colors shadow-sm"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    Apply
                  </button>
                  <button
                    onClick={() => onReject(pid)}
                    className="flex-1 flex items-center justify-center gap-1.5 bg-slate-700/80 hover:bg-red-500/20 text-slate-300 hover:text-red-300 border border-transparent hover:border-red-500/30 text-xs font-semibold px-3 py-2 rounded-lg transition-colors"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[10px] text-slate-500 px-1">
          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
}

export default function AIChatPanel({ isOpen, onClose, activeEventId }: AIChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: `👋 Hi! I'm your ClubOps AI assistant.\n\nYou can ask me to:\n• List or create events, tasks, or volunteers\n• Generate announcements\n• Summarize documents\n• Execute complex multi-step commands\n\nTry typing a command below!`,
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const req: AICommandRequest = {
        command: text.trim(),
        active_event_id: activeEventId,
      };
      const res = await AIService.executeCommand(req);

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: res.response,
        timestamp: new Date(),
        proposals: res.proposals,
        status: res.status,
        details: res.details,
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err: any) {
      const errMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `⚠️ Error: ${err?.response?.data?.detail || err?.message || 'Something went wrong. Please try again.'}`,
        timestamp: new Date(),
        status: 'ERROR',
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async (proposalId: number) => {
    await sendMessage(`confirm proposal ${proposalId}`);
  };

  const handleReject = async (proposalId: number) => {
    await sendMessage(`reject proposal ${proposalId}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div className={`fixed right-0 top-0 h-full w-full sm:w-[440px] bg-slate-950 border-l border-slate-800 z-50 flex flex-col shadow-2xl shadow-black/80 transition-transform duration-300 ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-slate-900/80 backdrop-blur-md shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center shadow-sm">
              <Sparkles className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">AI Assistant</h3>
              <p className="text-xs text-slate-400">Natural language commands</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            aria-label="Close Assistant"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4 sm:space-y-5">
          {messages.map(msg => (
            <MessageBubble
              key={msg.id}
              msg={msg}
              onConfirm={handleConfirm}
              onReject={handleReject}
            />
          ))}

          {isLoading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-violet-600/30 border border-violet-500/30 flex items-center justify-center">
                <Bot className="w-4 h-4 text-violet-400" />
              </div>
              <div className="bg-slate-800/80 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2.5">
                <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
                <span className="text-sm text-slate-300">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Suggested commands — only show when no messages beyond welcome */}
        {messages.length <= 1 && (
          <div className="px-4 sm:px-5 pb-3.5 flex flex-col gap-1.5 shrink-0">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-1 px-1">Suggested prompts</p>
            {SUGGESTED_COMMANDS.map(cmd => (
              <button
                key={cmd}
                onClick={() => sendMessage(cmd)}
                className="flex items-center gap-2.5 text-left text-xs text-slate-300 hover:text-white bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-slate-700 rounded-xl px-3.5 py-2.5 transition-colors group"
              >
                <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition-colors shrink-0" />
                <span>{cmd}</span>
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="px-4 pb-4 pt-2.5 border-t border-slate-800 bg-slate-900/60 shrink-0">
          <div className="flex gap-2 items-end bg-slate-900 border border-slate-700/80 rounded-xl p-2 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-all">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a command… (Enter to send)"
              className="flex-1 bg-transparent text-sm text-white placeholder-slate-400 resize-none outline-none px-2.5 py-1.5 max-h-32 leading-normal"
              style={{ minHeight: '38px' }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              className="w-9 h-9 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors shrink-0 shadow-md shadow-indigo-600/25"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 text-white animate-spin" />
              ) : (
                <Send className="w-4 h-4 text-white" />
              )}
            </button>
          </div>
          <p className="text-[10px] text-slate-500 text-center mt-2">Shift + Enter for new line</p>
        </div>
      </div>
    </>
  );
}
