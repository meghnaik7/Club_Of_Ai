import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Users, Activity, CheckCircle, XCircle, ChevronDown, Mail } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import VolunteersService from '../services/volunteers.service';
import type { Volunteer } from '../services/volunteers.service';

export default function VolunteerList() {
  const [volunteers, setVolunteers] = useState<Volunteer[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  
  // Filters
  const [loadFilter, setLoadFilter] = useState('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');

  useEffect(() => {
    VolunteersService.list()
      .then(setVolunteers)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = volunteers.filter(v => {
    const name = v.user?.full_name || '';
    const email = v.user?.email || '';
    const skills = v.skills || '';
    const matchesSearch = name.toLowerCase().includes(search.toLowerCase()) || 
                          email.toLowerCase().includes(search.toLowerCase()) ||
                          skills.toLowerCase().includes(search.toLowerCase());
    const matchesLoad = loadFilter === 'ALL' || v.load_indicator === loadFilter;
    const matchesStatus = statusFilter === 'ALL' || v.status === statusFilter;
    
    return matchesSearch && matchesLoad && matchesStatus;
  });

  const getLoadBadge = (load?: string) => {
    switch (load) {
      case 'LOW': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'MEDIUM': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'OVERLOADED': return 'bg-red-500/10 text-red-400 border-red-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  const activeCount = volunteers.filter(v => v.status === 'ACTIVE').length;
  const overloadedCount = volunteers.filter(v => v.load_indicator === 'OVERLOADED').length;

  return (
    <DashboardLayout title="Volunteers Directory">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Summary Stats Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Total Volunteers</span>
            <p className="text-2xl font-black text-white mt-1">{volunteers.length}</p>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">Active</span>
            <p className="text-2xl font-black text-white mt-1">{activeCount}</p>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-400">Balanced Load</span>
            <p className="text-2xl font-black text-white mt-1">
              {volunteers.filter(v => v.load_indicator === 'LOW' || v.load_indicator === 'MEDIUM').length}
            </p>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-red-400">Overloaded</span>
            <p className="text-2xl font-black text-white mt-1">{overloadedCount}</p>
          </div>
        </div>

        {/* Action & Filters Bar */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search by volunteer name, email, or skill..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <div className="relative">
              <select 
                className="bg-slate-900 border border-slate-800 rounded-xl pl-3 pr-8 py-2.5 text-white text-xs sm:text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                value={loadFilter}
                onChange={e => setLoadFilter(e.target.value)}
              >
                <option value="ALL">All Workloads</option>
                <option value="LOW">Low Load</option>
                <option value="MEDIUM">Medium Load</option>
                <option value="OVERLOADED">Overloaded</option>
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
            </div>

            <div className="relative">
              <select 
                className="bg-slate-900 border border-slate-800 rounded-xl pl-3 pr-8 py-2.5 text-white text-xs sm:text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
              >
                <option value="ALL">All Statuses</option>
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
            </div>

            <Link
              to="/volunteers/new"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl transition-all font-semibold text-xs sm:text-sm shadow-lg shadow-indigo-600/30 shrink-0"
            >
              <Plus className="w-4 h-4" /> Add Volunteer
            </Link>
          </div>
        </div>

        {/* Volunteers Grid */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-12 text-center flex flex-col items-center justify-center">
            <div className="w-16 h-16 bg-slate-800/80 rounded-2xl flex items-center justify-center mb-4 text-slate-500">
              <Users className="w-8 h-8" />
            </div>
            <h3 className="text-base font-bold text-white mb-1">
              {search || loadFilter !== 'ALL' || statusFilter !== 'ALL' ? 'No volunteers match your filters' : 'No volunteers registered yet'}
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mb-6">
              {search ? 'Try clearing search terms or resetting filters.' : 'Add your club members to start assigning event tasks.'}
            </p>
            <Link
              to="/volunteers/new"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold shadow-lg shadow-indigo-600/30"
            >
              <Plus className="w-4 h-4" /> Add Volunteer
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map(vol => (
              <Link
                key={vol.id}
                to={`/volunteers/${vol.id}`}
                className="bg-slate-900/80 border border-slate-800/90 hover:border-slate-700 rounded-3xl p-6 transition-all hover:shadow-xl hover:shadow-slate-950/60 group block relative overflow-hidden"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-3.5">
                    <div className="w-12 h-12 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-2xl flex items-center justify-center text-white font-black text-base shadow-md">
                      {vol.user?.full_name?.charAt(0) || 'U'}
                    </div>
                    <div>
                      <h3 className="text-white font-bold group-hover:text-indigo-300 transition-colors">
                        {vol.user?.full_name}
                      </h3>
                      <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                        <Mail className="w-3 h-3 text-slate-500" />
                        {vol.user?.email}
                      </p>
                    </div>
                  </div>
                  {vol.status === 'ACTIVE' ? (
                    <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                      <CheckCircle className="w-3 h-3" /> Active
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[11px] font-semibold text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
                      <XCircle className="w-3 h-3" /> Inactive
                    </span>
                  )}
                </div>

                {/* Skills tags */}
                <div className="flex flex-wrap gap-1.5 mb-5 min-h-[32px]">
                  {vol.skills ? vol.skills.split(',').map((skill, i) => (
                    <span key={i} className="text-[11px] font-medium px-2.5 py-0.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-slate-300">
                      {skill.trim()}
                    </span>
                  )) : (
                    <span className="text-xs text-slate-600 italic">No skills listed</span>
                  )}
                </div>

                {/* Footer metrics */}
                <div className="flex items-center justify-between pt-4 border-t border-slate-800/80">
                  <div className="flex items-center gap-1.5 text-xs text-slate-400">
                    <Activity className="w-3.5 h-3.5 text-indigo-400" />
                    <span>{vol.active_task_count || 0} active tasks</span>
                  </div>
                  <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border uppercase tracking-wider ${getLoadBadge(vol.load_indicator)}`}>
                    Load: {vol.load_indicator || 'LOW'}
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
