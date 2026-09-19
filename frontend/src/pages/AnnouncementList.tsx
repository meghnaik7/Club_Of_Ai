import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Megaphone, Trash2, ExternalLink, Copy, Check } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import AnnouncementsService from '../services/announcements.service';
import type { Announcement } from '../services/announcements.service';

const STATUS_COLORS: Record<string, string> = {
  DRAFT: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  PUBLISHED: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  ARCHIVED: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
};

export default function AnnouncementList() {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [deleting, setDeleting] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    AnnouncementsService.list()
      .then(setAnnouncements)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this announcement?')) return;
    setDeleting(id);
    try {
      await AnnouncementsService.delete(id);
      setAnnouncements(prev => prev.filter(a => a.id !== id));
    } finally {
      setDeleting(null);
    }
  };

  const handleCopyContent = (ann: Announcement) => {
    navigator.clipboard.writeText(`${ann.title}\n\n${ann.content}`).then(() => {
      setCopiedId(ann.id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  const filtered = announcements.filter(a =>
    a.title.toLowerCase().includes(search.toLowerCase()) ||
    (a.content && a.content.toLowerCase().includes(search.toLowerCase())) ||
    (a.target_audience && a.target_audience.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <DashboardLayout title="Broadcast Announcements">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* KPI Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Total Campaigns</span>
            <p className="text-2xl font-black text-white mt-1">{announcements.length}</p>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">Published</span>
            <p className="text-2xl font-black text-white mt-1">
              {announcements.filter(a => a.status === 'PUBLISHED').length}
            </p>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400">Drafts</span>
            <p className="text-2xl font-black text-white mt-1">
              {announcements.filter(a => a.status === 'DRAFT').length}
            </p>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-violet-400">Multi-Channel</span>
            <p className="text-2xl font-black text-white mt-1">WhatsApp & Email</p>
          </div>
        </div>

        {/* Action Header bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              id="announcement-search"
              type="text"
              placeholder="Search announcements by title, audience, or content..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          <Link
            to="/announcements/new"
            id="create-announcement-btn"
            className="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl transition-all font-semibold text-xs sm:text-sm shadow-lg shadow-indigo-600/30 shrink-0"
          >
            <Plus className="w-4 h-4" /> New Announcement
          </Link>
        </div>

        {/* List Content */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-800/80 rounded-2xl flex items-center justify-center mb-4 text-slate-500">
              <Megaphone className="w-8 h-8" />
            </div>
            <h3 className="text-base font-bold text-white mb-1">
              {search ? 'No matching announcements' : 'No announcements published yet'}
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mb-6">
              {search ? 'Try using different search keywords.' : 'Create an announcement or use our AI Generator to draft copies for WhatsApp, Email & Socials.'}
            </p>
            <Link
              to="/announcements/new"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold shadow-lg shadow-indigo-600/30"
            >
              <Plus className="w-4 h-4" /> Create First Broadcast
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map(ann => (
              <div
                key={ann.id}
                className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-5 sm:p-6 transition-all group shadow-sm"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2.5 mb-2.5 flex-wrap">
                      <h3 className="text-base font-bold text-white group-hover:text-indigo-300 transition-colors">
                        {ann.title}
                      </h3>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${
                        STATUS_COLORS[ann.status] || STATUS_COLORS.DRAFT
                      }`}>
                        {ann.status}
                      </span>
                      {ann.target_audience && (
                        <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                          Audience: {ann.target_audience}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-300 text-xs sm:text-sm leading-relaxed whitespace-pre-line line-clamp-3">
                      {ann.content}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-3">
                      Created on {new Date(ann.created_at).toLocaleDateString('en-US', {
                        month: 'short', day: 'numeric', year: 'numeric'
                      })}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 pt-3 sm:pt-0 border-t sm:border-t-0 border-slate-800 justify-end">
                    <button
                      onClick={() => handleCopyContent(ann)}
                      className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-750 px-3 py-1.5 rounded-xl transition-colors border border-slate-750"
                      title="Copy content to clipboard"
                    >
                      {copiedId === ann.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedId === ann.id ? 'Copied' : 'Copy'}</span>
                    </button>

                    <Link
                      to={`/announcements/${ann.id}/edit`}
                      className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors border border-slate-750"
                      title="Edit announcement"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </Link>

                    <button
                      onClick={() => handleDelete(ann.id)}
                      disabled={deleting === ann.id}
                      className="p-1.5 rounded-xl text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
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
