import React from 'react';
import type { ActionStatus, ActionType, ClanRole } from '../../types/domain';

export const RoleBadge: React.FC<{ role: ClanRole | string }> = ({ role }) => {
  switch (role) {
    case 'leader':
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
          👑 Líder
        </span>
      );
    case 'coLeader':
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
          ⚔️ Colíder
        </span>
      );
    case 'elder':
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
          🛡️ Veterano
        </span>
      );
    case 'member':
    default:
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-700/50 text-slate-300 border border-slate-600/30">
          Miembro
        </span>
      );
  }
};

export const ReliabilityBadge: React.FC<{ score: number | string | null | undefined }> = ({ score }) => {
  const numericScore = typeof score === 'number' ? score : parseFloat(String(score ?? 0)) || 0;
  let colorClasses = 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
  if (numericScore < 50) {
    colorClasses = 'bg-rose-500/20 text-rose-400 border-rose-500/30';
  } else if (numericScore < 80) {
    colorClasses = 'bg-amber-500/20 text-amber-400 border-amber-500/30';
  }

  return (
    <span className={`px-2 py-0.5 rounded-md text-xs font-mono font-bold border ${colorClasses}`}>
      {numericScore.toFixed(1)}%
    </span>
  );
};

export const ActionTypeBadge: React.FC<{ type: ActionType | string }> = ({ type }) => {
  switch (type) {
    case 'kick':
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">
          Expulsión
        </span>
      );
    case 'demote_member':
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
          Descenso a Miembro
        </span>
      );
    case 'promote_elder':
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
          Ascenso a Veterano
        </span>
      );
    case 'leadership_notice':
    default:
      return (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40">
          Aviso a Liderazgo
        </span>
      );
  }
};

export const StatusBadge: React.FC<{ status: ActionStatus | string }> = ({ status }) => {
  switch (status) {
    case 'pending':
      return (
        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
          Pendiente
        </span>
      );
    case 'executed':
      return (
        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Ejecutada
        </span>
      );
    case 'dismissed':
      return (
        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-700/40 text-slate-400 border border-slate-600/20">
          Descartada
        </span>
      );
    default:
      return null;
  }
};
