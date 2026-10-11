import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import { authApi } from '../api/client';
import type { AuthTokens, UserProfile } from '../types/domain';

const API_BASE = import.meta.env.VITE_API_URL || '';

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    try {
      const token = localStorage.getItem('cr_access_token');
      const saved = localStorage.getItem('cr_user');
      return token && saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const isAuthenticated = Boolean(user && localStorage.getItem('cr_access_token'));

  const logout = useCallback(() => {
    localStorage.removeItem('cr_access_token');
    localStorage.removeItem('cr_refresh_token');
    localStorage.removeItem('cr_user');
    setUser(null);
  }, []);

  const refreshProfile = useCallback(async () => {
    const token = localStorage.getItem('cr_access_token');
    if (!token) return;
    try {
      const profile = await authApi.getMe();
      setUser(profile);
      localStorage.setItem('cr_user', JSON.stringify(profile));
    } catch {
      // Handled by axios interceptor
    }
  }, []);

  useEffect(() => {
    // If token exists, refresh live profile on startup
    const token = localStorage.getItem('cr_access_token');
    if (token) {
      refreshProfile();
    }
  }, [refreshProfile]);

  useEffect(() => {
    const handleAuthExpired = () => {
      logout();
    };

    window.addEventListener('cr-auth-expired', handleAuthExpired);
    return () => {
      window.removeEventListener('cr-auth-expired', handleAuthExpired);
    };
  }, [logout]);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const { data } = await axios.post<AuthTokens & { user?: UserProfile }>(`${API_BASE}/api/token/`, {
        username,
        password,
      });

      localStorage.setItem('cr_access_token', data.access);
      localStorage.setItem('cr_refresh_token', data.refresh);

      let profile: UserProfile = data.user || { username, is_superuser: false };
      try {
        profile = await authApi.getMe();
      } catch {
        // Fallback to data.user or minimal profile
      }

      localStorage.setItem('cr_user', JSON.stringify(profile));
      setUser(profile);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
};


// oxlint-disable-next-line react/only-export-components
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
