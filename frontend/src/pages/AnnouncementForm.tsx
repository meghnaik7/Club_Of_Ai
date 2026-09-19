import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Sparkles, Loader2, Copy, Check, ChevronDown } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import AnnouncementsService from '../services/announcements.service';
import type { AnnouncementCreate, VariantsResponse } from '../services/announcements.service';
import EventsService from '../services/events.service';
import type { Event } from '../services/events.service';

const TONES = ['engaging', 'formal', 'casual', 'urgent', 'inspirational'];

export default function AnnouncementForm() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  // Form state
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [status, setStatus] = useState('DRAFT');
  const [eventId, setEventId] = useState<number | ''>('');
  const [events, setEvents] = useState<Event[]>([]);

  // AI generate state
  const [tone, setTone] = useState('engaging');
  const [highlights, setHighlights] = useState('');
  const [generating, setGenerating] = useState(false);

  // Variants state
  const [variants, setVariants] = useState<VariantsResponse | null>(null);
  const [generatingVariants, setGeneratingVariants] = useState(false);
  const [savedId, setSavedId] = useState<number | null>(null);

  // UI state
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    EventsService.list().then(setEvents).catch(() => {});
    if (isEdit && id) {
      AnnouncementsService.get(Number(id)).then(ann => {
        setTitle(ann.title);
        setContent(ann.content);
        setTargetAudience(ann.target_audience || '');
        setStatus(ann.status);
        setEventId(ann.event_id || '');
        setSavedId(ann.id);
      }).catch(() => navigate('/announcements'));
    }
  }, [id]);

  const handleGenerate = async () => {
    if (!eventId) { setError('Select an event to generate content.'); return; }
    setGenerating(true);
    setError('');
    try {
      const res = await AnnouncementsService.generate({
        event_id: Number(eventId),
        tone,
        target_audience: targetAudience || undefined,
        key_highlights: highlights ? highlights.split('\n').filter(Boolean) : undefined,
      });
      setTitle(res.title);
      setContent(res.content);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Generation failed.');
    } finally {
      setGenerating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) { setError('Title and content are required.'); return; }
    setSubmitting(true);
    setError('');
    try {
      const payload: AnnouncementCreate = {
        title,
        content,
        target_audience: targetAudience || undefined,
        event_id: eventId ? Number(eventId) : undefined,
      };
      if (isEdit && id) {
        await AnnouncementsService.update(Number(id), { ...payload, status });
        setSavedId(Number(id));
      } else {
        const created = await AnnouncementsService.create(payload);
        setSavedId(created.id);
      }
      navigate('/announcements');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to save.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleGenerateVariants = async () => {
    const targetId = savedId ?? (isEdit ? Number(id) : null);
    if (!targetId) { setError('Save the announcement first to generate variants.'); return; }
    setGeneratingVariants(true);
    try {
      const v = await AnnouncementsService.generateVariants(targetId);
      setVariants(v);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Variant generation failed.');
    } finally {
      setGeneratingVariants(false);
    }
  };

  const copyText = (text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key);
      setTimeout(() => setCopied(null), 2000);
    });
  };

  return (
    <DashboardLayout title={isEdit ? 'Edit Announcement' : 'New Announcement'}>
      <div className="max-w-3xl mx-auto space-y-6">
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-xl px-4 py-3">
            {error}
          </div>
        )}

        {/* AI Generate Panel */}
        <div className="bg-slate-900 border border-violet-500/20 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-violet-600/20 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-sm">AI Generate</h3>
              <p className="text-slate-500 text-xs">Auto-fill title and content from event info</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Event</label>
              <div className="relative">
                <select
                  id="generate-event-select"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-violet-500 appearance-none"
                  value={eventId}
                  onChange={e => setEventId(e.target.value ? Number(e.target.value) : '')}
                >
                  <option value="">Select an event…</option>
                  {events.map(ev => <option key={ev.id} value={ev.id}>{ev.title}</option>)}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Tone</label>
              <div className="relative">
                <select
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-violet-500 appearance-none capitalize"
                  value={tone}
                  onChange={e => setTone(e.target.value)}
                >
                  {TONES.map(t => <option key={t} value={t} className="capitalize">{t}</option>)}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
              </div>
            </div>
          </div>
          <div className="mb-4">
            <label className="block text-xs font-medium text-slate-400 mb-1">Key highlights (one per line, optional)</label>
            <textarea
              rows={2}
              placeholder="Free food&#10;Live music&#10;Prizes"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-violet-500 resize-none"
              value={highlights}
              onChange={e => setHighlights(e.target.value)}
            />
          </div>
          <button
            id="ai-generate-btn"
            type="button"
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
          >
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {generating ? 'Generating…' : 'Generate Content'}
          </button>
        </div>

        {/* Form */}
        <form id="announcement-form" onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h3 className="text-white font-semibold mb-2">Announcement Details</h3>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Title *</label>
            <input
              id="announcement-title"
              required
              type="text"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              placeholder="Announcement title"
              value={title}
              onChange={e => setTitle(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Content *</label>
            <textarea
              id="announcement-content"
              required
              rows={6}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors resize-none"
              placeholder="Write the announcement content here…"
              value={content}
              onChange={e => setContent(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Target Audience</label>
              <input
                type="text"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500"
                placeholder="e.g. All Students, Club Members"
                value={targetAudience}
                onChange={e => setTargetAudience(e.target.value)}
              />
            </div>
            {isEdit && (
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Status</label>
                <div className="relative">
                  <select
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                    value={status}
                    onChange={e => setStatus(e.target.value)}
                  >
                    <option value="DRAFT">Draft</option>
                    <option value="PUBLISHED">Published</option>
                    <option value="ARCHIVED">Archived</option>
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                </div>
              </div>
            )}
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={submitting}
              id="save-announcement-btn"
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors"
            >
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {isEdit ? 'Save Changes' : 'Create Announcement'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/announcements')}
              className="text-slate-400 hover:text-white text-sm px-4 py-2.5 rounded-lg hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>

        {/* Variants Panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-white font-semibold text-sm">Platform Variants</h3>
              <p className="text-slate-500 text-xs mt-0.5">Generate WhatsApp, Email & Instagram versions</p>
            </div>
            <button
              id="generate-variants-btn"
              type="button"
              onClick={handleGenerateVariants}
              disabled={generatingVariants}
              className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 disabled:opacity-50 text-slate-300 text-xs font-medium px-3 py-2 rounded-lg transition-colors"
            >
              {generatingVariants ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-violet-400" />}
              {generatingVariants ? 'Generating…' : 'Generate Variants'}
            </button>
          </div>

          {variants ? (
            <div className="space-y-4">
              {/* WhatsApp */}
              <VariantCard
                label="WhatsApp"
                color="emerald"
                text={variants.whatsapp}
                onCopy={() => copyText(variants.whatsapp, 'wa')}
                copied={copied === 'wa'}
              />
              {/* Email */}
              <VariantCard
                label="Email"
                color="blue"
                text={`Subject: ${variants.email.subject}\n\n${variants.email.body}`}
                onCopy={() => copyText(`Subject: ${variants.email.subject}\n\n${variants.email.body}`, 'email')}
                copied={copied === 'email'}
              />
              {/* Instagram */}
              <VariantCard
                label="Instagram"
                color="pink"
                text={`${variants.instagram.caption}\n\n${variants.instagram.hashtags.join(' ')}`}
                onCopy={() => copyText(`${variants.instagram.caption}\n\n${variants.instagram.hashtags.join(' ')}`, 'ig')}
                copied={copied === 'ig'}
              />
            </div>
          ) : (
            <p className="text-slate-600 text-sm text-center py-4">
              {isEdit ? 'Click "Generate Variants" to create platform-specific versions.' : 'Save the announcement first, then generate variants.'}
            </p>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}

function VariantCard({ label, color, text, onCopy, copied }: {
  label: string;
  color: 'emerald' | 'blue' | 'pink';
  text: string;
  onCopy: () => void;
  copied: boolean;
}) {
  const colorMap = {
    emerald: 'border-emerald-500/20 text-emerald-400',
    blue: 'border-blue-500/20 text-blue-400',
    pink: 'border-pink-500/20 text-pink-400',
  };
  return (
    <div className={`bg-slate-950/60 border rounded-xl p-4 ${colorMap[color].split(' ')[0]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs font-semibold uppercase tracking-wider ${colorMap[color].split(' ')[1]}`}>{label}</span>
        <button
          onClick={onCopy}
          className="flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-white bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded-md transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">{text}</pre>
    </div>
  );
}
