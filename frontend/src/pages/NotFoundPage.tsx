import React from 'react';
import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-4">
      <h1 className="text-6xl font-black text-amber-500 mb-2">404</h1>
      <h2 className="text-xl font-bold text-slate-200 mb-2">Página no encontrada</h2>
      <p className="text-slate-400 text-sm max-w-sm mb-6">
        La ruta solicitada no existe o no tienes permisos para acceder a ella.
      </p>
      <Link
        to="/"
        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-semibold transition-all border border-slate-700"
      >
        <Home className="w-4 h-4" />
        Volver al Roster
      </Link>
    </div>
  );
};
