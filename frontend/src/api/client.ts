import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
import type {
  AuthTokens,
  Clan,
  CurrentWarOverview,
  Member,
  MemberWarHistoryResponse,
  RosterAction,
  WarPass,
} from '../types/domain';

const API_BASE = import.meta.env.VITE_API_URL || '';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: attach JWT access token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('cr_access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 and refresh token
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else if (token) {
      promise.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (originalRequest.url?.includes('/api/token/')) {
        return Promise.reject(error);
      }

      const refreshToken = localStorage.getItem('cr_refresh_token');
      if (!refreshToken) {
        localStorage.removeItem('cr_access_token');
        localStorage.removeItem('cr_refresh_token');
        window.dispatchEvent(new Event('cr-auth-expired'));
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { data } = await axios.post<AuthTokens>(`${API_BASE}/api/token/refresh/`, {
          refresh: refreshToken,
        });

        localStorage.setItem('cr_access_token', data.access);
        if (data.refresh) {
          localStorage.setItem('cr_refresh_token', data.refresh);
        }

        processQueue(null, data.access);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${data.access}`;
        }
        return apiClient(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        localStorage.removeItem('cr_access_token');
        localStorage.removeItem('cr_refresh_token');
        window.dispatchEvent(new Event('cr-auth-expired'));
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Endpoints
export const clansApi = {
  list: async () => {
    const { data } = await apiClient.get<Clan[]>('/api/clans/');
    return data;
  },
  get: async (tag: string) => {
    const encodedTag = encodeURIComponent(tag);
    const { data } = await apiClient.get<Clan>(`/api/clans/${encodedTag}/`);
    return data;
  },
  getMembers: async (tag: string) => {
    const encodedTag = encodeURIComponent(tag);
    const { data } = await apiClient.get<Member[]>(`/api/clans/${encodedTag}/members/`);
    return data;
  },
  sync: async (tag: string) => {
    const encodedTag = encodeURIComponent(tag);
    const { data } = await apiClient.post<{ message: string; clan: Clan }>(`/api/clans/${encodedTag}/sync/`);
    return data;
  },
  getCurrentWar: async (tag: string) => {
    const encodedTag = encodeURIComponent(tag);
    const { data } = await apiClient.get<CurrentWarOverview>(`/api/clans/${encodedTag}/current-war/`);
    return data;
  },
};

export const warPassesApi = {
  list: async (clanTag?: string) => {
    const params = clanTag ? { clan: clanTag } : {};
    const { data } = await apiClient.get<WarPass[]>('/api/war-passes/', { params });
    return data;
  },
  create: async (payload: { member: string; reason: string; start_date: string; end_date: string }) => {
    const { data } = await apiClient.post<WarPass>('/api/war-passes/', payload);
    return data;
  },
  delete: async (id: number) => {
    await apiClient.delete(`/api/war-passes/${id}/`);
  },
};

export const rosterActionsApi = {
  list: async (params?: { clan?: string; status?: string }) => {
    const { data } = await apiClient.get<RosterAction[]>('/api/roster-actions/', { params });
    return data;
  },
  execute: async (id: number) => {
    const { data } = await apiClient.post<{ message: string; action: RosterAction }>(`/api/roster-actions/${id}/execute/`);
    return data;
  },
  dismiss: async (id: number) => {
    const { data } = await apiClient.post<{ message: string; action: RosterAction }>(`/api/roster-actions/${id}/dismiss/`);
    return data;
  },
};

export const membersApi = {
  getWarHistory: async (tag: string) => {
    const encodedTag = encodeURIComponent(tag);
    const { data } = await apiClient.get<MemberWarHistoryResponse>(`/api/members/${encodedTag}/war-history/`);
    return data;
  },
};
