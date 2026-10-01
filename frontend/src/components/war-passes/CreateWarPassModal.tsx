import React, { useState, useEffect } from 'react';
import { X, Ticket, Calendar, User, FileText, AlertCircle, Loader2 } from 'lucide-react';
import { warPassesApi, clansApi } from '../../api/client';
import type { Clan, Member, WarPass } from '../../types/domain';

interface CreateWarPassModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (newPass: WarPass) => void;
  initialClanTag?: string;
  initialMemberTag?: string;
}

export const CreateWarPassModal: React.FC<CreateWarPassModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialClanTag,
  initialMemberTag,
}) => {
  const [clans, setClans] = useState<Clan[]>([]);
  const [selectedClanTag, setSelectedClanTag] = useState<string>(initialClanTag || '');
  const [members, setMembers] = useState<Member[]>([]);
  const [selectedMemberTag, setSelectedMemberTag] = useState<string>(initialMemberTag || '');

  const todayStr = new Date().toISOString().split('T')[0];
  const nextWeek = new Date();
  nextWeek.setDate(nextWeek.getDate() + 4);
  const nextWeekStr = nextWeek.toISOString().split('T')[0];

  const [startDate, setStartDate] = useState<string>(todayStr);
  const [endDate, setEndDate] = useState<string>(nextWeekStr);
  const [reason, setReason] = useState<string>('');

  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load clans on mount
  useEffect(() => {
    if (!isOpen) return;
    const loadClans = async () => {
      try {
        const clanList = await clansApi.list();
        setClans(clanList);
        if (!selectedClanTag && clanList.length > 0) {
          setSelectedClanTag(clanList[0].tag);
        }
      } catch {
        setError('Error al cargar clanes.');
      }
    };
    loadClans();
  }, [isOpen, selectedClanTag]);

  // Load members when selectedClanTag changes
  useEffect(() => {
    if (!selectedClanTag) return;
    const loadClanMembers = async () => {
      try {
        setIsLoadingMembers(true);
        const roster = await clansApi.getMembers(selectedClanTag);
        setMembers(roster);
        if (initialMemberTag && roster.some((m) => m.tag === initialMemberTag)) {
          setSelectedMemberTag(initialMemberTag);
        } else if (roster.length > 0 && !selectedMemberTag) {
          setSelectedMemberTag(roster[0].tag);
        }
      } catch {
        setMembers([]);
      } finally {
        setIsLoadingMembers(false);
      }
    };
    loadClanMembers();
  }, [selectedClanTag, initialMemberTag, selectedMemberTag]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMemberTag || !reason || !startDate || !endDate) {
      setError('Por favor completa todos los campos requeridos.');
      return;
    }

    if (new Date(startDate) > new Date(endDate)) {
      setError('La fecha de inicio no puede ser posterior a la fecha de fin.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      const created = await warPassesApi.create({
        member: selectedMemberTag,
        reason,
        start_date: startDate,
        end_date: endDate,
      });

      onSuccess(created);
      onClose();
    } catch {
      setError('No se pudo crear el Pase de Guerra. Verifica las fechas y los datos.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl relative overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
              <Ticket className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Otorgar Pase de Guerra</h2>
              <p className="text-xs text-slate-400">Exención de sanciones por ausencia justificada</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          {/* Clan select */}
          {clans.length > 1 && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Clan</label>
              <select
                value={selectedClanTag}
                onChange={(e) => {
                  setSelectedClanTag(e.target.value);
                  setSelectedMemberTag('');
                }}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
              >
                {clans.map((c) => (
                  <option key={c.tag} value={c.tag}>
                    {c.name} ({c.tag})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Member select */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center justify-between">
              <span>Miembro a Exentar</span>
              {isLoadingMembers && (
                <span className="text-[11px] text-amber-400 flex items-center gap-1 font-normal">
                  <Loader2 className="w-3 h-3 animate-spin" /> Cargando miembros...
                </span>
              )}
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                <User className="w-4 h-4" />
              </div>
              <select
                value={selectedMemberTag}
                onChange={(e) => setSelectedMemberTag(e.target.value)}
                required
                className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
              >
                <option value="">Selecciona un jugador...</option>
                {members.map((m) => (
                  <option key={m.tag} value={m.tag}>
                    {m.name} ({m.tag}) — {m.role}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Date Range */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Fecha de Inicio
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Calendar className="w-4 h-4" />
                </div>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Fecha de Fin
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Calendar className="w-4 h-4" />
                </div>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  required
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
                />
              </div>
            </div>
          </div>

          {/* Reason */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Motivo o Justificación
            </label>
            <div className="relative">
              <div className="absolute top-2.5 left-3 pointer-events-none text-slate-500">
                <FileText className="w-4 h-4" />
              </div>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="ej. Exámenes de final de semestre, viaje de trabajo, etc."
                rows={3}
                required
                className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500 resize-none"
              />
            </div>
          </div>

          {/* Actions */}
          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 rounded-xl text-xs font-bold bg-amber-500 text-slate-950 hover:bg-amber-400 transition-colors shadow-md shadow-amber-500/20 disabled:opacity-50 flex items-center gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Guardando...
                </>
              ) : (
                'Otorgar Pase'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
