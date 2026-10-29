/**
 * Типы для приложения
 */

export interface User {
  id: number;
  telegram_id: number;
  telegram_username?: string;
  full_name: string;
  bio?: string;
  skills: string[];
  role_preference?: string;
  experience_level: string;
  avatar_url?: string;
  created_at: string;
}

export interface Hackathon {
  id: number;
  name: string;
  description?: string;
  start_date: string;
  end_date: string;
  status: 'upcoming' | 'active' | 'finished';
  max_team_size: number;
  created_at: string;
}

export interface Team {
  id: number;
  hackathon_id: number;
  name: string;
  description?: string;
  captain_id: number;
  status: 'open' | 'closed';
  created_at: string;
  members?: TeamMember[];
}

export interface TeamMember {
  id: number;
  full_name: string;
  role_preference?: string;
  skills: string[];
}

export interface Invitation {
  id: number;
  team_id: number;
  user_id: number;
  sent_by_id: number;
  kind: 'invite' | 'application';
  status: 'pending' | 'accepted' | 'declined' | 'cancelled';
  created_at: string;
  responded_at?: string;
  team?: Team;
  sent_by?: User;
  user?: User;
}

export interface HackathonAnalytics {
  total_participants: number;
  total_teams: number;
  participants_without_team: number;
  participants_in_team: number;
  average_team_size: number;
  skills_frequency: Record<string, number>;
  experience_distribution: Record<string, number>;
}

