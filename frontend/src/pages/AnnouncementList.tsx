import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Megaphone, Trash2, ExternalLink } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import AnnouncementsService from '../services/announcements.service';
import type { Announcement } from '../services/announcements.service';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  PUBLISHED: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  ARCHIVED: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
};

export default function AnnouncementList() {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [deleting, setDeleting] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    AnnouncementsService.list()
      .then(setAnnouncements)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this announcement?')) return;
    setDeleting(id);
    try {
      await AnnouncementsService.delete(id);
      setAnnouncements(prev => prev.filter(a => a.id !== id));
    } finally {
      setDeleting(null);
    }
  };

  const filtered = announcements.filter(a =>
    a.title.toLowerCase().includes(search.toLowerCase()) ||
    (a.content && a.content.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <DashboardLayout title="Announcements">
      <div className="max-w-5xl mx-auto">
        {/* Header bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              id="announcement-search"
              type="text"
              placeholder="Search announcements..."
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <Link
            to="/announcements/new"
            id="create-announcement-btn"
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg transition-colors font-medium text-sm shrink-0"
          >
            <Plus className="w-4 h-4" /> New Announcement
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
              <Megaphone className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">
              {search ? 'No matching announcements' : 'No announcements yet'}
            </h3>
            <p className="text-slate-400 max-w-sm mb-6">
              {search ? 'Try different keywords.' : 'Create your first announcement or use AI to generate one.'}
            </p>
            {!search && (
              <Link
                to="/announcements/new"
                className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg transition-colors font-medium text-sm"
              >
                <Plus className="w-4 h-4" /> Create Announcement
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map(ann => (
              <div
                key={ann.id}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 transition-all group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <h3 className="text-white font-semibold group-hover:text-indigo-300 transition-colors">
                        {ann.title}
                      </h3>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${
                        STATUS_COLORS[ann.status] || STATUS_COLORS.DRAFT
                      }`}>
                        {ann.status}
                      </span>
                      {ann.target_audience && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                          {ann.target_audience}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-400 text-sm line-clamp-2">{ann.content}</p>
                    <p className="text-[11px] text-slate-600 mt-2">
                      {new Date(ann.created_at).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric'
                      })}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <Link
                      to={`/announcements/${ann.id}/edit`}
                      className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-white hover:bg-slate-800 transition-colors"
                      title="Edit"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </Link>
                    <button
                      onClick={() => handleDelete(ann.id)}
                      disabled={deleting === ann.id}
                      className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
