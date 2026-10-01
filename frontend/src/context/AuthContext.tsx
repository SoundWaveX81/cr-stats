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
    const saved = localStorage.getItem('cr_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const isAuthenticated = Boolean(user && localStorage.getItem('cr_access_token'));

  const logout = useCallback(() => {
    localStorage.removeItem('cr_access_token');
    localStorage.removeItem('cr_refresh_token');
    localStorage.removeItem('cr_user');
    setUser(null);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('cr_access_token');
    const savedUser = localStorage.getItem('cr_user');
    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        setUser(null);
      }
    } else {
      setUser(null);
    }
    setIsLoading(false);

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

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
