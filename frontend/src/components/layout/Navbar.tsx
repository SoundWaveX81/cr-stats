import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Shield, Users, Swords, Award, Ticket, LogOut } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Navbar: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
      isActive
        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30 shadow-sm'
        : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
    }`;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand / Logo */}
        <div className="flex items-center gap-6">
          <NavLink to="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-600 to-amber-400 flex items-center justify-center shadow-lg shadow-amber-500/20 group-hover:scale-105 transition-transform">
              <Shield className="w-5 h-5 text-slate-950" />
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-amber-400 via-amber-200 to-amber-500 bg-clip-text text-transparent">
                CR Total
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                Gobernanza
              </span>
            </div>
          </NavLink>

          {/* Main Navigation */}
          {isAuthenticated && (
            <nav className="hidden md:flex items-center gap-2">
              <NavLink to="/" end className={navLinkClasses}>
                <Users className="w-4 h-4" />
                Roster del Clan
              </NavLink>
              <NavLink to="/war" className={navLinkClasses}>
                <Swords className="w-4 h-4" />
                Guerra Actual
              </NavLink>
              <NavLink to="/governance" className={navLinkClasses}>
                <Award className="w-4 h-4" />
                Acciones de Roster
              </NavLink>
              <NavLink to="/war-passes" className={navLinkClasses}>
                <Ticket className="w-4 h-4" />
                Pases de Guerra
              </NavLink>
            </nav>
          )}
        </div>

        {/* User Session */}
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex flex-col text-right">
                <span className="text-xs text-slate-400 font-medium">Líder conectado</span>
                <span className="text-sm font-semibold text-slate-200">{user?.username}</span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-all"
                title="Cerrar Sesión"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Salir</span>
              </button>
            </div>
          ) : (
            <NavLink
              to="/login"
              className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-amber-500 text-slate-950 hover:bg-amber-400 transition-colors shadow-md shadow-amber-500/10"
            >
              Iniciar Sesión
            </NavLink>
          )}
        </div>
      </div>

      {/* Mobile Navigation bar */}
      {isAuthenticated && (
        <div className="md:hidden border-t border-slate-800/80 px-4 py-2 flex items-center justify-around bg-slate-950">
          <NavLink to="/" end className={navLinkClasses}>
            <Users className="w-4 h-4" />
            <span className="text-xs">Roster</span>
          </NavLink>
          <NavLink to="/war" className={navLinkClasses}>
            <Swords className="w-4 h-4" />
            <span className="text-xs">Guerra</span>
          </NavLink>
          <NavLink to="/governance" className={navLinkClasses}>
            <Award className="w-4 h-4" />
            <span className="text-xs">Acciones</span>
          </NavLink>
          <NavLink to="/war-passes" className={navLinkClasses}>
            <Ticket className="w-4 h-4" />
            <span className="text-xs">Pases</span>
          </NavLink>
        </div>
      )}
    </header>
  );
};
