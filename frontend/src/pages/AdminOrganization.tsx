import React, { useEffect, useState, useMemo } from 'react';
import {
  Network, Building2, Users, ShieldAlert, CheckCircle2, AlertCircle,
  Plus, Search, RefreshCw, ChevronDown, ChevronRight, UserPlus,
  Edit3, Trash2, Crown, UserCheck, ShieldCheck, Filter
} from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import api from '../lib/axios';
import { useAuth } from '../context/AuthContext';

interface TreeUser {
  id: number;
  full_name: string;
  email: string;
  role: string;
}

interface TreeSubTeam {
  id: number;
  name: string;
  description?: string;
  lead: TreeUser | null;
  volunteers: TreeUser[];
}

interface TreeClub {
  club_id: number;
  club_name: string;
  description?: string;
  structure_type: 'CASE_1_DIRECT_VOLUNTEERS' | 'CASE_2_SUBTEAMS';
  club_head: TreeUser | null;
  subteams: TreeSubTeam[];
  direct_volunteers: TreeUser[];
}

interface OrgTreeResponse {
  root: string;
  administrators: TreeUser[];
  clubs: TreeClub[];
  unassigned_users: TreeUser[];
  timestamp: string;
}

interface AdminUser {
  id: number;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
  club_id: number | null;
  club_name: string | null;
  subteam_id: number | null;
  subteam_name: string | null;
}

