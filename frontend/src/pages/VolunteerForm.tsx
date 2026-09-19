import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
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
    // For Phase 3, fetch current user as a fallback if users API doesn't exist
    api.get('/auth/me')
      .then(res => setUsers([res.data]))
      .catch(() => {});
      
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
        .catch(() => setError('Failed to load volunteer'))
        .finally(() => setLoading(false));
    }
  }, [id, isEdit]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    try {
      if (isEdit) {
        await api.put(`/volunteers/${id}`, {
          skills: form.skills,
          availability: form.availability,
          status: form.status
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

  const inputClass = "w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors";
  const labelClass = "block text-sm font-medium text-slate-300 mb-1.5";

  return (
    <DashboardLayout title={isEdit ? 'Edit Volunteer' : 'Add Volunteer'}>
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

            {!isEdit && (
              <div>
                <label className={labelClass}>Select User Account *</label>
                <select
                  name="user_id"
                  required
                  className={inputClass}
                  value={form.user_id}
                  onChange={handleChange}
                >
                  <option value="" disabled>-- Select a user --</option>
                  {users.map(u => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-2">
                  A volunteer profile must be linked to an existing user account.
                </p>
              </div>
            )}

            <div>
              <label className={labelClass}>Skills (comma separated)</label>
              <input
                type="text"
                name="skills"
                className={inputClass}
                value={form.skills}
                onChange={handleChange}
                placeholder="e.g. Photography, Logistics, Marketing"
              />
            </div>

            <div>
              <label className={labelClass}>Availability (comma separated)</label>
              <input
                type="text"
                name="availability"
                className={inputClass}
                value={form.availability}
                onChange={handleChange}
                placeholder="e.g. Weekends, Friday Afternoons"
              />
            </div>

            <div>
              <label className={labelClass}>Status</label>
              <select
                name="status"
                className={inputClass}
                value={form.status}
                onChange={handleChange}
              >
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </div>

            <div className="flex items-center gap-4 pt-4">
              <button
                type="submit"
                disabled={saving}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg px-6 py-2.5 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : isEdit ? 'Update Profile' : 'Create Profile'}
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
