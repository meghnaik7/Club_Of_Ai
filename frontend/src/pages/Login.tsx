import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  LogIn, Loader2, ShieldAlert, Award, Briefcase, Users,
  Sparkles, CheckCircle2, Eye, EyeOff
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../lib/axios';

interface DemoPersona {
  key: 'admin' | 'club_head' | 'subteam_lead' | 'volunteer';
  title: string;
  badge: string;
  badgeColor: string;
  icon: React.ElementType;
  description: string;
  accent: string;
  email: string;
  password: string;
}

const DEMO_PERSONAS: DemoPersona[] = [
  {
    key: 'admin',
    title: 'Admin Role',
    badge: 'System Admin',
    badgeColor: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
    icon: ShieldAlert,
    description: 'Full management of clubs, roles, audit logs & system config',
    accent: 'hover:border-rose-500/50 hover:bg-rose-500/5',
    email: 'admin@demo.local',
    password: 'demo123',
  },
  {
    key: 'club_head',
    title: 'Club Head Role',
    badge: 'GDG Demo Club',
    badgeColor: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    icon: Award,
    description: 'Directs club operations, creates subteams, events & risks',
    accent: 'hover:border-amber-500/50 hover:bg-amber-500/5',
    email: 'clubhead@demo.local',
    password: 'demo123',
  },
  {
    key: 'subteam_lead',
    title: 'SubTeam Lead Role',
    badge: 'AI/ML Team Lead',
    badgeColor: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
    icon: Briefcase,
    description: 'Manages AI/ML volunteers, creates tasks & solves blockers',
    accent: 'hover:border-emerald-500/50 hover:bg-emerald-500/5',
    email: 'teamlead@demo.local',
    password: 'demo123',
  },
  {
    key: 'volunteer',
    title: 'Volunteer Role',
    badge: 'Active Volunteer',
    badgeColor: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
    icon: Users,
    description: 'Executes assigned tasks, tracks workload & personal profile',
    accent: 'hover:border-indigo-500/50 hover:bg-indigo-500/5',
    email: 'volunteer@demo.local',
    password: 'demo123',
  },
];

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSelectRole = (persona: DemoPersona) => {
    setSelectedRole(persona.key);
    setEmail(persona.email);
    setPassword(persona.password);
    setError('');
    setInfoMessage(`Loaded credentials for ${persona.badge} (${persona.email}). Review and click "Sign In" below to authenticate.`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('username', email.trim());
      formData.append('password', password);

      const response = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      const token = response.data.access_token;
      login(token);

      // Navigate based on authenticated user profile
      try {
        const meRes = await api.get('/auth/me', {
          headers: { Authorization: `Bearer ${token}` }
        });
        const role = (meRes.data?.role || '').toUpperCase();
        if (role.includes('ADMIN')) {
          navigate('/admin/organization');
        } else if (role.includes('SUBTEAM_LEAD') || role.includes('TEAM_LEADER')) {
          navigate('/teams');
        } else {
          navigate('/dashboard');
        }
      } catch {
        navigate('/dashboard');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 sm:p-6 relative overflow-hidden selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Background glow meshes */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-violet-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-2xl w-full bg-slate-900/90 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 sm:p-10 shadow-2xl relative z-10 my-8">
        <div className="flex flex-col items-center text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2.5 mb-5 group">
            <div className="w-12 h-12 bg-gradient-to-tr from-indigo-600 to-violet-500 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform">
              <span className="text-white text-base font-black tracking-wider">CO</span>
            </div>
          </Link>
          <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight">Sign in to ClubOps AI</h2>
          <p className="text-slate-400 text-xs sm:text-sm mt-1.5">Intelligent campus event operations & hierarchical RBAC</p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-3.5 rounded-xl mb-6 text-sm flex items-center gap-2">
            <span>{error}</span>
          </div>
        )}

        {/* ROLE QUICK-SELECT SECTION */}
        <div className="mb-8 p-5 sm:p-6 rounded-2xl bg-slate-950/70 border border-slate-800/90">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Select Role to Fill Credentials</h3>
            </div>
            <span className="text-[11px] text-slate-400">Authenticates via /auth/login</span>
          </div>
          <p className="text-xs text-slate-400 mb-4">
            Click any role below to pre-fill verified credentials into the sign-in form. Then click <strong>Sign In</strong> to authenticate.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {DEMO_PERSONAS.map((persona) => {
              const Icon = persona.icon;
              const isSelected = selectedRole === persona.key;

              return (
                <button
                  key={persona.key}
                  type="button"
                  onClick={() => handleSelectRole(persona)}
                  disabled={isLoading}
                  className={`group relative text-left p-3.5 rounded-xl border transition-all flex flex-col justify-between gap-2.5 ${
                    isSelected
                      ? 'border-indigo-500 bg-slate-800/90 ring-2 ring-indigo-500/40 shadow-lg shadow-indigo-500/10'
                      : `border-slate-800/80 bg-slate-900/60 ${persona.accent}`
                  } disabled:opacity-50`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                        isSelected ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300 group-hover:text-white'
                      }`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className={`text-xs sm:text-sm font-bold transition-colors ${
                          isSelected ? 'text-indigo-300' : 'text-white group-hover:text-indigo-300'
                        }`}>
                          {persona.title}
                        </h4>
                        <span className={`inline-block px-1.5 py-0.2 text-[10px] font-semibold rounded border mt-0.5 ${persona.badgeColor}`}>
                          {persona.badge}
                        </span>
                      </div>
                    </div>
                    {isSelected ? (
                      <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 rounded-full shrink-0">
                        <CheckCircle2 className="w-3 h-3" />
                        Selected
                      </span>
                    ) : (
                      <span className="text-[10px] text-slate-500 group-hover:text-indigo-400 transition-colors shrink-0">
                        Use Role
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 leading-tight">
                    {persona.description}
                  </p>
                  <div className="text-[10px] text-slate-500 font-mono truncate">
                    {persona.email}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Divider */}
        <div className="relative flex py-2 items-center mb-6">
          <div className="flex-grow border-t border-slate-800" />
          <span className="flex-shrink mx-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Sign In with Credentials
          </span>
          <div className="flex-grow border-t border-slate-800" />
        </div>

        {infoMessage && (
          <div className="bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 p-3.5 rounded-xl mb-4 text-xs sm:text-sm flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
            <span>{infoMessage}</span>
          </div>
        )}

        {/* Sign-In Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Email Address
            </label>
            <input
              type="email"
              required
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-600"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setSelectedRole(null);
                setInfoMessage(null);
              }}
              placeholder="you@university.edu"
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                Password
              </label>
            </div>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 pr-10 text-white text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-600"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setInfoMessage(null);
                }}
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors p-1"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          
          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl px-4 py-3 transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50 flex items-center justify-center gap-2 mt-6 text-sm"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <LogIn className="w-4 h-4" />}
            {isLoading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-400">
          Don't have an account?{' '}
          <Link to="/register" className="text-indigo-400 hover:text-indigo-300 font-semibold">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
