import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Calendar } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import api from '../lib/axios';

interface EventItem {
  id: number;
  title: string;
  description: string;
  date: string;
  venue: string;
  status: string;
  budget: number;
  expected_attendance: number;
}

export default function EventList() {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    api.get('/events')
      .then(res => setEvents(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = events.filter(e =>
    e.title.toLowerCase().includes(search.toLowerCase()) ||
    (e.venue && e.venue.toLowerCase().includes(search.toLowerCase()))
  );

  const statusColor = (status: string) => {
    switch (status) {
      case 'PUBLISHED': return 'bg-green-500/10 text-green-400 border-green-500/20';
      case 'CANCELLED': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'COMPLETED': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default: return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    }
  };

  return (
    <DashboardLayout title="Events">
      <div className="max-w-6xl mx-auto space-y-6 sm:space-y-8">
        {/* Header bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4">
          <div className="relative flex-1 sm:max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search events by title or venue..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors placeholder-slate-500"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <Link
            to="/events/new"
            className="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-colors font-semibold text-sm shrink-0 shadow-md shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" /> New Event
          </Link>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 sm:p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
              <Calendar className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">
              {search ? 'No matching events found' : 'No events yet'}
            </h3>
            <p className="text-slate-400 text-sm max-w-sm mb-6">
              {search ? 'Try adjusting your search terms.' : 'Create your first event to get started.'}
            </p>
            {!search && (
              <Link
                to="/events/new"
                className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-colors font-semibold text-sm"
              >
                <Plus className="w-4 h-4" /> Create Event
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {filtered.map(event => {
              const eventDate = new Date(event.date);
              const daysLeft = Math.ceil((eventDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
              return (
                <Link
                  key={event.id}
                  to={`/events/${event.id}`}
                  className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 sm:p-6 transition-all hover:shadow-xl hover:shadow-slate-950/60 group flex flex-col justify-between h-full space-y-4"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-3.5">
                      <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${statusColor(event.status)}`}>
                        {event.status}
                      </span>
                      {daysLeft > 0 && event.status !== 'COMPLETED' && event.status !== 'CANCELLED' && (
                        <span className="text-[11px] font-medium text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-md">
                          {daysLeft}d left
                        </span>
                      )}
                    </div>
                    <h3 className="text-base font-semibold text-white mb-2 group-hover:text-indigo-300 transition-colors line-clamp-1">
                      {event.title}
                    </h3>
                    {event.description && (
                      <p className="text-slate-400 text-xs sm:text-sm line-clamp-2 leading-relaxed">
                        {event.description}
                      </p>
                    )}
                  </div>
                  <div className="pt-3 border-t border-slate-800/60 flex items-center gap-2.5 sm:gap-3 text-xs text-slate-400 mt-auto flex-wrap">
                    <span>
                      {eventDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </span>
                    {event.venue && <span>· {event.venue}</span>}
                    {event.budget > 0 && <span>· ₹{event.budget.toLocaleString()}</span>}
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
