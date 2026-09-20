import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Edit, Trash2, Mail, Clock, Activity, CheckCircle, XCircle } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import api from '../lib/axios';

interface UserInfo {
  id: number;
  full_name: string;
  email: string;
}

interface Volunteer {
  id: number;
  user_id: number;
  skills: string;
  availability: string;
  status: string;
  active_task_count: number;
  load_indicator: string;
  user: UserInfo;
}

interface AssignedTask {
  id: number;
  title: string;
  status: string;
  event_id: number;
}

export default function VolunteerProfile() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [volunteer, setVolunteer] = useState<Volunteer | null>(null);
  const [tasks, setTasks] = useState<AssignedTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get(`/volunteers/${id}`),
      api.get(`/volunteers/${id}/tasks`)
    ])
      .then(([volRes, tasksRes]) => {
        setVolunteer(volRes.data);
        setTasks(tasksRes.data);
      })
      .catch(() => navigate('/volunteers'))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this volunteer profile?')) return;
    setDeleting(true);
    try {
      await api.delete(`/volunteers/${id}`);
      navigate('/volunteers');
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to delete volunteer');
      setDeleting(false);
    }
  };

  if (loading || !volunteer) {
    return (
      <DashboardLayout title="Volunteer Profile">
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500"></div>
        </div>
      </DashboardLayout>
    );
  }

  const getLoadBadge = (load: string) => {
    switch (load) {
      case 'LOW': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'MEDIUM': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'OVERLOADED': return 'bg-red-500/10 text-red-400 border-red-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  const getTaskBadge = (status: string) => {
    switch (status) {
      case 'TODO': return 'bg-slate-500/10 text-slate-400';
      case 'IN_PROGRESS': return 'bg-blue-500/10 text-blue-400';
      case 'DONE': return 'bg-emerald-500/10 text-emerald-400';
      case 'BLOCKED': return 'bg-red-500/10 text-red-400';
      default: return 'bg-slate-500/10 text-slate-400';
    }
  };

  return (
    <DashboardLayout title="Volunteer Profile">
      <div className="max-w-4xl mx-auto space-y-6 sm:space-y-8">
        {/* Top bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4">
          <button
            onClick={() => navigate('/volunteers')}
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm font-medium transition-colors py-1 self-start"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Directory
          </button>
          <div className="flex items-center gap-2.5 self-end sm:self-auto">
            <Link
              to={`/volunteers/${id}/edit`}
              className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-colors shadow-sm"
            >
              <Edit className="w-4 h-4 text-slate-300" /> Edit
            </Link>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="inline-flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" /> {deleting ? 'Removing...' : 'Remove'}
            </button>
          </div>
        </div>

        {/* Profile Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-sm">
          <div className="flex flex-col sm:flex-row items-start justify-between gap-4 mb-6">
            <div className="flex items-start gap-4 sm:gap-6">
              <div className="w-16 h-16 sm:w-20 sm:h-20 bg-slate-800 rounded-2xl flex items-center justify-center text-slate-200 text-2xl sm:text-3xl font-bold shrink-0 shadow-inner border border-slate-700/50">
                {volunteer.user?.full_name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              
              <div className="pt-0.5 min-w-0">
                <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
                  <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight">{volunteer.user?.full_name}</h1>
                  {volunteer.status === 'ACTIVE' ? (
                    <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 text-slate-500 shrink-0" />
                  )}
                </div>
                
                <div className="flex items-center gap-2 text-xs sm:text-sm text-slate-400">
                  <Mail className="w-3.5 h-3.5 text-slate-500" />
                  <a href={`mailto:${volunteer.user?.email}`} className="hover:text-indigo-400 transition-colors truncate">
                    {volunteer.user?.email}
                  </a>
                </div>
              </div>
            </div>

            <span className={`self-start px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full border ${getLoadBadge(volunteer.load_indicator)}`}>
              Load: {volunteer.load_indicator}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-6 border-t border-slate-800/60">
            <div>
              <h3 className="text-xs sm:text-sm font-semibold text-slate-300 mb-2.5 flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-400" /> Skills
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {volunteer.skills ? volunteer.skills.split(',').map((skill, i) => (
                  <span key={i} className="px-3 py-1 bg-slate-800/80 border border-slate-700/60 text-slate-200 text-xs font-medium rounded-full">
                    {skill.trim()}
                  </span>
                )) : (
                  <span className="text-xs text-slate-500 italic">No skills provided</span>
                )}
              </div>
            </div>

            <div>
              <h3 className="text-xs sm:text-sm font-semibold text-slate-300 mb-2.5 flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-400" /> Availability
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {volunteer.availability ? volunteer.availability.split(',').map((avail, i) => (
                  <span key={i} className="px-3 py-1 bg-slate-800/50 border border-slate-700/60 text-slate-300 text-xs rounded-full">
                    {avail.trim()}
                  </span>
                )) : (
                  <span className="text-xs text-slate-500 italic">No availability provided</span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Assigned Tasks */}
        <div className="space-y-3 sm:space-y-4">
          <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2.5">
            <span>Assigned Tasks</span>
            <span className="bg-indigo-500/20 text-indigo-300 text-xs py-0.5 px-2.5 rounded-full font-semibold">
              {volunteer.active_task_count} Active
            </span>
          </h2>
          
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
            {tasks.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-400">
                No tasks currently assigned to this volunteer.
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {tasks.map(task => (
                  <div key={task.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-4 hover:bg-slate-850 transition-colors">
                    <div>
                      <h4 className="text-sm font-semibold text-white mb-0.5">{task.title}</h4>
                      <p className="text-xs text-slate-500">
                        Event ID: {task.event_id}
                      </p>
                    </div>
                    <span className={`self-start sm:self-center text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border ${getTaskBadge(task.status)}`}>
                      {task.status.replace('_', ' ')}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
