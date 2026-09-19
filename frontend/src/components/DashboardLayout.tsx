import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LogOut, LayoutDashboard, Calendar, Users } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface DashboardLayoutProps {
  children: React.ReactNode;
  title: string;
}

export default function DashboardLayout({ children, title }: DashboardLayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/events', icon: Calendar, label: 'Events' },
    { to: '/volunteers', icon: Users, label: 'Volunteers' },
  ];

  return (
    <div className="min-h-screen bg-slate-950 flex text-slate-200">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 hidden md:flex flex-col">
        <div className="p-6">
          <Link to="/dashboard" className="text-xl font-bold text-white flex items-center gap-2">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm">CO</span>
            </div>
            ClubOps AI
          </Link>
        </div>

        <nav className="flex-1 px-4 space-y-2 mt-4">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.to) && item.to !== '#';
            return (
              <Link
                key={item.label}
                to={item.to}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
                  isActive
                    ? 'bg-indigo-500/10 text-indigo-400'
                    : 'hover:bg-slate-800/50 text-slate-400 hover:text-slate-200'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 mt-auto">
          <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-slate-700 rounded-full flex items-center justify-center text-slate-300 font-medium">
                {user?.full_name?.charAt(0) || 'U'}
              </div>
              <div>
                <p className="text-sm font-medium text-white">{user?.full_name}</p>
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
        <header className="h-16 border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm flex items-center px-8 shrink-0">
          <h2 className="text-lg font-medium text-white">{title}</h2>
        </header>

        <div className="flex-1 overflow-auto p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
