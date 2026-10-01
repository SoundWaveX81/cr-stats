import React from 'react';
import { Check, X, Clock, AlertTriangle, ShieldAlert, Sparkles, User, Loader2 } from 'lucide-react';
import type { RosterAction } from '../../types/domain';
import { ActionTypeBadge, StatusBadge } from '../common/Badge';

interface RosterActionCardProps {
  action: RosterAction;
  onExecute: (id: number) => Promise<void>;
  onDismiss: (id: number) => Promise<void>;
  isProcessing: boolean;
}

export const RosterActionCard: React.FC<RosterActionCardProps> = ({
  action,
  onExecute,
  onDismiss,
  isProcessing,
}) => {
  const getActionIcon = () => {
    switch (action.action_type) {
      case 'kick':
        return <ShieldAlert className="w-5 h-5 text-rose-400" />;
      case 'demote_member':
        return <AlertTriangle className="w-5 h-5 text-amber-400" />;
      case 'promote_elder':
        return <Sparkles className="w-5 h-5 text-emerald-400" />;
      case 'leadership_notice':
      default:
        return <User className="w-5 h-5 text-purple-400" />;
    }
  };

  const getBorderColor = () => {
    switch (action.action_type) {
      case 'kick':
        return 'border-rose-500/30 hover:border-rose-500/50';
      case 'demote_member':
        return 'border-amber-500/30 hover:border-amber-500/50';
      case 'promote_elder':
        return 'border-emerald-500/30 hover:border-emerald-500/50';
      default:
        return 'border-purple-500/30 hover:border-purple-500/50';
    }
  };

  return (
    <div
      className={`bg-slate-900 border ${getBorderColor()} rounded-2xl p-5 shadow-lg transition-all flex flex-col justify-between`}
    >
      <div>
        {/* Header: Action Type & Status */}
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-slate-950 border border-slate-800">
              {getActionIcon()}
            </div>
            <div>
              <ActionTypeBadge type={action.action_type} />
            </div>
          </div>
          <StatusBadge status={action.status} />
        </div>

        {/* Member Details */}
        <div className="bg-slate-950/70 p-3 rounded-xl border border-slate-800/80 mb-3">
          <div className="flex items-center justify-between">
            <span className="font-extrabold text-sm text-slate-100">
              {action.member_name || action.member_tag || action.member}
            </span>
            <span className="font-mono text-xs text-amber-400 font-semibold">
              {action.member_tag || action.member}
            </span>
          </div>
          {action.clan_name && (
            <div className="text-[11px] text-slate-400 mt-1">
              Clan: <span className="text-slate-300 font-semibold">{action.clan_name}</span> ({action.clan})
            </div>
          )}
        </div>

        {/* Reason */}
        <div className="text-xs text-slate-300 bg-slate-800/40 p-3 rounded-xl border border-slate-700/30 mb-4">
          <p className="font-medium">{action.reason}</p>
        </div>
      </div>

      {/* Footer / Actions */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
          <Clock className="w-3.5 h-3.5" />
          <span>
            {new Date(action.created_at).toLocaleDateString('es-ES', {
              day: 'numeric',
              month: 'short',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>

        {action.status === 'pending' ? (
          <div className="flex items-center gap-2">
            <button
              onClick={() => onDismiss(action.id)}
              disabled={isProcessing}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg font-semibold text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 hover:text-slate-100 transition-all disabled:opacity-50"
              title="Descartar acción"
            >
              <X className="w-3.5 h-3.5 text-slate-400" />
              <span>Descartar</span>
            </button>

            <button
              onClick={() => onExecute(action.id)}
              disabled={isProcessing}
              className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg font-bold text-xs bg-emerald-600 hover:bg-emerald-500 text-slate-950 shadow-md shadow-emerald-600/20 transition-all disabled:opacity-50"
              title="Marcar como ejecutada en Clash Royale"
            >
              {isProcessing ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Check className="w-3.5 h-3.5" />
              )}
              <span>Ejecutada</span>
            </button>
          </div>
        ) : action.status === 'executed' ? (
          <span className="text-emerald-400 font-semibold flex items-center gap-1 text-[11px]">
            <Check className="w-3.5 h-3.5" /> Ejecutada en el juego
          </span>
        ) : (
          <span className="text-slate-500 font-semibold flex items-center gap-1 text-[11px]">
            <X className="w-3.5 h-3.5" /> Descartada por líder
          </span>
        )}
      </div>
    </div>
  );
};
