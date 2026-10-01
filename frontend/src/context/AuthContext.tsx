import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import axios from 'axios';
import type { AuthTokens, UserProfile } from '../types/domain';

const API_BASE = import.meta.env.VITE_API_URL || '';

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
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
  const [isLoading] = useState<boolean>(false);

  const isAuthenticated = Boolean(user && localStorage.getItem('cr_access_token'));

  const logout = useCallback(() => {
    localStorage.removeItem('cr_access_token');
    localStorage.removeItem('cr_refresh_token');
    localStorage.removeItem('cr_user');
    setUser(null);
  }, []);

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
    const { data } = await axios.post<AuthTokens>(`${API_BASE}/api/token/`, {
      username,
      password,
    });

    localStorage.setItem('cr_access_token', data.access);
    localStorage.setItem('cr_refresh_token', data.refresh);

    const profile: UserProfile = { username };
    localStorage.setItem('cr_user', JSON.stringify(profile));
    setUser(profile);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
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
