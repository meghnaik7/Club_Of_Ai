import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Edit, Trash2, Calendar, MapPin, DollarSign,
  Clock, CheckCircle, Plus, Megaphone, Sparkles, CheckSquare
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EventsService from '../services/events.service';
import type { Event } from '../services/events.service';
import TasksService from '../services/tasks.service';
import type { Task } from '../services/tasks.service';
import AnnouncementsService from '../services/announcements.service';
import type { Announcement } from '../services/announcements.service';

export default function EventDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState<Event | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    const eventId = Number(id);

    Promise.allSettled([
      EventsService.get(eventId),
      TasksService.list({ event_id: eventId }),
      AnnouncementsService.list(eventId),
    ]).then(([evRes, tasksRes, annRes]) => {
      if (evRes.status === 'fulfilled') {
        setEvent(evRes.value);
      } else {
        navigate('/events');
      }
      if (tasksRes.status === 'fulfilled') {
        setTasks(tasksRes.value);
      }
      if (annRes.status === 'fulfilled') {
        setAnnouncements(annRes.value);
      }
    }).finally(() => setLoading(false));
  }, [id, navigate]);

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this event? This will also remove associated tasks.')) return;
    setDeleting(true);
    try {
      await EventsService.delete(Number(id));
      navigate('/events');
    } catch {
      setDeleting(false);
    }
  };

  const handleTaskStatusToggle = async (task: Task) => {
    const nextStatus = task.status === 'DONE' ? 'TODO' : 'DONE';
    try {
      const updated = await TasksService.update(task.id, { status: nextStatus });
      setTasks(prev => prev.map(t => t.id === task.id ? updated : t));
    } catch (err) {
      console.error('Failed to update task status', err);
    }
  };

  if (loading || !event) {
    return (
      <DashboardLayout title="Event Details">
        <div className="flex justify-center py-24">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
        </div>
      </DashboardLayout>
    );
  }

  const eventDate = new Date(event.date);
  const daysRemaining = Math.ceil((eventDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
  const isPast = daysRemaining < 0;
  const budget = Number(event.budget || 0);
  const budgetSpent = Number(event.budget_spent || 0);
  const budgetPercentage = budget > 0 ? Math.min((budgetSpent / budget) * 100, 100) : 0;

  const totalTasks = tasks.length;
  const completedTasks = tasks.filter(t => t.status === 'DONE').length;
  const completionPercentage = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  const statusColor = (status: string) => {
    switch (status) {
      case 'PUBLISHED': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'CANCELLED': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'COMPLETED': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default: return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    }
  };

  return (
    <DashboardLayout title={event.title} activeEventId={event.id}>
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Navigation Bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <button
            onClick={() => navigate('/events')}
            className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors group"
          >
            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" /> Back to Events
          </button>
          <div className="flex items-center gap-2.5 flex-wrap">
            <Link
              to={`/events/${id}/edit`}
              className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white px-4 py-2 rounded-xl text-xs sm:text-sm font-medium border border-slate-700 transition-colors"
            >
              <Edit className="w-3.5 h-3.5" /> Edit Event
            </Link>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="inline-flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" /> {deleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </div>

        {/* Hero Event Banner */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 relative overflow-hidden shadow-xl">
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <span className={`text-xs px-3 py-1 rounded-full font-bold border uppercase tracking-wider ${statusColor(event.status)}`}>
              {event.status}
            </span>
            {!isPast && event.status !== 'COMPLETED' && event.status !== 'CANCELLED' && (
              <span className="text-xs text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 rounded-full font-medium flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-indigo-400" />
                {daysRemaining === 0 ? 'Happening today!' : daysRemaining === 1 ? 'Tomorrow' : `${daysRemaining} days remaining`}
              </span>
            )}
            {event.expected_attendance ? (
              <span className="text-xs text-slate-400 bg-slate-800 px-3 py-1 rounded-full">
                Expected: {event.expected_attendance} attendees
              </span>
            ) : null}
          </div>

          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight mb-3">{event.title}</h1>
          {event.description && (
            <p className="text-slate-300 text-sm sm:text-base mb-6 max-w-3xl leading-relaxed">
              {event.description}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-6 text-xs sm:text-sm text-slate-400 pt-2 border-t border-slate-800/80">
            <span className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-400" />
              {eventDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
              {' at '}
              {eventDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
            </span>
            {event.venue && (
              <span className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-violet-400" />
                {event.venue}
              </span>
            )}
          </div>
        </div>

        {/* 4 KPI Metrics Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <div className="flex items-center gap-2 mb-2 text-slate-400 text-xs font-semibold uppercase">
              <Clock className="w-4 h-4 text-amber-400" /> Timeline
            </div>
            <p className={`text-2xl font-black ${isPast ? 'text-slate-400' : 'text-white'}`}>
              {isPast ? 'Past Event' : `${daysRemaining} Days`}
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              {eventDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </p>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <div className="flex items-center gap-2 mb-2 text-slate-400 text-xs font-semibold uppercase">
              <CheckCircle className="w-4 h-4 text-emerald-400" /> Tasks Completion
            </div>
            <p className="text-2xl font-black text-white">{completedTasks}/{totalTasks}</p>
            <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${completionPercentage}%` }}
              />
            </div>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <div className="flex items-center gap-2 mb-2 text-slate-400 text-xs font-semibold uppercase">
              <DollarSign className="w-4 h-4 text-indigo-400" /> Budget Spent
            </div>
            <p className="text-2xl font-black text-white">
              ₹{budgetSpent.toLocaleString()}
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              Allocated: ₹{budget.toLocaleString()} ({Math.round(budgetPercentage)}%)
            </p>
          </div>

          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <div className="flex items-center gap-2 mb-2 text-slate-400 text-xs font-semibold uppercase">
              <Megaphone className="w-4 h-4 text-violet-400" /> Broadcasts
            </div>
            <p className="text-2xl font-black text-white">{announcements.length}</p>
            <p className="text-[11px] text-slate-500 mt-1">
              {announcements.filter(a => a.status === 'PUBLISHED').length} live campaigns
            </p>
          </div>
        </div>

        {/* Two Columns: Event Tasks & Event Announcements */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Event Tasks (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                  <CheckSquare className="w-5 h-5 text-indigo-400" />
                  Event Tasks ({tasks.length})
                </h3>
                <p className="text-xs text-slate-400">Work breakdown & operational checklists</p>
              </div>
              <Link
                to="/tasks"
                className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" /> Add Task
              </Link>
            </div>

            {tasks.length === 0 ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center">
                <CheckSquare className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-sm font-semibold text-white">No tasks created yet</p>
                <p className="text-xs text-slate-400 max-w-xs mx-auto mt-1 mb-4">
                  Break down this event into logistical and execution tasks, or ask the AI Assistant.
                </p>
                <Link
                  to="/tasks"
                  className="inline-flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-xs font-medium border border-slate-700"
                >
                  <Plus className="w-3.5 h-3.5" /> Create Task
                </Link>
              </div>
            ) : (
              <div className="space-y-2.5">
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    className="p-4 bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-xl flex items-start gap-3 transition-colors group"
                  >
                    <button
                      onClick={() => handleTaskStatusToggle(task)}
                      className={`w-5 h-5 rounded-full border-2 mt-0.5 flex items-center justify-center shrink-0 transition-all ${
                        task.status === 'DONE'
                          ? 'bg-emerald-500 border-emerald-500'
                          : 'border-slate-600 hover:border-emerald-500'
                      }`}
                    >
                      {task.status === 'DONE' && <CheckCircle className="w-3.5 h-3.5 text-white" />}
                    </button>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-sm font-medium ${task.status === 'DONE' ? 'line-through text-slate-500' : 'text-white'}`}>
                          {task.title}
                        </span>
                        <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${
                          task.status === 'DONE' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                          task.status === 'IN_PROGRESS' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                          task.status === 'BLOCKED' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                          'bg-slate-500/10 text-slate-400 border-slate-500/20'
                        }`}>
                          {task.status.replace('_', ' ')}
                        </span>
                        {task.priority && (
                          <span className="text-[10px] text-slate-500">
                            · {task.priority.toLowerCase()}
                          </span>
                        )}
                      </div>
                      {task.description && (
                        <p className="text-xs text-slate-400 mt-1 line-clamp-1">{task.description}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: Event Announcements (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                  <Megaphone className="w-5 h-5 text-violet-400" />
                  Announcements ({announcements.length})
                </h3>
                <p className="text-xs text-slate-400">Campaigns for this event</p>
              </div>
              <Link
                to="/announcements/new"
                className="inline-flex items-center gap-1.5 bg-violet-600 hover:bg-violet-500 text-white px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" /> Broadcast
              </Link>
            </div>

            {announcements.length === 0 ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-8 text-center">
                <Megaphone className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-sm font-semibold text-white">No announcements yet</p>
                <p className="text-xs text-slate-400 max-w-xs mx-auto mt-1 mb-4">
                  Use our AI agent to generate tailored copy for WhatsApp, Instagram, and Email.
                </p>
                <Link
                  to="/announcements/new"
                  className="inline-flex items-center gap-1.5 bg-violet-600/20 hover:bg-violet-600/30 text-violet-300 px-4 py-2 rounded-xl text-xs font-medium border border-violet-500/30"
                >
                  <Sparkles className="w-3.5 h-3.5" /> AI Broadcast
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {announcements.map((ann) => (
                  <Link
                    key={ann.id}
                    to={`/announcements/${ann.id}/edit`}
                    className="block p-4 bg-slate-900/80 border border-slate-800 hover:border-slate-700 rounded-2xl transition-colors group"
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <h4 className="text-sm font-bold text-white group-hover:text-violet-300 transition-colors truncate">
                        {ann.title}
                      </h4>
                      <span className="text-[9px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 uppercase font-semibold">
                        {ann.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 line-clamp-2 leading-relaxed">
                      {ann.content}
                    </p>
                    {ann.target_audience && (
                      <p className="text-[10px] text-slate-500 mt-2">
                        Audience: {ann.target_audience}
                      </p>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
