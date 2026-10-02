import React, { useState, useMemo } from 'react';
import {
  Search,
  ArrowUpDown,
  Ticket,
  Users,
  Check,
  X,
  Trophy,
  HandHeart,
  Clock,
  History,
  HelpCircle,
} from 'lucide-react';
import type { Member } from '../../types/domain';
import { RoleBadge, ReliabilityBadge } from '../common/Badge';
import { PlayerWarHistoryModal } from './PlayerWarHistoryModal';
import { ReliabilityModal, type ReliabilityMemberContext } from '../common/ReliabilityModal';

interface RosterTableProps {
  members: Member[];
  onGrantWarPass?: (member: Member) => void;
}

type SortField =
  | 'reliability_score'
  | 'name'
  | 'role'
  | 'trophies'
  | 'donations'
  | 'last_seen';
type SortOrder = 'asc' | 'desc';

const formatRelativeTime = (
  isoString: string | null | undefined
): { label: string; dotColor: string } => {
  if (!isoString) return { label: 'Desconocido', dotColor: 'bg-slate-500' };
  const diffMs = Date.now() - new Date(isoString).getTime();
  if (isNaN(diffMs)) return { label: 'Desconocido', dotColor: 'bg-slate-500' };
  const diffMinutes = Math.floor(diffMs / 60000);
  if (diffMinutes < 1) return { label: 'Ahora', dotColor: 'bg-emerald-400' };
  if (diffMinutes < 60) return { label: `${diffMinutes}m`, dotColor: 'bg-emerald-400' };
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return { label: `${diffHours}h`, dotColor: 'bg-emerald-400' };
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return { label: 'Ayer', dotColor: 'bg-emerald-500/80' };
  if (diffDays <= 3) return { label: `${diffDays}d`, dotColor: 'bg-amber-400' };
  if (diffDays < 7) return { label: `${diffDays}d`, dotColor: 'bg-rose-400' };
  const weeks = Math.floor(diffDays / 7);
  if (weeks < 4) return { label: `${weeks} sem`, dotColor: 'bg-rose-500' };
  const months = Math.floor(diffDays / 30);
  return { label: `${months} m`, dotColor: 'bg-rose-600' };
};

