import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Edit, Trash2, Calendar, MapPin, DollarSign,
  Users, Clock, CheckCircle, AlertTriangle, BarChart3
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import api from '../lib/axios';

interface EventDetail {
  id: number;
  title: string;
  description: string;
  date: string;
  venue: string;
  budget: number;
  budget_spent: number;
  expected_attendance: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export default function EventDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState<EventDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api.get(`/events/${id}`)
      .then(res => setEvent(res.data))
      .catch(() => navigate('/events'))
      .finally(() => setLoading(false));
  }, [id, navigate]);

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this event?')) return;
    setDeleting(true);
    try {
      await api.delete(`/events/${id}`);
      navigate('/events');
    } catch {
      setDeleting(false);
    }
  };

  if (loading || !event) {
    return (
      <DashboardLayout title="Event Details">
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500"></div>
        </div>
      </DashboardLayout>
    );
  }

  const eventDate = new Date(event.date);
  const daysRemaining = Math.ceil((eventDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  const isPast = daysRemaining < 0;
  const budgetPercentage = event.budget > 0 ? Math.min((event.budget_spent / event.budget) * 100, 100) : 0;

  // Placeholder metrics (tasks/volunteers/risks will be from future phases)
  const totalTasks = 0;
  const completedTasks = 0;
  const completionPercentage = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
  const volunteerCount = 0;
  const activeRisks = 0;

  const statusColor = (status: string) => {
    switch (status) {
      case 'PUBLISHED': return 'bg-green-500/10 text-green-400 border-green-500/20';
      case 'CANCELLED': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'COMPLETED': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default: return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    }
  };

  return (
    <DashboardLayout title={event.title}>
      <div className="max-w-5xl mx-auto space-y-6 sm:space-y-8">
        {/* Top bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4">
          <button
            onClick={() => navigate('/events')}
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm font-medium transition-colors py-1 self-start"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Events
          </button>
          <div className="flex items-center gap-2.5 self-end sm:self-auto">
            <Link
              to={`/events/${id}/edit`}
              className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-colors shadow-sm"
            >
              <Edit className="w-4 h-4 text-slate-300" /> Edit
            </Link>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="inline-flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" /> {deleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </div>

        {/* Event Info Header */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8">
          <div className="flex flex-wrap items-center gap-2.5 mb-4">
            <span className={`text-xs px-3 py-1 rounded-full font-semibold border ${statusColor(event.status)}`}>
              {event.status}
            </span>
            {!isPast && event.status !== 'COMPLETED' && event.status !== 'CANCELLED' && (
              <span className="text-xs text-slate-400 bg-slate-800/80 px-2.5 py-1 rounded-md flex items-center gap-1.5 font-medium">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                {daysRemaining === 0 ? 'Today' : daysRemaining === 1 ? '1 day left' : `${daysRemaining} days left`}
              </span>
            )}
          </div>
          <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white mb-3 tracking-tight">{event.title}</h1>
          {event.description && (
            <p className="text-slate-300 text-sm sm:text-base mb-6 max-w-3xl leading-relaxed">{event.description}</p>
          )}
          <div className="flex flex-wrap items-center gap-4 sm:gap-6 text-xs sm:text-sm text-slate-400 pt-1 border-t border-slate-800/60">
            <span className="flex items-center gap-2 pt-2">
              <Calendar className="w-4 h-4 text-indigo-400 shrink-0" />
              <span>
                {eventDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
                {' at '}
                {eventDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
              </span>
            </span>
            {event.venue && (
              <span className="flex items-center gap-2 pt-2">
                <MapPin className="w-4 h-4 text-indigo-400 shrink-0" />
                <span>{event.venue}</span>
              </span>
            )}
          </div>
        </div>

        {/* Dashboard Metrics Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4 sm:p-5 rounded-2xl shadow-sm">
            <div className="flex items-center gap-2 mb-2.5">
              <Calendar className="w-4 h-4 text-indigo-400" />
              <span className="text-xs text-slate-400 font-medium">Event Date</span>
            </div>
            <p className="text-lg font-bold text-white">
              {eventDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </p>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 sm:p-5 rounded-2xl shadow-sm">
            <div className="flex items-center gap-2 mb-2.5">
              <Clock className="w-4 h-4 text-amber-400" />
              <span className="text-xs text-slate-400 font-medium">Days Remaining</span>
            </div>
            <p className={`text-lg font-bold ${isPast ? 'text-red-400' : 'text-white'}`}>
              {isPast ? 'Past' : daysRemaining}
            </p>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 sm:p-5 rounded-2xl shadow-sm">
            <div className="flex items-center gap-2 mb-2.5">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-xs text-slate-400 font-medium">Tasks Progress</span>
            </div>
            <p className="text-lg font-bold text-white">{completedTasks}/{totalTasks}</p>
            <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2.5">
              <div
                className="bg-green-500 h-1.5 rounded-full transition-all"
                style={{ width: `${completionPercentage}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 sm:p-5 rounded-2xl shadow-sm">
            <div className="flex items-center gap-2 mb-2.5">
              <BarChart3 className="w-4 h-4 text-purple-400" />
              <span className="text-xs text-slate-400 font-medium">Completion</span>
            </div>
            <p className="text-lg font-bold text-white">{completionPercentage}%</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4 sm:p-5 rounded-2xl shadow-sm">
            <div className="flex items-center gap-2 mb-2.5">
              <Users className="w-4 h-4 text-cyan-400" />
              <span className="text-xs text-slate-400 font-medium">Volunteers</span>
            </div>
            <p className="text-lg font-bold text-white">{volunteerCount}</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 sm:p-5 rounded-2xl shadow-sm">
            <div className="flex items-center gap-2 mb-2.5">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-xs text-slate-400 font-medium">Active Risks</span>
            </div>
            <p className="text-lg font-bold text-white">{activeRisks}</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 sm:p-5 rounded-2xl shadow-sm">
            <div className="flex items-center gap-2 mb-2.5">
              <DollarSign className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-slate-400 font-medium">Budget Allocated</span>
            </div>
            <p className="text-lg font-bold text-white">₹{event.budget.toLocaleString()}</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-4 sm:p-5 rounded-2xl shadow-sm">
            <div className="flex items-center gap-2 mb-2.5">
              <DollarSign className="w-4 h-4 text-orange-400" />
              <span className="text-xs text-slate-400 font-medium">Budget Spent</span>
            </div>
            <p className="text-lg font-bold text-white">₹{event.budget_spent.toLocaleString()}</p>
            <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2.5">
              <div
                className={`h-1.5 rounded-full transition-all ${budgetPercentage > 90 ? 'bg-red-500' : budgetPercentage > 70 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                style={{ width: `${budgetPercentage}%` }}
              ></div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
