import React, { useEffect, useState } from 'react';
import {
  User as UserIcon, Mail, Phone, Calendar, Shield,
  CheckCircle, Clock, AlertTriangle, AlertCircle, Edit3, X, Check,
  Activity, Layers, Building, Tag, RefreshCw, Loader2
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { useAuth } from '../context/AuthContext';
import api from '../lib/axios';

interface ProfileData {
  basic_info: {
    id: number;
    full_name: string;
    email: string;
    phone: string;
    username: string;
    avatar_url: string;
    bio: string;
    account_status: string;
    is_active: boolean;
    joined_date: string | null;
  };
  organization: {
    role: string;
    role_display: string;
    club_id: number | null;
    club_name: string | null;
    club_description: string | null;
    subteam_id: number | null;
    subteam_name: string | null;
    subteam_description: string | null;
    club_head_info: { id: number; name: string; email: string } | null;
    subteam_lead_info: { id: number; name: string; email: string } | null;
  };
  skills: string[];
  availability: string;
  workload: {
    active_tasks: number;
    in_progress_tasks: number;
    blocked_tasks: number;
    completed_tasks: number;
    overdue_tasks: number;
    total_tasks: number;
    load_status: 'LOW' | 'MEDIUM' | 'OVERLOADED';
    max_capacity: number;
  };
  tasks: Array<{
    id: number;
    title: string;
    description: string | null;
    status: string;
    priority: string;
    due_date: string | null;
    is_overdue: boolean;
    event_id: number | null;
    event_title: string | null;
    team_id: number | null;
    team_name: string | null;
  }>;
  events: {
    upcoming: Array<{ id: number; title: string; date: string | null; venue: string | null; status: string }>;
    participated: Array<{ id: number; title: string; date: string | null; venue: string | null; status: string }>;
    assigned: Array<{ id: number; title: string; date: string | null; venue: string | null; status: string }>;
  };
  permissions: {
    human_readable: string[];
    granular_keys: string[];
  };
}

export default function Profile() {
  const { refreshAuthz } = useAuth();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit Modal State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editFormData, setEditFormData] = useState({
    full_name: '',
    username: '',
    phone: '',
    avatar_url: '',
    bio: '',
    skills: '',
    availability: '',
  });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Task filter tab state
  const [taskFilter, setTaskFilter] = useState<'ALL' | 'ACTIVE' | 'IN_PROGRESS' | 'BLOCKED' | 'DONE' | 'OVERDUE'>('ALL');
  // Event filter tab state
  const [eventTab, setEventTab] = useState<'UPCOMING' | 'ASSIGNED' | 'PARTICIPATED'>('UPCOMING');

  const fetchProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get('/users/me/profile');
      setProfile(res.data);
      setEditFormData({
        full_name: res.data.basic_info.full_name || '',
        username: res.data.basic_info.username || '',
        phone: res.data.basic_info.phone || '',
        avatar_url: res.data.basic_info.avatar_url || '',
        bio: res.data.basic_info.bio || '',
        skills: (res.data.skills || []).join(', '),
        availability: res.data.availability || '',
      });
    } catch (err: any) {
      console.error('Failed to load profile:', err);
      setError(err.response?.data?.detail || 'Failed to load user profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleOpenEdit = () => {
    if (!profile) return;
    setEditFormData({
      full_name: profile.basic_info.full_name || '',
      username: profile.basic_info.username || '',
      phone: profile.basic_info.phone || '',
      avatar_url: profile.basic_info.avatar_url || '',
      bio: profile.basic_info.bio || '',
      skills: (profile.skills || []).join(', '),
      availability: profile.availability || '',
    });
    setSaveError(null);
    setSaveSuccess(false);
    setIsEditModalOpen(true);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    try {
      // Send only permitted personal information fields
      const payload = {
        full_name: editFormData.full_name.trim(),
        username: editFormData.username.trim() || null,
        phone: editFormData.phone.trim() || null,
        avatar_url: editFormData.avatar_url.trim() || null,
        bio: editFormData.bio.trim() || null,
        skills: editFormData.skills.split(',').map(s => s.trim()).filter(Boolean),
        availability: editFormData.availability.trim() || null,
      };

      const res = await api.patch('/users/me/profile', payload);
      setProfile(res.data);
      setSaveSuccess(true);
      await refreshAuthz();
      setTimeout(() => {
        setIsEditModalOpen(false);
        setSaveSuccess(false);
      }, 1000);
    } catch (err: any) {
      console.error('Failed to update profile:', err);
      setSaveError(err.response?.data?.detail || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  // Status & Priority Badge Helpers
  const getRoleBadgeColor = (role: string) => {
    const r = (role || '').toUpperCase();
    if (r.includes('ADMIN')) return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
    if (r.includes('CLUB_HEAD') || r.includes('CLUB_LEADER')) return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
    if (r.includes('SUBTEAM_LEAD') || r.includes('TEAM_LEADER')) return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
    return 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30';
  };

  const getLoadBadge = (loadStatus: string) => {
    switch (loadStatus) {
      case 'LOW':
        return {
          bg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
          dot: 'bg-emerald-400',
          label: 'Low Workload'
        };
      case 'MEDIUM':
        return {
          bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
          dot: 'bg-amber-400',
          label: 'Balanced Load'
        };
      case 'OVERLOADED':
        return {
          bg: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
          dot: 'bg-rose-400',
          label: 'Overloaded'
        };
      default:
        return {
          bg: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
          dot: 'bg-slate-400',
          label: 'Normal'
        };
    }
  };

  const getTaskStatusBadge = (status: string) => {
    switch (status) {
      case 'TODO':
        return 'bg-slate-800 text-slate-300 border-slate-700';
      case 'IN_PROGRESS':
        return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
      case 'DONE':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'BLOCKED':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      case 'CANCELLED':
        return 'bg-slate-800/60 text-slate-500 border-slate-800';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'URGENT':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      case 'HIGH':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      case 'MEDIUM':
        return 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20';
      case 'LOW':
        return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
      default:
        return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
    }
  };

  // Filter tasks
  const filteredTasks = (profile?.tasks || []).filter(task => {
    if (taskFilter === 'ALL') return true;
    if (taskFilter === 'ACTIVE') return ['TODO', 'IN_PROGRESS', 'BLOCKED'].includes(task.status);
    if (taskFilter === 'IN_PROGRESS') return task.status === 'IN_PROGRESS';
    if (taskFilter === 'BLOCKED') return task.status === 'BLOCKED';
    if (taskFilter === 'DONE') return task.status === 'DONE';
    if (taskFilter === 'OVERDUE') return task.is_overdue;
    return true;
  });

  if (loading) {
    return (
      <DashboardLayout title="User Profile">
        <div className="flex flex-col items-center justify-center py-28 text-center">
          <div className="relative">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 animate-pulse flex items-center justify-center mb-4">
              <Loader2 className="w-7 h-7 text-indigo-400 animate-spin" />
            </div>
          </div>
          <h3 className="text-base font-semibold text-white">Loading Profile...</h3>
          <p className="text-xs text-slate-400 mt-1">Retrieving organization roles, assigned tasks & workload</p>
        </div>
      </DashboardLayout>
    );
  }

  if (error || !profile) {
    return (
      <DashboardLayout title="User Profile">
        <div className="max-w-2xl mx-auto my-12 p-8 bg-slate-900 border border-red-500/30 rounded-3xl text-center">
          <div className="w-12 h-12 rounded-2xl bg-red-500/10 text-red-400 mx-auto flex items-center justify-center mb-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Unable to Load Profile</h3>
          <p className="text-sm text-slate-400 mb-6">{error || 'An unexpected error occurred.'}</p>
          <button
            onClick={fetchProfile}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-all"
          >
            <RefreshCw className="w-4 h-4" /> Try Again
          </button>
        </div>
      </DashboardLayout>
    );
  }

  const loadBadge = getLoadBadge(profile.workload.load_status);

  return (
    <DashboardLayout title="User Profile">
      <div className="max-w-7xl mx-auto space-y-8 pb-12">
        {/* 1. PROFILE HEADER CARD */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-950 via-slate-900 to-slate-950 border border-indigo-500/20 p-6 sm:p-8 shadow-xl">
          <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
          
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
              {/* Profile Avatar / Photo */}
              <div className="relative group shrink-0">
                {profile.basic_info.avatar_url ? (
                  <img
                    src={profile.basic_info.avatar_url}
                    alt={profile.basic_info.full_name}
                    className="w-20 h-20 sm:w-24 sm:h-24 rounded-2xl object-cover border-2 border-indigo-500/40 shadow-xl shadow-indigo-950/50"
                  />
                ) : (
                  <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-2xl bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-700 flex items-center justify-center text-white text-3xl font-black shadow-xl shadow-indigo-950/50 border border-indigo-400/30">
                    {profile.basic_info.full_name ? profile.basic_info.full_name.charAt(0).toUpperCase() : 'U'}
                  </div>
                )}
                <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 border-2 border-slate-900 flex items-center justify-center" title="Active Account">
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                </div>
              </div>

              {/* Title & Metadata */}
              <div>
                <div className="flex flex-wrap items-center gap-2.5 mb-2">
                  <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
                    {profile.basic_info.full_name}
                  </h1>
                  <span className={`px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider rounded-full border ${getRoleBadgeColor(profile.organization.role)}`}>
                    {profile.organization.role_display}
                  </span>
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-medium text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    {profile.basic_info.account_status}
                  </span>
                </div>

                <p className="text-slate-400 text-xs sm:text-sm max-w-2xl leading-relaxed">
                  {profile.basic_info.bio || 'Campus community contributor collaborating on events, tasks, and technical operations.'}
                </p>

                <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-slate-400">
                  <span className="inline-flex items-center gap-1.5 text-slate-300">
                    <Mail className="w-3.5 h-3.5 text-slate-500" />
                    {profile.basic_info.email}
                  </span>
                  {profile.basic_info.phone && (
                    <span className="inline-flex items-center gap-1.5 text-slate-300">
                      <Phone className="w-3.5 h-3.5 text-slate-500" />
                      {profile.basic_info.phone}
                    </span>
                  )}
                  {profile.basic_info.joined_date && (
                    <span className="inline-flex items-center gap-1.5 text-slate-400">
                      <Calendar className="w-3.5 h-3.5 text-slate-500" />
                      Member since {new Date(profile.basic_info.joined_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Action Button */}
            <div className="shrink-0 flex items-center gap-3">
              <button
                type="button"
                onClick={handleOpenEdit}
                className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all active:scale-95"
              >
                <Edit3 className="w-4 h-4" /> Edit Profile
              </button>
            </div>
          </div>
        </div>

        {/* 2. THREE CORE COLUMNS: Basic Info + Organization + Skills/Availability */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Card A: Basic Information */}
          <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2.5 pb-4 mb-4 border-b border-slate-800/80">
                <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <UserIcon className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Basic Information</h3>
              </div>

              <dl className="space-y-3.5 text-xs">
                <div>
                  <dt className="text-slate-500 font-medium">Full Name</dt>
                  <dd className="text-white font-semibold mt-0.5">{profile.basic_info.full_name}</dd>
                </div>
                <div>
                  <dt className="text-slate-500 font-medium">Email Address</dt>
                  <dd className="text-slate-200 mt-0.5">{profile.basic_info.email}</dd>
                </div>
                <div>
                  <dt className="text-slate-500 font-medium">Username</dt>
                  <dd className="text-slate-300 mt-0.5 font-mono">@{profile.basic_info.username}</dd>
                </div>
                <div>
                  <dt className="text-slate-500 font-medium">Phone / Contact</dt>
                  <dd className="text-slate-300 mt-0.5">{profile.basic_info.phone || 'None provided'}</dd>
                </div>
                <div>
                  <dt className="text-slate-500 font-medium">Account Status</dt>
                  <dd className="mt-0.5 inline-flex items-center gap-1.5 text-emerald-400 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    {profile.basic_info.account_status}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500 font-medium">Joined Date</dt>
                  <dd className="text-slate-300 mt-0.5">
                    {profile.basic_info.joined_date ? new Date(profile.basic_info.joined_date).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) : 'Recently'}
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          {/* Card B: Organization Information */}
          <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2.5 pb-4 mb-4 border-b border-slate-800/80">
                <div className="w-8 h-8 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
                  <Building className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Organization</h3>
              </div>

              <dl className="space-y-3.5 text-xs">
                <div>
                  <dt className="text-slate-500 font-medium">Assigned Role</dt>
                  <dd className="mt-1">
                    <span className={`px-2 py-0.5 text-xs font-bold rounded-md border ${getRoleBadgeColor(profile.organization.role)}`}>
                      {profile.organization.role_display}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500 font-medium">Club Assignment</dt>
                  <dd className="text-white font-semibold mt-0.5">
                    {profile.organization.club_name || 'Global / Unassigned'}
                  </dd>
                  {profile.organization.club_description && (
                    <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">{profile.organization.club_description}</p>
                  )}
                </div>
                <div>
                  <dt className="text-slate-500 font-medium">SubTeam Assignment</dt>
                  <dd className="text-white font-semibold mt-0.5">
                    {profile.organization.subteam_name ? profile.organization.subteam_name : 'None (Direct Club Member)'}
                  </dd>
                  {profile.organization.subteam_description && (
                    <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">{profile.organization.subteam_description}</p>
                  )}
                </div>

                {/* Team Lead / Club Head Details */}
                {profile.organization.club_head_info && (
                  <div className="pt-2 border-t border-slate-800/60">
                    <dt className="text-slate-500 font-medium">Club Head Contact</dt>
                    <dd className="text-slate-200 mt-0.5 flex items-center justify-between">
                      <span className="font-semibold text-white">{profile.organization.club_head_info.name}</span>
                      <span className="text-[11px] text-indigo-400">{profile.organization.club_head_info.email}</span>
                    </dd>
                  </div>
                )}
                {profile.organization.subteam_lead_info && (
                  <div className="pt-2 border-t border-slate-800/60">
                    <dt className="text-slate-500 font-medium">SubTeam Lead Contact</dt>
                    <dd className="text-slate-200 mt-0.5 flex items-center justify-between">
                      <span className="font-semibold text-white">{profile.organization.subteam_lead_info.name}</span>
                      <span className="text-[11px] text-emerald-400">{profile.organization.subteam_lead_info.email}</span>
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>

          {/* Card C: Skills & Availability */}
          <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2.5 pb-4 mb-4 border-b border-slate-800/80">
                <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                  <Activity className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Skills & Availability</h3>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="text-xs font-semibold text-slate-400 mb-2.5 flex items-center gap-1.5">
                    <Tag className="w-3.5 h-3.5 text-amber-400" /> Skill Badges
                  </h4>
                  {profile.skills && profile.skills.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {profile.skills.map((skill, i) => (
                        <span
                          key={i}
                          className="px-2.5 py-1 bg-slate-800/90 border border-slate-700 text-indigo-200 text-xs font-semibold rounded-lg shadow-sm"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500 italic">No skills listed yet. Click "Edit Profile" to add skill tags.</p>
                  )}
                </div>

                <div className="pt-3 border-t border-slate-800/60">
                  <h4 className="text-xs font-semibold text-slate-400 mb-2 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-emerald-400" /> Availability Window
                  </h4>
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-xs font-medium text-slate-200">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    {profile.availability || 'Weekdays & Weekends'}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-2">
                    Target weekly capacity: <strong className="text-slate-300">{profile.workload.max_capacity} hrs/week</strong>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 3. WORKLOAD SECTION */}
        <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800/80">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Layers className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Workload & Task Execution</h3>
                <p className="text-xs text-slate-400">Live task execution load and performance tracking</p>
              </div>
            </div>

            {/* Load Indicator Pill */}
            <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-bold uppercase tracking-wider ${loadBadge.bg}`}>
              <span className={`w-2 h-2 rounded-full ${loadBadge.dot} animate-ping`} />
              <span>Status: {profile.workload.load_status}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Tasks</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-extrabold text-white">{profile.workload.active_tasks}</span>
                <span className="text-xs text-indigo-400 font-medium">In Queue</span>
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Completed</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-extrabold text-emerald-400">{profile.workload.completed_tasks}</span>
                <span className="text-xs text-emerald-500/80 font-medium">Finished</span>
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Blocked</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-extrabold text-rose-400">{profile.workload.blocked_tasks}</span>
                <span className="text-xs text-rose-500/80 font-medium">Needs Action</span>
              </div>
            </div>

            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Overdue</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className={`text-2xl font-extrabold ${profile.workload.overdue_tasks > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
                  {profile.workload.overdue_tasks}
                </span>
                <span className="text-xs text-amber-500/80 font-medium">Past Deadline</span>
              </div>
            </div>
          </div>
        </div>

        {/* 4. TASKS SECTION WITH FILTER TABS */}
        <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <span>Task Information</span>
                <span className="px-2 py-0.5 text-xs font-semibold bg-slate-800 rounded-full text-slate-300">
                  {profile.tasks.length}
                </span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Tasks authorized for your role and organizational assignment</p>
            </div>

            {/* Filter Tabs */}
            <div className="flex flex-wrap items-center gap-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
              {(['ALL', 'ACTIVE', 'IN_PROGRESS', 'BLOCKED', 'DONE', 'OVERDUE'] as const).map(tab => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setTaskFilter(tab)}
                  className={`px-3 py-1.5 rounded-lg transition-colors ${
                    taskFilter === tab
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {tab === 'IN_PROGRESS' ? 'In Progress' : tab.charAt(0) + tab.slice(1).toLowerCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Task List */}
          {filteredTasks.length === 0 ? (
            <div className="p-10 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800">
              <CheckCircle className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm font-medium text-slate-400">No tasks found matching filter "{taskFilter}"</p>
              <p className="text-xs text-slate-500 mt-1">Check back as new tasks are scheduled and assigned.</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-800/60 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
              {filteredTasks.map(task => (
                <div
                  key={task.id}
                  className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-900/60 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="text-sm font-bold text-white">{task.title}</h4>
                      {task.is_overdue && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-md bg-rose-500/15 text-rose-300 border border-rose-500/30 uppercase">
                          <AlertTriangle className="w-3 h-3" /> Overdue
                        </span>
                      )}
                    </div>
                    {task.description && (
                      <p className="text-xs text-slate-400 line-clamp-1">{task.description}</p>
                    )}
                    <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                      {task.event_title && (
                        <span>Event: <strong className="text-slate-300 font-medium">{task.event_title}</strong></span>
                      )}
                      {task.team_name && (
                        <span>Team: <strong className="text-slate-300 font-medium">{task.team_name}</strong></span>
                      )}
                      {task.due_date && (
                        <span>Due: <strong className="text-slate-300 font-medium">{new Date(task.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</strong></span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 self-start sm:self-center">
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-md border ${getPriorityBadge(task.priority)}`}>
                      {task.priority}
                    </span>
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-md border ${getTaskStatusBadge(task.status)}`}>
                      {task.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 5. EVENT INFORMATION & PERMISSIONS SPLIT */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Events Card (7 Cols) */}
          <div className="lg:col-span-7 bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Event Information</h3>
                <p className="text-xs text-slate-400">Club events and operations you participate in</p>
              </div>

              {/* Event Sub-tabs */}
              <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
                <button
                  onClick={() => setEventTab('UPCOMING')}
                  className={`px-3 py-1 rounded-lg ${eventTab === 'UPCOMING' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
                >
                  Upcoming
                </button>
                <button
                  onClick={() => setEventTab('ASSIGNED')}
                  className={`px-3 py-1 rounded-lg ${eventTab === 'ASSIGNED' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
                >
                  Assigned
                </button>
                <button
                  onClick={() => setEventTab('PARTICIPATED')}
                  className={`px-3 py-1 rounded-lg ${eventTab === 'PARTICIPATED' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
                >
                  Past
                </button>
              </div>
            </div>

            {/* Event list */}
            {(() => {
              const currentEvents =
                eventTab === 'UPCOMING'
                  ? profile.events.upcoming
                  : eventTab === 'ASSIGNED'
                  ? profile.events.assigned
                  : profile.events.participated;

              if (currentEvents.length === 0) {
                return (
                  <div className="p-8 text-center rounded-xl bg-slate-950/40 border border-dashed border-slate-800 text-slate-400 text-xs">
                    No {eventTab.toLowerCase()} events recorded for your account.
                  </div>
                );
              }

              return (
                <div className="space-y-2.5">
                  {currentEvents.map(ev => (
                    <div
                      key={ev.id}
                      className="p-4 rounded-xl bg-slate-950/50 border border-slate-800 flex items-center justify-between gap-3 hover:border-slate-700 transition-all"
                    >
                      <div>
                        <h4 className="text-xs sm:text-sm font-bold text-white">{ev.title}</h4>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          {ev.venue ? `${ev.venue} · ` : ''}
                          {ev.date ? new Date(ev.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'TBD'}
                        </p>
                      </div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 uppercase tracking-wider shrink-0">
                        {ev.status}
                      </span>
                    </div>
                  ))}
                </div>
              );
            })()}
          </div>

          {/* Permissions & Capabilities Summary (5 Cols) */}
          <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-sm space-y-4 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2.5 pb-4 border-b border-slate-800/80">
                <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <Shield className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">Role Permissions</h3>
                  <p className="text-xs text-slate-400">What you can perform in ClubOps AI</p>
                </div>
              </div>

              <div className="space-y-2.5 mt-4">
                {profile.permissions.human_readable.map((permText, i) => (
                  <div key={i} className="flex items-start gap-2.5 text-xs text-slate-200">
                    <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{permText}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-[11px] text-slate-400 mt-4">
              <span className="font-semibold text-slate-300">Security Guarantee:</span> Internal credentials, secrets, and auth tokens are sanitized and safely managed by RBAC session middleware.
            </div>
          </div>
        </div>
      </div>

      {/* 6. PROFILE EDIT MODAL */}
      {isEditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-lg font-bold text-white">Edit Personal Profile</h3>
                <p className="text-xs text-slate-400 mt-0.5">Update personal details, bio, skills, and availability</p>
              </div>
              <button
                type="button"
                onClick={() => setIsEditModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {saveError && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{saveError}</span>
              </div>
            )}

            {saveSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
                <Check className="w-4 h-4 shrink-0" />
                <span>Profile updated successfully!</span>
              </div>
            )}

            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                  value={editFormData.full_name}
                  onChange={(e) => setEditFormData({ ...editFormData, full_name: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Username
                  </label>
                  <input
                    type="text"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 placeholder:text-slate-600 font-mono"
                    value={editFormData.username}
                    onChange={(e) => setEditFormData({ ...editFormData, username: e.target.value })}
                    placeholder="username"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                    Phone / Contact
                  </label>
                  <input
                    type="text"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 placeholder:text-slate-600"
                    value={editFormData.phone}
                    onChange={(e) => setEditFormData({ ...editFormData, phone: e.target.value })}
                    placeholder="+1 555-0199"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Profile Photo URL
                </label>
                <input
                  type="url"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 placeholder:text-slate-600"
                  value={editFormData.avatar_url}
                  onChange={(e) => setEditFormData({ ...editFormData, avatar_url: e.target.value })}
                  placeholder="https://images.unsplash.com/..."
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Bio / Summary
                </label>
                <textarea
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-white text-sm focus:outline-none focus:border-indigo-500 placeholder:text-slate-600"
                  value={editFormData.bio}
                  onChange={(e) => setEditFormData({ ...editFormData, bio: e.target.value })}
                  placeholder="Tell us about your campus role and background..."
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Skills (comma-separated)
                </label>
                <input
                  type="text"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 placeholder:text-slate-600"
                  value={editFormData.skills}
                  onChange={(e) => setEditFormData({ ...editFormData, skills: e.target.value })}
                  placeholder="Python, AI/ML, React, Cloud, Git"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Availability Window
                </label>
                <select
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
                  value={editFormData.availability}
                  onChange={(e) => setEditFormData({ ...editFormData, availability: e.target.value })}
                >
                  <option value="WEEKDAYS,WEEKENDS">Weekdays & Weekends</option>
                  <option value="WEEKDAYS">Weekdays Only</option>
                  <option value="WEEKENDS">Weekends Only</option>
                  <option value="FLEXIBLE">Flexible / On-Call</option>
                </select>
              </div>

              {/* Locked System Attributes Notice */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-[11px] text-slate-400">
                <span className="text-slate-300 font-semibold">Protected Fields:</span> Role, Club, and SubTeam assignments are controlled by the organizational authorization system and cannot be modified here.
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  disabled={saving}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-xs font-semibold shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  {saving ? 'Saving Changes...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
