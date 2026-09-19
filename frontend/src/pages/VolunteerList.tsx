import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Users, Activity, CheckCircle, XCircle } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import api from '../lib/axios';

interface UserInfo {
  id: number;
  full_name: string;
  email: string;
}

interface Volunteer {
  id: number;
  user_id: int;
  skills: string;
  availability: string;
  status: string;
  active_task_count: int;
  load_indicator: string;
  user: UserInfo;
}

export default function VolunteerList() {
  const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  
  // Filters
  const [loadFilter, setLoadFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');

  useEffect(() => {
    api.get('/volunteers')
      .then(res => setVolunteers(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = volunteers.filter(v => {
    const matchesSearch = v.user?.full_name.toLowerCase().includes(search.toLowerCase()) || 
                          v.user?.email.toLowerCase().includes(search.toLowerCase()) ||
                          (v.skills && v.skills.toLowerCase().includes(search.toLowerCase()));
    const matchesLoad = loadFilter === 'ALL' || v.load_indicator === loadFilter;
    const matchesStatus = statusFilter === 'ALL' || v.status === statusFilter;
    
    return matchesSearch && matchesLoad && matchesStatus;
  });

  const getLoadBadge = (load: string) => {
    switch (load) {
      case 'LOW': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'MEDIUM': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'OVERLOADED': return 'bg-red-500/10 text-red-400 border-red-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  return (
    <DashboardLayout title="Volunteers">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search by name, email, or skill..."
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <select 
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500"
              value={loadFilter}
              onChange={e => setLoadFilter(e.target.value)}
            >
              <option value="ALL">All Loads</option>
              <option value="LOW">Low Load</option>
              <option value="MEDIUM">Medium Load</option>
              <option value="OVERLOADED">Overloaded</option>
            </select>
            <select 
              className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500"
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
            >
              <option value="ALL">All Status</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
            <Link
              to="/volunteers/new"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-lg transition-colors font-medium text-sm shrink-0"
            >
              <Plus className="w-4 h-4" /> Add Volunteer
            </Link>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500"></div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
              <Users className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">No volunteers found</h3>
            <p className="text-slate-400 max-w-sm">
              Adjust your filters or add a new volunteer to get started.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map(vol => (
              <Link
                key={vol.id}
                to={`/volunteers/${vol.id}`}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 transition-all hover:shadow-lg hover:shadow-slate-950/50 group block"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-slate-800 rounded-full flex items-center justify-center text-slate-300 font-medium">
                      {vol.user?.full_name?.charAt(0) || 'U'}
                    </div>
                    <div>
                      <h3 className="text-white font-medium group-hover:text-indigo-400 transition-colors">
                        {vol.user?.full_name}
                      </h3>
                      <p className="text-xs text-slate-500">{vol.user?.email}</p>
                    </div>
                  </div>
                  {vol.status === 'ACTIVE' ? (
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  ) : (
                    <XCircle className="w-4 h-4 text-slate-600" />
                  )}
                </div>

                <div className="flex flex-wrap gap-2 mb-4">
                  {vol.skills ? vol.skills.split(',').map((skill, i) => (
                    <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                      {skill.trim()}
                    </span>
                  )) : (
                    <span className="text-xs text-slate-600 italic">No skills listed</span>
                  )}
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-slate-800/50">
                  <div className="flex items-center gap-1.5 text-xs text-slate-400">
                    <Activity className="w-3.5 h-3.5" />
                    {vol.active_task_count} active tasks
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-1 rounded-full border uppercase tracking-wider ${getLoadBadge(vol.load_indicator)}`}>
                    {vol.load_indicator}
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
