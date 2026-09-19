import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../lib/axios';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: string;
}

export interface UserTeamSummary {
  id: number;
  name: string;
  role: string;
}

export interface UserEventSummary {
  event_id: number;
  role: string;
}

export interface UserAuthzSummary {
  user_id: number;
  full_name: string;
  email: string;
  is_club_leader: boolean;
  club_role: string | null;
  teams: UserTeamSummary[];
  event_roles: UserEventSummary[];
  permissions: string[];
}

interface AuthContextType {
  user: User | null;
  authz: UserAuthzSummary | null;
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
  loading: boolean;
  can: (permissionKey: string, scopeType?: string, scopeId?: number) => boolean;
  isClubLeader: boolean;
  userTeams: UserTeamSummary[];
  refreshAuthz: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [authz, setAuthz] = useState<UserAuthzSummary | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  const fetchAuthData = useCallback(async () => {
    if (!token) {
      setUser(null);
      setAuthz(null);
      setLoading(false);
      return;
    }

    try {
      const [userRes, summaryRes] = await Promise.all([
        api.get('/auth/me'),
        api.get('/auth/me/summary').catch(() => null)
      ]);
      setUser(userRes.data);
      if (summaryRes && summaryRes.data) {
        setAuthz(summaryRes.data);
      }
    } catch (error) {
      console.error("Failed to fetch user auth profile", error);
      logout();
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchAuthData();
  }, [fetchAuthData]);

  const login = (newToken: string) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setAuthz(null);
  };

  const refreshAuthz = async () => {
    if (token) {
      try {
        const summaryRes = await api.get('/auth/me/summary');
        if (summaryRes.data) {
          setAuthz(summaryRes.data);
        }
      } catch (err) {
        console.error("Failed to refresh authz profile", err);
      }
    }
  };

  const can = useCallback((permissionKey: string, scopeType?: string, scopeId?: number): boolean => {
    if (!authz) return false;
    if (authz.is_club_leader) return true;

    // Check scope if team is specified
    if (scopeType === 'TEAM' && scopeId) {
      const userTeam = authz.teams.find(t => t.id === scopeId);
      if (!userTeam) return false;
      if (userTeam.role === 'TEAM_LEADER') {
        const leaderDisallowed = ['team.delete', 'team.create', 'team.leader.assign', 'team.leader.remove', 'club.manage'];
        if (leaderDisallowed.includes(permissionKey)) return false;
        return true;
      }
      if (userTeam.role === 'TEAM_MEMBER') {
        const memberAllowed = ['task.view', 'task.status.update', 'task.comment.create', 'team.view', 'team.member.view'];
        return memberAllowed.includes(permissionKey);
      }
      return false;
    }

    // Default permission list check
    return authz.permissions.includes(permissionKey);
  }, [authz]);

  const isClubLeader = Boolean(authz?.is_club_leader);
  const userTeams = authz?.teams || [];

  return (
    <AuthContext.Provider value={{
      user,
      authz,
      token,
      login,
      logout,
      loading,
      can,
      isClubLeader,
      userTeams,
      refreshAuthz
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
