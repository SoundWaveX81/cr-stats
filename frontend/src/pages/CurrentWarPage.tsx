import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Swords,
  Trophy,
  Flame,
  Target,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Ticket,
  Users,
  Shield,
  Loader2,
  TrendingUp,
} from 'lucide-react';
import { clansApi } from '../api/client';
import type { Clan, CurrentWarOverview, WarParticipant } from '../types/domain';
import { RoleBadge } from '../components/common/Badge';

export const CurrentWarPage: React.FC = () => {
  const { clanTag: urlClanTag } = useParams<{ clanTag?: string }>();
  const navigate = useNavigate();

  const [clans, setClans] = useState<Clan[]>([]);
  const [selectedClan, setSelectedClan] = useState<Clan | null>(null);
  const [warData, setWarData] = useState<CurrentWarOverview | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Table filters
  const [searchTerm, setSearchTerm] = useState('');
  const [attackFilter, setAttackFilter] = useState<'all' | 'zero' | 'incomplete' | 'complete' | 'pass'>('all');

  // Load clans list on mount
  useEffect(() => {
    const loadClans = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const res = await clansApi.list();
        const clanList: Clan[] = Array.isArray(res) ? res : ((res as unknown as { results?: Clan[] })?.results || []);
        setClans(clanList);

        if (clanList.length > 0) {
          const matchedClan = urlClanTag
            ? clanList.find((c) => c.tag.toUpperCase() === urlClanTag.toUpperCase()) || clanList[0]
            : clanList[0];
          setSelectedClan(matchedClan);
        }
      } catch {
        setError('Error al cargar la lista de clanes.');
      } finally {
        setIsLoading(false);
      }
    };

    loadClans();
  }, [urlClanTag]);

  // Load current war data whenever selectedClan changes
  const loadWarData = useCallback(async (tag: string, background = false) => {
    try {
      if (!background) setIsLoading(true);
      else setIsRefreshing(true);
      setError(null);

      const data = await clansApi.getCurrentWar(tag);
      setWarData(data);
    } catch {
      setError('No se pudo obtener la información de la guerra actual desde la API de Clash Royale.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (selectedClan) {
      const fetchCurrentWar = async () => {
        await loadWarData(selectedClan.tag);
      };
      fetchCurrentWar();
    }
  }, [selectedClan, loadWarData]);

  const handleClanChange = (newTag: string) => {
    const clan = clans.find((c) => c.tag === newTag);
    if (clan) {
      setSelectedClan(clan);
      navigate(`/clans/${encodeURIComponent(clan.tag)}/war`);
    }
  };

  const handleRefresh = () => {
    if (selectedClan) {
      loadWarData(selectedClan.tag, true);
    }
  };

  // Filter participants
  const filteredParticipants = useMemo(() => {
    if (!warData?.participants) return [];
    return warData.participants.filter((p: WarParticipant) => {
      const matchSearch =
        p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.tag.toLowerCase().includes(searchTerm.toLowerCase());

      let matchFilter = true;
      if (attackFilter === 'zero') matchFilter = p.attacks_used === 0;
      else if (attackFilter === 'incomplete') matchFilter = p.attacks_used > 0 && p.attacks_used < 4;
      else if (attackFilter === 'complete') matchFilter = p.attacks_used >= 4;
      else if (attackFilter === 'pass') matchFilter = p.has_war_pass;

      return matchSearch && matchFilter;
    });
  }, [warData, searchTerm, attackFilter]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
        <span className="text-slate-400 text-sm">Consultando estado en vivo de la River Race...</span>
      </div>
    );
  }

  if (error || !warData) {
    return (
      <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-start gap-4">
        <AlertTriangle className="w-6 h-6 flex-shrink-0 mt-0.5" />
        <div>
          <h2 className="font-bold text-base mb-1">Error al obtener la guerra actual</h2>
          <p className="text-sm">{error || 'No hay datos disponibles para este clan.'}</p>
          <button
            onClick={handleRefresh}
            className="mt-3 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/30 transition-colors"
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const { clan, race, stats, clans: competingClans } = warData;
  const attackCompletionPercent = stats.total_attacks_possible > 0
    ? Math.round((stats.total_attacks_used / stats.total_attacks_possible) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Clan Selector Bar & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-600 to-amber-400 flex items-center justify-center shadow-lg shadow-amber-500/20 flex-shrink-0">
            <Swords className="w-5 h-5 text-slate-950" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-black text-white">{clan.name}</h1>
              <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-slate-800 text-amber-400 border border-amber-500/20">
                {clan.tag}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-400">
              <span className="capitalize font-semibold text-purple-400">
                {race.day_type === 'war' ? '⚔️ Día de Guerra' : '🛡️ Día de Entrenamiento'}
              </span>
              <span>•</span>
              <span>Semana {race.section_index + 1} (Día {race.day_index + 1}/7)</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {clans.length > 1 && (
            <select
              value={selectedClan?.tag || ''}
              onChange={(e) => handleClanChange(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500 font-semibold"
            >
              {clans.map((c) => (
                <option key={c.tag} value={c.tag}>
                  {c.name} ({c.tag})
                </option>
              ))}
            </select>
          )}

          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold uppercase tracking-wider bg-slate-800 hover:bg-slate-700 text-amber-300 border border-amber-500/30 transition-all disabled:opacity-50"
            title="Refrescar datos en vivo con Supercell"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Actualizando...' : 'En Vivo'}</span>
          </button>
        </div>
      </div>

      {/* River Race Standings (5 Competing Clans) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-amber-400" />
            <h2 className="text-base font-extrabold text-white">Clasificación de la River Race</h2>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300 font-semibold">
            Posición Actual: <strong className="text-amber-400">{clan.position}º de {clan.total_clans}</strong>
          </span>
        </div>

        {/* Competing Clans List */}
        <div className="grid grid-cols-1 gap-3">
          {competingClans.map((c) => {
            const isFirst = c.rank === 1;
            const isMyClan = c.is_user_clan;
            const maxFameInRace = Math.max(...competingClans.map((cl) => cl.fame), 1);
            const famePercent = Math.min(100, Math.round((c.fame / maxFameInRace) * 100));

            return (
              <div
                key={c.tag}
                className={`p-3.5 rounded-xl border transition-all ${
                  isMyClan
                    ? 'bg-amber-500/10 border-amber-500/50 shadow-md shadow-amber-500/5'
                    : 'bg-slate-950/60 border-slate-800'
                }`}
              >
                <div className="flex items-center justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span
                      className={`w-6 h-6 rounded-lg flex items-center justify-center font-black text-xs ${
                        isFirst
                          ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                          : c.rank === 2
                          ? 'bg-slate-300 text-slate-950'
                          : c.rank === 3
                          ? 'bg-amber-700 text-white'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {c.rank}º
                    </span>
                    <span className={`font-bold text-sm truncate ${isMyClan ? 'text-amber-300' : 'text-slate-200'}`}>
                      {c.name}
                    </span>
                    <span className="font-mono text-[10px] text-slate-500 hidden sm:inline">{c.tag}</span>
                    {isMyClan && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                        Tu Clan
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-4 flex-shrink-0 text-right">
                    <div>
                      <span className="text-xs text-slate-400">Trofeos: </span>
                      <span className="font-mono text-xs font-bold text-slate-300">{c.clan_score}</span>
                    </div>
                    <div>
                      <span className="font-extrabold text-sm text-amber-400">
                        {c.fame.toLocaleString('es-ES')}
                      </span>
                      <span className="text-[10px] text-slate-400 ml-1">medallas</span>
                    </div>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden border border-slate-800/80">
                  <div
                    className={`h-full rounded-full transition-all ${
                      isMyClan ? 'bg-gradient-to-r from-amber-500 to-amber-300' : isFirst ? 'bg-amber-500/60' : 'bg-slate-700'
                    }`}
                    style={{ width: `${Math.max(4, famePercent)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        {/* Mathematical Projection Banner */}
        <div className="mt-4 p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          {clan.position > 1 ? (
            <div className="flex items-center gap-2 text-slate-300">
              <TrendingUp className="w-4 h-4 text-amber-400 flex-shrink-0" />
              <span>
                Distancia al 1º puesto: <strong className="text-amber-400">{stats.gap_to_first.toLocaleString('es-ES')} medallas</strong>.
                {stats.wins_needed_for_first > 0 && (
                  <span className="ml-1 text-slate-400">
                    (Se necesitan <strong className="text-slate-100">{stats.wins_needed_for_first} victorias</strong> de los ataques pendientes para alcanzar la cima).
                  </span>
                )}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-emerald-300">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>
                👑 ¡Tu clan se encuentra actualmente en el <strong>1º Puesto</strong> de la River Race!
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Aggregate Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Attacks Progress */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Ataques Realizados
            </span>
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
              <Swords className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-black text-white">{stats.total_attacks_used}</span>
              <span className="text-xs text-slate-500">/ {stats.total_attacks_possible} posibles</span>
            </div>
            <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden mt-2.5 border border-slate-800">
              <div
                className="h-full bg-blue-500 rounded-full transition-all"
                style={{ width: `${attackCompletionPercent}%` }}
              />
            </div>
          </div>
          <span className="text-[11px] text-slate-400 mt-2 block">
            {attackCompletionPercent}% de participación completada hoy
          </span>
        </div>

        {/* Card 2: Attacks Pending */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Ataques Pendientes
            </span>
            <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-black text-rose-400">{stats.total_attacks_pending}</span>
              <span className="text-xs text-slate-500">por ejecutar</span>
            </div>
            <span className="text-[11px] text-slate-400 mt-2 block">
              En {stats.total_members} miembros activos del clan
            </span>
          </div>
        </div>

        {/* Card 3: Potential Points */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Puntos Potenciales (Max)
            </span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <Flame className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-emerald-400">
                +{stats.potential_points_max.toLocaleString('es-ES')}
              </span>
            </div>
            <span className="text-[11px] text-slate-400 mt-2 block">
              En caso de victorias exitosas (900 pts/ataque)
            </span>
          </div>
        </div>

        {/* Card 4: Max Reachable Fame */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Puntuación Max Alcanzable
            </span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
              <Target className="w-4 h-4" />
            </div>
          </div>
          <div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-amber-300">
                {stats.potential_max_fame.toLocaleString('es-ES')}
              </span>
              <span className="text-xs text-slate-500">medallas</span>
            </div>
            <span className="text-[11px] text-slate-400 mt-2 block">
              Techo de medallas posibles en la jornada actual
            </span>
          </div>
        </div>
      </div>

      {/* Participants Detail Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {/* Table Filter Bar */}
        <div className="p-4 sm:p-5 border-b border-slate-800 flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar jugador por nombre o tag (#...)"
              className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500 transition-all"
            />
          </div>

          {/* Quick attack filters */}
          <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-950 rounded-xl border border-slate-800">
            {[
              { id: 'all', label: 'Todos' },
              { id: 'zero', label: '0/4 Ataques' },
              { id: 'incomplete', label: '1-3/4 Ataques' },
              { id: 'complete', label: '4/4 Completados' },
              { id: 'pass', label: 'Con Pase' },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setAttackFilter(f.id as typeof attackFilter)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  attackFilter === f.id
                    ? 'bg-amber-500 text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4 sm:px-6">Jugador</th>
                <th className="py-3.5 px-3">Rol</th>
                <th className="py-3.5 px-3 text-center">Ataques Hoy</th>
                <th className="py-3.5 px-3 text-center">Pendientes</th>
                <th className="py-3.5 px-3 text-center">Confiabilidad</th>
                <th className="py-3.5 px-3 text-right">Medallas Hoy</th>
                <th className="py-3.5 px-3 text-center">Barcos</th>
                <th className="py-3.5 px-3 text-center">Exención</th>
                <th className="py-3.5 px-4 sm:px-6 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {filteredParticipants.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-500">
                    <div className="flex flex-col items-center gap-2">
                      <Users className="w-8 h-8 opacity-40" />
                      <span>No se encontraron jugadores con los filtros aplicados.</span>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredParticipants.map((p) => {
                  const isDone = p.attacks_used >= 4;
                  const isZero = p.attacks_used === 0;

                  return (
                    <tr key={p.tag} className="hover:bg-slate-800/40 transition-colors group">
                      {/* Name & Tag */}
                      <td className="py-3 px-4 sm:px-6">
                        <div className="flex flex-col">
                          <span className="font-bold text-slate-100 group-hover:text-amber-400 transition-colors">
                            {p.name}
                          </span>
                          <span className="font-mono text-[10px] text-slate-500">{p.tag}</span>
                        </div>
                      </td>

                      {/* Role */}
                      <td className="py-3 px-3">
                        <RoleBadge role={p.role} />
                      </td>

                      {/* Attacks Done (Visual Dots/Badges) */}
                      <td className="py-3 px-3 text-center">
                        <span
                          className={`inline-flex items-center justify-center font-mono font-bold text-xs px-2.5 py-0.5 rounded-lg border ${
                            isDone
                              ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                              : isZero
                              ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                              : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                          }`}
                        >
                          {p.attacks_used} / 4
                        </span>
                      </td>

                      {/* Pending */}
                      <td className="py-3 px-3 text-center">
                        <span
                          className={`font-mono font-bold ${
                            p.attacks_pending > 0 ? 'text-rose-400' : 'text-slate-500'
                          }`}
                        >
                          {p.attacks_pending}
                        </span>
                      </td>

                      {/* Reliability Score */}
                      <td className="py-3 px-3 text-center">
                        {p.reliability_score !== undefined ? (
                          <div className="flex flex-col items-center">
                            <span
                              className={`font-mono font-bold text-xs ${
                                p.reliability_score >= 80
                                  ? 'text-emerald-400'
                                  : p.reliability_score >= 50
                                  ? 'text-amber-400'
                                  : 'text-rose-400'
                              }`}
                            >
                              {p.reliability_score.toFixed(0)}%
                            </span>
                            {p.attacks_used === 0 && p.reliability_score < 50 && (
                              <span className="text-[10px] text-rose-400 font-bold tracking-tight">
                                🚨 Riesgo
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>

                      {/* Medals */}
                      <td className="py-3 px-3 text-right">
                        <span className="font-mono font-bold text-amber-400">
                          {p.medals.toLocaleString('es-ES')}
                        </span>
                      </td>

                      {/* Boat Attacks */}
                      <td className="py-3 px-3 text-center">
                        {p.boat_attacks > 0 ? (
                          <span className="text-xs px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono font-bold">
                            ⚔️ {p.boat_attacks}
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>

                      {/* War Pass Exemption */}
                      <td className="py-3 px-3 text-center">
                        {p.has_war_pass ? (
                          <span
                            className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30"
                            title={p.war_pass_reason || 'Pase de Guerra activo'}
                          >
                            <Shield className="w-3 h-3" /> Exento
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 sm:px-6 text-right">
                        <button
                          onClick={() =>
                            navigate(
                              `/war-passes?member=${encodeURIComponent(p.tag)}&clan=${encodeURIComponent(
                                clan.tag
                              )}`
                            )
                          }
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-amber-500/20 text-slate-300 hover:text-amber-300 border border-slate-700 hover:border-amber-500/30 transition-all shadow-sm"
                          title="Otorgar Pase de Guerra"
                        >
                          <Ticket className="w-3.5 h-3.5 text-amber-400" />
                          <span>Pase</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
