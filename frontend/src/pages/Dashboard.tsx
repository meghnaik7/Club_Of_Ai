import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Calendar, Plus, CheckSquare, Users, Megaphone,
  ArrowRight, Clock, Sparkles, CheckCircle, AlertCircle
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import { useAuth } from '../context/AuthContext';
import EventsService from '../services/events.service';
import type { Event } from '../services/events.service';
import TasksService from '../services/tasks.service';
import type { Task } from '../services/tasks.service';
import VolunteersService from '../services/volunteers.service';
import type { Volunteer } from '../services/volunteers.service';
import AnnouncementsService from '../services/announcements.service';
import type { Announcement } from '../services/announcements.service';

export default function Dashboard() {
  const { user } = useAuth();
  const [events, setEvents] = useState<Event[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      EventsService.list(),
      TasksService.list(),
      VolunteersService.list(),
      AnnouncementsService.list()
    ]).then(([eventsRes, tasksRes, volRes, annRes]) => {
      if (eventsRes.status === 'fulfilled') setEvents(eventsRes.value);
      if (tasksRes.status === 'fulfilled') setTasks(tasksRes.value);
      if (volRes.status === 'fulfilled') setVolunteers(volRes.value);
      if (annRes.status === 'fulfilled') setAnnouncements(annRes.value);
    }).finally(() => setLoading(false));
  }, []);

  const upcomingEvents = events.filter(e => new Date(e.date) >= new Date() && e.status !== 'CANCELLED');
  const completedTasks = tasks.filter(t => t.status === 'DONE').length;
  const taskCompletionRate = tasks.length > 0 ? Math.round((completedTasks / tasks.length) * 100) : 0;
  const activeVolunteers = volunteers.filter(v => v.status === 'ACTIVE').length;

  return (
    <DashboardLayout title="Operational Dashboard">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Welcome Banner */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-950 via-slate-900 to-violet-950 border border-indigo-500/20 p-6 sm:p-8 shadow-xl">
          <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
          <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold mb-3">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                AI-Powered Club Event Operations
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
                Welcome back, {user?.full_name?.split(' ')[0] || 'Organizer'}!
              </h2>
              <p className="text-slate-400 text-sm mt-1 max-w-xl">
                Here is your live campus operations summary. Manage events, track volunteer task execution, and coordinate multi-channel announcements.
              </p>
            </div>

            {/* Quick action buttons */}
            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              <Link
                to="/events/new"
                className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold shadow-lg shadow-indigo-600/30 transition-all"
              >
                <Plus className="w-4 h-4" /> New Event
              </Link>
              <Link
                to="/tasks"
                className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white px-4 py-2.5 rounded-xl text-xs sm:text-sm font-medium border border-slate-700 transition-colors"
              >
                <CheckSquare className="w-4 h-4 text-emerald-400" /> Tasks
              </Link>
              <Link
                to="/announcements/new"
                className="inline-flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white px-4 py-2.5 rounded-xl text-xs sm:text-sm font-medium border border-slate-700 transition-colors"
              >
                <Megaphone className="w-4 h-4 text-violet-400" /> Broadcast
              </Link>
            </div>
          </div>
        </div>

        {/* 4 KPI Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Card 1: Events */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 hover:border-slate-700/80 transition-all shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Events Pipeline</span>
              <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                <Calendar className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-white">{events.length}</span>
              <span className="text-xs text-indigo-400 font-medium">{upcomingEvents.length} upcoming</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              {events.filter(e => e.status === 'COMPLETED').length} events completed successfully
            </p>
          </div>

          {/* Card 2: Tasks */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 hover:border-slate-700/80 transition-all shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Task Execution</span>
              <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <CheckSquare className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-white">{completedTasks}/{tasks.length}</span>
              <span className="text-xs text-emerald-400 font-medium">{taskCompletionRate}% done</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-1.5 mt-3 overflow-hidden">
              <div
                className="bg-gradient-to-r from-emerald-500 to-teal-400 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${taskCompletionRate}%` }}
              />
            </div>
          </div>

          {/* Card 3: Volunteers */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 hover:border-slate-700/80 transition-all shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Volunteers</span>
              <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <Users className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-white">{volunteers.length}</span>
              <span className="text-xs text-amber-400 font-medium">{activeVolunteers} active</span>
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              {volunteers.filter(v => v.load_indicator === 'OVERLOADED').length} overloaded members
            </p>
          </div>

          {/* Card 4: Announcements */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 hover:border-slate-700/80 transition-all shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Broadcasts</span>
              <div className="w-9 h-9 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
                <Megaphone className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-white">{announcements.length}</span>
              <span className="text-xs text-violet-400 font-medium">
                {announcements.filter(a => a.status === 'PUBLISHED').length} published
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-2">
              Across WhatsApp, Email & Socials
            </p>
          </div>
        </div>

        {/* Two-Column Core Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Recent & Upcoming Events (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-white tracking-tight">Active Events</h3>
                <p className="text-xs text-slate-400">Manage schedules, venues & budgets</p>
              </div>
              <Link
                to="/events"
                className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1 group"
              >
                View all ({events.length})
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
              </Link>
            </div>

            {loading ? (
              <div className="flex justify-center py-16 bg-slate-900/40 rounded-2xl border border-slate-800/60">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-500" />
              </div>
            ) : events.length === 0 ? (
              <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-8 text-center flex flex-col items-center justify-center">
                <div className="w-12 h-12 bg-slate-800/80 rounded-2xl flex items-center justify-center mb-3">
                  <Calendar className="w-6 h-6 text-slate-500" />
                </div>
                <h4 className="text-sm font-semibold text-white mb-1">No events scheduled</h4>
                <p className="text-xs text-slate-400 max-w-xs mb-4">Create your first club event or use our AI Agent to generate a full event plan.</p>
                <Link
                  to="/events/new"
                  className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-xs font-semibold"
                >
                  <Plus className="w-3.5 h-3.5" /> Create Event
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {events.slice(0, 4).map((event) => {
                  const evDate = new Date(event.date);
                  const daysRemaining = Math.ceil((evDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
                  return (
                    <Link
                      key={event.id}
                      to={`/events/${event.id}`}
                      className="block bg-slate-900/60 hover:bg-slate-850 border border-slate-800/80 hover:border-slate-700/80 p-4 sm:p-5 rounded-2xl transition-all group"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2.5 mb-1.5 flex-wrap">
                            <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${
                              event.status === 'PUBLISHED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                              event.status === 'COMPLETED' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                              event.status === 'CANCELLED' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                              'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            }`}>
                              {event.status}
                            </span>
                            {daysRemaining > 0 && event.status !== 'COMPLETED' && (
                              <span className="text-[11px] text-indigo-400 font-medium flex items-center gap-1">
                                <Clock className="w-3 h-3" /> {daysRemaining} days left
                              </span>
                            )}
                          </div>
                          <h4 className="text-sm sm:text-base font-bold text-white group-hover:text-indigo-300 transition-colors truncate">
                            {event.title}
                          </h4>
                          <p className="text-xs text-slate-400 mt-1 line-clamp-1">
                            {event.venue ? `${event.venue} · ` : ''}
                            {evDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                            {event.budget ? ` · ₹${Number(event.budget).toLocaleString()}` : ''}
                          </p>
                        </div>
                        <div className="w-8 h-8 rounded-lg bg-slate-800/60 flex items-center justify-center text-slate-400 group-hover:text-white group-hover:bg-indigo-600 transition-colors shrink-0">
                          <ArrowRight className="w-4 h-4" />
                        </div>
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right Column: Tasks & Announcements Preview (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Urgent Tasks Preview */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white tracking-tight">Active Tasks</h4>
                  <p className="text-[11px] text-slate-400">Assigned across operations</p>
                </div>
                <Link to="/tasks" className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold">
                  View all →
                </Link>
              </div>

              {tasks.length === 0 ? (
                <p className="text-xs text-slate-500 py-4 text-center">No tasks currently assigned.</p>
              ) : (
                <div className="space-y-2.5">
                  {tasks.slice(0, 4).map((task) => (
                    <div
                      key={task.id}
                      className="p-3 bg-slate-950/60 border border-slate-800/60 rounded-xl flex items-center justify-between gap-3"
                    >
                      <div className="flex-1 min-w-0">
                        <p className={`text-xs font-medium text-white truncate ${task.status === 'DONE' ? 'line-through text-slate-500' : ''}`}>
                          {task.title}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.2 rounded border ${
                            task.status === 'DONE' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                            task.status === 'IN_PROGRESS' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                            task.status === 'BLOCKED' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                            'bg-slate-500/10 text-slate-400 border-slate-500/20'
                          }`}>
                            {task.status.replace('_', ' ')}
                          </span>
                          {task.priority && (
                            <span className="text-[10px] text-slate-500 capitalize">{task.priority.toLowerCase()}</span>
                          )}
                        </div>
                      </div>
                      {task.status === 'DONE' ? (
                        <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                      ) : task.status === 'BLOCKED' ? (
                        <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                      ) : (
                        <Clock className="w-4 h-4 text-slate-500 shrink-0" />
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent Announcements Preview */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-white tracking-tight">Recent Announcements</h4>
                  <p className="text-[11px] text-slate-400">Marketing & campus outreach</p>
                </div>
                <Link to="/announcements" className="text-xs text-violet-400 hover:text-violet-300 font-semibold">
                  View all →
                </Link>
              </div>

              {announcements.length === 0 ? (
                <p className="text-xs text-slate-500 py-4 text-center">No announcements created yet.</p>
              ) : (
                <div className="space-y-3">
                  {announcements.slice(0, 2).map((ann) => (
                    <Link
                      key={ann.id}
                      to={`/announcements/${ann.id}/edit`}
                      className="block p-3.5 bg-slate-950/60 border border-slate-800/60 hover:border-slate-700 rounded-xl transition-colors group"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <h5 className="text-xs font-bold text-white group-hover:text-violet-300 transition-colors truncate">
                          {ann.title}
                        </h5>
                        <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-slate-800 text-slate-400 uppercase font-semibold">
                          {ann.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                        {ann.content}
                      </p>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
