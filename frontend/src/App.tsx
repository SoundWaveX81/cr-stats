import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { Layout } from './components/layout/Layout';
import { LoginPage } from './pages/LoginPage';
import { RosterPage } from './pages/RosterPage';
import { CurrentWarPage } from './pages/CurrentWarPage';
import { GovernancePage } from './pages/GovernancePage';
import { WarPassesPage } from './pages/WarPassesPage';
import { NotFoundPage } from './pages/NotFoundPage';

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
          {/* Public Authentication Route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<RosterPage />} />
            <Route path="clans/:clanTag" element={<RosterPage />} />
            <Route path="war" element={<CurrentWarPage />} />
            <Route path="clans/:clanTag/war" element={<CurrentWarPage />} />
            <Route path="governance" element={<GovernancePage />} />
            <Route path="war-passes" element={<WarPassesPage />} />
          </Route>

          {/* 404 Route */}
          <Route path="/404" element={<NotFoundPage />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </ErrorBoundary>
  );
};

export default App;
