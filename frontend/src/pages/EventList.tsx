import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Calendar, MapPin, Clock, ArrowRight, DollarSign } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EventsService from '../services/events.service';
import type { Event } from '../services/events.service';

export default function EventList() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  useEffect(() => {
    EventsService.list()
      .then(setEvents)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = events.filter(e => {
    const matchesSearch = e.title.toLowerCase().includes(search.toLowerCase()) ||
      (e.venue && e.venue.toLowerCase().includes(search.toLowerCase())) ||
      (e.description && e.description.toLowerCase().includes(search.toLowerCase()));
    const matchesStatus = statusFilter === 'ALL' || e.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusColor = (status: string) => {
    switch (status) {
      case 'PUBLISHED': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'CANCELLED': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'COMPLETED': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default: return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    }
  };

  const statuses = ['ALL', 'PUBLISHED', 'DRAFT', 'COMPLETED', 'CANCELLED'];

  return (
    <DashboardLayout title="Events Management">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header & Filter Bar */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search events by name, venue, or description..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1 lg:pb-0">
            {statuses.map(st => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold capitalize transition-all shrink-0 ${
                  statusFilter === st
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20'
                    : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                {st.toLowerCase().replace('_', ' ')}
              </button>
            ))}

            <Link
              to="/events/new"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl transition-all font-semibold text-xs sm:text-sm shadow-lg shadow-indigo-600/30 shrink-0 ml-2"
            >
              <Plus className="w-4 h-4" /> New Event
            </Link>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-800/80 rounded-2xl flex items-center justify-center mb-4 text-slate-500">
              <Calendar className="w-8 h-8" />
            </div>
            <h3 className="text-base font-bold text-white mb-1">
              {search || statusFilter !== 'ALL' ? 'No matching events found' : 'No events scheduled yet'}
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mb-6">
              {search ? 'Try clearing your search query or choosing another status tab.' : 'Create your first campus club event to start coordinating teams.'}
            </p>
            <Link
              to="/events/new"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold shadow-lg shadow-indigo-600/30"
            >
              <Plus className="w-4 h-4" /> Create Event
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map(event => {
              const eventDate = new Date(event.date);
              const daysLeft = Math.ceil((eventDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
              const budget = Number(event.budget || 0);
              const budgetSpent = Number(event.budget_spent || 0);
              const spentPct = budget > 0 ? Math.min(Math.round((budgetSpent / budget) * 100), 100) : 0;

              return (
                <Link
                  key={event.id}
                  to={`/events/${event.id}`}
                  className="bg-slate-900/80 border border-slate-800/90 hover:border-slate-700 rounded-3xl p-6 transition-all hover:shadow-xl hover:shadow-slate-950/60 group flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-4">
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${statusColor(event.status)}`}>
                        {event.status}
                      </span>
                      {daysLeft > 0 && event.status !== 'COMPLETED' && event.status !== 'CANCELLED' && (
                        <span className="text-[11px] text-indigo-400 font-medium flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {daysLeft}d left
                        </span>
                      )}
                    </div>

                    <h3 className="text-lg font-bold text-white mb-2 group-hover:text-indigo-300 transition-colors">
                      {event.title}
                    </h3>

                    {event.description && (
                      <p className="text-slate-400 text-xs sm:text-sm line-clamp-2 leading-relaxed mb-4">
                        {event.description}
                      </p>
                    )}
                  </div>

                  <div className="pt-4 border-t border-slate-800/80 space-y-3">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-indigo-400" />
                        {eventDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                      {event.venue && (
                        <span className="flex items-center gap-1.5 truncate max-w-[140px]">
                          <MapPin className="w-3.5 h-3.5 text-violet-400 shrink-0" />
                          <span className="truncate">{event.venue}</span>
                        </span>
                      )}
                    </div>

                    {budget > 0 && (
                      <div>
                        <div className="flex justify-between text-[11px] text-slate-500 mb-1">
                          <span className="flex items-center gap-1">
                            <DollarSign className="w-3 h-3 text-emerald-400" /> Budget Spent
                          </span>
                          <span>₹{budgetSpent.toLocaleString()} / ₹{budget.toLocaleString()}</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-1 overflow-hidden">
                          <div
                            className="bg-emerald-500 h-1 rounded-full transition-all"
                            style={{ width: `${spentPct}%` }}
                          />
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-end text-xs font-semibold text-indigo-400 group-hover:text-indigo-300 pt-1">
                      <span>View Operations</span>
                      <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
