import React, { useEffect } from 'react';
import {
  X,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Swords,
  Ticket,
  HelpCircle,
  History,
} from 'lucide-react';
import { RoleBadge } from './Badge';
import type { ClanRole } from '../../types/domain';

export interface ReliabilityMemberContext {
  name: string;
  tag: string;
  role?: ClanRole | string;
  reliabilityScore: number;
  attacksToday?: number;
  hasWarPass?: boolean;
  warPassReason?: string | null;
}

interface ReliabilityModalProps {
  isOpen: boolean;
  onClose: () => void;
  member?: ReliabilityMemberContext | null;
  onViewWarHistory?: (tag: string) => void;
}

export const ReliabilityModal: React.FC<ReliabilityModalProps> = ({
  isOpen,
  onClose,
  member,
  onViewWarHistory,
}) => {
  // Close on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const score = member ? member.reliabilityScore : null;
  const isReliable = score !== null ? score >= 80 : null;
  const isIrregular = score !== null ? score >= 50 && score < 80 : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl flex flex-col shadow-2xl relative overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-xl border ${
                score === null || isReliable
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                  : isIrregular
                  ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                  : 'bg-rose-500/20 text-rose-400 border-rose-500/30'
              }`}
            >
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base font-bold text-white">
                  {member ? `Confiabilidad: ${member.name}` : '¿Cómo funciona la Confiabilidad?'}
                </h2>
                {member?.role && <RoleBadge role={member.role} />}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                {member ? (
                  <span className="font-mono text-slate-500">{member.tag}</span>
                ) : (
                  'Guía del sistema de disciplina y asistencia del clan'
                )}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Cerrar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 sm:p-6 space-y-5 overflow-y-auto max-h-[75vh]">
          {/* Player specific score card (if member provided) */}
          {member && (
            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">
                  Puntaje Actual
                </span>
                <div className="flex items-baseline gap-2 mt-1">
                  <span
                    className={`text-3xl font-mono font-bold ${
                      isReliable
                        ? 'text-emerald-400'
                        : isIrregular
                        ? 'text-amber-400'
                        : 'text-rose-400'
                    }`}
                  >
                    {member.reliabilityScore.toFixed(1)}%
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-bold border ${
                      isReliable
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : isIrregular
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                    }`}
                  >
                    {isReliable
                      ? '🟢 Confiable'
                      : isIrregular
                      ? '🟡 Irregular'
                      : '🔴 En Riesgo de Sanción'}
                  </span>
                </div>
              </div>

              {/* Today's attacks status */}
              {member.attacksToday !== undefined && (
                <div className="sm:text-right border-t sm:border-t-0 sm:border-l border-slate-800 pt-2 sm:pt-0 sm:pl-4">
                  <span className="text-xs text-slate-400 block font-semibold">
                    Ataques en la Jornada de Hoy
                  </span>
                  <div className="flex items-center sm:justify-end gap-1.5 font-mono font-bold mt-1">
                    <Swords className="w-4 h-4 text-amber-400" />
                    <span
                      className={`text-sm ${
                        member.attacksToday >= 4
                          ? 'text-emerald-400'
                          : member.attacksToday === 0
                          ? 'text-rose-400'
                          : 'text-amber-400'
                      }`}
                    >
                      {member.attacksToday} / 4 realizados
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Key Clarification: Live vs Closed War Days */}
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3.5 text-xs text-amber-200/90 space-y-2">
            <div className="flex items-center gap-2 font-bold text-amber-300">
              <Clock className="w-4 h-4 flex-shrink-0" />
              <span>Diferencia clave: Jornada en Curso vs. Histórico Disciplinario</span>
            </div>
            <p className="leading-relaxed">
              La <strong>Confiabilidad</strong> no se calcula sobre el día de hoy, sino sobre las{' '}
              <strong>jornadas de guerra ya cerradas</strong> (últimos 14 días).
            </p>
            <p className="leading-relaxed text-amber-200/80">
              Por eso, si un jugador ya realizó sus <strong>4/4 ataques hoy</strong>, sus medallas
              suman en vivo para la carrera, pero su porcentaje de confiabilidad histórica se
              actualizará al <strong>cierre de la jornada</strong> (10:00 UTC).
            </p>
          </div>

          {/* How it's calculated */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <HelpCircle className="w-4 h-4 text-slate-400" />
              <span>Fórmula de Cálculo</span>
            </h3>
            <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 text-center">
              Confiabilidad = (Ataques realizados en días cerrados / Ataques requeridos) × 100
            </div>
            <ul className="text-xs text-slate-400 space-y-2 leading-relaxed">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                <span>
                  <strong>Días evaluados:</strong> Solo se computan los días clasificados como{' '}
                  <strong className="text-slate-200">guerra</strong> (jueves a domingo) que hayan
                  cerrado formalmente. Los días de entrenamiento no penalizan.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <Ticket className="w-3.5 h-3.5 text-purple-400 mt-0.5 flex-shrink-0" />
                <span>
                  <strong>Pases de Guerra:</strong> Las ausencias autorizadas mediante un Pase de
                  Guerra activo <strong className="text-slate-200">eximen al jugador</strong> y no
                  reducen su porcentaje.
                  {member?.hasWarPass && (
                    <span className="block mt-1 text-purple-300 font-medium bg-purple-500/10 p-1.5 rounded-lg border border-purple-500/20">
                      🛡️ Este jugador tiene un Pase activo: {member.warPassReason || 'Justificado'}
                    </span>
                  )}
                </span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-400 mt-0.5 flex-shrink-0" />
                <span>
                  <strong>Jugadores Nuevos:</strong> Si un jugador acaba de unirse y no ha vivido
                  ninguna jornada de guerra cerrada previa en el clan, parte con un{' '}
                  <strong className="text-slate-200">100% de confiabilidad inicial</strong>.
                </span>
              </li>
            </ul>
          </div>

          {/* Scale thresholds */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Escala de Disciplina del Clan
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <span className="font-bold text-emerald-400 block font-mono">≥ 80.0%</span>
                <span className="text-[11px] font-semibold text-slate-300 block">Confiable</span>
                <p className="text-[10px] text-slate-400 mt-1">
                  Cumple sus 4 ataques habitualmente. Habilitado para ascenso a Veterano.
                </p>
              </div>

              <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
                <span className="font-bold text-amber-400 block font-mono">50.0% - 79.9%</span>
                <span className="text-[11px] font-semibold text-slate-300 block">Irregular</span>
                <p className="text-[10px] text-slate-400 mt-1">
                  Ha dejado ataques incompletos recientemente. Requiere seguimiento del liderazgo.
                </p>
              </div>

              <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20">
                <span className="font-bold text-rose-400 block font-mono">&lt; 50.0%</span>
                <span className="text-[11px] font-semibold text-slate-300 block">Alto Riesgo</span>
                <p className="text-[10px] text-slate-400 mt-1">
                  Faltas reiteradas. Candidato prioritario a expulsión o degradación al cierre.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 sm:p-4 border-t border-slate-800 bg-slate-900/90 backdrop-blur-md flex items-center justify-between gap-3 text-xs">
          {member && onViewWarHistory ? (
            <button
              onClick={() => {
                onClose();
                onViewWarHistory(member.tag);
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-semibold bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/30 transition-all shadow-sm"
            >
              <History className="w-3.5 h-3.5" />
              <span>Ver historial de 10 guerras de {member.name}</span>
            </button>
          ) : (
            <span className="text-slate-500 text-[11px]">
              Actualizado automáticamente en cada cierre de jornada.
            </span>
          )}

          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition-colors"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};
