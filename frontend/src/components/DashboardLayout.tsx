import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LogOut, LayoutDashboard, Calendar, Users, Megaphone, CheckSquare, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import AIChatPanel from './AIChatPanel';

interface DashboardLayoutProps {
  children: React.ReactNode;
  title: string;
  activeEventId?: number;
}

export default function DashboardLayout({ children, title, activeEventId }: DashboardLayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [aiOpen, setAiOpen] = useState(false);

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/events', icon: Calendar, label: 'Events' },
    { to: '/volunteers', icon: Users, label: 'Volunteers' },
    { to: '/tasks', icon: CheckSquare, label: 'Tasks' },
    { to: '/announcements', icon: Megaphone, label: 'Announcements' },
  ];

  return (
    <div className="min-h-screen bg-slate-950 flex text-slate-200">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 hidden md:flex flex-col">
        <div className="p-6">
          <Link to="/dashboard" className="text-xl font-bold text-white flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm font-bold">CO</span>
            </div>
            ClubOps AI
          </Link>
        </div>

        <nav className="flex-1 px-4 space-y-1 mt-2">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.to) && item.to !== '#';
            return (
              <Link
                key={item.label}
                to={item.to}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-xl transition-colors ${
                  isActive
                    ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                    : 'hover:bg-slate-800/50 text-slate-400 hover:text-slate-200 border border-transparent'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium text-sm">{item.label}</span>
              </Link>
            );
          })}

          {/* AI Assistant Button */}
          <button
            onClick={() => setAiOpen(true)}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all hover:bg-violet-500/10 text-violet-400 hover:text-violet-300 border border-transparent hover:border-violet-500/20 mt-2"
          >
            <Sparkles className="w-5 h-5" />
            <span className="font-medium text-sm">AI Assistant</span>
            <span className="ml-auto text-[9px] bg-violet-500/20 text-violet-400 px-1.5 py-0.5 rounded-full font-semibold uppercase tracking-wider">Beta</span>
          </button>
        </nav>

        <div className="p-4 mt-auto">
          <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                {user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <div className="overflow-hidden">
                <p className="text-sm font-medium text-white truncate">{user?.full_name}</p>
                <p className="text-xs text-slate-400 capitalize">{user?.role?.toLowerCase().replace('_', ' ')}</p>
              </div>
            </div>
            <button
              onClick={logout}
              className="w-full flex items-center justify-center gap-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-400/10 py-2 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <header className="h-16 border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm flex items-center justify-between px-8 shrink-0">
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          {/* Mobile AI button */}
          <button
            onClick={() => setAiOpen(true)}
            className="md:hidden flex items-center gap-2 text-xs bg-violet-600/20 hover:bg-violet-600/30 border border-violet-500/30 text-violet-400 px-3 py-1.5 rounded-lg transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            AI
          </button>
        </header>

        <div className="flex-1 overflow-auto p-8">
          {children}
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
