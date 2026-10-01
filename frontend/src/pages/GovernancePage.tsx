import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { Award, Filter, Loader2, CheckCircle2, ShieldAlert } from 'lucide-react';
import { rosterActionsApi, clansApi } from '../api/client';
import type { RosterAction, Clan, ActionStatus } from '../types/domain';
import { RosterActionCard } from '../components/governance/RosterActionCard';

export const GovernancePage: React.FC = () => {
  const [actions, setActions] = useState<RosterAction[]>([]);
  const [clans, setClans] = useState<Clan[]>([]);
  const [selectedClan, setSelectedClan] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<ActionStatus | 'all'>('pending');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [actionsData, clansData] = await Promise.all([
        rosterActionsApi.list(),
        clansApi.list(),
      ]);
      setActions(Array.isArray(actionsData) ? actionsData : ((actionsData as unknown as { results?: RosterAction[] })?.results || []));
      setClans(Array.isArray(clansData) ? clansData : ((clansData as unknown as { results?: Clan[] })?.results || []));
    } catch {
      setActions([]);
      setClans([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExecute = async (id: number) => {
    try {
      setProcessingId(id);
      const res = await rosterActionsApi.execute(id);
      setFeedbackMessage(res.message);
      setActions((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'executed', executed_at: new Date().toISOString() } : a))
      );
      setTimeout(() => setFeedbackMessage(null), 4000);
    } catch {
      alert('Error al marcar la acción como ejecutada.');
    } finally {
      setProcessingId(null);
    }
  };

  const handleDismiss = async (id: number) => {
    try {
      setProcessingId(id);
      const res = await rosterActionsApi.dismiss(id);
      setFeedbackMessage(res.message);
      setActions((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'dismissed' } : a))
      );
      setTimeout(() => setFeedbackMessage(null), 4000);
    } catch {
      alert('Error al descartar la acción.');
    } finally {
      setProcessingId(null);
    }
  };

  const pendingCount = useMemo(
    () => actions.filter((a) => a.status === 'pending').length,
    [actions]
  );

  const filteredActions = useMemo(() => {
    return actions.filter((action) => {
      const matchStatus = selectedStatus === 'all' || action.status === selectedStatus;
      const matchClan = selectedClan === 'all' || action.clan === selectedClan;
      const matchType = selectedType === 'all' || action.action_type === selectedType;
      return matchStatus && matchClan && matchType;
    });
  }, [actions, selectedStatus, selectedClan, selectedType]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2.5">
              <Award className="w-6 h-6 text-amber-400" />
              Acciones de Roster
            </h1>
            {pendingCount > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                {pendingCount} pendientes
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Revisión y auditoría de sanciones automáticas y ascensos recomendados
          </p>
        </div>
      </div>

      {/* Feedback banner */}
      {feedbackMessage && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center gap-2.5 animate-fade-in">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          <span>{feedbackMessage}</span>
        </div>
      )}

      {/* Filter and Tab Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
        {/* Status Tabs */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-950 rounded-xl border border-slate-800">
          {(['pending', 'executed', 'dismissed', 'all'] as const).map((status) => {
            const labels: Record<string, string> = {
              pending: 'Pendientes',
              executed: 'Ejecutadas',
              dismissed: 'Descartadas',
              all: 'Todas',
            };
            const isActive = selectedStatus === status;
            return (
              <button
                key={status}
                onClick={() => setSelectedStatus(status)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-amber-500 text-slate-950 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {labels[status]}
              </button>
            );
          })}
        </div>

        {/* Dropdowns (Clan & Action Type) */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-500 hidden sm:block" />
            <select
              value={selectedClan}
              onChange={(e) => setSelectedClan(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              <option value="all">Todos los Clanes</option>
              {clans.map((c) => (
                <option key={c.tag} value={c.tag}>
                  {c.name} ({c.tag})
                </option>
              ))}
            </select>
          </div>

          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-amber-500"
          >
            <option value="all">Todos los Tipos</option>
            <option value="kick">Expulsión</option>
            <option value="demote_member">Descenso a Miembro</option>
            <option value="promote_elder">Ascenso a Veterano</option>
            <option value="leadership_notice">Aviso a Liderazgo</option>
          </select>
        </div>
      </div>

      {/* Grid of Actions */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[30vh] gap-3">
          <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
          <span className="text-slate-400 text-sm">Cargando acciones de roster...</span>
        </div>
      ) : filteredActions.length === 0 ? (
        <div className="p-12 rounded-2xl bg-slate-900 border border-slate-800 text-center">
          <ShieldAlert className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h2 className="text-base font-bold text-slate-200">
            No hay acciones registradas con los filtros seleccionados
          </h2>
          <p className="text-slate-400 text-xs mt-1 max-w-sm mx-auto">
            Cuando el motor de gobernanza evalúe las jornadas de guerra, las recomendaciones de expulsión, descenso y ascenso aparecerán aquí.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredActions.map((action) => (
            <RosterActionCard
              key={action.id}
              action={action}
              onExecute={handleExecute}
              onDismiss={handleDismiss}
              isProcessing={processingId === action.id}
            />
          ))}
        </div>
      )}
    </div>
  );
};