export const RosterTable: React.FC<RosterTableProps> = ({ members, onGrantWarPass }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('trophies');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [selectedMemberTagForHistory, setSelectedMemberTagForHistory] = useState<string | null>(null);
  const [reliabilityModalContext, setReliabilityModalContext] = useState<ReliabilityMemberContext | null | 'general'>(null);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      const defaultDesc = [
        'reliability_score',
        'trophies',
        'donations',
        'last_seen',
      ].includes(field);
      setSortOrder(defaultDesc ? 'desc' : 'asc');
    }
  };

  const filteredMembers = useMemo(() => {
    return (members || [])
      .filter((member) => {
        const matchesSearch =
          (member.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
          (member.tag || '').toLowerCase().includes(searchTerm.toLowerCase());
        const matchesRole = roleFilter === 'all' || member.role === roleFilter;
        return matchesSearch && matchesRole;
      })
      .sort((a, b) => {
        let comparison = 0;
        if (sortField === 'reliability_score') {
          const scoreA =
            typeof a.reliability_score === 'number'
              ? a.reliability_score
              : parseFloat(String(a.reliability_score ?? 0)) || 0;
          const scoreB =
            typeof b.reliability_score === 'number'
              ? b.reliability_score
              : parseFloat(String(b.reliability_score ?? 0)) || 0;
          comparison = scoreA - scoreB;
        } else if (sortField === 'trophies') {
          comparison = (a.trophies || 0) - (b.trophies || 0);
        } else if (sortField === 'donations') {
          comparison = (a.donations || 0) - (b.donations || 0);
        } else if (sortField === 'last_seen') {
          const timeA = a.last_seen ? new Date(a.last_seen).getTime() : 0;
          const timeB = b.last_seen ? new Date(b.last_seen).getTime() : 0;
          comparison = timeA - timeB;
        } else if (sortField === 'name') {
          comparison = (a.name || '').localeCompare(b.name || '');
        } else if (sortField === 'role') {
          const rolePriority: Record<string, number> = {
            leader: 4,
            coLeader: 3,
            elder: 2,
            member: 1,
          };
          const priorityA = rolePriority[a.role] ?? 0;
          const priorityB = rolePriority[b.role] ?? 0;
          comparison = priorityA - priorityB;
        }
        return sortOrder === 'asc' ? comparison : -comparison;
      });
  }, [members, searchTerm, roleFilter, sortField, sortOrder]);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
      {/* Table Controls */}
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
            placeholder="Buscar por nombre o tag (#...)"
            className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500 focus:border-amber-500 transition-all"
          />
        </div>

        {/* Filters and count */}
        <div className="flex items-center gap-3">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500"
          >
            <option value="all">Todos los Roles</option>
            <option value="leader">Líder</option>
            <option value="coLeader">Colíderes</option>
            <option value="elder">Veteranos</option>
            <option value="member">Miembros</option>
          </select>

          <span className="text-xs text-slate-400 font-medium px-2 py-1 bg-slate-950 rounded-lg border border-slate-800">
            {filteredMembers.length} {filteredMembers.length === 1 ? 'jugador' : 'jugadores'}
          </span>
        </div>
      </div>

      {/* Roster Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
            <tr>
              {/* Member */}
              <th
                onClick={() => handleSort('name')}
                className="py-3.5 px-4 sm:px-6 cursor-pointer hover:text-slate-200 transition-colors"
              >
                <div className="flex items-center gap-1.5">
                  <span>Miembro</span>
                  <ArrowUpDown className="w-3.5 h-3.5" />
                </div>
              </th>

              {/* Role */}
              <th
                onClick={() => handleSort('role')}
                className="py-3.5 px-3 cursor-pointer hover:text-slate-200 transition-colors"
              >
                <div className="flex items-center gap-1.5">
                  <span>Rol</span>
                  <ArrowUpDown className="w-3.5 h-3.5" />
                </div>
              </th>

              {/* Trophies */}
              <th
                onClick={() => handleSort('trophies')}
                className="py-3.5 px-3 cursor-pointer hover:text-slate-200 transition-colors"
              >
                <div className="flex items-center gap-1.5">
                  <Trophy className="w-3.5 h-3.5 text-amber-400" />
                  <span>Trofeos</span>
                  <ArrowUpDown className="w-3.5 h-3.5" />
                </div>
              </th>

              {/* Donations */}
              <th
                onClick={() => handleSort('donations')}
                className="py-3.5 px-3 cursor-pointer hover:text-slate-200 transition-colors"
              >
                <div className="flex items-center gap-1.5">
                  <HandHeart className="w-3.5 h-3.5 text-blue-400" />
                  <span>Donaciones</span>
                  <ArrowUpDown className="w-3.5 h-3.5" />
                </div>
              </th>

              {/* Last Seen */}
              <th
                onClick={() => handleSort('last_seen')}
                className="py-3.5 px-3 cursor-pointer hover:text-slate-200 transition-colors"
              >
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-purple-400" />
                  <span>Última Conexión</span>
                  <ArrowUpDown className="w-3.5 h-3.5" />
                </div>
              </th>

              {/* Reliability Score */}
              <th className="py-3.5 px-3 hover:text-slate-200 transition-colors">
                <div className="flex items-center gap-1.5">
                  <span
                    onClick={() => handleSort('reliability_score')}
                    className="cursor-pointer flex items-center gap-1"
                  >
                    <span>Confiabilidad</span>
                    <ArrowUpDown className="w-3.5 h-3.5" />
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setReliabilityModalContext('general');
                    }}
                    className="text-slate-500 hover:text-amber-400 p-0.5 rounded transition-colors"
                    title="¿Cómo se calcula la confiabilidad?"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                  </button>
                </div>
              </th>

              {/* Status */}
              <th className="py-3.5 px-3 text-center">Estado</th>

              {/* Actions */}
              <th className="py-3.5 px-4 sm:px-6 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-medium">
            {filteredMembers.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-500">
                  <div className="flex flex-col items-center gap-2">
                    <Users className="w-8 h-8 opacity-40" />
                    <span>No se encontraron miembros con los filtros aplicados.</span>
                  </div>
                </td>
              </tr>
            ) : (
              filteredMembers.map((member) => (
                <tr
                  key={member.tag}
                  onClick={() => setSelectedMemberTagForHistory(member.tag)}
                  className="hover:bg-slate-800/40 transition-colors group cursor-pointer"
                >
                  {/* Member Name + Tag */}
                  <td className="py-3 px-4 sm:px-6">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex flex-col">
                        <span className="font-bold text-slate-100 group-hover:text-amber-400 transition-colors">
                          {member.name}
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">{member.tag}</span>
                      </div>
                      <span
                        className="opacity-0 group-hover:opacity-100 text-amber-400 transition-opacity"
                        title="Ver historial de 10 guerras"
                      >
                        <History className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </td>

                  {/* Role */}
                  <td className="py-3 px-3">
                    <RoleBadge role={member.role} />
                  </td>

                  {/* Trophies */}
                  <td className="py-3 px-3">
                    <div className="flex items-center gap-1.5 font-bold text-amber-300">
                      <Trophy className="w-3.5 h-3.5 text-amber-400/80" />
                      <span>{(member.trophies || 0).toLocaleString('es-ES')}</span>
                    </div>
                  </td>

                  {/* Donations */}
                  <td className="py-3 px-3">
                    <div className="flex flex-col">
                      <span className="font-semibold text-slate-200">
                        {(member.donations || 0).toLocaleString('es-ES')}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        Recibidas: {(member.donations_received || 0).toLocaleString('es-ES')}
                      </span>
                    </div>
                  </td>

                  {/* Last Seen */}
                  <td className="py-3 px-3">
                    {(() => {
                      const { label, dotColor } = formatRelativeTime(member.last_seen);
                      const fullDate = member.last_seen
                        ? new Date(member.last_seen).toLocaleString('es-ES', {
                            dateStyle: 'short',
                            timeStyle: 'short',
                          })
                        : 'Sin registro';
                      return (
                        <div className="flex items-center gap-2" title={`Última vez visto: ${fullDate}`}>
                          <span className={`w-2 h-2 rounded-full ${dotColor} flex-shrink-0`} />
                          <span className="text-slate-300 font-medium whitespace-nowrap">{label}</span>
                        </div>
                      );
                    })()}
                  </td>

                  {/* Reliability Score */}
                  <td className="py-3 px-3">
                    {(() => {
                      const scoreNum =
                        typeof member.reliability_score === 'number'
                          ? member.reliability_score
                          : parseFloat(String(member.reliability_score ?? 0)) || 0;
                      return (
                        <div
                          onClick={(e) => {
                            e.stopPropagation();
                            setReliabilityModalContext({
                              name: member.name,
                              tag: member.tag,
                              role: member.role,
                              reliabilityScore: scoreNum,
                            });
                          }}
                          className="flex items-center gap-2 max-w-[140px] cursor-pointer hover:opacity-80 transition-opacity"
                          title="Clic para entender por qué tiene este puntaje de confiabilidad"
                        >
                          <ReliabilityBadge score={scoreNum} />
                          <div className="flex-1 h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                            <div
                              className={`h-full rounded-full transition-all ${
                                scoreNum >= 80
                                  ? 'bg-emerald-500'
                                  : scoreNum >= 50
                                  ? 'bg-amber-500'
                                  : 'bg-rose-500'
                              }`}
                              style={{ width: `${Math.min(100, Math.max(0, scoreNum))}%` }}
                            />
                          </div>
                        </div>
                      );
                    })()}
                  </td>

                  {/* Active Status */}
                  <td className="py-3 px-3 text-center">
                    {member.is_active ? (
                      <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-semibold">
                        <Check className="w-3.5 h-3.5" /> Activo
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                        <X className="w-3.5 h-3.5" /> Inactivo
                      </span>
                    )}
                  </td>

                  {/* Action */}
                  <td className="py-3 px-4 sm:px-6 text-right">
                    {onGrantWarPass && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onGrantWarPass(member);
                        }}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-amber-500/20 text-slate-300 hover:text-amber-300 border border-slate-700 hover:border-amber-500/30 transition-all shadow-sm"
                        title="Otorgar Pase de Guerra"
                      >
                        <Ticket className="w-3.5 h-3.5 text-amber-400" />
                        <span>Pase</span>
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* War History Modal */}
      <PlayerWarHistoryModal
        memberTag={selectedMemberTagForHistory}
        isOpen={!!selectedMemberTagForHistory}
        onClose={() => setSelectedMemberTagForHistory(null)}
        onGrantWarPass={
          onGrantWarPass
            ? (tag) => {
                const m = members.find((mem) => mem.tag === tag);
                if (m) onGrantWarPass(m);
              }
            : undefined
        }
      />

      {/* Reliability Explainer Modal */}
      <ReliabilityModal
        isOpen={!!reliabilityModalContext}
        onClose={() => setReliabilityModalContext(null)}
        member={reliabilityModalContext !== 'general' ? reliabilityModalContext : null}
        onViewWarHistory={(tag) => setSelectedMemberTagForHistory(tag)}
      />
    </div>
  );
};