export default function AdminOrganization() {
  const { isAdmin, refreshAuthz } = useAuth();

  const [treeData, setTreeData] = useState<OrgTreeResponse | null>(null);
  const [allUsers, setAllUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [structureFilter, setStructureFilter] = useState<'ALL' | 'CASE_1' | 'CASE_2'>('ALL');
  const [collapsedClubs, setCollapsedClubs] = useState<Record<number, boolean>>({});

  // Alert State
  const [alert, setAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Modal State for Assigning User Role & Scope
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | ''>('');
  const [selectedClubId, setSelectedClubId] = useState<number | ''>('');
  const [selectedRole, setSelectedRole] = useState<'CLUB_HEAD' | 'SUBTEAM_LEAD' | 'VOLUNTEER'>('VOLUNTEER');
  const [selectedSubTeamId, setSelectedSubTeamId] = useState<number | ''>('');
  const [assignmentReason, setAssignmentReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const showAlert = (type: 'success' | 'error', message: string) => {
    setAlert({ type, message });
    setTimeout(() => setAlert(null), 5000);
  };

  const loadOrgData = async () => {
    try {
      setRefreshing(true);
      const [treeRes, usersRes] = await Promise.all([
        api.get('/admin/organization/tree'),
        api.get('/admin/users')
      ]);
      setTreeData(treeRes.data);
      setAllUsers(usersRes.data);
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Failed to load organization hierarchy.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadOrgData();
  }, []);

  const toggleClubCollapse = (clubId: number) => {
    setCollapsedClubs(prev => ({ ...prev, [clubId]: !prev[clubId] }));
  };

  // Open modal with presets
  const handleOpenAssignModal = (preselectedUser?: TreeUser, preselectedClubId?: number, preselectedRole?: 'CLUB_HEAD' | 'SUBTEAM_LEAD' | 'VOLUNTEER') => {
    if (preselectedUser) {
      setSelectedUserId(preselectedUser.id);
    } else {
      setSelectedUserId('');
    }

    if (preselectedClubId) {
      setSelectedClubId(preselectedClubId);
    } else if (treeData && treeData.clubs.length > 0) {
      setSelectedClubId(treeData.clubs[0].club_id);
    } else {
      setSelectedClubId('');
    }

    if (preselectedRole) {
      setSelectedRole(preselectedRole);
    } else {
      setSelectedRole('VOLUNTEER');
    }

    setSelectedSubTeamId('');
    setAssignmentReason('');
    setModalOpen(true);
  };

  // Submit Assignment
  const handleAssignmentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) {
      showAlert('error', 'Please select a user to assign.');
      return;
    }

    if (!selectedClubId) {
      showAlert('error', 'Please select a club.');
      return;
    }

    if (selectedRole === 'SUBTEAM_LEAD' && !selectedSubTeamId) {
      showAlert('error', 'SubTeam Lead must be assigned to a specific SubTeam.');
      return;
    }

    try {
      setIsSubmitting(true);
      const payload = {
        role: selectedRole,
        club_id: Number(selectedClubId),
        subteam_id: selectedSubTeamId ? Number(selectedSubTeamId) : null,
        reason: assignmentReason || undefined
      };

      const res = await api.post(`/admin/users/${selectedUserId}/assign-role`, payload);
      showAlert('success', res.data.message || 'User assignment updated successfully!');
      setModalOpen(false);
      await loadOrgData();
      await refreshAuthz();
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Assignment failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Remove organizational assignment
  const handleRemoveOrganization = async (targetUser: TreeUser) => {
    if (!window.confirm(`Are you sure you want to remove ${targetUser.full_name} from their club/team assignments?`)) {
      return;
    }

    try {
      const res = await api.delete(`/admin/users/${targetUser.id}/organization?reason=Admin+Removed`);
      showAlert('success', res.data.message || `${targetUser.full_name} removed from organization.`);
      await loadOrgData();
      await refreshAuthz();
    } catch (err: any) {
      showAlert('error', err?.response?.data?.detail || 'Failed to remove user.');
    }
  };

  // Filtered Clubs
  const filteredClubs = useMemo(() => {
    if (!treeData) return [];
    let list = treeData.clubs;

    if (structureFilter === 'CASE_1') {
      list = list.filter(c => c.structure_type === 'CASE_1_DIRECT_VOLUNTEERS');
    } else if (structureFilter === 'CASE_2') {
      list = list.filter(c => c.structure_type === 'CASE_2_SUBTEAMS');
    }

    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();

    return list.filter(c => {
      const matchesClub = c.club_name.toLowerCase().includes(q) || (c.description || '').toLowerCase().includes(q);
      const matchesHead = c.club_head && (c.club_head.full_name.toLowerCase().includes(q) || c.club_head.email.toLowerCase().includes(q));
      const matchesDirect = c.direct_volunteers.some(v => v.full_name.toLowerCase().includes(q) || v.email.toLowerCase().includes(q));
      const matchesSubteams = c.subteams.some(s =>
        s.name.toLowerCase().includes(q) ||
        (s.lead && (s.lead.full_name.toLowerCase().includes(q) || s.lead.email.toLowerCase().includes(q))) ||
        s.volunteers.some(v => v.full_name.toLowerCase().includes(q) || v.email.toLowerCase().includes(q))
      );
      return matchesClub || matchesHead || matchesDirect || matchesSubteams;
    });
  }, [treeData, structureFilter, searchQuery]);

  // SubTeams for modal dropdown
  const availableSubTeams = useMemo(() => {
    if (!treeData || !selectedClubId) return [];
    const club = treeData.clubs.find(c => c.club_id === Number(selectedClubId));
    return club ? club.subteams : [];
  }, [treeData, selectedClubId]);

  // Overall Stats
  const stats = useMemo(() => {
    if (!treeData) return { clubsCount: 0, subteamsCount: 0, leadsCount: 0, volunteersCount: 0, unassignedCount: 0 };
    let subteamsCount = 0;
    let leadsCount = 0;
    let volunteersCount = 0;

    treeData.clubs.forEach(c => {
      if (c.club_head) leadsCount++;
      volunteersCount += c.direct_volunteers.length;
      c.subteams.forEach(s => {
        subteamsCount++;
        if (s.lead) leadsCount++;
        volunteersCount += s.volunteers.length;
      });
    });

    return {
      clubsCount: treeData.clubs.length,
      subteamsCount,
      leadsCount,
      volunteersCount,
      unassignedCount: treeData.unassigned_users.length
    };
  }, [treeData]);

  if (!isAdmin) {
    return (
      <DashboardLayout title="Access Denied">
        <div className="p-8 max-w-xl mx-auto text-center">
          <div className="w-16 h-16 bg-rose-500/20 text-rose-400 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-rose-500/30">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Administrator Access Required</h2>
          <p className="text-slate-400 text-sm">
            Only System Administrators have privileges to view and configure the system-wide organizational hierarchy.
          </p>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Organization Hierarchy & RBAC">
      <div className="p-6 max-w-7xl mx-auto space-y-6">

        {/* Header Title & Actions */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 bg-indigo-600/20 border border-indigo-500/30 rounded-xl flex items-center justify-center text-indigo-400">
                <Network className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white tracking-tight">Organization Hierarchy</h1>
                <p className="text-slate-400 text-xs mt-0.5">
                  Hierarchical Role-Based Access Control • Case 1 (Direct) & Case 2 (SubTeams)
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadOrgData}
              disabled={refreshing}
              className="px-3.5 py-2 bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 rounded-xl text-xs font-medium border border-slate-700/60 transition-all flex items-center gap-2 shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => handleOpenAssignModal()}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium shadow-md shadow-indigo-600/30 transition-all flex items-center gap-2"
            >
              <UserPlus className="w-4 h-4" />
              Assign User Scope
            </button>
          </div>
        </div>

        {/* Alert Banner */}
        {alert && (
          <div className={`p-4 rounded-2xl border flex items-center gap-3 text-sm transition-all ${
            alert.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-500/15 border-rose-500/30 text-rose-300'
          }`}>
            {alert.type === 'success' ? <CheckCircle2 className="w-5 h-5 shrink-0" /> : <AlertCircle className="w-5 h-5 shrink-0" />}
            <span>{alert.message}</span>
          </div>
        )}

        {/* Stat Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-sm">
            <p className="text-slate-400 text-xs font-medium">Clubs</p>
            <p className="text-2xl font-bold text-white mt-1">{stats.clubsCount}</p>
            <span className="text-[10px] text-slate-500 mt-1 block">Active Organizations</span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-sm">
            <p className="text-slate-400 text-xs font-medium">SubTeams</p>
            <p className="text-2xl font-bold text-indigo-400 mt-1">{stats.subteamsCount}</p>
            <span className="text-[10px] text-slate-500 mt-1 block">Optional Teams Layer</span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-sm">
            <p className="text-slate-400 text-xs font-medium">Leadership</p>
            <p className="text-2xl font-bold text-amber-400 mt-1">{stats.leadsCount}</p>
            <span className="text-[10px] text-slate-500 mt-1 block">Heads & Leads</span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-sm">
            <p className="text-slate-400 text-xs font-medium">Volunteers</p>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{stats.volunteersCount}</p>
            <span className="text-[10px] text-slate-500 mt-1 block">SubTeam & Direct</span>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-sm col-span-2 md:col-span-1">
            <p className="text-slate-400 text-xs font-medium">Unassigned</p>
            <p className="text-2xl font-bold text-slate-300 mt-1">{stats.unassignedCount}</p>
            <span className="text-[10px] text-slate-500 mt-1 block">Awaiting Placement</span>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="bg-slate-900/60 border border-slate-800/80 p-3.5 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search club, team, user or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3.5 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
            />
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto justify-end">
            <span className="text-xs text-slate-400 flex items-center gap-1.5 font-medium">
              <Filter className="w-3.5 h-3.5" />
              Structure:
            </span>
            <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => setStructureFilter('ALL')}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  structureFilter === 'ALL' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All
              </button>
              <button
                onClick={() => setStructureFilter('CASE_1')}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  structureFilter === 'CASE_1' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Case 1 (Direct)
              </button>
              <button
                onClick={() => setStructureFilter('CASE_2')}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                  structureFilter === 'CASE_2' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Case 2 (SubTeams)
              </button>
            </div>
          </div>
        </div>

        {/* Tree Root: System Admin */}
        <div className="bg-gradient-to-r from-rose-950/40 via-slate-900 to-slate-900 border border-rose-500/30 rounded-2xl p-5 shadow-lg relative overflow-hidden">
          <div className="absolute right-0 top-0 bottom-0 w-32 bg-rose-500/5 blur-2xl pointer-events-none" />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-rose-500/20 border border-rose-500/40 text-rose-400 rounded-xl flex items-center justify-center font-bold text-sm shadow-sm">
                <Crown className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-white font-bold text-sm">System Administration</span>
                  <span className="px-2 py-0.5 text-[10px] font-semibold bg-rose-500/20 text-rose-300 rounded-md border border-rose-500/30">
                    SUPERUSER ROOT
                  </span>
                </div>
                <p className="text-slate-400 text-xs mt-0.5">
                  Full unrestricted authority across all clubs, teams, tasks, volunteers, AI actions, and audit logs.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {treeData?.administrators.map(admin => (
                <div key={admin.id} className="flex items-center gap-2 px-3 py-1.5 bg-slate-950/70 border border-slate-800 rounded-xl text-xs">
                  <div className="w-5 h-5 rounded-full bg-rose-600 text-white font-semibold text-[10px] flex items-center justify-center">
                    {admin.full_name.charAt(0)}
                  </div>
                  <span className="text-slate-200 font-medium">{admin.full_name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Hierarchy Clubs Display */}
        {loading ? (
          <div className="p-12 text-center text-slate-400">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-500" />
            <p className="text-sm">Loading organization structure...</p>
          </div>
        ) : filteredClubs.length === 0 ? (
          <div className="p-12 text-center bg-slate-900/50 border border-slate-800 rounded-2xl">
            <Building2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-300 font-medium text-sm">No Clubs Match Filter</p>
            <p className="text-slate-500 text-xs mt-1">Try resetting your search query or structure filter.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {filteredClubs.map(club => {
              const isCollapsed = collapsedClubs[club.club_id];

              return (
                <div
                  key={club.club_id}
                  className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-md transition-all hover:border-slate-700/80"
                >
                  {/* Club Header Bar */}
                  <div className="p-4 bg-slate-900/90 border-b border-slate-800/80 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => toggleClubCollapse(club.club_id)}
                        className="p-1 text-slate-400 hover:text-white rounded-lg transition-colors"
                      >
                        {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      <div className="w-8 h-8 bg-indigo-500/20 text-indigo-400 rounded-lg flex items-center justify-center border border-indigo-500/30">
                        <Building2 className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2.5">
                          <h2 className="text-base font-bold text-white">{club.club_name}</h2>
                          <span className={`px-2 py-0.5 text-[10px] font-semibold rounded-md ${
                            club.structure_type === 'CASE_1_DIRECT_VOLUNTEERS'
                              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                              : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          }`}>
                            {club.structure_type === 'CASE_1_DIRECT_VOLUNTEERS' ? 'Case 1: Direct Volunteers' : 'Case 2: SubTeams'}
                          </span>
                        </div>
                        {club.description && (
                          <p className="text-xs text-slate-400 mt-0.5">{club.description}</p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleOpenAssignModal(undefined, club.club_id, 'CLUB_HEAD')}
                        className="px-3 py-1.5 bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5"
                      >
                        <Crown className="w-3.5 h-3.5" />
                        {club.club_head ? 'Change Head' : 'Appoint Head'}
                      </button>
                      <button
                        onClick={() => handleOpenAssignModal(undefined, club.club_id, 'VOLUNTEER')}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-medium transition-all flex items-center gap-1.5"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        Add Member
                      </button>
                    </div>
                  </div>

                  {/* Club Content */}
                  {!isCollapsed && (
                    <div className="p-5 space-y-6">

                      {/* Club Head Node */}
                      <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-xl flex items-center justify-center font-bold text-xs">
                            <Crown className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold uppercase tracking-wider text-amber-400">Club Head</span>
                              {club.club_head ? (
                                <span className="text-xs text-slate-200 font-semibold">{club.club_head.full_name}</span>
                              ) : (
                                <span className="text-xs text-slate-500 italic">No Club Head Appointed</span>
                              )}
                            </div>
                            {club.club_head && (
                              <p className="text-xs text-slate-400 mt-0.5">{club.club_head.email}</p>
                            )}
                          </div>
                        </div>

                        {club.club_head && (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleOpenAssignModal(club.club_head!, club.club_id, 'CLUB_HEAD')}
                              className="p-1.5 text-slate-400 hover:text-amber-300 hover:bg-amber-500/10 rounded-lg transition-colors"
                              title="Edit Assignment"
                            >
                              <Edit3 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleRemoveOrganization(club.club_head!)}
                              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                              title="Remove Club Head"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Case 1: Direct Volunteers (No Subteam) */}
                      {club.direct_volunteers.length > 0 && (
                        <div className="space-y-3 pl-4 border-l-2 border-blue-500/30">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">
                                Direct Club Volunteers
                              </span>
                              <span className="px-2 py-0.2 text-[10px] bg-blue-500/20 text-blue-300 font-semibold rounded-full">
                                {club.direct_volunteers.length}
                              </span>
                              <span className="text-[11px] text-slate-500">(Case 1: No SubTeam Assigned)</span>
                            </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                            {club.direct_volunteers.map(vol => (
                              <div
                                key={vol.id}
                                className="bg-slate-950/40 border border-slate-800/80 p-3 rounded-xl flex items-center justify-between hover:border-slate-700 transition-colors"
                              >
                                <div className="flex items-center gap-2.5 min-w-0">
                                  <div className="w-7 h-7 rounded-full bg-blue-600/20 border border-blue-500/30 text-blue-300 font-semibold text-xs flex items-center justify-center shrink-0">
                                    {vol.full_name.charAt(0)}
                                  </div>
                                  <div className="min-w-0">
                                    <p className="text-xs font-medium text-white truncate">{vol.full_name}</p>
                                    <p className="text-[10px] text-slate-400 truncate">{vol.email}</p>
                                  </div>
                                </div>
                                <div className="flex items-center gap-1 shrink-0">
                                  <button
                                    onClick={() => handleOpenAssignModal(vol, club.club_id, 'VOLUNTEER')}
                                    className="p-1 text-slate-400 hover:text-indigo-300 rounded"
                                    title="Reassign / Place in Subteam"
                                  >
                                    <Edit3 className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() => handleRemoveOrganization(vol)}
                                    className="p-1 text-slate-400 hover:text-rose-400 rounded"
                                    title="Remove from Club"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Case 2: SubTeams Branch */}
                      {club.subteams.length > 0 && (
                        <div className="space-y-4 pl-4 border-l-2 border-emerald-500/30">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                                SubTeams & Leads
                              </span>
                              <span className="px-2 py-0.2 text-[10px] bg-emerald-500/20 text-emerald-300 font-semibold rounded-full">
                                {club.subteams.length}
                              </span>
                            </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {club.subteams.map(team => (
                              <div
                                key={team.id}
                                className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 space-y-3.5"
                              >
                                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                                  <div>
                                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">{team.name}</h3>
                                    {team.description && (
                                      <p className="text-[11px] text-slate-400 mt-0.5">{team.description}</p>
                                    )}
                                  </div>
                                  <button
                                    onClick={() => {
                                      setSelectedClubId(club.club_id);
                                      setSelectedSubTeamId(team.id);
                                      setSelectedRole('VOLUNTEER');
                                      setModalOpen(true);
                                    }}
                                    className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-[11px] font-medium transition-colors flex items-center gap-1"
                                  >
                                    <Plus className="w-3 h-3" />
                                    Add Volunteer
                                  </button>
                                </div>

                                {/* SubTeam Lead */}
                                <div className="bg-slate-900/90 border border-slate-800/80 p-2.5 rounded-lg flex items-center justify-between">
                                  <div className="flex items-center gap-2.5">
                                    <div className="w-6 h-6 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-md flex items-center justify-center font-bold text-[10px]">
                                      L
                                    </div>
                                    <div>
                                      <div className="flex items-center gap-1.5">
                                        <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">SubTeam Lead:</span>
                                        {team.lead ? (
                                          <span className="text-xs text-white font-medium">{team.lead.full_name}</span>
                                        ) : (
                                          <span className="text-xs text-slate-500 italic">No Lead Assigned</span>
                                        )}
                                      </div>
                                      {team.lead && (
                                        <p className="text-[10px] text-slate-400">{team.lead.email}</p>
                                      )}
                                    </div>
                                  </div>

                                  <button
                                    onClick={() => {
                                      setSelectedClubId(club.club_id);
                                      setSelectedSubTeamId(team.id);
                                      setSelectedRole('SUBTEAM_LEAD');
                                      if (team.lead) setSelectedUserId(team.lead.id);
                                      setModalOpen(true);
                                    }}
                                    className="p-1 text-slate-400 hover:text-emerald-300 rounded"
                                    title="Assign / Change SubTeam Lead"
                                  >
                                    <Edit3 className="w-3.5 h-3.5" />
                                  </button>
                                </div>

                                {/* SubTeam Volunteers List */}
                                <div className="space-y-1.5">
                                  <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block">
                                    Team Volunteers ({team.volunteers.length})
                                  </span>

                                  {team.volunteers.length === 0 ? (
                                    <p className="text-[11px] text-slate-500 italic py-1">No volunteers assigned to this subteam yet.</p>
                                  ) : (
                                    <div className="space-y-1 max-h-40 overflow-y-auto pr-1">
                                      {team.volunteers.map(vol => (
                                        <div
                                          key={vol.id}
                                          className="p-2 bg-slate-900/40 rounded-lg flex items-center justify-between text-xs"
                                        >
                                          <div className="flex items-center gap-2 min-w-0">
                                            <div className="w-5 h-5 rounded-full bg-slate-800 text-slate-300 text-[10px] flex items-center justify-center shrink-0">
                                              {vol.full_name.charAt(0)}
                                            </div>
                                            <span className="text-slate-200 truncate">{vol.full_name}</span>
                                          </div>
                                          <div className="flex items-center gap-1 shrink-0">
                                            <button
                                              onClick={() => handleOpenAssignModal(vol, club.club_id, 'VOLUNTEER')}
                                              className="p-1 text-slate-400 hover:text-indigo-300 rounded"
                                              title="Reassign Scope"
                                            >
                                              <Edit3 className="w-3 h-3" />
                                            </button>
                                            <button
                                              onClick={() => handleRemoveOrganization(vol)}
                                              className="p-1 text-slate-400 hover:text-rose-400 rounded"
                                              title="Remove from Team"
                                            >
                                              <Trash2 className="w-3 h-3" />
                                            </button>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Unassigned Users Card */}
        {treeData && treeData.unassigned_users.length > 0 && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4 text-slate-400" />
                <h3 className="text-sm font-bold text-white">Unassigned Users ({treeData.unassigned_users.length})</h3>
                <span className="text-xs text-slate-500">Users not yet assigned to any club or scope</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
              {treeData.unassigned_users.map(u => (
                <div
                  key={u.id}
                  className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl flex items-center justify-between"
                >
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-white truncate">{u.full_name}</p>
                    <p className="text-[10px] text-slate-500 truncate">{u.email}</p>
                  </div>
                  <button
                    onClick={() => handleOpenAssignModal(u)}
                    className="px-2.5 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-medium transition-colors flex items-center gap-1"
                  >
                    <UserPlus className="w-3 h-3" />
                    Assign
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* ─────────────────────────────────────────────────────────────
          ASSIGNMENT MODAL
         ───────────────────────────────────────────────────────────── */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
                  <UserCheck className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Assign Role & Scope</h3>
                  <p className="text-xs text-slate-400">Configure hierarchical placement</p>
                </div>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-white text-sm p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAssignmentSubmit} className="space-y-4">
              {/* Select User */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Select User *</label>
                <select
                  value={selectedUserId}
                  onChange={(e) => setSelectedUserId(Number(e.target.value))}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                >
                  <option value="">-- Choose User --</option>
                  {allUsers.map(u => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email}) - Current: {u.role} {u.club_name ? `in ${u.club_name}` : '(No Club)'}
                    </option>
                  ))}
                </select>
              </div>

              {/* Select Club */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Select Club *</label>
                <select
                  value={selectedClubId}
                  onChange={(e) => {
                    setSelectedClubId(Number(e.target.value));
                    setSelectedSubTeamId('');
                  }}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                >
                  <option value="">-- Choose Club --</option>
                  {treeData?.clubs.map(c => (
                    <option key={c.club_id} value={c.club_id}>
                      {c.club_name} ({c.structure_type === 'CASE_1_DIRECT_VOLUNTEERS' ? 'Direct Volunteers' : `${c.subteams.length} SubTeams`})
                    </option>
                  ))}
                </select>
              </div>

              {/* Select Role */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Select Role *</label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedRole('CLUB_HEAD')}
                    className={`p-2.5 rounded-xl border text-xs font-medium transition-all flex flex-col items-center gap-1 ${
                      selectedRole === 'CLUB_HEAD'
                        ? 'bg-amber-500/20 border-amber-500/40 text-amber-300 shadow-sm'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Crown className="w-4 h-4" />
                    <span>Club Head</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedRole('SUBTEAM_LEAD')}
                    className={`p-2.5 rounded-xl border text-xs font-medium transition-all flex flex-col items-center gap-1 ${
                      selectedRole === 'SUBTEAM_LEAD'
                        ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300 shadow-sm'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>SubTeam Lead</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSelectedRole('VOLUNTEER')}
                    className={`p-2.5 rounded-xl border text-xs font-medium transition-all flex flex-col items-center gap-1 ${
                      selectedRole === 'VOLUNTEER'
                        ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300 shadow-sm'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Users className="w-4 h-4" />
                    <span>Volunteer</span>
                  </button>
                </div>
              </div>

              {/* Conditional SubTeam Selection */}
              {selectedRole === 'SUBTEAM_LEAD' && (
                <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <label className="block text-xs font-semibold text-emerald-400">
                    Target SubTeam (Required for SubTeam Lead) *
                  </label>
                  {availableSubTeams.length === 0 ? (
                    <p className="text-xs text-rose-400">
                      This club currently has no subteams. Please create a team in Teams Management first.
                    </p>
                  ) : (
                    <select
                      value={selectedSubTeamId}
                      onChange={(e) => setSelectedSubTeamId(Number(e.target.value))}
                      required
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500/50"
                    >
                      <option value="">-- Choose SubTeam to Lead --</option>
                      {availableSubTeams.map(t => (
                        <option key={t.id} value={t.id}>
                          {t.name} {t.lead ? `(Current lead: ${t.lead.full_name})` : '(No lead)'}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              {selectedRole === 'VOLUNTEER' && (
                <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                  <label className="block text-xs font-semibold text-slate-300">
                    SubTeam Placement (Optional)
                  </label>
                  <select
                    value={selectedSubTeamId}
                    onChange={(e) => setSelectedSubTeamId(e.target.value ? Number(e.target.value) : '')}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500/50"
                  >
                    <option value="">Case 1: Direct Club Volunteer (No SubTeam)</option>
                    {availableSubTeams.map(t => (
                      <option key={t.id} value={t.id}>
                        Case 2: {t.name} ({t.volunteers.length} members)
                      </option>
                    ))}
                  </select>
                  <span className="text-[11px] text-slate-500 block">
                    Leave as Direct Club Volunteer for clubs with no subteams.
                  </span>
                </div>
              )}

              {selectedRole === 'CLUB_HEAD' && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/25 rounded-xl text-xs text-amber-300 flex items-start gap-2">
                  <Crown className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>
                    This user will become the authorized <strong>Club Head</strong> of this club. Any existing Club Head will be updated accordingly.
                  </span>
                </div>
              )}

              {/* Reason Input */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Reason / Justification (Audit Logged)</label>
                <input
                  type="text"
                  placeholder="e.g., Appointed by Council, Event leadership transfer..."
                  value={assignmentReason}
                  onChange={(e) => setAssignmentReason(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || (selectedRole === 'SUBTEAM_LEAD' && !selectedSubTeamId)}
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium shadow-md shadow-indigo-600/30 transition-all flex items-center gap-2 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Confirm Assignment
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </DashboardLayout>
  );
}
