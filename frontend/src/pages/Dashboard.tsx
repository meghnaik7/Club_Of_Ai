import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Calendar, Plus } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import api from '../lib/axios';

interface EventSummary {
  id: number;
  title: string;
  date: string;
  status: string;
  venue: string;
}

export default function Dashboard() {
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/events')
      .then(res => setEvents(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const upcomingCount = events.filter(e => new Date(e.date) > new Date() && e.status !== 'CANCELLED').length;

  return (
    <DashboardLayout title="Dashboard Overview">
      <div className="max-w-5xl mx-auto space-y-6 sm:space-y-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
          <div className="bg-slate-900 border border-slate-800 p-5 sm:p-6 rounded-2xl shadow-sm">
            <p className="text-xs sm:text-sm text-slate-400 font-medium mb-1.5">Total Events</p>
            <p className="text-2xl sm:text-3xl font-bold text-white tracking-tight">{events.length}</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-5 sm:p-6 rounded-2xl shadow-sm">
            <p className="text-xs sm:text-sm text-slate-400 font-medium mb-1.5">Upcoming Events</p>
            <p className="text-2xl sm:text-3xl font-bold text-indigo-400 tracking-tight">{upcomingCount}</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-5 sm:p-6 rounded-2xl shadow-sm">
            <p className="text-xs sm:text-sm text-slate-400 font-medium mb-1.5">Completed Events</p>
            <p className="text-2xl sm:text-3xl font-bold text-emerald-400 tracking-tight">
              {events.filter(e => e.status === 'COMPLETED').length}
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        ) : events.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 sm:p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
              <Calendar className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">No events yet</h3>
            <p className="text-slate-400 text-sm max-w-sm mb-6">Create your first event to get started managing club activities.</p>
            <Link
              to="/events/new"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-colors font-semibold text-sm shadow-md shadow-indigo-600/20"
            >
              <Plus className="w-4 h-4" /> Create Event
            </Link>
          </div>
        ) : (
          <div className="space-y-3 sm:space-y-4">
            <div className="flex items-center justify-between pb-1">
              <h3 className="text-white font-semibold text-base sm:text-lg">Recent Events</h3>
              <Link
                to="/events"
                className="text-indigo-400 hover:text-indigo-300 text-xs sm:text-sm font-medium transition-colors"
              >
                View all →
              </Link>
            </div>
            {events.slice(0, 5).map(event => (
              <Link
                key={event.id}
                to={`/events/${event.id}`}
                className="block bg-slate-900 border border-slate-800 hover:border-slate-700 p-4 sm:p-5 rounded-2xl transition-all hover:bg-slate-850 group"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-4">
                  <div className="min-w-0 flex-1">
                    <h4 className="font-semibold text-white group-hover:text-indigo-300 transition-colors truncate">{event.title}</h4>
                    <p className="text-xs sm:text-sm text-slate-400 mt-1 truncate">
                      {new Date(event.date).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric'
                      })}
                      {event.venue && ` · ${event.venue}`}
                    </p>
                  </div>
                  <span className={`self-start sm:self-center text-xs px-3 py-1 rounded-full font-semibold border shrink-0 ${
                    event.status === 'PUBLISHED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                    event.status === 'CANCELLED' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                    event.status === 'COMPLETED' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                    'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                  }`}>
                    {event.status}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
