import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Ticket, Plus, Trash2, Calendar, Shield, Loader2, CheckCircle2 } from 'lucide-react';
import { warPassesApi, clansApi } from '../api/client';
import type { WarPass, Clan } from '../types/domain';
import { CreateWarPassModal } from '../components/war-passes/CreateWarPassModal';

export const WarPassesPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialMember = searchParams.get('member') || undefined;
  const initialClan = searchParams.get('clan') || undefined;

  const [passes, setPasses] = useState<WarPass[]>([]);
  const [clans, setClans] = useState<Clan[]>([]);
  const [selectedClan, setSelectedClan] = useState<string>(initialClan || 'all');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(Boolean(initialMember));
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [todayStr] = useState<string>(() => new Date().toISOString().split('T')[0]);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [passesData, clansData] = await Promise.all([
        warPassesApi.list(selectedClan === 'all' ? undefined : selectedClan),
        clansApi.list(),
      ]);
      setPasses(Array.isArray(passesData) ? passesData : ((passesData as unknown as { results?: WarPass[] })?.results || []));
      setClans(Array.isArray(clansData) ? clansData : ((clansData as unknown as { results?: Clan[] })?.results || []));
    } catch {
      setPasses([]);
      setClans([]);
    } finally {
      setIsLoading(false);
    }
  }, [selectedClan]);

  useEffect(() => {
    const fetchData = async () => {
      await loadData();
    };
    fetchData();
  }, [loadData]);

  const handleDelete = async (id: number) => {
    if (!window.confirm('¿Estás seguro de que deseas revocar este Pase de Guerra?')) {
      return;
    }

    try {
      setDeletingId(id);
      await warPassesApi.delete(id);
      setPasses((prev) => prev.filter((p) => p.id !== id));
      setFeedback('Pase de Guerra revocado correctamente.');
      setTimeout(() => setFeedback(null), 4000);
    } catch {
      alert('Error al revocar el Pase de Guerra.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleCreated = (newPass: WarPass) => {
    setPasses((prev) => [newPass, ...prev]);
    setFeedback('Pase de Guerra otorgado exitosamente.');
    setTimeout(() => setFeedback(null), 4000);
  };

  const activeCount = useMemo(() => passes.filter((p) => p.is_active_now).length, [passes]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2.5">
              <Ticket className="w-6 h-6 text-amber-400" />
              Pases de Guerra
            </h1>
            {activeCount > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                {activeCount} activos hoy
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Gestión y auditoría de exenciones temporales por ausencias justificadas
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-lg shadow-amber-500/20 transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Otorgar Pase</span>
        </button>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2.5 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{feedback}</span>
        </div>
      )}

      {/* Filter Bar */}
      {clans.length > 1 && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400">Filtrar por Clan:</span>
          <select
            value={selectedClan}
            onChange={(e) => setSelectedClan(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-amber-500"
          >
            <option value="all">Todos los Clanes</option>
            {clans.map((c) => (
              <option key={c.tag} value={c.tag}>
                {c.name} ({c.tag})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Passes List / Table */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[30vh] gap-3">
          <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
          <span className="text-slate-400 text-sm">Cargando pases de guerra...</span>
        </div>
      ) : passes.length === 0 ? (
        <div className="p-12 rounded-2xl bg-slate-900 border border-slate-800 text-center">
          <Ticket className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h2 className="text-base font-bold text-slate-200">No hay pases de guerra registrados</h2>
          <p className="text-slate-400 text-xs mt-1 max-w-sm mx-auto">
            Otorga un pase a los miembros que tengan una ausencia justificada para eximirlos automáticamente de sanciones durante la River Race.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {passes.map((pass) => (
            <div
              key={pass.id}
              className={`bg-slate-900 border ${
                pass.is_active_now
                  ? 'border-emerald-500/40 shadow-emerald-500/5'
                  : 'border-slate-800'
              } rounded-2xl p-5 shadow-lg flex flex-col justify-between`}
            >
              <div>
                {/* Header: Member & Status */}
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20">
                      <Shield className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="font-extrabold text-sm text-slate-100 block">
                        {pass.member_name || pass.member}
                      </span>
                      <span className="font-mono text-[10px] text-amber-400">{pass.member}</span>
                    </div>
                  </div>

                  {pass.is_active_now ? (
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      Activo Hoy
                    </span>
                  ) : pass.end_date < todayStr ? (
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-500 border border-slate-700">
                      Finalizado
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-blue-500/20 text-blue-300 border border-blue-500/30">
                      Programado
                    </span>
                  )}
                </div>

                {/* Period */}
                <div className="bg-slate-950/70 p-2.5 rounded-xl border border-slate-800/80 mb-3 flex items-center gap-2 text-xs text-slate-300">
                  <Calendar className="w-4 h-4 text-purple-400 flex-shrink-0" />
                  <span>
                    Del <strong className="text-slate-100">{pass.start_date}</strong> al{' '}
                    <strong className="text-slate-100">{pass.end_date}</strong>
                  </span>
                </div>

                {/* Reason */}
                <div className="text-xs text-slate-300 bg-slate-800/40 p-3 rounded-xl border border-slate-700/30 mb-4">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                    Motivo
                  </span>
                  <p className="font-medium text-slate-200">{pass.reason}</p>
                </div>
              </div>

              {/* Footer: Delete / Revoke */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
                <span className="text-[10px]">
                  Registrado el {new Date(pass.created_at).toLocaleDateString('es-ES')}
                </span>
                <button
                  onClick={() => handleDelete(pass.id)}
                  disabled={deletingId === pass.id}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                  title="Revocar pase"
                >
                  {deletingId === pass.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      <CreateWarPassModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleCreated}
        initialClanTag={initialClan}
        initialMemberTag={initialMember}
      />
    </div>
  );
};
