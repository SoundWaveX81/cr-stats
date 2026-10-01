import React from 'react';
import { Shield, RefreshCw, Users, Target, Clock, CheckCircle2, AlertCircle } from 'lucide-react';
import type { Clan } from '../../types/domain';

interface ClanHeaderCardProps {
  clan: Clan;
  onSync: () => Promise<void>;
  isSyncing: boolean;
  syncSuccess: string | null;
  syncError: string | null;
}

export const ClanHeaderCard: React.FC<ClanHeaderCardProps> = ({
  clan,
  onSync,
  isSyncing,
  syncSuccess,
  syncError,
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
      {/* Background Accent */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-amber-500/5 rounded-full blur-3xl pointer-events-none"></div>

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 relative z-10">
        {/* Clan Info */}
        <div className="flex items-start sm:items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-amber-600 via-amber-500 to-amber-300 flex items-center justify-center shadow-lg shadow-amber-500/20 flex-shrink-0">
            <Shield className="w-8 h-8 text-slate-950" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-black text-white tracking-tight">{clan.name}</h1>
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-slate-800 text-amber-400 border border-amber-500/20">
                {clan.tag}
              </span>
              {clan.is_active ? (
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  Activo
                </span>
              ) : (
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-400 border border-slate-600/30">
                  Inactivo
                </span>
              )}
            </div>

            {/* Clan Metric Chips */}
            <div className="flex flex-wrap items-center gap-4 mt-3 text-xs text-slate-400">
              <div className="flex items-center gap-1.5 bg-slate-950/60 px-2.5 py-1 rounded-lg border border-slate-800">
                <Users className="w-3.5 h-3.5 text-blue-400" />
                <span>
                  <strong className="text-slate-200">{clan.members_count}</strong> / 50 Miembros
                </span>
              </div>

              <div className="flex items-center gap-1.5 bg-slate-950/60 px-2.5 py-1 rounded-lg border border-slate-800">
                <Target className="w-3.5 h-3.5 text-amber-400" />
                <span>
                  Umbral: <strong className="text-slate-200">{clan.medal_threshold}</strong> medallas
                </span>
              </div>

              <div className="flex items-center gap-1.5 bg-slate-950/60 px-2.5 py-1 rounded-lg border border-slate-800">
                <Clock className="w-3.5 h-3.5 text-purple-400" />
                <span>
                  Reinicio: <strong className="text-slate-200">{clan.war_day_reset_time} UTC</strong>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Sync Button */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <button
            onClick={onSync}
            disabled={isSyncing}
            className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 shadow-md shadow-amber-500/5 hover:border-amber-500/60 transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            <RefreshCw
              className={`w-4 h-4 text-amber-400 transition-transform ${
                isSyncing ? 'animate-spin' : 'group-hover:rotate-180 duration-500'
              }`}
            />
            <span>{isSyncing ? 'Sincronizando...' : 'Sincronizar API'}</span>
          </button>
        </div>
      </div>

      {/* Sync Status Banners */}
      {syncSuccess && (
        <div className="mt-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{syncSuccess}</span>
        </div>
      )}

      {syncError && (
        <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{syncError}</span>
        </div>
      )}
    </div>
  );
};
