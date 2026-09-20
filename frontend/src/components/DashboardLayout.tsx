import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LogOut, LayoutDashboard, Calendar, Users, Megaphone,
  CheckSquare, Sparkles, Menu, X, BookOpen, Briefcase, ShieldCheck, Network, Mic, User as UserIcon, Bot
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import VoiceAssistant from './voice/VoiceAssistant';

interface DashboardLayoutProps {
  children: React.ReactNode;
  title: string;
  activeEventId?: number;
}

export default function DashboardLayout({ children, title, activeEventId }: DashboardLayoutProps) {
  const { user, logout, isAdmin, isClubHead, isClubLeader, isSubTeamLead, isVolunteer, userTeams } = useAuth();
  const location = useLocation();
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);


  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/profile', icon: UserIcon, label: 'My Profile' },
    ...(isAdmin ? [{ to: '/admin/organization', icon: Network, label: 'Organization' }] : []),
    ...((isAdmin || isClubHead || isSubTeamLead) ? [{ to: '/teams', icon: Briefcase, label: isSubTeamLead && !isClubHead ? 'My SubTeam' : 'Teams' }] : []),
    ...((isAdmin || isClubHead) ? [{ to: '/events', icon: Calendar, label: 'Events' }] : []),
    ...((isAdmin || isClubHead || isSubTeamLead) ? [{ to: '/volunteers', icon: Users, label: isSubTeamLead && !isClubHead ? 'Team Volunteers' : 'Volunteers' }] : []),
    { to: '/tasks', icon: CheckSquare, label: isVolunteer ? 'My Tasks' : 'Tasks' },
    { to: '/announcements', icon: Megaphone, label: 'Announcements' },
    { to: '/agentic-ai', icon: Bot, label: 'Agentic AI' },
    { to: '/documents', icon: BookOpen, label: 'RAG Knowledge' },
    ...((isAdmin || isClubHead || isClubLeader) ? [{ to: '/permissions', icon: ShieldCheck, label: 'Permissions' }] : []),

  ];

  const getRoleLabel = () => {
    if (isAdmin) return 'System Admin';
    if (isClubHead) return 'Club Head';
    const leaderTeam = userTeams.find(t => t.role === 'SUBTEAM_LEAD' || t.role === 'TEAM_LEADER');
    if (leaderTeam) return `${leaderTeam.name} Lead`;
    if (isSubTeamLead) return 'SubTeam Lead';
    if (isVolunteer) return 'Volunteer';
    if (userTeams.length > 0) return `${userTeams[0].name} Member`;
    return user?.role?.toLowerCase().replace('_', ' ') || 'Member';
  };

  return (
    <div className="min-h-screen bg-slate-950 flex text-slate-200 antialiased selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Desktop Sidebar */}
      <aside className="w-64 bg-slate-900/90 backdrop-blur-md border-r border-slate-800 hidden md:flex flex-col shrink-0 z-20">
        <div className="p-6 border-b border-slate-800/60">
          <Link to="/dashboard" className="text-xl font-bold text-white flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-tr from-indigo-600 to-violet-500 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <span className="text-white text-sm font-black tracking-wider">CO</span>
            </div>
            <div>
              <span className="bg-gradient-to-r from-white via-slate-100 to-indigo-200 bg-clip-text text-transparent font-black tracking-tight">ClubOps</span>
              <span className="text-indigo-400 font-bold ml-1 text-xs px-1.5 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">AI</span>
            </div>
          </Link>
        </div>

        <nav className="flex-1 px-4 space-y-1.5 mt-4">
          <p className="px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Management</p>
          {navItems.map((item) => {
            const isActive = location.pathname === item.to || (item.to !== '/dashboard' && location.pathname.startsWith(item.to));
            return (
              <Link
                key={item.label}
                to={item.to}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all duration-200 ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-300 font-semibold border border-indigo-500/30 shadow-sm shadow-indigo-950'
                    : 'hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-transparent'
                }`}
              >
                <item.icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                <span className="text-sm">{item.label}</span>
              </Link>
            );
          })}

          <div className="pt-3">
            <p className="px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2">Intelligence</p>

            {/* Voice AI Button */}
            <button
              onClick={() => setVoiceOpen(true)}
              className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all duration-200 bg-gradient-to-r from-rose-600/10 to-amber-600/10 hover:from-rose-600/20 hover:to-amber-600/20 text-rose-300 hover:text-white border border-rose-500/20 hover:border-rose-500/40 group mt-1"
            >
              <Mic className="w-4 h-4 text-rose-400 group-hover:scale-110 transition-transform" />
              <span className="font-semibold text-sm">Voice AI</span>
              <span className="ml-auto text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/30 px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider">
                Multilingual
              </span>
            </button>
          </div>
        </nav>

        <div className="p-4 mt-auto border-t border-slate-800/60">
          <div className="bg-slate-850/80 p-3.5 rounded-xl border border-slate-700/40 shadow-sm">
            <Link to="/profile" className="flex items-center gap-3 mb-3 group hover:opacity-90 transition-opacity">
              <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center text-white font-bold text-xs shadow-sm group-hover:scale-105 transition-transform">
                {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <div className="overflow-hidden">
                <p className="text-xs font-semibold text-white truncate group-hover:text-indigo-300 transition-colors">{user?.full_name}</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`inline-block px-1.5 py-0.5 text-[10px] font-semibold rounded ${
                    isAdmin
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      : isClubHead
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : isSubTeamLead
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                  }`}>
                    {getRoleLabel()}
                  </span>
                </div>
              </div>
            </Link>
            <button
              onClick={logout}
              className="w-full flex items-center justify-center gap-2 text-xs font-medium text-slate-400 hover:text-red-400 hover:bg-red-400/10 py-2 rounded-lg transition-colors border border-transparent hover:border-red-500/20"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} />
          <div className="relative w-72 bg-slate-900 border-r border-slate-800 p-6 flex flex-col h-full z-10 shadow-2xl">
            <div className="flex items-center justify-between pb-6 border-b border-slate-800">
              <Link to="/dashboard" onClick={() => setMobileMenuOpen(false)} className="text-lg font-bold text-white flex items-center gap-2.5">
                <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center font-black text-xs">CO</div>
                <span>ClubOps AI</span>
              </Link>
              <button onClick={() => setMobileMenuOpen(false)} className="p-1 rounded-lg text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <nav className="flex-1 space-y-1.5 mt-6">
              {navItems.map((item) => {
                const isActive = location.pathname === item.to || (item.to !== '/dashboard' && location.pathname.startsWith(item.to));
                return (
                  <Link
                    key={item.label}
                    to={item.to}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium ${
                      isActive ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30' : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    <item.icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}


              <button
                onClick={() => { setMobileMenuOpen(false); setVoiceOpen(true); }}
                className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium bg-rose-600/15 text-rose-300 border border-rose-500/30 mt-2"
              >
                <Mic className="w-4 h-4 text-rose-400" />
                <span>Voice AI (Multilingual)</span>
              </button>
            </nav>

            <div className="pt-4 border-t border-slate-800">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                  {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                <div className="truncate">
                  <p className="text-xs font-medium text-white truncate">{user?.full_name}</p>
                  <div className="flex items-center gap-1 mt-0.5">
                    <span className={`inline-block px-1.5 py-0.5 text-[9px] font-semibold rounded ${
                      isAdmin
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : isClubHead
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : isSubTeamLead
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                    }`}>
                      {getRoleLabel()}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={logout}
                className="w-full flex items-center justify-center gap-2 text-xs text-red-400 hover:bg-red-400/10 py-2 rounded-lg border border-red-500/20"
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden min-w-0">
        <header className="h-16 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md flex items-center justify-between px-4 sm:px-8 shrink-0 z-10">
          <div className="flex items-center gap-3">
            {/* Mobile menu trigger */}
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              aria-label="Open menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-base sm:text-lg font-bold text-white tracking-tight">{title}</h1>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {/* Voice AI Quick Launcher */}
            <button
              onClick={() => setVoiceOpen(true)}
              title="Speak in English, Hindi, or Gujarati"
              className="flex items-center gap-2 bg-slate-850 hover:bg-slate-800 text-slate-200 border border-slate-700 hover:border-rose-500/40 px-3 sm:px-3.5 py-1.5 sm:py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all hover:scale-[1.02] active:scale-[0.98] shadow-sm"
            >
              <Mic className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
              <span className="hidden sm:inline">Voice Mode</span>
            </button>

            {/* Agentic AI Command Center Quick Link */}
            <Link
              to="/agentic-ai"
              className="flex items-center gap-2 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white px-3 sm:px-4 py-1.5 sm:py-2 rounded-xl text-xs sm:text-sm font-semibold shadow-lg shadow-indigo-500/20 transition-all hover:shadow-indigo-500/30 hover:scale-[1.02] active:scale-[0.98]"
            >
              <Bot className="w-3.5 h-3.5 text-violet-200" />
              <span className="hidden sm:inline">Agentic AI</span>
              <span className="sm:hidden">AI</span>
            </Link>

            {/* User Profile Quick Button */}
            <Link
              to="/profile"
              title="My Profile"
              className="flex items-center gap-2 bg-slate-850 hover:bg-slate-800 text-slate-200 border border-slate-700 hover:border-indigo-500/40 px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-xl text-xs sm:text-sm font-medium transition-all hover:scale-[1.02] active:scale-[0.98] shadow-sm"
            >
              <UserIcon className="w-3.5 h-3.5 text-indigo-400" />
              <span className="hidden md:inline">Profile</span>
            </Link>
          </div>
        </header>

        <div className="flex-1 overflow-auto p-4 sm:p-6 lg:p-8">
          {children}
        </div>
      </main>


      {/* Standalone Voice Assistant Modal (RAG mode) */}
      <VoiceAssistant
        isOpen={voiceOpen}
        onClose={() => setVoiceOpen(false)}
        activeEventId={activeEventId}
        mode="rag"
      />
    </div>
  );
}
