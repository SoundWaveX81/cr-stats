import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Shield, AlertCircle, Loader2 } from 'lucide-react';
import { clansApi } from '../api/client';
import type { Clan, Member } from '../types/domain';
import { ClanHeaderCard } from '../components/clans/ClanHeaderCard';
import { RosterTable } from '../components/clans/RosterTable';

export const RosterPage: React.FC = () => {
  const { clanTag: urlClanTag } = useParams<{ clanTag?: string }>();
  const navigate = useNavigate();

  const [clans, setClans] = useState<Clan[]>([]);
  const [selectedClan, setSelectedClan] = useState<Clan | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Sync state
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncSuccess, setSyncSuccess] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  // Load all available clans
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
        setError('Error al cargar la lista de clanes. Verifica la conexión con el servidor.');
      } finally {
        setIsLoading(false);
      }
    };

    loadClans();
  }, [urlClanTag]);

  // Load members whenever selectedClan changes
  const loadMembers = useCallback(async (tag: string) => {
    try {
      const res = await clansApi.getMembers(tag);
      const roster: Member[] = Array.isArray(res) ? res : ((res as unknown as { results?: Member[] })?.results || []);
      setMembers(roster);
    } catch {
      setMembers([]);
    }
  }, []);

  useEffect(() => {
    if (selectedClan) {
      loadMembers(selectedClan.tag);
    }
  }, [selectedClan, loadMembers]);

  const handleClanChange = (newTag: string) => {
    const clan = clans.find((c) => c.tag === newTag);
    if (clan) {
      setSelectedClan(clan);
      navigate(`/clans/${encodeURIComponent(clan.tag)}`);
    }
  };

  const handleSync = async () => {
    if (!selectedClan) return;

    try {
      setIsSyncing(true);
      setSyncSuccess(null);
      setSyncError(null);

      const result = await clansApi.sync(selectedClan.tag);
      setSyncSuccess(result.message || 'Sincronización con Clash Royale completada.');

      // Update selected clan and refresh members
      setSelectedClan(result.clan);
      await loadMembers(selectedClan.tag);
    } catch {
      setSyncError('No se pudo sincronizar con la API de Clash Royale. Intenta más tarde.');
    } finally {
      setIsSyncing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <Loader2 className="w-8 h-8 text-amber-500 animate-spin" />
        <span className="text-slate-400 text-sm">Cargando clanes...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 flex items-start gap-4">
        <AlertCircle className="w-6 h-6 flex-shrink-0 mt-0.5" />
        <div>
          <h2 className="font-bold text-base mb-1">Ocurrió un error</h2>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (clans.length === 0) {
    return (
      <div className="p-12 rounded-2xl bg-slate-900 border border-slate-800 text-center">
        <Shield className="w-12 h-12 text-slate-600 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-slate-200">No hay clanes registrados</h2>
        <p className="text-slate-400 text-sm mt-1 max-w-md mx-auto">
          Registra un clan a través del panel de Django Admin o el endpoint de API para comenzar a monitorear la River Race.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Clan Selector Bar (if multi-clan) */}
      {clans.length > 1 && (
        <div className="flex items-center justify-between bg-slate-900/60 p-3 rounded-xl border border-slate-800">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Clan Seleccionado:
          </span>
          <select
            value={selectedClan?.tag || ''}
            onChange={(e) => handleClanChange(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-amber-500 font-semibold"
          >
            {clans.map((c) => (
              <option key={c.tag} value={c.tag}>
                {c.name} ({c.tag})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Clan Overview Card */}
      {selectedClan && (
        <ClanHeaderCard
          clan={selectedClan}
          onSync={handleSync}
          isSyncing={isSyncing}
          syncSuccess={syncSuccess}
          syncError={syncError}
        />
      )}

      {/* Members Roster Table */}
      <RosterTable
        members={members}
        onGrantWarPass={(member) => {
          navigate(`/war-passes?member=${encodeURIComponent(member.tag)}&clan=${encodeURIComponent(selectedClan?.tag || '')}`);
        }}
      />
    </div>
  );
};
