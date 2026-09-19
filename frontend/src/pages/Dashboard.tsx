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
      <div className="max-w-5xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
            <p className="text-sm text-slate-400 font-medium mb-1">Total Events</p>
            <p className="text-3xl font-bold text-white">{events.length}</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
            <p className="text-sm text-slate-400 font-medium mb-1">Upcoming Events</p>
            <p className="text-3xl font-bold text-white">{upcomingCount}</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
            <p className="text-sm text-slate-400 font-medium mb-1">Completed</p>
            <p className="text-3xl font-bold text-white">
              {events.filter(e => e.status === 'COMPLETED').length}
            </p>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        ) : events.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center h-64 flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
              <Calendar className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">No events yet</h3>
            <p className="text-slate-400 max-w-sm mb-6">Create your first event to get started.</p>
            <Link
              to="/events/new"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg transition-colors font-medium text-sm"
            >
              <Plus className="w-4 h-4" /> Create Event
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-white font-semibold">Recent Events</h3>
              <Link
                to="/events"
                className="text-indigo-400 hover:text-indigo-300 text-sm font-medium"
              >
                View all →
              </Link>
            </div>
            {events.slice(0, 5).map(event => (
              <Link
                key={event.id}
                to={`/events/${event.id}`}
                className="block bg-slate-900 border border-slate-800 hover:border-slate-700 p-5 rounded-xl transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium text-white">{event.title}</h4>
                    <p className="text-sm text-slate-400 mt-1">
                      {new Date(event.date).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric'
                      })}
                      {event.venue && ` · ${event.venue}`}
                    </p>
                  </div>
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                    event.status === 'PUBLISHED' ? 'bg-green-500/10 text-green-400' :
                    event.status === 'CANCELLED' ? 'bg-red-500/10 text-red-400' :
                    event.status === 'COMPLETED' ? 'bg-blue-500/10 text-blue-400' :
                    'bg-yellow-500/10 text-yellow-400'
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
