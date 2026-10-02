import React, { useEffect, useState, useCallback } from 'react';
import {
  X,
  History,
  Trophy,
  Swords,
  Shield,
  AlertCircle,
  Loader2,
  Calendar,
  Flame,
  CheckCircle2,
  AlertTriangle,
  Ticket,
} from 'lucide-react';
import { membersApi } from '../../api/client';
import type { MemberWarHistoryResponse } from '../../types/domain';
import { RoleBadge } from '../common/Badge';

interface PlayerWarHistoryModalProps {
  memberTag: string | null;
  isOpen: boolean;
  onClose: () => void;
  onGrantWarPass?: (memberTag: string) => void;
}

export const PlayerWarHistoryModal: React.FC<PlayerWarHistoryModalProps> = ({
  memberTag,
  isOpen,
  onClose,
  onGrantWarPass,
}) => {
  const [historyData, setHistoryData] = useState<MemberWarHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async (tag: string) => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await membersApi.getWarHistory(tag);
      setHistoryData(data);
    } catch {
      setError('No se pudo cargar el historial de guerras del jugador.');
      setHistoryData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isOpen || !memberTag) {
      return;
    }
    const timer = setTimeout(() => {
      fetchHistory(memberTag);
    }, 0);
    return () => clearTimeout(timer);
  }, [isOpen, memberTag, fetchHistory]);

  // Handle ESC key press
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

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl relative overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
              <History className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-bold text-white">
                  {historyData?.member.name || 'Historial de Jugador'}
                </h2>
                {historyData?.member.role && <RoleBadge role={historyData.member.role} />}
              </div>
              <p className="text-xs text-slate-400 font-mono flex items-center gap-2 mt-0.5">
                <span>{memberTag}</span>
                {historyData?.member.clan_name && (
                  <>
                    <span className="text-slate-600">•</span>
                    <span className="text-slate-300 font-sans">{historyData.member.clan_name}</span>
                  </>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onGrantWarPass && memberTag && (
              <button
                onClick={() => {
                  onClose();
                  onGrantWarPass(memberTag);
                }}
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-amber-500/20 text-slate-300 hover:text-amber-300 border border-slate-700 hover:border-amber-500/30 transition-all shadow-sm"
              >
                <Ticket className="w-3.5 h-3.5 text-amber-400" />
                <span>Pase de Guerra</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="Cerrar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-6 flex-1">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
              <span className="text-slate-400 text-sm">Cargando ataques y carreras históricas...</span>
            </div>
          )}

          {error && !isLoading && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span>{error}</span>
              </div>
              {memberTag && (
                <button
                  onClick={() => fetchHistory(memberTag)}
                  className="px-3 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-semibold transition-colors"
                >
                  Reintentar
                </button>
              )}
            </div>
          )}

          {historyData && !isLoading && (
            <>
              {/* Summary KPIs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
                {/* Reliability / Attendance */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-semibold mb-1">
                    <span>Confiabilidad</span>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  <div>
                    <div className="flex items-baseline gap-1.5">
                      <span
                        className={`text-2xl font-mono font-bold ${
                          historyData.summary.attendance_rate >= 80
                            ? 'text-emerald-400'
                            : historyData.summary.attendance_rate >= 50
                            ? 'text-amber-400'
                            : 'text-rose-400'
                        }`}
                      >
                        {historyData.summary.attendance_rate.toFixed(1)}%
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500 font-mono mt-0.5 block">
                      {historyData.summary.total_attacks_used} / {historyData.summary.total_attacks_expected} ataques
                    </span>
                  </div>
                </div>

                {/* Races Analyzed */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-semibold mb-1">
                    <span>Carreras</span>
                    <Calendar className="w-3.5 h-3.5 text-blue-400" />
                  </div>
                  <div>
                    <div className="text-2xl font-mono font-bold text-slate-100">
                      {historyData.summary.races_analyzed}
                    </div>
                    <span className="text-[11px] text-slate-500 block mt-0.5">
                      {historyData.summary.total_war_days} días de guerra
                    </span>
                  </div>
                </div>

                {/* Total Medals */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-semibold mb-1">
                    <span>Medallas Totales</span>
                    <Flame className="w-3.5 h-3.5 text-amber-400" />
                  </div>
                  <div>
                    <div className="text-2xl font-mono font-bold text-amber-300">
                      {historyData.summary.total_medals.toLocaleString('es-ES')}
                    </div>
                    <span className="text-[11px] text-slate-500 block mt-0.5">
                      Acumuladas en carreras
                    </span>
                  </div>
                </div>

                {/* Boat Attacks */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 flex flex-col justify-between">
                  <div className="flex items-center justify-between text-slate-400 text-xs font-semibold mb-1">
                    <span>Ataques a Barcos</span>
                    <Swords className="w-3.5 h-3.5 text-rose-400" />
                  </div>
                  <div>
                    <div
                      className={`text-2xl font-mono font-bold ${
                        historyData.summary.total_boat_attacks > 0 ? 'text-rose-400' : 'text-slate-200'
                      }`}
                    >
                      {historyData.summary.total_boat_attacks}
                    </div>
                    <span className="text-[11px] text-slate-500 block mt-0.5">
                      {historyData.summary.total_boat_attacks > 0
                        ? '🚨 Bloquea ascensos'
                        : '0 ataques (Excelente)'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Trophies & Donations Bar */}
              <div className="flex items-center justify-between bg-slate-950/40 border border-slate-800/50 rounded-xl px-4 py-2.5 text-xs text-slate-400">
                <div className="flex items-center gap-1.5 font-semibold text-slate-300">
                  <Trophy className="w-3.5 h-3.5 text-amber-400" />
                  <span>Trofeos:</span>
                  <span className="text-amber-300 font-bold font-mono">
                    {historyData.member.trophies.toLocaleString('es-ES')}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span>
                    Donadas:{' '}
                    <strong className="text-slate-200 font-mono">
                      {historyData.member.donations.toLocaleString('es-ES')}
                    </strong>
                  </span>
                  <span className="text-slate-700">|</span>
                  <span>
                    Recibidas:{' '}
                    <strong className="text-slate-200 font-mono">
                      {historyData.member.donations_received.toLocaleString('es-ES')}
                    </strong>
                  </span>
                </div>
              </div>

              {/* Races Timeline */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                    <Swords className="w-4 h-4 text-amber-400" />
                    <span>Últimas {historyData.races.length} Carreras de Río</span>
                  </h3>
                  <span className="text-xs text-slate-500">Ordenadas de la más reciente a la más antigua</span>
                </div>

                {historyData.races.length === 0 ? (
                  <div className="p-8 rounded-xl bg-slate-950/60 border border-slate-800 text-center text-slate-500 text-xs">
                    No se registran ataques en las últimas carreras de río para este jugador.
                  </div>
                ) : (
                  <div className="space-y-3">
                    {historyData.races.map((race, raceIdx) => {
                      const isComplete = race.total_attacks >= race.max_attacks && race.max_attacks > 0;
                      const isZero = race.total_attacks === 0 && race.max_attacks > 0;

                      return (
                        <div
                          key={`${race.season_id}-${race.section_index}-${raceIdx}`}
                          className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-4 transition-all hover:border-slate-700"
                        >
                          {/* Race Header */}
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/60">
                            <div className="flex items-center gap-2.5">
                              <span className="font-bold text-sm text-slate-100">
                                Temporada {race.season_id} • Semana {race.section_index}
                              </span>
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                                  race.state === 'clans_finished'
                                    ? 'bg-slate-800 text-slate-300 border-slate-700'
                                    : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                                }`}
                              >
                                {race.state === 'clans_finished' ? 'Finalizada' : 'En Curso'}
                              </span>
                            </div>

                            <div className="flex items-center gap-3 text-xs">
                              {/* Race Attack Count */}
                              <div className="flex items-center gap-1.5 font-mono">
                                <span className="text-slate-400">Ataques:</span>
                                <span
                                  className={`font-bold px-2 py-0.5 rounded-md border ${
                                    isComplete
                                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                                      : isZero
                                      ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                                      : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                                  }`}
                                >
                                  {race.total_attacks} / {race.max_attacks}
                                </span>
                              </div>

                              {/* Race Medals */}
                              <div className="flex items-center gap-1 text-amber-300 font-mono font-bold">
                                <Flame className="w-3.5 h-3.5 text-amber-400" />
                                <span>{race.medals.toLocaleString('es-ES')}</span>
                              </div>

                              {/* Race Boat Attacks */}
                              {race.boat_attacks > 0 && (
                                <span className="text-[10px] font-mono font-bold text-rose-400 px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/20">
                                  ⚔️ {race.boat_attacks} b.
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Days Breakdown */}
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
                            {race.days.map((day) => {
                              const dayDone = day.attacks_used >= (day.max_attacks || 4);
                              const dayZero = day.attacks_used === 0;

                              return (
                                <div
                                  key={day.date}
                                  className="bg-slate-900/90 border border-slate-800/70 rounded-lg p-2.5 flex flex-col justify-between"
                                >
                                  <div className="flex items-center justify-between text-[11px] mb-1.5">
                                    <span className="font-semibold text-slate-300">
                                      {day.day_name}
                                    </span>
                                    <span className="text-[10px] text-slate-500 font-mono">
                                      {day.date.slice(5)}
                                    </span>
                                  </div>

                                  <div className="flex items-center justify-between mt-auto">
                                    {day.has_war_pass ? (
                                      <span
                                        className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30"
                                        title={day.war_pass_reason || 'Pase de Guerra'}
                                      >
                                        <Shield className="w-2.5 h-2.5" /> Exento
                                      </span>
                                    ) : day.day_type === 'war' ? (
                                      <span
                                        className={`inline-flex items-center justify-center font-mono font-bold text-[11px] px-2 py-0.5 rounded-md border ${
                                          dayDone
                                            ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                                            : dayZero
                                            ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                                            : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                                        }`}
                                      >
                                        {day.attacks_used} / {day.max_attacks}
                                      </span>
                                    ) : (
                                      <span className="text-[11px] font-mono text-slate-400">
                                        {day.attacks_used} atq.
                                      </span>
                                    )}

                                    {day.medals_earned > 0 && (
                                      <span className="text-[10px] font-mono text-amber-400/90">
                                        +{day.medals_earned}
                                      </span>
                                    )}
                                  </div>

                                  {day.boat_attacks_count > 0 && (
                                    <span className="text-[9px] text-rose-400 font-semibold mt-1">
                                      ⚔️ {day.boat_attacks_count} barco
                                    </span>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-3 sm:p-4 border-t border-slate-800 bg-slate-900/90 backdrop-blur-md flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500/70" />
            <span>Datos calculados a partir de las últimas 10 carreras de río registradas.</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition-colors"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
