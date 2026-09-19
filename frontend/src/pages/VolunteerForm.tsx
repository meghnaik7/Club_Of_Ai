import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, UserCheck, ChevronDown, Loader2 } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import api from '../lib/axios';

interface VolunteerFormData {
  user_id: number | '';
  skills: string;
  availability: string;
  status: string;
}

const defaultForm: VolunteerFormData = {
  user_id: '',
  skills: '',
  availability: '',
  status: 'ACTIVE',
};

interface UserSummary {
  id: number;
  email: string;
  full_name: string;
  role?: string;
}

export default function VolunteerForm() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const [form, setForm] = useState<VolunteerFormData>(defaultForm);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Fetch registered users for linking
    api.get('/auth/users')
      .then(res => setUsers(res.data))
      .catch(() => {
        // Fallback to current user if /users is not accessible
        api.get('/auth/me')
          .then(res => setUsers([res.data]))
          .catch(() => {});
      });

    if (isEdit) {
      setLoading(true);
      api.get(`/volunteers/${id}`)
        .then(res => {
          const v = res.data;
          setForm({
            user_id: v.user_id,
            skills: v.skills || '',
            availability: v.availability || '',
            status: v.status || 'ACTIVE',
          });
          if (v.user) {
            setUsers(prev => prev.some(u => u.id === v.user.id) ? prev : [...prev, v.user]);
          }
        })
        .catch(() => setError('Failed to load volunteer profile'))
        .finally(() => setLoading(false));
    }
  }, [id, isEdit]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isEdit && !form.user_id) {
      setError('Please select a user account to link to this volunteer profile.');
      return;
    }
    setSaving(true);
    setError('');

    try {
      if (isEdit) {
        await api.put(`/volunteers/${id}`, {
          skills: form.skills,
          availability: form.availability,
          status: form.status,
        });
      } else {
        await api.post('/volunteers', form);
      }
      navigate('/volunteers');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save volunteer profile');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const inputClass = "w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors placeholder:text-slate-600";
  const labelClass = "block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5";

  return (
    <DashboardLayout title={isEdit ? 'Edit Volunteer Profile' : 'Register New Volunteer'}>
      <div className="max-w-2xl mx-auto space-y-6">
        <button
          onClick={() => navigate('/volunteers')}
          className="inline-flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors group"
        >
          <ArrowLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" /> Back to Volunteers
        </button>

        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
          </div>
        ) : (
          <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-xl">
            <div className="flex items-center gap-3 mb-6 pb-6 border-b border-slate-800">
              <div className="w-10 h-10 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                <UserCheck className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white tracking-tight">
                  {isEdit ? 'Update Volunteer Info' : 'New Volunteer Profile'}
                </h2>
                <p className="text-xs text-slate-400">
                  Manage skills, work availability, and operational status
                </p>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl text-sm mb-6">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {!isEdit && (
                <div>
                  <label className={labelClass}>Select Registered User Account *</label>
                  <div className="relative">
                    <select
                      name="user_id"
                      required
                      className={`${inputClass} appearance-none pr-10`}
                      value={form.user_id}
                      onChange={handleChange}
                    >
                      <option value="">-- Choose a user account --</option>
                      {users.map(u => (
                        <option key={u.id} value={u.id}>
                          {u.full_name} ({u.email}) {u.role ? `· ${u.role}` : ''}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1.5">
                    Volunteers are linked to registered user accounts in the ClubOps system.
                  </p>
                </div>
              )}

              <div>
                <label className={labelClass}>Skills & Capabilities</label>
                <input
                  type="text"
                  name="skills"
                  className={inputClass}
                  value={form.skills}
                  onChange={handleChange}
                  placeholder="e.g. Stage Setup, Audio/Visual, Graphic Design, Logistics, Photography"
                />
                <p className="text-[11px] text-slate-500 mt-1.5">
                  Comma-separated list used by AI task assignment.
                </p>
              </div>

              <div>
                <label className={labelClass}>Availability</label>
                <input
                  type="text"
                  name="availability"
                  className={inputClass}
                  value={form.availability}
                  onChange={handleChange}
                  placeholder="e.g. Weekends, Friday Afternoons, All Days after 5 PM"
                />
                <p className="text-[11px] text-slate-500 mt-1.5">
                  Specifies when this volunteer can be scheduled for event tasks.
                </p>
              </div>

              <div>
                <label className={labelClass}>Status</label>
                <div className="relative">
                  <select
                    name="status"
                    className={`${inputClass} appearance-none pr-10`}
                    value={form.status}
                    onChange={handleChange}
                  >
                    <option value="ACTIVE">Active (Available for task assignment)</option>
                    <option value="INACTIVE">Inactive (Temporarily unavailable)</option>
                  </select>
                  <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                </div>
              </div>

              <div className="flex items-center gap-3 pt-4 border-t border-slate-800">
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl px-6 py-2.5 text-sm shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
                >
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  {saving ? 'Saving...' : isEdit ? 'Update Volunteer' : 'Create Profile'}
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/volunteers')}
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
