import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Send,
  Bot,
  User,
  Loader2,
  CheckCircle,
  XCircle,
  Sparkles,
  ChevronRight,
  Trash2,
  Mic,
  ThumbsUp,
  ThumbsDown,
  ShieldCheck,
  Check
} from 'lucide-react';
import AIService from '../services/ai.service';
import type { ChatMessage, AICommandRequest } from '../services/ai.service';
import VoiceAssistant from './voice/VoiceAssistant';
import type { VoiceChatResponse } from '../services/voice.service';

interface AIChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
  activeEventId?: number;
}

const SUGGESTED_COMMANDS = [
  'Venue booking is delayed by 3 days',
  'Rahul is unavailable tomorrow. Redistribute his tasks',
  'Plan TechFest on 15 November with 500 students',
  'Extract actions from meeting notes',
  'Analyze and resolve risks',
  'What problems happened during last year event?',
];

function FeedbackPrompt({
  proposalId,
  eventId,
  onSubmitted
}: {
  proposalId: number;
  eventId?: number;
  onSubmitted: () => void;
}) {
  const [rating, setRating] = useState<'GOOD' | 'POOR' | null>(null);
  const [feedbackType, setFeedbackType] = useState<string>('');
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDone, setIsDone] = useState(false);

  const handleSelectRating = async (selected: 'GOOD' | 'POOR') => {
    setRating(selected);
    if (selected === 'GOOD') {
      setIsSubmitting(true);
      try {
        await AIService.submitFeedback({
          proposal_id: proposalId,
          event_id: eventId,
          rating: 'GOOD',
          feedback_type: 'positive_execution',
        });
        setIsDone(true);
        onSubmitted();
      } catch (e) {
        console.error('Failed to submit feedback:', e);
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleSubmitNegative = async () => {
    if (!feedbackType) return;
    setIsSubmitting(true);
    try {
      await AIService.submitFeedback({
        proposal_id: proposalId,
        event_id: eventId,
        rating: 'POOR',
        feedback_type: feedbackType,
        comment: comment || undefined,
      });
      setIsDone(true);
      onSubmitted();
    } catch (e) {
      console.error('Failed to submit negative feedback:', e);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isDone) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2 mt-2">
        <Check className="w-3.5 h-3.5" />
        <span>Feedback saved! Calibrating future agent recommendations.</span>
      </div>
    );
  }

  return (
    <div className="mt-3 pt-2.5 border-t border-slate-700/60 text-xs">
      <p className="text-slate-300 font-medium mb-1.5">Was this plan useful?</p>
      <div className="flex gap-2 mb-2">
        <button
          onClick={() => handleSelectRating('GOOD')}
          disabled={isSubmitting}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1 px-2.5 rounded-lg border text-xs transition-all ${
            rating === 'GOOD'
              ? 'bg-emerald-600 text-white border-emerald-500'
              : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
          }`}
        >
          <ThumbsUp className="w-3.5 h-3.5 text-emerald-400" />
          <span>Good</span>
        </button>
        <button
          onClick={() => handleSelectRating('POOR')}
          disabled={isSubmitting}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1 px-2.5 rounded-lg border text-xs transition-all ${
            rating === 'POOR'
              ? 'bg-rose-600/40 text-rose-300 border-rose-500'
              : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
          }`}
        >
          <ThumbsDown className="w-3.5 h-3.5 text-rose-400" />
          <span>Not useful</span>
        </button>
      </div>

      {rating === 'POOR' && (
        <div className="space-y-2 bg-slate-900/90 p-2.5 rounded-lg border border-slate-700 mt-2">
          <p className="text-[11px] text-slate-400 font-medium">Reason for correction:</p>
          <div className="grid grid-cols-2 gap-1.5">
            {[
              { id: 'wrong_volunteer', label: 'Wrong volunteer' },
              { id: 'deadline_unrealistic', label: 'Deadline unrealistic' },
              { id: 'missing_dependency', label: 'Missing dependency' },
              { id: 'too_many_changes', label: 'Too many changes' },
              { id: 'other', label: 'Other' },
            ].map(opt => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setFeedbackType(opt.id)}
                className={`text-[11px] text-left px-2 py-1 rounded border transition-colors ${
                  feedbackType === opt.id
                    ? 'bg-indigo-600/40 border-indigo-500 text-indigo-200 font-semibold'
                    : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <input
            type="text"
            placeholder="Optional comment / note..."
            value={comment}
            onChange={e => setComment(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <button
            onClick={handleSubmitNegative}
            disabled={!feedbackType || isSubmitting}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-1 rounded text-xs transition-colors"
          >
            {isSubmitting ? 'Submitting...' : 'Save Feedback'}
          </button>
        </div>
      )}
    </div>
  );
}

function MessageBubble({
  msg,
  onConfirm,
  onReject,
  activeEventId,
}: {
  msg: ChatMessage;
  onConfirm: (id: number) => void;
  onReject: (id: number) => void;
  activeEventId?: number;
}) {
  const isUser = msg.role === 'user';
  const diffPreview = msg.details?.diff_preview;
  const isApplied = msg.status === 'APPLIED';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
        isUser ? 'bg-indigo-600' : 'bg-violet-600/30 border border-violet-500/30'
      }`}>
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-violet-400" />
        )}
      </div>

      <div className={`max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-2 w-full`}>
        {/* Bubble */}
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-indigo-600 text-white rounded-tr-sm'
            : 'bg-slate-800/80 text-slate-200 border border-slate-700/50 rounded-tl-sm w-full'
        }`}>
          <p className="whitespace-pre-wrap">{msg.content}</p>
        </div>

        {/* Status badge */}
        {msg.status && msg.status !== 'COMPLETED' && (
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider ${
            msg.status === 'PENDING_CONFIRMATION' || msg.status === 'AWAITING_CONFIRMATION'
              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
              : msg.status === 'ERROR'
              ? 'bg-red-500/10 text-red-400 border border-red-500/20'
              : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
          }`}>
            {msg.status.replace('_', ' ')}
          </span>
        )}

        {/* Rich Proposal Before vs Proposed Diff Cards */}
        {msg.proposals && msg.proposals.length > 0 && (
          <div className="flex flex-col gap-2.5 w-full">
            {msg.proposals.map(pid => (
              <div key={pid} className="bg-slate-900/90 border border-slate-700/70 rounded-xl p-3.5 shadow-lg">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-semibold text-white">Proposal #{pid}</span>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-medium border border-violet-500/30">
                    Human-in-the-Loop Review
                  </span>
                </div>

                {/* Diff Comparison Cards */}
                {diffPreview?.diffs && diffPreview.diffs.length > 0 ? (
                  <div className="space-y-2.5 my-2">
                    {diffPreview.diffs.slice(0, 4).map((d: any, idx: number) => (
                      <div key={idx} className="bg-slate-950/70 rounded-lg p-2.5 border border-slate-800 text-xs">
                        {d.before && d.proposed ? (
                          <div className="grid grid-cols-2 gap-2">
                            {/* Before Card */}
                            <div className="border-r border-slate-800/80 pr-2">
                              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Before</span>
                              <div className="mt-1 space-y-0.5">
                                <p className="font-semibold text-slate-300 truncate">{d.before.task || d.summary}</p>
                                <p className="text-slate-400 text-[11px]"><span className="text-slate-500">Owner:</span> {d.before.owner || 'None'}</p>
                                <p className="text-slate-400 text-[11px]"><span className="text-slate-500">Due:</span> {d.before.due || 'None'}</p>
                                <p className="text-slate-500 text-[10px]">Status: {d.before.status || 'TODO'}</p>
                              </div>
                            </div>
                            {/* Proposed Card */}
                            <div className="pl-1">
                              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">Proposed</span>
                              <div className="mt-1 space-y-0.5">
                                <p className="font-semibold text-white truncate">{d.proposed.task || d.summary}</p>
                                <p className="text-emerald-300 text-[11px]"><span className="text-slate-500">Owner:</span> {d.proposed.owner || 'Unassigned'}</p>
                                <p className="text-emerald-300 text-[11px]"><span className="text-slate-500">Due:</span> {d.proposed.due || 'TBD'}</p>
                                <p className="text-emerald-400 text-[10px]">Status: {d.proposed.status || 'TODO'}</p>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div>
                            <p className="font-medium text-white">{d.summary}</p>
                            {d.proposed && (
                              <div className="mt-1 text-[11px] text-emerald-300 flex items-center gap-2">
                                <span>Owner: {d.proposed.owner || 'Unassigned'}</span>
                                <span>• Due: {d.proposed.due || 'TBD'}</span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Confidence Badge & Rationale & Impact */}
                        <div className="mt-2 pt-1.5 border-t border-slate-800/60 flex items-center justify-between">
                          <span className={`px-1.5 py-0.5 rounded font-bold uppercase text-[10px] tracking-wider ${
                            d.confidence === 'LOW'
                              ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                              : d.confidence === 'MEDIUM'
                              ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                              : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                          }`}>
                            {d.confidence || 'HIGH'} Confidence
                          </span>
                        </div>
                        {d.reason && (
                          <div className="mt-1 text-[11px] text-slate-300">
                            <span className="text-slate-500 font-medium">Reason: </span>{d.reason}
                          </div>
                        )}
                        {d.impact && (
                          <div className="text-[11px] text-indigo-300 mt-0.5">
                            <span className="text-slate-500 font-medium">Impact: </span>{d.impact}
                          </div>
                        )}

                      </div>
                    ))}
                    {diffPreview.diffs.length > 4 && (
                      <p className="text-[10px] text-slate-500 text-center">+ {diffPreview.diffs.length - 4} additional items in proposal</p>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 mb-2">Review staged changes before applying to production.</p>
                )}

                {/* Actions or Feedback prompt */}
                {!isApplied ? (
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => onConfirm(pid)}
                      className="flex-1 flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-2 rounded-lg transition-colors shadow"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      Approve & Apply
                    </button>
                    <button
                      onClick={() => onReject(pid)}
                      className="flex-1 flex items-center justify-center gap-1.5 bg-slate-800 hover:bg-rose-900/40 text-slate-300 hover:text-rose-300 border border-slate-700 text-xs font-medium px-3 py-2 rounded-lg transition-colors"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Reject
                    </button>
                  </div>
                ) : null}

                {/* Feedback prompt after action executed */}
                <FeedbackPrompt
                  proposalId={pid}
                  eventId={activeEventId}
                  onSubmitted={() => {}}
                />
              </div>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[10px] text-slate-600">
          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
}


const welcomeMessage: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: `👋 Hi! I'm your ClubOps AI assistant.\n\nYou can ask me to:\n• List or create events, tasks, or volunteers\n• Generate announcements\n• Summarize documents & answer policy questions\n• Execute complex multi-step commands\n\nTry typing a command below!`,
  timestamp: new Date(),
};

export default function AIChatPanel({ isOpen, onClose, activeEventId }: AIChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [historyCount, setHistoryCount] = useState(0);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isVoiceOpen, setIsVoiceOpen] = useState(false);
  const [activeThreadId, setActiveThreadId] = useState<string | undefined>(undefined);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleVoiceTurnComplete = (turn: VoiceChatResponse) => {
    if (turn.thread_id) {
      setActiveThreadId(turn.thread_id);
    }
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: turn.transcript,
      timestamp: new Date(),
    };
    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: turn.response_text,
      timestamp: new Date(),
      proposals: turn.proposals,
      status: turn.status,
      details: turn.details,
    };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
  };


  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);

      // Load previous past asked questions along with answers
      AIService.getHistory(activeEventId)
        .then(res => {
          if (res?.items && res.items.length > 0) {
            const historyMsgs: ChatMessage[] = [];
            for (const item of res.items) {
              historyMsgs.push({
                id: `hist-q-${item.id}`,
                role: 'user',
                content: item.question,
                timestamp: item.created_at ? new Date(item.created_at) : new Date(),
              });
              historyMsgs.push({
                id: `hist-a-${item.id}`,
                role: 'assistant',
                content: item.answer,
                status: item.status,
                proposals: item.proposals,
                timestamp: item.created_at ? new Date(item.created_at) : new Date(),
              });
            }
            setMessages([welcomeMessage, ...historyMsgs]);
            setHistoryCount(res.items.length);
          }
        })
        .catch(err => console.error("Error loading chat history:", err));
    }
  }, [isOpen, activeEventId]);

  const handleClearHistory = async () => {
    try {
      await AIService.clearHistory(activeEventId);
      setMessages([welcomeMessage]);
      setHistoryCount(0);
    } catch (err) {
      console.error("Failed to clear chat history:", err);
    }
  };

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
        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 md:hidden"
        onClick={onClose}
      />

      {/* Panel */}
      <div className={`fixed right-0 top-0 h-full w-full md:w-[420px] bg-slate-950 border-l border-slate-800 z-50 flex flex-col shadow-2xl shadow-black/50 transition-transform duration-300 ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-slate-900/70 backdrop-blur-sm shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-white">AI Assistant</h3>
                {historyCount > 0 && (
                  <span className="text-[10px] bg-violet-500/20 text-violet-300 px-1.5 py-0.5 rounded border border-violet-500/30 font-medium">
                    {historyCount} past Q&A
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500">Natural language commands & RAG</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            {historyCount > 0 && (
              <button
                onClick={handleClearHistory}
                title="Clear chat history"
                className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-red-400 hover:bg-slate-800/80 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {messages.map(msg => (
            <MessageBubble
              key={msg.id}
              msg={msg}
              onConfirm={handleConfirm}
              onReject={handleReject}
              activeEventId={activeEventId}
            />
          ))}

          {isLoading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-violet-600/30 border border-violet-500/30 flex items-center justify-center">
                <Bot className="w-4 h-4 text-violet-400" />
              </div>
              <div className="bg-slate-800/80 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
                <span className="text-sm text-slate-400">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Suggested commands — only show when no messages beyond welcome */}
        {messages.length <= 1 && (
          <div className="px-5 pb-3 flex flex-col gap-1.5 shrink-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600 mb-1">Suggestions</p>
            {SUGGESTED_COMMANDS.map(cmd => (
              <button
                key={cmd}
                onClick={() => sendMessage(cmd)}
                className="flex items-center gap-2 text-left text-xs text-slate-400 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-lg px-3 py-2 transition-colors group"
              >
                <ChevronRight className="w-3 h-3 text-slate-600 group-hover:text-indigo-400 transition-colors shrink-0" />
                {cmd}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="px-4 pb-4 pt-2 border-t border-slate-800 bg-slate-900/50 shrink-0">
          <div className="flex gap-2 items-end bg-slate-900 border border-slate-700 rounded-xl p-2 focus-within:border-indigo-500/70 focus-within:ring-1 focus-within:ring-indigo-500/20 transition-all">
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a command… (Enter to send)"
              className="flex-1 bg-transparent text-sm text-white placeholder-slate-600 resize-none outline-none py-1.5 px-1 max-h-32"
              style={{ minHeight: '36px' }}
            />
            <button
              type="button"
              onClick={() => setIsVoiceOpen(true)}
              title="Voice Assistant (Sarvam Multilingual)"
              className="w-9 h-9 rounded-lg bg-slate-800 hover:bg-violet-600/30 text-violet-400 hover:text-white border border-slate-700 hover:border-violet-500/40 flex items-center justify-center transition-all shrink-0 shadow-sm"
            >
              <Mic className="w-4 h-4" />
            </button>
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              className="w-9 h-9 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors shrink-0"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 text-white animate-spin" />
              ) : (
                <Send className="w-4 h-4 text-white" />
              )}
            </button>
          </div>
          <p className="text-[10px] text-slate-700 text-center mt-2">Shift+Enter for newline • Click 🎙 for Voice Mode</p>
        </div>
      </div>

      {/* Embedded Multilingual Voice Assistant Modal */}
      <VoiceAssistant
        isOpen={isVoiceOpen}
        onClose={() => setIsVoiceOpen(false)}
        activeEventId={activeEventId}
        initialThreadId={activeThreadId}
        onTurnComplete={handleVoiceTurnComplete}
      />
    </>
  );
}

