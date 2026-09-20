import { useState, useEffect } from 'react';
import {
  Sparkles, Bot, AlertTriangle, Users, Calendar, CheckCircle2, XCircle,
  TrendingUp, ThumbsUp, ThumbsDown, Clock, ShieldCheck, RefreshCw,
  Send, Loader2, Check, MessageSquare
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import AIService from '../services/ai.service';
import type { FeedbackAnalytics } from '../services/ai.service';

export default function AgenticAI() {
  const [activeTab, setActiveTab] = useState<'console' | 'planner' | 'recovery' | 'redistribution' | 'meeting' | 'risks' | 'evals'>('console');
  
  // Analytics state
  const [analytics, setAnalytics] = useState<FeedbackAnalytics | null>(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);


  // Command Console state
  const [commandInput, setCommandInput] = useState('');
  const [consoleLog, setConsoleLog] = useState<Array<{
    role: 'user' | 'agent';
    text: string;
    details?: any;
    proposalId?: number;
    status?: string;
    timestamp: Date;
  }>>([
    {
      role: 'agent',
      text: "👋 Welcome to the ClubOps Agentic AI Command Center!\n\nI am connected to your club's database state, critical path engine, and volunteer scheduling systems. Select an autonomous workflow above or ask any question like 'What is the next event?'.",
      timestamp: new Date()
    }
  ]);
  const [runningAgent, setRunningAgent] = useState(false);

  // Active proposals waiting for human approval
  const [activeProposal, setActiveProposal] = useState<{
    id: number;
    intent: string;
    diffs: any[];
    status: string;
  } | null>(null);

  // Form states for specialized workflow triggers
  const [plannerForm, setPlannerForm] = useState({
    title: 'Hackathon 2026',
    date: '2026-11-15',
    attendance: 500,
    budget: 60000,
    venue: 'Main Auditorium',
    brief: '36-hour inter-college AI hackathon with 500 attendees and sponsor booths.'
  });

  const [recoveryForm, setRecoveryForm] = useState({
    delayDays: 3,
    reason: 'Venue booking delayed by facilities department approval backlog'
  });

  const [redistributeForm, setRedistributeForm] = useState({
    volunteerName: 'Rahul',
    reason: 'Unavailable tomorrow due to university examination'
  });

  const [meetingForm, setMeetingForm] = useState({
    notes: "Core Organizers Sync Notes:\n- Rahul will finalize sponsor agreements by Friday\n- Priya will coordinate stage lighting and auditorium sound checks\n- Need volunteers to set up registration desks by Thursday morning"
  });

  // Post-decision feedback widget state
  const [feedbackRating, setFeedbackRating] = useState<'GOOD' | 'POOR' | null>(null);
  const [feedbackType, setFeedbackType] = useState<string>('');
  const [feedbackComment, setFeedbackComment] = useState('');
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [feedbackDone, setFeedbackDone] = useState(false);

  const fetchAnalytics = async () => {
    setLoadingAnalytics(true);
    try {
      const data = await AIService.getFeedbackAnalytics();
      setAnalytics(data);
    } catch (err) {
      console.error('Failed to load feedback analytics:', err);
    } finally {
      setLoadingAnalytics(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const handleSendCommand = async (cmdText?: string) => {
    const textToSend = (cmdText || commandInput).trim();
    if (!textToSend || runningAgent) return;

    setConsoleLog(prev => [...prev, {
      role: 'user',
      text: textToSend,
      timestamp: new Date()
    }]);
    setCommandInput('');
    setRunningAgent(true);

    try {
      const resp = await AIService.executeCommand({ command: textToSend });
      const details = resp.details || {};
      const proposalId = resp.proposals && resp.proposals.length > 0 ? resp.proposals[0] : undefined;

      // Extract proposal diffs if any
      const diffPreview = details.diff_preview || (details.result && details.result.diff_preview);
      if (proposalId && diffPreview) {
        setActiveProposal({
          id: proposalId,
          intent: details.intent || textToSend,
          diffs: diffPreview.diffs || [],
          status: resp.status || 'AWAITING_CONFIRMATION'
        });
        setFeedbackDone(false);
        setFeedbackRating(null);
      }

      setConsoleLog(prev => [...prev, {
        role: 'agent',
        text: resp.response,
        details: details,
        proposalId: proposalId,
        status: resp.status,
        timestamp: new Date()
      }]);
    } catch (err: any) {
      setConsoleLog(prev => [...prev, {
        role: 'agent',
        text: `Error executing command: ${err.response?.data?.message || err.message || 'Agent error occurred.'}`,
        timestamp: new Date()
      }]);
    } finally {
      setRunningAgent(false);
    }
  };

  const handleApproveProposal = async (proposalId: number) => {
    setRunningAgent(true);
    try {
      await AIService.confirmProposal(proposalId);
      if (activeProposal && activeProposal.id === proposalId) {
        setActiveProposal({ ...activeProposal, status: 'APPLIED' });
      }

      setConsoleLog(prev => [...prev, {
        role: 'agent',
        text: `✅ Proposal #${proposalId} successfully approved and applied to production database.`,
        status: 'APPLIED',
        timestamp: new Date()
      }]);
      fetchAnalytics();
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    } finally {
      setRunningAgent(false);
    }
  };

  const handleRejectProposal = async (proposalId: number) => {
    setRunningAgent(true);
    try {
      await AIService.rejectProposal(proposalId);
      if (activeProposal && activeProposal.id === proposalId) {
        setActiveProposal({ ...activeProposal, status: 'REJECTED' });
      }
      setConsoleLog(prev => [...prev, {
        role: 'agent',
        text: `❌ Proposal #${proposalId} has been rejected without modifying state.`,
        status: 'REJECTED',
        timestamp: new Date()
      }]);
      fetchAnalytics();
    } catch (err: any) {
      alert(`Rejection error: ${err.message}`);
    } finally {
      setRunningAgent(false);
    }
  };

  const handleSubmitFeedback = async (proposalId: number, rating: 'GOOD' | 'POOR', type?: string, comment?: string) => {
    setSubmittingFeedback(true);
    try {
      await AIService.submitFeedback({
        proposal_id: proposalId,
        rating,
        feedback_type: type || (rating === 'GOOD' ? 'positive_execution' : 'other'),
        comment: comment || undefined
      });
      setFeedbackDone(true);
      fetchAnalytics();
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    } finally {
      setSubmittingFeedback(false);
    }
  };

  return (
    <DashboardLayout title="Agentic AI Command Center">
      <div className="max-w-7xl mx-auto space-y-6 pb-12">
        {/* Top Header Banner */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-violet-950 via-slate-900 to-indigo-950 border border-violet-500/20 p-6 sm:p-8 shadow-2xl">
          <div className="absolute top-0 right-0 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-violet-500/15 border border-violet-500/30 text-violet-300 text-xs font-semibold mb-3">
                <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                Autonomous Multi-Agent Orchestration & Closed-Loop HITL Engine
              </div>
              <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
                ClubOps Agentic AI Operations
              </h1>
              <p className="text-slate-400 text-sm mt-1 max-w-2xl">
                Autonomous workflow planning, delay recovery, adaptive volunteer load rebalancing, and transactional Human-in-the-Loop staging. Distinct from Document RAG.
              </p>
            </div>
            
            {/* Quick evaluation KPI chip */}
            {analytics && (
              <div className="flex items-center gap-4 bg-slate-950/70 border border-violet-500/20 rounded-2xl p-4 shrink-0">
                <div className="text-center px-2">
                  <p className="text-xs text-slate-400 font-medium">Acceptance</p>
                  <p className="text-xl font-black text-emerald-400">{analytics.proposal_acceptance_rate_percent}%</p>
                </div>
                <div className="h-8 w-px bg-slate-800" />
                <div className="text-center px-2">
                  <p className="text-xs text-slate-400 font-medium">Recovery</p>
                  <p className="text-xl font-black text-violet-400">{analytics.recovery_success_rate_percent}%</p>
                </div>
                <div className="h-8 w-px bg-slate-800" />
                <div className="text-center px-2">
                  <p className="text-xs text-slate-400 font-medium">Satisfaction</p>
                  <p className="text-xl font-black text-amber-400">{analytics.satisfaction_rate_percent}%</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-2">
          {[
            { id: 'console', label: 'Operations Console', icon: Bot },
            { id: 'planner', label: 'Event Planner', icon: Calendar },
            { id: 'recovery', label: 'Delay Recovery', icon: Clock },
            { id: 'redistribution', label: 'Volunteer Rebalancing', icon: Users },
            { id: 'meeting', label: 'Meeting Actions', icon: MessageSquare },
            { id: 'risks', label: 'Risk Remediator', icon: AlertTriangle },
            { id: 'evals', label: 'Evaluations & Feedback', icon: TrendingUp },
          ].map(t => {
            const Icon = t.icon;
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id as any)}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                  isActive
                    ? 'bg-violet-600 text-white shadow-lg shadow-violet-600/30'
                    : 'bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Action Panel (2 cols) */}
          <div className="lg:col-span-2 space-y-6">
            {/* 1. OPERATIONS CONSOLE */}
            {activeTab === 'console' && (
              <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 space-y-4 shadow-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-white font-bold text-base">
                    <Bot className="w-5 h-5 text-violet-400" />
                    <span>Agentic Multi-Turn Dialog</span>
                  </div>
                  <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                    Online & Scoped
                  </span>
                </div>

                {/* Quick Prompts */}
                <div className="space-y-1.5">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Quick Operations Prompts:</p>
                  <div className="flex flex-wrap gap-2">
                    {[
                      "What is the next event?",
                      "Plan TechFest on 15 November with 500 students",
                      "Rahul is unavailable tomorrow. Redistribute his tasks",
                      "Venue booking is delayed by 3 days",
                      "Analyze and resolve all operational risks"
                    ].map((p, i) => (
                      <button
                        key={i}
                        onClick={() => handleSendCommand(p)}
                        className="text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white px-3 py-1.5 rounded-lg border border-slate-700/60 transition-colors text-left"
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Log messages */}
                <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-4 min-h-[360px] max-h-[480px] overflow-y-auto space-y-4 font-sans text-sm">
                  {consoleLog.map((entry, idx) => (
                    <div
                      key={idx}
                      className={`flex flex-col gap-1.5 ${
                        entry.role === 'user' ? 'items-end' : 'items-start'
                      }`}
                    >
                      <div className="flex items-center gap-2 text-[11px] text-slate-500">
                        <span>{entry.role === 'user' ? 'Organizer' : 'Agentic Engine'}</span>
                        <span>•</span>
                        <span>{entry.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <div
                        className={`rounded-2xl px-4 py-3 max-w-[90%] whitespace-pre-wrap leading-relaxed ${
                          entry.role === 'user'
                            ? 'bg-indigo-600 text-white rounded-tr-sm'
                            : 'bg-slate-800/90 text-slate-200 border border-slate-700/60 rounded-tl-sm shadow-md'
                        }`}
                      >
                        {entry.text}
                      </div>
                    </div>
                  ))}
                  {runningAgent && (
                    <div className="flex items-center gap-2.5 text-violet-400 text-xs italic p-2 bg-violet-500/10 rounded-lg w-fit border border-violet-500/20">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Agent formulating plan and calculating state dependencies...</span>
                    </div>
                  )}
                </div>

                {/* Input bar */}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSendCommand();
                  }}
                  className="flex gap-2"
                >
                  <input
                    type="text"
                    placeholder="Enter agent command (e.g. 'What is the next event?', 'Redistribute tasks')..."
                    value={commandInput}
                    onChange={(e) => setCommandInput(e.target.value)}
                    disabled={runningAgent}
                    className="flex-1 bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500 transition-colors"
                  />
                  <button
                    type="submit"
                    disabled={!commandInput.trim() || runningAgent}
                    className="bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white font-semibold px-5 py-2.5 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-violet-600/30"
                  >
                    {runningAgent ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    <span>Dispatch</span>
                  </button>
                </form>
              </div>
            )}

            {/* 2. EVENT PLANNER */}
            {activeTab === 'planner' && (
              <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 space-y-4">
                <div className="flex items-center gap-2 text-white font-bold text-lg">
                  <Calendar className="w-5 h-5 text-indigo-400" />
                  <span>AI Event Planner Agent</span>
                </div>
                <p className="text-slate-400 text-xs">
                  Synthesizes constraints, past post-mortem lessons from RAG knowledge, decomposes timeline into 3 phases (PRE_EVENT, EVENT_DAY, POST_EVENT), recommends volunteer assignments, and stages transactional proposal.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  <div>
                    <label className="text-slate-400 font-medium block mb-1">Event Title</label>
                    <input
                      type="text"
                      value={plannerForm.title}
                      onChange={e => setPlannerForm({...plannerForm, title: e.target.value})}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 font-medium block mb-1">Target Date</label>
                    <input
                      type="date"
                      value={plannerForm.date}
                      onChange={e => setPlannerForm({...plannerForm, date: e.target.value})}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 font-medium block mb-1">Expected Attendees</label>
                    <input
                      type="number"
                      value={plannerForm.attendance}
                      onChange={e => setPlannerForm({...plannerForm, attendance: Number(e.target.value)})}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 font-medium block mb-1">Budget (₹)</label>
                    <input
                      type="number"
                      value={plannerForm.budget}
                      onChange={e => setPlannerForm({...plannerForm, budget: Number(e.target.value)})}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="text-slate-400 font-medium block mb-1">Venue</label>
                    <input
                      type="text"
                      value={plannerForm.venue}
                      onChange={e => setPlannerForm({...plannerForm, venue: e.target.value})}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="text-slate-400 font-medium block mb-1">Brief & Objectives</label>
                    <textarea
                      rows={3}
                      value={plannerForm.brief}
                      onChange={e => setPlannerForm({...plannerForm, brief: e.target.value})}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                    />
                  </div>
                </div>

                <button
                  onClick={() => handleSendCommand(`Plan event ${plannerForm.title} on ${plannerForm.date} with ${plannerForm.attendance} attendees. Budget: ₹${plannerForm.budget}. Venue: ${plannerForm.venue}. Brief: ${plannerForm.brief}`)}
                  disabled={runningAgent}
                  className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold px-5 py-2.5 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-indigo-600/30 text-sm"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Generate Complete Plan & Proposal Diff</span>
                </button>
              </div>
            )}

            {/* 3. DELAY RECOVERY */}
            {activeTab === 'recovery' && (
              <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 space-y-4">
                <div className="flex items-center gap-2 text-white font-bold text-lg">
                  <Clock className="w-5 h-5 text-amber-400" />
                  <span>Delay Recovery Agent</span>
                </div>
                <p className="text-slate-400 text-xs">
                  Performs critical path traversal, evaluates volunteer slack and overload, splits bottleneck tasks, parallelizes independent activities, and produces a Before vs Proposed diff with high confidence.
                </p>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="text-slate-400 font-medium block mb-1">Delay Duration (Days)</label>
                    <input
                      type="number"
                      value={recoveryForm.delayDays}
                      onChange={e => setRecoveryForm({...recoveryForm, delayDays: Number(e.target.value)})}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 font-medium block mb-1">Delay Cause / Context</label>
                    <input
                      type="text"
                      value={recoveryForm.reason}
                      onChange={e => setRecoveryForm({...recoveryForm, reason: e.target.value})}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                    />
                  </div>
                </div>

                <button
                  onClick={() => handleSendCommand(`Venue booking is delayed by ${recoveryForm.delayDays} days. ${recoveryForm.reason}`)}
                  disabled={runningAgent}
                  className="bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-semibold px-5 py-2.5 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-amber-600/30 text-sm"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Calculate Critical Path & Recover Schedule</span>
                </button>
              </div>
            )}

            {/* 4. VOLUNTEER REDISTRIBUTION */}
            {activeTab === 'redistribution' && (
              <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 space-y-4">
                <div className="flex items-center gap-2 text-white font-bold text-lg">
                  <Users className="w-5 h-5 text-cyan-400" />
                  <span>Volunteer Rebalancing Agent</span>
                </div>
                <p className="text-slate-400 text-xs">
                  Identifies active tasks assigned to an unavailable volunteer and matches alternative volunteers based on workload capacity, skill overlap, and closed-loop feedback history penalties.
                </p>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="text-slate-400 font-medium block mb-1">Unavailable Volunteer</label>
                    <input
                      type="text"
                      value={redistributeForm.volunteerName}
                      onChange={e => setRedistributeForm({...redistributeForm, volunteerName: e.target.value})}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 font-medium block mb-1">Unavailability Reason</label>
                    <input
                      type="text"
                      value={redistributeForm.reason}
                      onChange={e => setRedistributeForm({...redistributeForm, reason: e.target.value})}
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white"
                    />
                  </div>
                </div>

                <button
                  onClick={() => handleSendCommand(`${redistributeForm.volunteerName} is unavailable tomorrow. Redistribute his tasks. Reason: ${redistributeForm.reason}`)}
                  disabled={runningAgent}
                  className="bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 text-white font-semibold px-5 py-2.5 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-cyan-600/30 text-sm"
                >
                  <Users className="w-4 h-4" />
                  <span>Rebalance Tasks Across Qualified Volunteers</span>
                </button>
              </div>
            )}

            {/* 5. MEETING ACTIONS */}
            {activeTab === 'meeting' && (
              <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 space-y-4">
                <div className="flex items-center gap-2 text-white font-bold text-lg">
                  <MessageSquare className="w-5 h-5 text-emerald-400" />
                  <span>Meeting Action Extractor Agent</span>
                </div>
                <p className="text-slate-400 text-xs">
                  Parses informal meeting transcripts and notes, performs entity resolution against registered volunteers, extracts relative deadlines (e.g. 'by Friday'), and prevents duplicate task creation.
                </p>

                <div className="text-xs">
                  <label className="text-slate-400 font-medium block mb-1">Meeting Notes / Transcript Text</label>
                  <textarea
                    rows={6}
                    value={meetingForm.notes}
                    onChange={e => setMeetingForm({ notes: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-white font-mono"
                  />
                </div>

                <button
                  onClick={() => handleSendCommand(`Extract action items from meeting notes:\n${meetingForm.notes}`)}
                  disabled={runningAgent}
                  className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-semibold px-5 py-2.5 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-emerald-600/30 text-sm"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Extract Action Items & Stage Proposal</span>
                </button>
              </div>
            )}

            {/* 6. RISKS */}
            {activeTab === 'risks' && (
              <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 space-y-4">
                <div className="flex items-center gap-2 text-white font-bold text-lg">
                  <AlertTriangle className="w-5 h-5 text-rose-400" />
                  <span>Autonomous Risk Remediation Agent</span>
                </div>
                <p className="text-slate-400 text-xs">
                  Leverages deterministic detectors (unowned tasks, overloaded volunteers, timeline inversions, critical path delays, zero-slack bottlenecks) and automatically formulates actionable remediations.
                </p>

                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
                  <p className="font-semibold mb-1">Continuous Risk Surveillance Active</p>
                  <p className="text-rose-400/80">
                    Deterministic monitors audit project state every cycle. Triggering the agent runs immediate deep reasoning and generates an atomic recovery proposal.
                  </p>
                </div>

                <button
                  onClick={() => handleSendCommand('Analyze and resolve all operational risks')}
                  disabled={runningAgent}
                  className="bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white font-semibold px-5 py-2.5 rounded-xl transition-all flex items-center gap-2 shadow-lg shadow-rose-600/30 text-sm"
                >
                  <AlertTriangle className="w-4 h-4" />
                  <span>Execute Risk Detection & Stage Resolution</span>
                </button>
              </div>
            )}

            {/* 7. EVALUATIONS & FEEDBACK */}
            {activeTab === 'evals' && (
              <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-white font-bold text-lg">
                    <TrendingUp className="w-5 h-5 text-violet-400" />
                    <span>Closed-Loop Feedback & Evaluation Metrics</span>
                  </div>
                  <button
                    onClick={fetchAnalytics}
                    disabled={loadingAnalytics}
                    className="flex items-center gap-1.5 text-xs text-violet-400 hover:text-white bg-violet-500/10 px-3 py-1.5 rounded-lg border border-violet-500/20 disabled:opacity-50"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingAnalytics ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                  </button>

                </div>

                {analytics && (
                  <div className="space-y-6">
                    {/* KPI grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                        <p className="text-xs text-slate-400 font-medium">Total Feedback</p>
                        <p className="text-2xl font-black text-white mt-1">{analytics.total_feedbacks}</p>
                      </div>
                      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                        <p className="text-xs text-slate-400 font-medium">Acceptance Rate</p>
                        <p className="text-2xl font-black text-emerald-400 mt-1">{analytics.proposal_acceptance_rate_percent}%</p>
                      </div>
                      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                        <p className="text-xs text-slate-400 font-medium">Recovery Success</p>
                        <p className="text-2xl font-black text-violet-400 mt-1">{analytics.recovery_success_rate_percent}%</p>
                      </div>
                      <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                        <p className="text-xs text-slate-400 font-medium">Satisfaction Rate</p>
                        <p className="text-2xl font-black text-amber-400 mt-1">{analytics.satisfaction_rate_percent}%</p>
                      </div>
                    </div>

                    {/* Correction / Rejection breakdown */}
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                      <p className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">Correction Reason Distribution</p>
                      {Object.keys(analytics.top_negative_reasons).length > 0 ? (
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                          {Object.entries(analytics.top_negative_reasons).map(([reason, count]) => (
                            <div key={reason} className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-xs">
                              <span className="text-slate-400 capitalize">{reason.replace('_', ' ')}</span>
                              <p className="text-lg font-bold text-rose-400 mt-0.5">{count} flags</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500">No negative corrections recorded. All proposals accepted cleanly.</p>
                      )}
                    </div>

                    {/* Recent Feedback Feed */}
                    <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2.5">
                      <p className="text-xs font-bold text-slate-300 uppercase tracking-wider">Recent Human Evaluations</p>
                      {analytics.recent_feedbacks.length > 0 ? (
                        <div className="space-y-2">
                          {analytics.recent_feedbacks.map(fb => (
                            <div key={fb.id} className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 text-xs flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                {fb.rating === 'GOOD' ? (
                                  <ThumbsUp className="w-3.5 h-3.5 text-emerald-400" />
                                ) : (
                                  <ThumbsDown className="w-3.5 h-3.5 text-rose-400" />
                                )}
                                <span className="font-semibold text-white capitalize">{fb.feedback_type?.replace('_', ' ') || fb.rating}</span>
                                {fb.comment && <span className="text-slate-400 truncate max-w-xs">"{fb.comment}"</span>}
                              </div>
                              <span className="text-[10px] text-slate-500">Proposal #{fb.proposal_id || 'Direct'}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-500">No recent evaluations logged yet.</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Side Panel: Human-in-the-Loop Proposal Staging (1 col) */}
          <div className="space-y-6">
            <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 shadow-xl space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <div className="flex items-center gap-2 text-white font-bold text-base">
                  <ShieldCheck className="w-5 h-5 text-emerald-400" />
                  <span>Staged Action Proposal</span>
                </div>
                {activeProposal && (
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                    activeProposal.status === 'APPLIED'
                      ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                      : activeProposal.status === 'REJECTED'
                      ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                      : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                  }`}>
                    {activeProposal.status.replace('_', ' ')}
                  </span>
                )}
              </div>

              {activeProposal ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-xs font-semibold text-white">Proposal #{activeProposal.id}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{activeProposal.intent}</p>
                  </div>

                  {/* Comparative Cards */}
                  <div className="space-y-3">
                    <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Before vs Proposed Changes:</p>
                    {activeProposal.diffs.map((d, idx) => (
                      <div key={idx} className="bg-slate-950/80 rounded-xl p-3 border border-slate-800 text-xs space-y-2">
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
                            <p className="font-semibold text-white">{d.summary}</p>
                            {d.proposed && (
                              <p className="text-emerald-300 text-[11px] mt-0.5">Owner: {d.proposed.owner || 'Unassigned'} • Due: {d.proposed.due || 'TBD'}</p>
                            )}
                          </div>
                        )}

                        {/* Confidence Badge & Rationale */}
                        <div className="mt-2 pt-2 border-t border-slate-800/60 flex items-center justify-between">
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
                          <p className="text-[11px] text-slate-300 mt-1"><span className="text-slate-500 font-medium">Reason: </span>{d.reason}</p>
                        )}
                        {d.impact && (
                          <p className="text-[11px] text-indigo-300"><span className="text-slate-500 font-medium">Impact: </span>{d.impact}</p>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Actions */}
                  {activeProposal.status !== 'APPLIED' && activeProposal.status !== 'REJECTED' ? (
                    <div className="flex gap-2 pt-2">
                      <button
                        onClick={() => handleApproveProposal(activeProposal.id)}
                        disabled={runningAgent}
                        className="flex-1 flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2 px-3 rounded-xl text-xs transition-colors shadow-lg shadow-emerald-600/20"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Approve & Apply</span>
                      </button>
                      <button
                        onClick={() => handleRejectProposal(activeProposal.id)}
                        disabled={runningAgent}
                        className="flex-1 flex items-center justify-center gap-1.5 bg-slate-800 hover:bg-rose-900/40 text-slate-300 hover:text-rose-300 border border-slate-700 font-medium py-2 px-3 rounded-xl text-xs transition-colors"
                      >
                        <XCircle className="w-4 h-4" />
                        <span>Reject</span>
                      </button>
                    </div>
                  ) : null}

                  {/* Post-Decision Feedback Prompt */}
                  <div className="pt-3 border-t border-slate-800/80 text-xs">
                    <p className="font-semibold text-slate-300 mb-2">Evaluate Agent Performance:</p>
                    {feedbackDone ? (
                      <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2.5">
                        <Check className="w-4 h-4" />
                        <span>Feedback logged! Adaptive ranker calibrated.</span>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              setFeedbackRating('GOOD');
                              handleSubmitFeedback(activeProposal.id, 'GOOD', 'positive_execution');
                            }}
                            disabled={submittingFeedback}
                            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg border text-xs font-semibold transition-all ${
                              feedbackRating === 'GOOD'
                                ? 'bg-emerald-600 text-white border-emerald-500'
                                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
                            }`}
                          >
                            <ThumbsUp className="w-3.5 h-3.5 text-emerald-400" />
                            <span>Accurate</span>
                          </button>
                          <button
                            onClick={() => setFeedbackRating('POOR')}
                            disabled={submittingFeedback}
                            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg border text-xs font-semibold transition-all ${
                              feedbackRating === 'POOR'
                                ? 'bg-rose-600/40 text-rose-300 border-rose-500'
                                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
                            }`}
                          >
                            <ThumbsDown className="w-3.5 h-3.5 text-rose-400" />
                            <span>Needs Correction</span>
                          </button>
                        </div>

                        {feedbackRating === 'POOR' && (
                          <div className="space-y-2.5 bg-slate-950 p-3 rounded-xl border border-slate-800">
                            <p className="text-[11px] text-slate-400 font-medium">Specify Correction Reason:</p>
                            <div className="grid grid-cols-2 gap-1.5">
                              {[
                                { id: 'wrong_volunteer', label: 'Wrong volunteer' },
                                { id: 'deadline_unrealistic', label: 'Unrealistic deadline' },
                                { id: 'missing_dependency', label: 'Missing dependency' },
                                { id: 'too_many_changes', label: 'Too many changes' },
                                { id: 'other', label: 'Other issue' },
                              ].map(opt => (
                                <button
                                  key={opt.id}
                                  type="button"
                                  onClick={() => setFeedbackType(opt.id)}
                                  className={`text-[11px] text-left px-2.5 py-1 rounded border transition-colors ${
                                    feedbackType === opt.id
                                      ? 'bg-violet-600/40 border-violet-500 text-violet-200 font-semibold'
                                      : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200'
                                  }`}
                                >
                                  {opt.label}
                                </button>
                              ))}
                            </div>
                            <input
                              type="text"
                              placeholder="Optional explanation notes..."
                              value={feedbackComment}
                              onChange={e => setFeedbackComment(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-white placeholder-slate-500"
                            />
                            <button
                              onClick={() => handleSubmitFeedback(activeProposal.id, 'POOR', feedbackType, feedbackComment)}
                              disabled={!feedbackType || submittingFeedback}
                              className="w-full bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white font-medium py-1.5 rounded text-xs transition-colors"
                            >
                              {submittingFeedback ? 'Calibrating...' : 'Submit Evaluation'}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 px-4 border border-dashed border-slate-800 rounded-xl space-y-2">
                  <ShieldCheck className="w-8 h-8 text-slate-600 mx-auto" />
                  <p className="text-xs font-semibold text-slate-400">No Active Proposals Awaiting Review</p>
                  <p className="text-[11px] text-slate-500">
                    Dispatch an autonomous agent command from the console or specialized workflows to stage a proposal here.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
