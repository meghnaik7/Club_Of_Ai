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
      <div className="max-w-5xl mx-auto space-y-6 sm:space-y-8">
        {/* Header bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 sm:gap-4">
          <div className="relative flex-1 sm:max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              id="announcement-search"
              type="text"
              placeholder="Search announcements..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors placeholder-slate-500"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <Link
            to="/announcements/new"
            id="create-announcement-btn"
            className="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-colors font-semibold text-sm shrink-0 shadow-md shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" /> New Announcement
          </Link>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 sm:p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
              <Megaphone className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">
              {search ? 'No matching announcements found' : 'No announcements yet'}
            </h3>
            <p className="text-slate-400 text-sm max-w-sm mb-6">
              {search ? 'Try different keywords.' : 'Create your first announcement or use AI to generate one.'}
            </p>
            {!search && (
              <Link
                to="/announcements/new"
                className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-colors font-semibold text-sm shadow-md shadow-indigo-600/20"
              >
                <Plus className="w-4 h-4" /> Create Announcement
              </Link>
            )}
          </div>
        ) : (
          <div className="space-y-3 sm:space-y-4">
            {filtered.map(ann => (
              <div
                key={ann.id}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 sm:p-6 transition-all group shadow-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 mb-2 flex-wrap">
                      <h3 className="text-base font-semibold text-white group-hover:text-indigo-300 transition-colors truncate">
                        {ann.title}
                      </h3>
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${
                        STATUS_COLORS[ann.status] || STATUS_COLORS.DRAFT
                      }`}>
                        {ann.status}
                      </span>
                      {ann.target_audience && (
                        <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-medium">
                          {ann.target_audience}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-300 text-sm line-clamp-2 leading-relaxed">{ann.content}</p>
                    <p className="text-xs text-slate-500 mt-2.5">
                      {new Date(ann.created_at).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric'
                      })}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0 pt-0.5">
                    <Link
                      to={`/announcements/${ann.id}/edit`}
                      className="w-8 h-8 flex items-center justify-center rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                      title="Edit"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </Link>
                    <button
                      onClick={() => handleDelete(ann.id)}
                      disabled={deleting === ann.id}
                      className="w-8 h-8 flex items-center justify-center rounded-xl text-slate-400 hover:text-red-400 hover:bg-red-400/10 transition-colors"
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
