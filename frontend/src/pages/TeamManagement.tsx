import React, { useEffect, useState, useCallback } from 'react';
import {
  Briefcase, Plus, Users, Trash2, CheckCircle2,
  AlertCircle, ChevronRight, Crown, RefreshCw
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import api from '../lib/axios';
import { useAuth } from '../context/AuthContext';

interface MemberUser {
  id: number;
  full_name: string;
  email: string;
}

interface TeamMember {
  id: number;
  team_id: number;
  user_id: number;
  role: 'TEAM_LEADER' | 'TEAM_MEMBER';
  joined_at?: string;
  user: MemberUser;
}

interface Team {
  id: number;
  name: string;
  description: string;
  member_count?: number;
  active_task_count?: number;
  leaders?: MemberUser[];
  members?: TeamMember[];
}

interface AvailableUser {
  id: number;
  full_name: string;
  email: string;
}

export default function TeamManagement() {
  const { isClubLeader, userTeams, refreshAuthz } = useAuth();
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [loading, setLoading] = useState(true);
  const [availableUsers, setAvailableUsers] = useState<AvailableUser[]>([]);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [showAssignLeaderModal, setShowAssignLeaderModal] = useState(false);

  // Forms
  const [newTeamName, setNewTeamName] = useState('');
  const [newTeamDesc, setNewTeamDesc] = useState('');
  const [selectedUserId, setSelectedUserId] = useState<number | ''>('');
  const [selectedMemberRole, setSelectedMemberRole] = useState<'TEAM_MEMBER' | 'TEAM_LEADER'>('TEAM_MEMBER');

  // Feedback alerts
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const showAlert = (type: 'success' | 'error', message: string) => {
    setAlert({ type, message });
    setTimeout(() => setAlert(null), 4500);
  };

  const fetchTeams = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/teams');
      setTeams(res.data);
      if (res.data.length > 0 && !selectedTeam) {
        // Load details for first team
        const firstTeamRes = await api.get(`/teams/${res.data[0].id}`);
        setSelectedTeam(firstTeamRes.data);
      } else if (selectedTeam) {
        const updatedSelected = await api.get(`/teams/${selectedTeam.id}`);
        setSelectedTeam(updatedSelected.data);
      }
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Failed to load teams');
    } finally {
      setLoading(false);
    }
  }, [selectedTeam]);

  const fetchAvailableUsers = async () => {
    try {
      // Volunteers endpoint returns users with profiles
      const res = await api.get('/volunteers');
      const users = res.data.map((v: any) => v.user).filter(Boolean);
      setAvailableUsers(users);
    } catch (err) {
      console.error('Failed to load available users', err);
    }
  };

  useEffect(() => {
    fetchTeams();
    fetchAvailableUsers();
  }, []);

  const handleSelectTeam = async (team: Team) => {
    try {
      const res = await api.get(`/teams/${team.id}`);
      setSelectedTeam(res.data);
    } catch (err: any) {
      showAlert('error', 'Failed to load team details');
    }
  };

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTeamName.trim()) return;
    try {
      const res = await api.post('/teams', {
        name: newTeamName.trim(),
        description: newTeamDesc.trim() || undefined,
      });
      showAlert('success', `Team '${res.data.name}' created successfully!`);
      setNewTeamName('');
      setNewTeamDesc('');
      setShowCreateModal(false);
      await fetchTeams();
      await refreshAuthz();
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Failed to create team');
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTeam || !selectedUserId) return;
    try {
      await api.post(`/teams/${selectedTeam.id}/members`, {
        user_id: Number(selectedUserId),
        role: selectedMemberRole,
      });
      showAlert('success', 'Team member added successfully!');
      setShowAddMemberModal(false);
      setSelectedUserId('');
      const updated = await api.get(`/teams/${selectedTeam.id}`);
      setSelectedTeam(updated.data);
      await fetchTeams();
      await refreshAuthz();
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Failed to add member');
    }
  };

  const handleAssignLeader = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTeam || !selectedUserId) return;
    try {
      await api.post(`/teams/${selectedTeam.id}/leaders`, {
        user_id: Number(selectedUserId),
      });
      showAlert('success', 'Team Leader assigned successfully!');
      setShowAssignLeaderModal(false);
      setSelectedUserId('');
      const updated = await api.get(`/teams/${selectedTeam.id}`);
      setSelectedTeam(updated.data);
      await fetchTeams();
      await refreshAuthz();
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Failed to assign team leader');
    }
  };

  const handleRemoveMember = async (userId: number, memberName: string) => {
    if (!selectedTeam) return;
    if (!confirm(`Are you sure you want to remove ${memberName} from ${selectedTeam.name}?`)) return;
    try {
      await api.delete(`/teams/${selectedTeam.id}/members/${userId}`);
      showAlert('success', `${memberName} removed from ${selectedTeam.name}`);
      const updated = await api.get(`/teams/${selectedTeam.id}`);
      setSelectedTeam(updated.data);
      await fetchTeams();
      await refreshAuthz();
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Failed to remove member');
    }
  };

  const handleDeleteTeam = async (teamId: number, teamName: string) => {
    if (!confirm(`Are you sure you want to delete '${teamName}'? This action cannot be undone.`)) return;
    try {
      await api.delete(`/teams/${teamId}`);
      showAlert('success', `Team '${teamName}' deleted.`);
      setSelectedTeam(null);
      await fetchTeams();
      await refreshAuthz();
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Failed to delete team');
    }
  };

  const isLeaderOfSelectedTeam = Boolean(
    selectedTeam && userTeams.some(t => t.id === selectedTeam.id && t.role === 'TEAM_LEADER')
  );
  const canManageSelectedTeam = isClubLeader || isLeaderOfSelectedTeam;

  return (
    <DashboardLayout title="Team Management">
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

        {/* Hierarchy Overview Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 p-6 rounded-2xl relative overflow-hidden shadow-lg">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Role-Based Access Control
                </span>
                <span className="text-xs text-slate-400">• Multi-Team Scoped</span>
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight">Hierarchical Team Structure</h2>
              <p className="text-sm text-slate-400 mt-1 max-w-2xl">
                Club Leader oversees the club. Team Leaders manage team tasks, volunteers, and member workflows.
                Team Members execute tasks within their assigned teams.
              </p>
            </div>
            {isClubLeader && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl shadow-md shadow-indigo-600/30 transition-all shrink-0"
              >
                <Plus className="w-4 h-4" />
                <span>Create New Team</span>
              </button>
            )}
          </div>
        </div>

        {/* Main Grid: Teams Navigation & Selected Team Details */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Team Cards / Selector */}
          <div className="lg:col-span-4 space-y-3">
            <div className="flex items-center justify-between px-1">
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Sub-Teams ({teams.length})</h3>
              <button onClick={fetchTeams} className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors">
                <RefreshCw className="w-3 h-3" />
                Refresh
              </button>
            </div>

            {loading && teams.length === 0 ? (
              <div className="p-8 text-center text-slate-500 bg-slate-900/50 rounded-2xl border border-slate-800">
                Loading teams...
              </div>
            ) : teams.length === 0 ? (
              <div className="p-8 text-center text-slate-500 bg-slate-900/50 rounded-2xl border border-slate-800">
                No teams created yet.
              </div>
            ) : (
              <div className="space-y-2.5">
                {teams.map((team) => {
                  const isSelected = selectedTeam?.id === team.id;
                  const isUserTeam = userTeams.some(t => t.id === team.id);
                  const userRoleInTeam = userTeams.find(t => t.id === team.id)?.role;

                  return (
                    <div
                      key={team.id}
                      onClick={() => handleSelectTeam(team)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-slate-900 border-indigo-500/50 shadow-md shadow-indigo-500/10'
                          : 'bg-slate-900/60 hover:bg-slate-900 border-slate-800/80 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <h4 className="text-base font-semibold text-white truncate">{team.name}</h4>
                            {isUserTeam && (
                              <span className="text-[10px] px-2 py-0.5 font-semibold rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                                {userRoleInTeam === 'TEAM_LEADER' ? 'Leader' : 'Member'}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">{team.description || 'No description provided'}</p>
                        </div>
                        <ChevronRight className={`w-4 h-4 shrink-0 transition-transform ${isSelected ? 'text-indigo-400 translate-x-0.5' : 'text-slate-600'}`} />
                      </div>

                      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-slate-800/60 text-xs text-slate-400">
                        <span className="flex items-center gap-1.5">
                          <Users className="w-3.5 h-3.5 text-slate-500" />
                          {team.member_count || 0} members
                        </span>
                        <span className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-slate-500" />
                          {team.active_task_count || 0} tasks
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right Column: Selected Team Workspace */}
          <div className="lg:col-span-8">
            {selectedTeam ? (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
                {/* Team Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                        <Briefcase className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-xl font-bold text-white">{selectedTeam.name}</h3>
                        <p className="text-xs text-slate-400 mt-0.5">{selectedTeam.description || 'Active club department'}</p>
                      </div>
                    </div>
                  </div>

                  {/* Actions Header */}
                  <div className="flex items-center gap-2">
                    {canManageSelectedTeam && (
                      <button
                        onClick={() => setShowAddMemberModal(true)}
                        className="inline-flex items-center gap-1.5 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add Member</span>
                      </button>
                    )}
                    {isClubLeader && (
                      <>
                        <button
                          onClick={() => setShowAssignLeaderModal(true)}
                          className="inline-flex items-center gap-1.5 px-3 py-2 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/30 text-xs font-semibold rounded-xl transition-colors"
                        >
                          <Crown className="w-3.5 h-3.5" />
                          <span>Assign Leader</span>
                        </button>
                        <button
                          onClick={() => handleDeleteTeam(selectedTeam.id, selectedTeam.name)}
                          className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-xl border border-transparent hover:border-red-500/20 transition-colors"
                          title="Delete Team"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Team Leaders Showcase */}
                <div>
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <Crown className="w-3.5 h-3.5 text-amber-400" />
                    Team Leadership
                  </h4>
                  {selectedTeam.leaders && selectedTeam.leaders.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {selectedTeam.leaders.map(leader => (
                        <div key={leader.id} className="p-3.5 bg-amber-500/5 border border-amber-500/20 rounded-xl flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-amber-500/20 text-amber-300 font-bold text-xs flex items-center justify-center shrink-0 border border-amber-500/30">
                            {leader.full_name?.charAt(0) || 'L'}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-semibold text-white truncate">{leader.full_name}</p>
                            <p className="text-xs text-amber-400/80 truncate">Team Leader • {leader.email}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 bg-slate-800/40 rounded-xl border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
                      <span>No Team Leader assigned yet. Club Leader manages this team directly.</span>
                      {isClubLeader && (
                        <button
                          onClick={() => setShowAssignLeaderModal(true)}
                          className="text-xs text-amber-400 hover:text-amber-300 font-semibold"
                        >
                          Assign Now &rarr;
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Team Members List */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                      <Users className="w-3.5 h-3.5 text-indigo-400" />
                      Team Members ({selectedTeam.members?.length || 0})
                    </h4>
                  </div>

                  {selectedTeam.members && selectedTeam.members.length > 0 ? (
                    <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
                      {selectedTeam.members.map(member => (
                        <div key={member.id} className="p-3.5 flex items-center justify-between gap-3 hover:bg-slate-800/30 transition-colors">
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="w-8 h-8 rounded-full bg-indigo-600/20 text-indigo-300 text-xs font-bold flex items-center justify-center shrink-0">
                              {member.user?.full_name?.charAt(0) || 'M'}
                            </div>
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-white truncate">{member.user?.full_name}</p>
                              <p className="text-xs text-slate-400 truncate">{member.user?.email}</p>
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            <span className={`text-[11px] px-2.5 py-1 font-semibold rounded-full border ${
                              member.role === 'TEAM_LEADER'
                                ? 'bg-amber-500/10 text-amber-300 border-amber-500/25'
                                : 'bg-slate-800 text-slate-300 border-slate-700'
                            }`}>
                              {member.role === 'TEAM_LEADER' ? 'Team Leader' : 'Team Member'}
                            </span>

                            {canManageSelectedTeam && (
                              <button
                                onClick={() => handleRemoveMember(member.user_id, member.user?.full_name || 'Member')}
                                className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                title="Remove member"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-6 text-center text-xs text-slate-500 bg-slate-950/30 rounded-xl border border-slate-800">
                      No members assigned to this team yet.
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-slate-800">
                Select a team from the left to view members and details.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modal: Create Team */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-indigo-400" />
              Create New Club Team
            </h3>
            <form onSubmit={handleCreateTeam} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Team Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. AWS Team, Sponsorship Team, Design Team"
                  value={newTeamName}
                  onChange={e => setNewTeamName(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Description</label>
                <textarea
                  rows={3}
                  placeholder="Team scope, responsibilities, and technical focus..."
                  value={newTeamDesc}
                  onChange={e => setNewTeamDesc(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow"
                >
                  Create Team
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Member */}
      {showAddMemberModal && selectedTeam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-400" />
              Add Member to {selectedTeam.name}
            </h3>
            <form onSubmit={handleAddMember} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Select User *</label>
                <select
                  required
                  value={selectedUserId}
                  onChange={e => setSelectedUserId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select a user...</option>
                  {availableUsers.map(u => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Role in Team</label>
                <select
                  value={selectedMemberRole}
                  onChange={e => setSelectedMemberRole(e.target.value as any)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="TEAM_MEMBER">Team Member (Task execution)</option>
                  <option value="TEAM_LEADER">Team Leader (Manage team tasks & members)</option>
                </select>
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddMemberModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow"
                >
                  Add to Team
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Assign Leader */}
      {showAssignLeaderModal && selectedTeam && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Crown className="w-5 h-5 text-amber-400" />
              Assign Leader for {selectedTeam.name}
            </h3>
            <p className="text-xs text-slate-400">
              Only the Club Leader can designate Team Leaders. Team Leaders have authority to create and assign tasks within their team.
            </p>
            <form onSubmit={handleAssignLeader} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Select User to be Team Leader *</label>
                <select
                  required
                  value={selectedUserId}
                  onChange={e => setSelectedUserId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select a user...</option>
                  {availableUsers.map(u => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email})
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAssignLeaderModal(false)}
                  className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold rounded-xl shadow"
                >
                  Confirm Leader
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
