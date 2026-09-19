import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Calendar, Loader2, ChevronDown } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import EventsService from '../services/events.service';
import type { EventCreate } from '../services/events.service';

interface EventFormData {
  title: string;
  description: string;
  date: string;
  venue: string;
  budget: number;
  expected_attendance: number;
  status: string;
}

const defaultForm: EventFormData = {
  title: '',
  description: '',
  date: '',
  venue: '',
  budget: 0,
  expected_attendance: 0,
  status: 'DRAFT',
};

export default function EventForm() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form, setForm] = useState<EventFormData>(defaultForm);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isEdit && id) {
      setLoading(true);
      EventsService.get(Number(id))
        .then(e => {
          setForm({
            title: e.title || '',
            description: e.description || '',
            date: e.date ? new Date(e.date).toISOString().slice(0, 16) : '',
            venue: e.venue || '',
            budget: e.budget || 0,
            expected_attendance: e.expected_attendance || 0,
            status: e.status || 'DRAFT',
          });
        })
        .catch(() => setError('Failed to load event'))
        .finally(() => setLoading(false));
    }
  }, [id, isEdit]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.date) {
      setError('Please provide an event name and date.');
      return;
    }
    setSaving(true);
    setError('');

    const payload: EventCreate = {
      title: form.title,
      description: form.description || undefined,
      date: new Date(form.date).toISOString(),
      venue: form.venue || undefined,
      budget: Number(form.budget),
      expected_attendance: Number(form.expected_attendance),
      status: form.status,
    };

    try {
      if (isEdit && id) {
        await EventsService.update(Number(id), payload);
      } else {
        await EventsService.create(payload);
      }
      navigate('/events');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save event');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const inputClass = "w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-600";
  const labelClass = "block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5";

  return (
    <DashboardLayout title={isEdit ? 'Edit Event Details' : 'Create New Event'}>
      <div className="max-w-3xl mx-auto space-y-6">
        <button
          onClick={() => navigate('/events')}
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" /> Back to Events
        </button>

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
          </div>
        ) : (
          <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-xl">
            <div className="flex items-center gap-3.5 mb-6 pb-6 border-b border-slate-800">
              <div className="w-10 h-10 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <Calendar className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white tracking-tight">
                  {isEdit ? 'Update Event Information' : 'New Club Event'}
                </h2>
                <p className="text-xs text-slate-400">
                  Configure schedule, venue logistics, and budget allocation
                </p>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl text-sm mb-6">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className={labelClass}>Event Title *</label>
                <input
                  type="text"
                  name="title"
                  required
                  className={inputClass}
                  value={form.title}
                  onChange={handleChange}
                  placeholder="e.g. AI Odyssey Hackathon 2026"
                />
              </div>

              <div>
                <label className={labelClass}>Description & Scope</label>
                <textarea
                  name="description"
                  rows={4}
                  className={`${inputClass} resize-none`}
                  value={form.description}
                  onChange={handleChange}
                  placeholder="Outline the main purpose, agenda highlights, and expectations..."
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Date & Time *</label>
                  <input
                    type="datetime-local"
                    name="date"
                    required
                    className={inputClass}
                    value={form.date}
                    onChange={handleChange}
                  />
                </div>
                <div>
                  <label className={labelClass}>Venue Location</label>
                  <input
                    type="text"
                    name="venue"
                    className={inputClass}
                    value={form.venue}
                    onChange={handleChange}
                    placeholder="e.g. Main Auditorium Hall A"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelClass}>Total Budget (₹)</label>
                  <input
                    type="number"
                    name="budget"
                    min="0"
                    step="100"
                    className={inputClass}
                    value={form.budget}
                    onChange={handleChange}
                  />
                </div>
                <div>
                  <label className={labelClass}>Expected Attendance</label>
                  <input
                    type="number"
                    name="expected_attendance"
                    min="0"
                    className={inputClass}
                    value={form.expected_attendance}
                    onChange={handleChange}
                  />
                </div>
              </div>

              {isEdit && (
                <div>
                  <label className={labelClass}>Lifecycle Status</label>
                  <div className="relative">
                    <select
                      name="status"
                      className={`${inputClass} appearance-none pr-10`}
                      value={form.status}
                      onChange={handleChange}
                    >
                      <option value="DRAFT">Draft</option>
                      <option value="PUBLISHED">Published</option>
                      <option value="COMPLETED">Completed</option>
                      <option value="CANCELLED">Cancelled</option>
                    </select>
                    <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                  </div>
                </div>
              )}

              <div className="flex items-center gap-3 pt-4 border-t border-slate-800">
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl px-6 py-2.5 text-sm shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
                >
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  {saving ? 'Saving...' : isEdit ? 'Update Event' : 'Create Event'}
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/events')}
                  className="text-slate-400 hover:text-white font-medium text-sm px-4 py-2.5 rounded-xl hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
