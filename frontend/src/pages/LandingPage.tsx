import { Link } from 'react-router-dom';
import {
  Sparkles, Calendar, Users, CheckSquare, Megaphone,
  ArrowRight, Bot, Zap, Shield, Brain,
  ChevronRight, Star
} from 'lucide-react';

const FEATURES = [
  {
    icon: Brain,
    color: 'from-violet-600 to-indigo-600',
    glow: 'rgba(139,92,246,0.3)',
    title: 'AI Command Center',
    desc: 'Natural language commands that understand your club. Ask the AI anything — it plans, proposes, and executes with your approval.',
  },
  {
    icon: Calendar,
    color: 'from-indigo-600 to-blue-600',
    glow: 'rgba(99,102,241,0.3)',
    title: 'Smart Event Management',
    desc: 'Create and manage events end-to-end. Track budgets, attendance, timelines, and tasks — all in one place.',
  },
  {
    icon: Users,
    color: 'from-blue-600 to-cyan-600',
    glow: 'rgba(59,130,246,0.3)',
    title: 'Volunteer Intelligence',
    desc: 'Automatically detect overloaded volunteers, suggest optimal task assignments, and track everyone\'s workload.',
  },
  {
    icon: Megaphone,
    color: 'from-pink-600 to-rose-600',
    glow: 'rgba(236,72,153,0.3)',
    title: 'AI Announcement Generator',
    desc: 'Generate polished WhatsApp, Email, and Instagram posts from a single prompt — tailored to your event.',
  },
  {
    icon: CheckSquare,
    color: 'from-emerald-600 to-teal-600',
    glow: 'rgba(16,185,129,0.3)',
    title: 'Task Planning & Tracking',
    desc: 'AI-generated task graphs, dependency tracking, cascaded rescheduling, and phase-based organization.',
  },
  {
    icon: Shield,
    color: 'from-amber-600 to-orange-600',
    glow: 'rgba(245,158,11,0.3)',
    title: 'Safe Action Proposals',
    desc: 'Every AI action creates a reviewable diff before applying changes. Full audit log and one-click undo.',
  },
];

const STATS = [
  { value: '10x', label: 'Faster event planning' },
  { value: '∞', label: 'Natural language commands' },
  { value: '3', label: 'AI announcement formats' },
  { value: '100%', label: 'Reversible AI actions' },
];

const HOW_IT_WORKS = [
  {
    step: '01',
    title: 'Connect your club',
    desc: 'Sign up and set up your club profile. Import events, volunteers, and tasks in seconds.',
  },
  {
    step: '02',
    title: 'Talk to your AI',
    desc: 'Type any command in plain English. The AI interprets, plans, and proposes changes for your review.',
  },
  {
    step: '03',
    title: 'Approve & execute',
    desc: 'Review the AI\'s action diff, approve or reject, and watch it all happen instantly.',
  },
];

