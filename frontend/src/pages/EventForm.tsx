import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import api from '../lib/axios';

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
    if (isEdit) {
      setLoading(true);
      api.get(`/events/${id}`)
        .then(res => {
          const e = res.data;
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
    setSaving(true);
    setError('');

    const payload = {
      ...form,
      date: new Date(form.date).toISOString(),
      budget: Number(form.budget),
      expected_attendance: Number(form.expected_attendance),
    };

    try {
      if (isEdit) {
        await api.put(`/events/${id}`, payload);
      } else {
        await api.post('/events', payload);
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

  const inputClass = "w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors";
  const labelClass = "block text-sm font-medium text-slate-300 mb-1.5";

  return (
    <DashboardLayout title={isEdit ? 'Edit Event' : 'Create Event'}>
      <div className="max-w-2xl mx-auto">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-2xl p-8 space-y-6">
            {error && (
              <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label className={labelClass}>Event Name *</label>
              <input
                type="text"
                name="title"
                required
                className={inputClass}
                value={form.title}
                onChange={handleChange}
                placeholder="e.g. Annual Tech Fest 2026"
              />
            </div>

            <div>
              <label className={labelClass}>Description</label>
              <textarea
                name="description"
                rows={4}
                className={inputClass}
                value={form.description}
                onChange={handleChange}
                placeholder="Describe the event..."
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className={labelClass}>Event Date *</label>
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
                <label className={labelClass}>Venue</label>
                <input
                  type="text"
                  name="venue"
                  className={inputClass}
                  value={form.venue}
                  onChange={handleChange}
                  placeholder="e.g. Main Auditorium"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div>
                <label className={labelClass}>Budget (₹)</label>
                <input
                  type="number"
                  name="budget"
                  min="0"
                  step="0.01"
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
                <label className={labelClass}>Status</label>
                <select
                  name="status"
                  className={inputClass}
                  value={form.status}
                  onChange={handleChange}
                >
                  <option value="DRAFT">Draft</option>
                  <option value="PUBLISHED">Published</option>
                  <option value="CANCELLED">Cancelled</option>
                  <option value="COMPLETED">Completed</option>
                </select>
              </div>
            )}

            <div className="flex items-center gap-4 pt-4">
              <button
                type="submit"
                disabled={saving}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg px-6 py-2.5 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : isEdit ? 'Update Event' : 'Create Event'}
              </button>
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="text-slate-400 hover:text-white font-medium text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </DashboardLayout>
  );
}
