import React, { useEffect, useState } from 'react';
import {
  ShieldCheck, ShieldAlert, Check, X, Plus, Trash2, Search,
  AlertCircle, CheckCircle2, User, Key, Layers
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import api from '../lib/axios';
import { useAuth } from '../context/AuthContext';

interface PermissionItem {
  id: number;
  key: string;
  description: string;
}

interface UserOverride {
  id: number;
  user_id: number;
  permission_id: number;
  permission_key: string;
  scope_type: string;
  scope_id?: number;
  effect: 'ALLOW' | 'DENY';
}

interface TeamItem {
  id: number;
  name: string;
}

interface UserItem {
  id: number;
  full_name: string;
  email: string;
}

export default function PermissionManagement() {
  const { isClubLeader } = useAuth();

  const [permissions, setPermissions] = useState<PermissionItem[]>([]);
  const [matrix, setMatrix] = useState<Record<string, string[]>>({});
  const [users, setUsers] = useState<UserItem[]>([]);
  const [teams, setTeams] = useState<TeamItem[]>([]);
  const [loading, setLoading] = useState(true);

  // User Overrides state
  const [selectedUser, setSelectedUser] = useState<UserItem | null>(null);
  const [userOverrides, setUserOverrides] = useState<UserOverride[]>([]);
  const [loadingOverrides, setLoadingOverrides] = useState(false);

  // New Override form
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [overrideKey, setOverrideKey] = useState('');
  const [overrideScopeType, setOverrideScopeType] = useState('GLOBAL');
  const [overrideScopeId, setOverrideScopeId] = useState<number | ''>('');
  const [overrideEffect, setOverrideEffect] = useState<'ALLOW' | 'DENY'>('ALLOW');

  // Search filter
  const [searchUser, setSearchUser] = useState('');
  const [activeTab, setActiveTab] = useState<'matrix' | 'overrides'>('matrix');

  // Alerts
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const showAlert = (type: 'success' | 'error', message: string) => {
    setAlert({ type, message });
    setTimeout(() => setAlert(null), 4500);
  };

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);
        const [permsRes, matrixRes, volunteersRes, teamsRes] = await Promise.all([
          api.get('/permissions'),
          api.get('/permissions/matrix'),
          api.get('/volunteers'),
          api.get('/teams')
        ]);
        setPermissions(permsRes.data);
        setMatrix(matrixRes.data);
        const userList = volunteersRes.data.map((v: any) => v.user).filter(Boolean);
        setUsers(userList);
        setTeams(teamsRes.data);
        if (userList.length > 0) {
          setSelectedUser(userList[0]);
        }
      } catch (err: any) {
        showAlert('error', err?.response?.data?.detail || 'Failed to load permissions');
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();
  }, []);

  const loadUserOverrides = async (userId: number) => {
    try {
      setLoadingOverrides(true);
      const res = await api.get(`/permissions/users/${userId}`);
      setUserOverrides(res.data);
    } catch (err: any) {
      showAlert('error', 'Failed to load user overrides');
    } finally {
      setLoadingOverrides(false);
    }
  };

  useEffect(() => {
    if (selectedUser) {
      loadUserOverrides(selectedUser.id);
    }
  }, [selectedUser]);

  const handleAddOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser || !overrideKey) return;

    try {
      await api.post(`/permissions/users/${selectedUser.id}`, {
        permission_key: overrideKey,
        scope_type: overrideScopeType,
        scope_id: overrideScopeId ? Number(overrideScopeId) : null,
        effect: overrideEffect,
      });

      showAlert('success', `Override ${overrideEffect} granted for ${overrideKey}`);
      setShowOverrideModal(false);
      setOverrideKey('');
      setOverrideScopeId('');
      await loadUserOverrides(selectedUser.id);
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Failed to save override');
    }
  };

  const handleDeleteOverride = async (overrideId: number) => {
    if (!selectedUser) return;
    try {
      await api.delete(`/permissions/users/${selectedUser.id}/${overrideId}`);
      showAlert('success', 'Override removed successfully');
      await loadUserOverrides(selectedUser.id);
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Failed to remove override');
    }
  };

  if (!isClubLeader) {
    return (
      <DashboardLayout title="Permissions">
        <div className="p-8 max-w-2xl mx-auto text-center space-y-4 bg-slate-900 border border-slate-800 rounded-2xl shadow-xl mt-12">
          <div className="w-12 h-12 bg-red-500/10 text-red-400 rounded-full flex items-center justify-center mx-auto border border-red-500/20">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-white">Access Denied</h2>
          <p className="text-sm text-slate-400">
            The Permissions & Overrides console is exclusively accessible by the <span className="text-indigo-400 font-semibold">Club Leader</span>.
            As a Team Leader or Member, you have team-scoped authority.
          </p>
        </div>
      </DashboardLayout>
    );
  }

  if (loading) {
    return (
      <DashboardLayout title="Permissions">
        <div className="p-12 text-center text-slate-500 bg-slate-900/50 rounded-2xl border border-slate-800 max-w-xl mx-auto mt-12">
          Loading permissions and role matrix...
        </div>
      </DashboardLayout>
    );
  }

  const filteredUsers = users.filter(u =>
    u.full_name.toLowerCase().includes(searchUser.toLowerCase()) ||
    u.email.toLowerCase().includes(searchUser.toLowerCase())
  );

  const roles = ['CLUB_LEADER', 'EVENT_COORDINATOR', 'TEAM_LEADER', 'TEAM_MEMBER'];

  return (
    <DashboardLayout title="Permissions & Overrides">
      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Alerts */}
        {alert && (
          <div className={`p-4 rounded-xl flex items-center gap-3 border ${
            alert.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-red-500/10 border-red-500/30 text-red-400'
          }`}>
            {alert.type === 'success' ? <CheckCircle2 className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
            <p className="text-sm font-medium">{alert.message}</p>
          </div>
        )}

        {/* Top Header */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5" />
                Club Leader Authority
              </span>
              <span className="text-xs text-slate-400">• Dynamic Permission Hierarchy</span>
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight">Authorization Matrix & Explicit Overrides</h2>
            <p className="text-sm text-slate-400 mt-1 max-w-3xl">
              Inspect default permissions across all club roles or assign user-specific <span className="text-emerald-400">ALLOW</span> / <span className="text-red-400">DENY</span> overrides for fine-grained scoping.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-slate-950/60 p-1.5 rounded-xl border border-slate-800 shrink-0">
            <button
              onClick={() => setActiveTab('matrix')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all ${
                activeTab === 'matrix' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              Role Matrix
            </button>
            <button
              onClick={() => setActiveTab('overrides')}
              className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-all ${
                activeTab === 'overrides' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              User Overrides
            </button>
          </div>
        </div>

        {/* TAB 1: Role Permissions Matrix */}
        {activeTab === 'matrix' && (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-white">Default Role Permissions Matrix</h3>
                <p className="text-xs text-slate-400 mt-0.5">Permissions granted automatically based on user role assignments.</p>
              </div>
              <span className="text-xs text-slate-500">{permissions.length} registered permissions</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/40 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    <th className="py-3.5 px-6">Permission Key</th>
                    <th className="py-3.5 px-6">Description</th>
                    {roles.map(r => (
                      <th key={r} className="py-3.5 px-4 text-center">
                        <span className={`px-2 py-1 rounded text-[10px] font-bold ${
                          r === 'CLUB_LEADER' ? 'text-amber-300 bg-amber-500/10' :
                          r === 'EVENT_COORDINATOR' ? 'text-violet-300 bg-violet-500/10' :
                          r === 'TEAM_LEADER' ? 'text-emerald-300 bg-emerald-500/10' :
                          'text-slate-300 bg-slate-800'
                        }`}>
                          {r.replace('_', ' ')}
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs">
                  {permissions.map((perm) => (
                    <tr key={perm.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 px-6 font-mono text-indigo-300 font-medium">
                        {perm.key}
                      </td>
                      <td className="py-3 px-6 text-slate-400">
                        {perm.description || '—'}
                      </td>
                      {roles.map(r => {
                        const hasPerm = r === 'CLUB_LEADER' || (matrix[r] && matrix[r].includes(perm.key));
                        return (
                          <td key={r} className="py-3 px-4 text-center">
                            {hasPerm ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-500/15 text-emerald-400">
                                <Check className="w-3.5 h-3.5" />
                              </span>
                            ) : (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-800/40 text-slate-600">
                                <X className="w-3 h-3" />
                              </span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 2: User Overrides */}
        {activeTab === 'overrides' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* User Selector Column */}
            <div className="lg:col-span-4 space-y-3">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-500" />
                <input
                  type="text"
                  placeholder="Filter users..."
                  value={searchUser}
                  onChange={e => setSearchUser(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
                {filteredUsers.map(u => {
                  const isSelected = selectedUser?.id === u.id;
                  return (
                    <div
                      key={u.id}
                      onClick={() => setSelectedUser(u)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-slate-900 border-indigo-500/50 shadow-md shadow-indigo-500/10'
                          : 'bg-slate-900/60 hover:bg-slate-900 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-indigo-600/20 text-indigo-300 font-bold text-xs flex items-center justify-center shrink-0">
                          {u.full_name?.charAt(0) || 'U'}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-white truncate">{u.full_name}</p>
                          <p className="text-xs text-slate-400 truncate">{u.email}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Overrides Management Workspace */}
            <div className="lg:col-span-8">
              {selectedUser ? (
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
                  {/* Selected User Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
                    <div>
                      <div className="flex items-center gap-2.5">
                        <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                          <User className="w-5 h-5" />
                        </div>
                        <div>
                          <h3 className="text-lg font-bold text-white">{selectedUser.full_name}</h3>
                          <p className="text-xs text-slate-400">{selectedUser.email}</p>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => setShowOverrideModal(true)}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Explicit Override</span>
                    </button>
                  </div>

                  {/* Active Overrides */}
                  <div>
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                      <Key className="w-3.5 h-3.5 text-indigo-400" />
                      Explicit Overrides ({userOverrides.length})
                    </h4>

                    {loadingOverrides ? (
                      <div className="p-8 text-center text-xs text-slate-500">Loading overrides...</div>
                    ) : userOverrides.length === 0 ? (
                      <div className="p-8 text-center bg-slate-950/40 rounded-xl border border-slate-800 text-xs text-slate-500">
                        No explicit permission overrides set for this user. They operate under standard role-based permissions.
                      </div>
                    ) : (
                      <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
                        {userOverrides.map((ov) => (
                          <div key={ov.id} className="p-4 flex items-center justify-between gap-4 hover:bg-slate-800/30 transition-colors">
                            <div className="space-y-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-mono text-xs font-semibold text-white">{ov.permission_key}</span>
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                  ov.effect === 'ALLOW'
                                    ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                                    : 'bg-red-500/15 text-red-400 border-red-500/30'
                                }`}>
                                  {ov.effect}
                                </span>
                              </div>
                              <p className="text-xs text-slate-400 flex items-center gap-2">
                                <Layers className="w-3 h-3 text-slate-500" />
                                Scope: <span className="text-slate-300 font-medium">{ov.scope_type}</span>
                                {ov.scope_id && <span>(ID #{ov.scope_id})</span>}
                              </p>
                            </div>

                            <button
                              onClick={() => handleDeleteOverride(ov.id)}
                              className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                              title="Delete override"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-slate-800">
                  Select a user from the left to manage their explicit permission overrides.
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Modal: Add Override */}
      {showOverrideModal && selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Key className="w-5 h-5 text-indigo-400" />
              Add Override for {selectedUser.full_name}
            </h3>
            <p className="text-xs text-slate-400">
              Explicit overrides take immediate precedence over role-based permissions.
            </p>

            <form onSubmit={handleAddOverride} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Permission Key *</label>
                <select
                  required
                  value={overrideKey}
                  onChange={e => setOverrideKey(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                >
                  <option value="">Select a permission...</option>
                  {permissions.map(p => (
                    <option key={p.id} value={p.key}>
                      {p.key} ({p.description})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Effect *</label>
                  <select
                    value={overrideEffect}
                    onChange={e => setOverrideEffect(e.target.value as any)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-semibold"
                  >
                    <option value="ALLOW">ALLOW (Grant)</option>
                    <option value="DENY">DENY (Explicit block)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Scope Type *</label>
                  <select
                    value={overrideScopeType}
                    onChange={e => setOverrideScopeType(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="GLOBAL">GLOBAL</option>
                    <option value="TEAM">TEAM</option>
                    <option value="EVENT">EVENT</option>
                  </select>
                </div>
              </div>

              {overrideScopeType === 'TEAM' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Target Team</label>
                  <select
                    value={overrideScopeId}
                    onChange={e => setOverrideScopeId(e.target.value ? Number(e.target.value) : '')}
                    className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="">Select target team...</option>
                    {teams.map(t => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowOverrideModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow"
                >
                  Save Override
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
