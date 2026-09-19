import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LogOut, LayoutDashboard, Calendar, Users, Megaphone, CheckSquare, Sparkles, Menu, X, Briefcase, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import AIChatPanel from './AIChatPanel';

interface DashboardLayoutProps {
  children: React.ReactNode;
  title: string;
  activeEventId?: number;
}

export default function DashboardLayout({ children, title, activeEventId }: DashboardLayoutProps) {
  const { user, logout, isClubLeader, userTeams } = useAuth();
  const location = useLocation();
  const [aiOpen, setAiOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/teams', icon: Briefcase, label: 'Teams' },
    { to: '/events', icon: Calendar, label: 'Events' },
    { to: '/volunteers', icon: Users, label: 'Volunteers' },
    { to: '/tasks', icon: CheckSquare, label: 'Tasks' },
    { to: '/announcements', icon: Megaphone, label: 'Announcements' },
    ...(isClubLeader ? [{ to: '/permissions', icon: ShieldCheck, label: 'Permissions' }] : []),
  ];

  const getRoleLabel = () => {
    if (isClubLeader) return 'Club Leader';
    const leaderTeam = userTeams.find(t => t.role === 'TEAM_LEADER');
    if (leaderTeam) return `${leaderTeam.name} Lead`;
    if (userTeams.length > 0) return `${userTeams[0].name} Member`;
    return user?.role?.toLowerCase().replace('_', ' ') || 'Member';
  };

  return (
    <div className="min-h-screen bg-slate-950 flex text-slate-200">
      {/* Desktop Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 hidden md:flex flex-col shrink-0">
        <div className="p-6">
          <Link to="/dashboard" className="text-xl font-bold text-white flex items-center gap-2.5">
            <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center shadow-md shadow-indigo-600/30">
              <span className="text-white text-sm font-bold tracking-tight">CO</span>
            </div>
            <span>ClubOps <span className="text-indigo-400">AI</span></span>
          </Link>
        </div>

        <nav className="flex-1 px-4 space-y-1.5 mt-1">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.to) && item.to !== '#';
            return (
              <Link
                key={item.label}
                to={item.to}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-colors font-medium text-sm ${
                  isActive
                    ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/25 shadow-sm'
                    : 'hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-transparent'
                }`}
              >
                <item.icon className="w-4 h-4 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}

          {/* AI Assistant Button */}
          <button
            onClick={() => setAiOpen(true)}
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all hover:bg-violet-500/15 text-violet-400 hover:text-violet-300 border border-transparent hover:border-violet-500/25 mt-3 group"
          >
            <Sparkles className="w-4 h-4 shrink-0 text-violet-400 group-hover:scale-110 transition-transform" />
            <span className="font-medium text-sm">AI Assistant</span>
            <span className="ml-auto text-[10px] bg-violet-500/20 text-violet-300 px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider">Beta</span>
          </button>
        </nav>

        <div className="p-4 mt-auto">
          <div className="bg-slate-800/50 p-3.5 rounded-2xl border border-slate-700/50">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-9 h-9 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-full flex items-center justify-center text-white font-semibold text-xs shrink-0 shadow-inner">
                {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-white truncate">{user?.full_name || 'User'}</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`inline-block px-2 py-0.5 text-[10px] font-semibold rounded-md ${
                    isClubLeader
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : userTeams.some(t => t.role === 'TEAM_LEADER')
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : 'bg-slate-700/60 text-slate-300'
                  }`}>
                    {getRoleLabel()}
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={logout}
              className="w-full flex items-center justify-center gap-2 text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-400/10 py-2 rounded-xl transition-colors"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
            onClick={() => setMobileMenuOpen(false)}
          />
          <aside className="relative w-72 max-w-[80vw] bg-slate-900 border-r border-slate-800 flex flex-col h-full z-10 p-4 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4 px-2">
              <Link
                to="/dashboard"
                onClick={() => setMobileMenuOpen(false)}
                className="text-lg font-bold text-white flex items-center gap-2"
              >
                <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                  <span className="text-white text-xs font-bold">CO</span>
                </div>
                ClubOps AI
              </Link>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <nav className="flex-1 space-y-1 overflow-y-auto">
              {navItems.map((item) => {
                const isActive = location.pathname.startsWith(item.to) && item.to !== '#';
                return (
                  <Link
                    key={item.label}
                    to={item.to}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-colors font-medium text-sm ${
                      isActive
                        ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/25'
                        : 'hover:bg-slate-800/60 text-slate-400 hover:text-slate-200 border border-transparent'
                    }`}
                  >
                    <item.icon className="w-4 h-4 shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}

              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  setAiOpen(true);
                }}
                className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl transition-all bg-violet-500/10 text-violet-400 border border-violet-500/20 mt-3"
              >
                <Sparkles className="w-4 h-4 shrink-0" />
                <span className="font-medium text-sm">AI Assistant</span>
                <span className="ml-auto text-[9px] bg-violet-500/20 text-violet-300 px-1.5 py-0.5 rounded-full font-semibold uppercase">Beta</span>
              </button>
            </nav>

            <div className="pt-4 border-t border-slate-800 mt-auto">
              <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700/50">
                <div className="flex items-center gap-3 mb-2.5">
                  <div className="w-8 h-8 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-full flex items-center justify-center text-white font-semibold text-xs shrink-0">
                    {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-white truncate">{user?.full_name || 'User'}</p>
                    <div className="flex items-center gap-1 mt-0.5">
                      <span className={`inline-block px-1.5 py-0.5 text-[9px] font-semibold rounded ${
                        isClubLeader
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : userTeams.some(t => t.role === 'TEAM_LEADER')
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-slate-700/60 text-slate-300'
                      }`}>
                        {getRoleLabel()}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    logout();
                  }}
                  className="w-full flex items-center justify-center gap-2 text-xs text-red-400 hover:text-red-300 hover:bg-red-400/10 py-1.5 rounded-lg transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Sign out
                </button>
              </div>
            </div>
          </aside>
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden min-w-0">
        <header className="h-16 border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm flex items-center justify-between px-4 sm:px-6 lg:px-8 shrink-0 gap-3">
          <div className="flex items-center gap-3 min-w-0">
            {/* Hamburger button on mobile */}
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden w-9 h-9 flex items-center justify-center rounded-xl bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors shrink-0"
              aria-label="Open Navigation Menu"
            >
              <Menu className="w-4 h-4" />
            </button>
            <h2 className="text-base sm:text-lg font-semibold text-white truncate">{title}</h2>
          </div>

          {/* Header Action / AI button */}
          <div className="flex items-center gap-2.5 shrink-0">
            <button
              onClick={() => setAiOpen(true)}
              className="flex items-center gap-2 text-xs font-semibold bg-violet-600/20 hover:bg-violet-600/30 border border-violet-500/30 text-violet-300 px-3.5 py-2 rounded-xl transition-colors shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5 text-violet-400" />
              <span>AI Assistant</span>
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-auto p-4 sm:p-6 lg:p-8">
          <div className="w-full max-w-7xl mx-auto">
            {children}
          </div>
        </div>
      </main>

      {/* AI Chat Panel */}
      <AIChatPanel
        isOpen={aiOpen}
        onClose={() => setAiOpen(false)}
        activeEventId={activeEventId}
      />
    </div>
  );
}