function FloatingCard({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`glass rounded-2xl p-5 ${className}`}>
      {children}
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="mesh-bg min-h-screen overflow-x-hidden">
      {/* ── NAVBAR ── */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 sm:px-6 md:px-12 py-3.5 sm:py-4 border-b border-white/5 bg-slate-950/70 backdrop-blur-xl">
        <div className="flex items-center gap-2.5 sm:gap-3">
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
          </div>
          <span className="text-lg sm:text-xl font-bold text-white tracking-tight">ClubOps <span className="gradient-text">AI</span></span>
        </div>
        <div className="hidden md:flex items-center gap-8 text-sm text-slate-400">
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#how-it-works" className="hover:text-white transition-colors">How it works</a>
          <a href="#stats" className="hover:text-white transition-colors">Stats</a>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <Link
            to="/login"
            className="hidden sm:block text-sm text-slate-400 hover:text-white transition-colors px-3 sm:px-4 py-2"
          >
            Sign in
          </Link>
          <Link
            to="/register"
            id="nav-get-started"
            className="flex items-center gap-1.5 sm:gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs sm:text-sm font-semibold px-3.5 sm:px-4 py-2 rounded-xl transition-all hover:shadow-lg hover:shadow-indigo-500/25"
          >
            Get Started <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="w-full pt-28 sm:pt-32 pb-16 sm:pb-20 px-4 sm:px-6 relative flex flex-col items-center">
        {/* Background orbs */}
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl animate-glow pointer-events-none" />
        <div className="absolute top-40 right-1/4 w-80 h-80 bg-violet-600/15 rounded-full blur-3xl animate-glow pointer-events-none" style={{ animationDelay: '1.5s' }} />

        <div className="w-full max-w-6xl mx-auto text-center relative flex flex-col items-center">
          {/* Badge */}
          <div className="animate-slide-up inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold px-3.5 sm:px-4 py-1.5 sm:py-2 rounded-full mb-6 sm:mb-8 uppercase tracking-widest">
            <Sparkles className="w-3.5 h-3.5" />
            AI-Powered Club Management
          </div>

          {/* Headline */}
          <h1 className="animate-slide-up delay-100 text-4xl sm:text-5xl md:text-7xl font-black text-white leading-[1.1] sm:leading-[1.08] tracking-tight mb-5 sm:mb-6 text-center">
            Run your club<br />
            <span className="gradient-text">10× smarter</span>
          </h1>

          {/* Sub-headline */}
          <p className="animate-slide-up delay-200 text-base sm:text-lg md:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed mb-8 sm:mb-10 px-2 text-center">
            ClubOps AI is the all-in-one platform for college clubs. Manage events, volunteers, and tasks — powered by an AI that speaks plain English.
          </p>

          {/* CTAs */}
          <div className="animate-slide-up delay-300 w-full flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center items-center mb-12 sm:mb-16 max-w-md sm:max-w-none mx-auto">
            <Link
              to="/register"
              id="hero-start-free"
              className="w-full sm:w-auto group flex items-center justify-center gap-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold px-6 sm:px-8 py-3.5 sm:py-4 rounded-2xl transition-all shadow-2xl shadow-indigo-500/30 hover:shadow-indigo-500/50 hover:-translate-y-0.5"
            >
              <Zap className="w-5 h-5" />
              Start for free
              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              to="/login"
              className="w-full sm:w-auto flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold px-6 sm:px-8 py-3.5 sm:py-4 rounded-2xl transition-all"
            >
              Sign in to dashboard
            </Link>
          </div>

          {/* Hero UI Preview */}
          <div className="animate-fade-in delay-400 relative w-full max-w-4xl mx-auto">
            {/* Floating cards around preview */}
            <FloatingCard className="absolute -left-2 md:-left-8 lg:-left-12 top-8 w-52 animate-float z-10 hidden md:block text-left">
              <div className="flex items-center gap-2 mb-3">
                <Bot className="w-4 h-4 text-violet-400" />
                <span className="text-xs font-semibold text-slate-300">AI Command</span>
              </div>
              <p className="text-xs text-slate-400 italic leading-relaxed">"Assign all unowned tasks to available volunteers"</p>
              <div className="mt-3 flex items-center gap-2">
                <div className="h-1.5 rounded-full bg-violet-500/40 flex-1" />
                <span className="text-[10px] text-violet-400 font-semibold">Processing…</span>
              </div>
            </FloatingCard>

            <FloatingCard className="absolute -right-2 md:-right-8 lg:-right-12 top-12 w-48 animate-float-delay z-10 hidden md:block text-left">
              <div className="flex items-center gap-2 mb-3">
                <CheckSquare className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-semibold text-slate-300">Tasks Today</span>
              </div>
              <div className="space-y-2">
                {['Setup venue', 'Send invites', 'Book catering'].map((t, i) => (
                  <div key={t} className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${i === 0 ? 'bg-emerald-500 border-emerald-500' : 'border-slate-600'}`}>
                      {i === 0 && <span className="text-white text-[8px]">✓</span>}
                    </div>
                    <span className={`text-[11px] ${i === 0 ? 'line-through text-slate-600' : 'text-slate-300'}`}>{t}</span>
                  </div>
                ))}
              </div>
            </FloatingCard>

            {/* Main dashboard mock */}
            <div className="glass rounded-2xl sm:rounded-3xl overflow-hidden shadow-2xl shadow-black/60 border border-white/10">
              {/* Mock header */}
              <div className="bg-slate-900/80 border-b border-white/5 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
                <div className="flex items-center gap-2.5 sm:gap-3">
                  <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
                    <span className="text-white text-[10px] sm:text-xs font-bold">CO</span>
                  </div>
                  <span className="text-white font-bold text-xs sm:text-sm">ClubOps AI</span>
                </div>
                <div className="flex items-center gap-1.5 sm:gap-2">
                  <div className="w-2 sm:w-2.5 h-2 sm:h-2.5 rounded-full bg-red-500/70" />
                  <div className="w-2 sm:w-2.5 h-2 sm:h-2.5 rounded-full bg-yellow-500/70" />
                  <div className="w-2 sm:w-2.5 h-2 sm:h-2.5 rounded-full bg-green-500/70" />
                </div>
              </div>

              <div className="flex h-64 sm:h-72 md:h-80">
                {/* Mock sidebar */}
                <div className="w-12 sm:w-14 md:w-48 bg-slate-900/60 border-r border-white/5 p-2 sm:p-3 flex flex-col gap-1 shrink-0">
                  {[
                    { icon: '⬛', label: 'Dashboard', active: true },
                    { icon: '📅', label: 'Events', active: false },
                    { icon: '👥', label: 'Volunteers', active: false },
                    { icon: '✅', label: 'Tasks', active: false },
                    { icon: '📣', label: 'Announcements', active: false },
                  ].map(item => (
                    <div key={item.label} className={`flex items-center gap-2 sm:gap-3 px-2 md:px-3 py-1.5 sm:py-2 rounded-xl transition-colors ${item.active ? 'bg-indigo-500/15 border border-indigo-500/20' : ''}`}>
                      <span className="text-xs sm:text-sm">{item.icon}</span>
                      <span className={`hidden md:block text-xs font-medium ${item.active ? 'text-indigo-300' : 'text-slate-500'}`}>{item.label}</span>
                    </div>
                  ))}
                  <div className="mt-auto flex items-center gap-2 sm:gap-3 px-2 md:px-3 py-1.5 sm:py-2 rounded-xl bg-violet-500/10 border border-violet-500/20">
                    <Sparkles className="w-3.5 sm:w-4 h-3.5 sm:h-4 text-violet-400 shrink-0" />
                    <span className="hidden md:block text-xs font-medium text-violet-400">AI Assistant</span>
                  </div>
                </div>

                {/* Mock main area */}
                <div className="flex-1 p-3 sm:p-5 overflow-hidden">
                  {/* Stats row */}
                  <div className="grid grid-cols-3 gap-1.5 sm:gap-3 mb-3 sm:mb-5">
                    {[
                      { label: 'Total Events', val: '12', color: 'text-indigo-400' },
                      { label: 'Upcoming', val: '4', color: 'text-amber-400' },
                      { label: 'Volunteers', val: '28', color: 'text-emerald-400' },
                    ].map(s => (
                      <div key={s.label} className="bg-slate-800/50 rounded-xl p-2 sm:p-3 border border-white/5">
                        <p className="text-[9px] sm:text-[10px] text-slate-500 mb-0.5 sm:mb-1 truncate">{s.label}</p>
                        <p className={`text-sm sm:text-lg font-bold ${s.color}`}>{s.val}</p>
                      </div>
                    ))}
                  </div>
                  {/* Event list mock */}
                  <p className="text-[11px] sm:text-xs font-semibold text-slate-400 mb-2 sm:mb-3">Recent Events</p>
                  <div className="space-y-1.5 sm:space-y-2">
                    {[
                      { title: 'Tech Hackathon 2025', date: 'Sep 22', status: 'PUBLISHED', color: 'text-emerald-400 bg-emerald-500/10' },
                      { title: 'AI Workshop Series', date: 'Oct 5', status: 'DRAFT', color: 'text-yellow-400 bg-yellow-500/10' },
                      { title: 'Annual Cultural Fest', date: 'Nov 12', status: 'PLANNING', color: 'text-blue-400 bg-blue-500/10' },
                    ].map(ev => (
                      <div key={ev.title} className="flex items-center justify-between bg-slate-800/30 rounded-lg px-2.5 sm:px-3 py-1.5 sm:py-2 border border-white/5">
                        <div className="min-w-0 pr-2">
                          <p className="text-[11px] sm:text-xs font-medium text-white truncate">{ev.title}</p>
                          <p className="text-[9px] sm:text-[10px] text-slate-500">{ev.date}</p>
                        </div>
                        <span className={`text-[8px] sm:text-[9px] font-bold px-1.5 sm:px-2 py-0.5 rounded-full shrink-0 ${ev.color}`}>{ev.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Glow under preview */}
            <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 w-3/4 h-16 bg-indigo-600/20 blur-2xl rounded-full pointer-events-none" />
          </div>
        </div>
      </section>

      {/* ── STATS ── */}
      <section id="stats" className="w-full py-12 sm:py-16 px-4 sm:px-6 flex justify-center">
        <div className="w-full max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-6">
          {STATS.map(stat => (
            <div key={stat.label} className="text-center glass rounded-2xl py-6 sm:py-8 px-3 sm:px-4">
              <p className="text-3xl sm:text-4xl md:text-5xl font-black gradient-text mb-1.5 sm:mb-2">{stat.value}</p>
              <p className="text-xs text-slate-400 font-medium">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section id="features" className="w-full py-14 sm:py-20 px-4 sm:px-6 flex justify-center">
        <div className="w-full max-w-6xl mx-auto">
          <div className="text-center mb-10 sm:mb-16">
            <p className="text-indigo-400 text-xs sm:text-sm font-semibold uppercase tracking-widest mb-2.5 sm:mb-3">Features</p>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-3 sm:mb-4 tracking-tight">
              Everything your club needs
            </h2>
            <p className="text-slate-400 text-sm sm:text-base md:text-lg max-w-xl mx-auto leading-relaxed">
              From AI-powered task planning to multi-platform announcements — built for the way modern clubs actually work.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {FEATURES.map((feature, i) => (
              <div
                key={feature.title}
                className="group glass rounded-2xl sm:rounded-3xl p-5 sm:p-6 hover:border-indigo-500/30 transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl"
                style={{ animationDelay: `${i * 0.1}s` }}
              >
                <div
                  className={`w-11 h-11 sm:w-12 sm:h-12 rounded-2xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 sm:mb-5 shadow-lg group-hover:scale-110 transition-transform`}
                  style={{ boxShadow: `0 8px 24px ${feature.glow}` }}
                >
                  <feature.icon className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                </div>
                <h3 className="text-base sm:text-lg font-bold text-white mb-2">{feature.title}</h3>
                <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section id="how-it-works" className="w-full py-14 sm:py-20 px-4 sm:px-6 flex justify-center">
        <div className="w-full max-w-5xl mx-auto">
          <div className="text-center mb-10 sm:mb-16">
            <p className="text-violet-400 text-xs sm:text-sm font-semibold uppercase tracking-widest mb-2.5 sm:mb-3">How it works</p>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-3 sm:mb-4 tracking-tight">
              Up and running in minutes
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8 relative">
            {/* Connector line */}
            <div className="hidden md:block absolute top-10 left-1/6 right-1/6 h-px bg-gradient-to-r from-transparent via-indigo-500/40 to-transparent" />

            {HOW_IT_WORKS.map(step => (
              <div key={step.step} className="relative text-center p-4">
                <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-3xl bg-gradient-to-br from-indigo-600 to-violet-600 flex flex-col items-center justify-center mx-auto mb-5 sm:mb-6 shadow-2xl shadow-indigo-500/30">
                  <span className="text-indigo-200 text-[10px] font-bold uppercase tracking-widest">{step.step}</span>
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-3">{step.title}</h3>
                <p className="text-slate-400 text-xs sm:text-sm leading-relaxed max-w-xs mx-auto">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── AI DEMO BLOCK ── */}
      <section className="w-full py-14 sm:py-20 px-4 sm:px-6 flex justify-center">
        <div className="w-full max-w-5xl mx-auto">
          <div className="glass rounded-2xl sm:rounded-3xl p-5 sm:p-8 md:p-12 border border-violet-500/20 relative overflow-hidden">
            {/* bg glow */}
            <div className="absolute inset-0 bg-gradient-to-br from-violet-600/10 to-indigo-600/5 pointer-events-none" />
            <div className="relative flex flex-col md:flex-row items-center gap-6 sm:gap-8 md:gap-10">
              <div className="flex-1 text-center md:text-left">
                <div className="inline-flex items-center gap-2 bg-violet-500/15 border border-violet-500/30 text-violet-300 text-xs font-semibold px-3 py-1.5 rounded-full mb-4 sm:mb-5 uppercase tracking-wider">
                  <Bot className="w-3.5 h-3.5" />
                  AI in action
                </div>
                <h2 className="text-2xl sm:text-3xl md:text-4xl font-black text-white mb-3 sm:mb-4 leading-tight tracking-tight">
                  Just type what<br className="hidden sm:inline" /> you need
                </h2>
                <p className="text-slate-400 text-sm sm:text-base leading-relaxed mb-6 max-w-md mx-auto md:mx-0">
                  No forms. No dropdowns. Just tell the AI what you want — it handles the rest and asks before applying any changes.
                </p>
                <Link
                  to="/register"
                  className="inline-flex items-center justify-center gap-2 bg-violet-600 hover:bg-violet-500 text-white font-bold px-6 py-3 rounded-xl transition-all shadow-lg shadow-violet-500/30"
                >
                  Try it free <ArrowRight className="w-4 h-4" />
                </Link>
              </div>

              {/* Chat mock */}
              <div className="flex-1 w-full max-w-sm">
                <div className="bg-slate-900/80 rounded-2xl border border-white/10 overflow-hidden shadow-xl">
                  <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5">
                    <Bot className="w-4 h-4 text-violet-400" />
                    <span className="text-xs font-semibold text-slate-300">AI Assistant</span>
                    <span className="ml-auto w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  </div>
                  <div className="p-3.5 sm:p-4 space-y-3.5 sm:space-y-4">
                    {/* User message */}
                    <div className="flex justify-end">
                      <div className="bg-indigo-600 text-white text-xs rounded-2xl rounded-tr-sm px-3.5 sm:px-4 py-2 sm:py-2.5 max-w-[85%]">
                        Assign all unowned tasks due this week to Arjun
                      </div>
                    </div>
                    {/* AI response */}
                    <div className="flex gap-2">
                      <div className="w-7 h-7 rounded-full bg-violet-600/30 border border-violet-500/30 flex items-center justify-center shrink-0">
                        <Bot className="w-3.5 h-3.5 text-violet-400" />
                      </div>
                      <div className="bg-slate-800 text-slate-200 text-xs rounded-2xl rounded-tl-sm px-3.5 sm:px-4 py-2 sm:py-2.5 max-w-[85%] leading-relaxed">
                        Found 3 unowned tasks due this week. Proposing assignment to Arjun (currently low load).<br /><br />
                        <span className="font-semibold text-violet-300">Proposal #42 created →</span>
                      </div>
                    </div>
                    {/* Proposal action */}
                    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-2.5 sm:p-3">
                      <p className="text-[10px] text-slate-400 mb-2">Proposal #42 — 3 tasks → Arjun</p>
                      <div className="flex gap-2">
                        <button className="flex-1 bg-emerald-600/80 hover:bg-emerald-600 text-white text-[11px] font-semibold py-1.5 rounded-lg transition-colors">✓ Apply</button>
                        <button className="flex-1 bg-slate-700 hover:bg-slate-650 text-slate-300 text-[11px] font-semibold py-1.5 rounded-lg transition-colors">✗ Reject</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── TESTIMONIAL / TRUST ── */}
      <section className="w-full py-12 sm:py-16 px-4 sm:px-6 flex justify-center">
        <div className="w-full max-w-4xl mx-auto text-center">
          <div className="flex justify-center gap-1 mb-3 sm:mb-4">
            {[...Array(5)].map((_, i) => (
              <Star key={i} className="w-4 h-4 sm:w-5 sm:h-5 text-amber-400 fill-amber-400" />
            ))}
          </div>
          <blockquote className="text-xl sm:text-2xl md:text-3xl font-bold text-white mb-4 sm:mb-6 leading-relaxed">
            "ClubOps AI cut our event planning time from{' '}
            <span className="gradient-text">days to hours.</span>"
          </blockquote>
          <p className="text-slate-400 text-xs sm:text-sm">
            — Student club organizers at leading engineering colleges
          </p>
        </div>
      </section>

      {/* ── CTA BANNER ── */}
      <section className="w-full py-14 sm:py-20 px-4 sm:px-6 flex justify-center">
        <div className="w-full max-w-4xl mx-auto text-center">
          <div className="glass rounded-2xl sm:rounded-3xl p-6 sm:p-10 md:p-12 relative overflow-hidden border border-indigo-500/20">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-600/15 to-violet-600/10 pointer-events-none" />
            <div className="absolute -top-12 -right-12 w-48 h-48 bg-violet-600/20 rounded-full blur-3xl pointer-events-none" />
            <div className="relative">
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-3 sm:mb-4 tracking-tight">
                Ready to run your<br />club with AI?
              </h2>
              <p className="text-slate-400 text-sm sm:text-base md:text-lg mb-6 sm:mb-8 max-w-lg mx-auto">
                Join club organizers who've already upgraded to smarter operations.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center max-w-md sm:max-w-none mx-auto">
                <Link
                  to="/register"
                  id="cta-register"
                  className="w-full sm:w-auto group flex items-center justify-center gap-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold px-6 sm:px-8 py-3.5 sm:py-4 rounded-2xl transition-all shadow-2xl shadow-indigo-500/30 hover:-translate-y-0.5"
                >
                  <Zap className="w-5 h-5" />
                  Create free account
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </Link>
                <Link
                  to="/login"
                  className="w-full sm:w-auto flex items-center justify-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold px-6 sm:px-8 py-3.5 sm:py-4 rounded-2xl transition-all"
                >
                  I have an account
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="w-full py-8 sm:py-10 px-4 sm:px-6 border-t border-white/5 flex justify-center">
        <div className="w-full max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
          <div className="flex items-center gap-2.5 sm:gap-3">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <Sparkles className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="text-sm font-bold text-white">ClubOps AI</span>
          </div>
          <p className="text-xs text-slate-500">
            © {new Date().getFullYear()} ClubOps AI. Built with ❤️ for college clubs.
          </p>
          <div className="flex items-center gap-6 text-xs text-slate-400">
            <Link to="/login" className="hover:text-white transition-colors">Login</Link>
            <Link to="/register" className="hover:text-white transition-colors">Register</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
