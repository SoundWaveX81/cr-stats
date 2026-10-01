export type ClanRole = 'leader' | 'coLeader' | 'elder' | 'member';

export type ActionType = 'kick' | 'demote_member' | 'promote_elder' | 'leadership_notice';

export type ActionStatus = 'pending' | 'executed' | 'dismissed';

export interface Clan {
  tag: string;
  name: string;
  medal_threshold: number;
  war_day_reset_time: string;
  is_active: boolean;
  members_count: number;
  created_at: string;
  updated_at: string;
}

export interface Member {
  tag: string;
  name: string;
  role: ClanRole;
  reliability_score: number | string;
  trophies: number;
  donations: number;
  donations_received: number;
  last_seen: string | null;
  is_active: boolean;
  joined_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WarPass {
  id: number;
  member: string; // Member tag
  member_name?: string;
  reason: string;
  start_date: string;
  end_date: string;
  is_active_now: boolean;
  created_at: string;
}

export interface RosterAction {
  id: number;
  clan: string;
  clan_name?: string;
  member: string;
  member_tag?: string;
  member_name?: string;
  member_role?: string;
  action_type: ActionType;
  reason: string;
  status: ActionStatus;
  executed_at: string | null;
  created_at: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface UserProfile {
  username: string;
}

export interface CompetingClan {
  rank: number;
  tag: string;
  name: string;
  badge_id?: number;
  fame: number;
  clan_score: number;
  is_user_clan: boolean;
}

export interface WarParticipant {
  tag: string;
  name: string;
  role: ClanRole;
  attacks_used: number;
  attacks_pending: number;
  medals: number;
  boat_attacks: number;
  has_war_pass: boolean;
  war_pass_reason?: string | null;
}

export interface WarStats {
  total_members: number;
  total_attacks_possible: number;
  total_attacks_used: number;
  total_attacks_pending: number;
  potential_points_max: number;
  potential_max_fame: number;
  first_place_fame: number;
  gap_to_first: number;
  wins_needed_for_first: number;
}

export interface RaceInfo {
  state: string;
  section_index: number;
  period_index: number;
  day_index: number;
  day_type: 'training' | 'war' | string;
}

export interface CurrentWarOverview {
  clan: {
    tag: string;
    name: string;
    fame: number;
    clan_score: number;
    position: number;
    total_clans: number;
  };
  race: RaceInfo;
  stats: WarStats;
  clans: CompetingClan[];
  participants: WarParticipant[];
}
