/**
 * API Types for Basketball Analytics Platform
 *
 * These types match the Pydantic schemas from the FastAPI backend.
 */

// Base response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

// League types
export interface League {
  id: string;
  name: string;
  code: string;
  country: string | null;
  season_count: number;
  created_at: string;
  updated_at: string;
}

export interface Season {
  id: string;
  league_id: string;
  name: string;
  start_date: string;
  end_date: string;
  external_ids: Record<string, string>;
  created_at: string;
  updated_at: string;
}

// Team types
export interface Team {
  id: string;
  name: string;
  code: string | null;
  city: string | null;
  country: string | null;
  venue: string | null;
  external_ids: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface TeamRosterPlayer {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  jersey_number: string | null;
  positions: string[];
}

export interface TeamRoster {
  team: Team;
  season_id: string;
  season_name: string;
  players: TeamRosterPlayer[];
}

export interface TeamGameSummary {
  game_id: string;
  game_date: string;
  opponent_team_id: string;
  opponent_team_name: string;
  is_home: boolean;
  team_score: number;
  opponent_score: number;
  venue: string | null;
}

export interface TeamGameHistory {
  items: TeamGameSummary[];
  total: number;
}

// Player types
export interface Player {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  birth_date: string | null;
  nationality: string | null;
  height_cm: number | null;
  positions: string[];
  external_ids: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface PlayerTeamHistory {
  team_id: string;
  team_name: string;
  season_id: string;
  season_name: string;
  jersey_number: string | null;
  positions: string[];
}

export interface PlayerWithHistory extends Player {
  team_history: PlayerTeamHistory[];
}

export interface PlayerGameStats {
  id: string;
  game_id: string;
  player_id: string;
  player_name: string;
  team_id: string;
  minutes_played: number | null;
  is_starter: boolean;
  points: number;
  field_goals_made: number;
  field_goals_attempted: number;
  two_pointers_made: number;
  two_pointers_attempted: number;
  three_pointers_made: number;
  three_pointers_attempted: number;
  free_throws_made: number;
  free_throws_attempted: number;
  offensive_rebounds: number;
  defensive_rebounds: number;
  total_rebounds: number;
  assists: number;
  turnovers: number;
  steals: number;
  blocks: number;
  personal_fouls: number;
  plus_minus: number | null;
  efficiency: number | null;
  extra_stats: Record<string, unknown>;
  // Game context
  game_date: string;
  opponent_team_id: string;
  opponent_team_name: string;
  is_home: boolean;
  team_score: number;
  opponent_score: number;
}

export interface PlayerSeasonStats {
  id: string;
  player_id: string;
  player_name: string;
  team_id: string;
  team_name: string;
  season_id: string;
  season_name: string;
  league_code: string | null;
  games_played: number;
  games_started: number;
  total_minutes: number;
  total_points: number;
  avg_points: number;
  avg_rebounds: number;
  avg_assists: number;
  field_goal_pct: number | null;
  three_point_pct: number | null;
  free_throw_pct: number | null;
}

export interface PlayerCareerStats {
  player_id: string;
  player_name: string;
  career_games_played: number;
  career_games_started: number;
  career_points: number;
  career_rebounds: number;
  career_assists: number;
  career_steals: number;
  career_blocks: number;
  career_turnovers: number;
  career_avg_points: number;
  career_avg_rebounds: number;
  career_avg_assists: number;
  seasons: PlayerSeasonStats[];
}

// Game types
export interface Game {
  id: string;
  season_id: string;
  home_team_id: string;
  away_team_id: string;
  home_team_name?: string;
  away_team_name?: string;
  home_team?: Team;
  away_team?: Team;
  game_date: string;
  game_time: string | null;
  venue: string | null;
  status: string;
  home_score: number | null;
  away_score: number | null;
  external_ids: Record<string, string>;
  created_at: string;
  updated_at: string;
  // Box score data (included in game detail response)
  home_players?: PlayerGameStats[];
  away_players?: PlayerGameStats[];
  home_team_stats?: TeamStats;
  away_team_stats?: TeamStats;
}

export interface TeamStats {
  team_id: string;
  team_name: string;
  is_home: boolean;
  points: number;
  field_goals_made: number;
  field_goals_attempted: number;
  field_goal_pct: number;
  three_pointers_made: number;
  three_pointers_attempted: number;
  three_point_pct: number;
  free_throws_made: number;
  free_throws_attempted: number;
  free_throw_pct: number;
  offensive_rebounds: number;
  defensive_rebounds: number;
  total_rebounds: number;
  assists: number;
  turnovers: number;
  steals: number;
  blocks: number;
  personal_fouls: number;
}

export interface GameBoxScore {
  game: Game;
  home_team: Team;
  away_team: Team;
  home_players: PlayerGameStats[];
  away_players: PlayerGameStats[];
}

// Play-by-play types
export interface PlayByPlayEvent {
  id: string;
  game_id: string;
  event_number: number;
  period: number;
  clock: string;
  event_type: string;
  event_subtype: string | null;
  player_id: string | null;
  player_name: string | null;
  team_id: string;
  team_name: string;
  success: boolean | null;
  coord_x: number | null;
  coord_y: number | null;
  attributes: Record<string, unknown>;
  description: string | null;
  related_event_ids: string[];
}

export interface PlayByPlayResponse {
  game_id: string;
  events: PlayByPlayEvent[];
  total_events: number;
}

// Sync types
export type SyncStatus = 'STARTED' | 'COMPLETED' | 'FAILED' | 'PARTIAL';

export interface SyncLog {
  id: string;
  source: string;
  entity_type: string;
  status: SyncStatus;
  season_id: string | null;
  season_name: string | null;
  game_id: string | null;
  records_processed: number;
  records_created: number;
  records_updated: number;
  records_skipped: number;
  error_message: string | null;
  error_details: unknown;
  started_at: string;
  completed_at: string | null;
}

export interface SyncSourceStatus {
  name: string;
  enabled: boolean;
  auto_sync_enabled: boolean;
  sync_interval_minutes: number;
  running_syncs: number;
  latest_season_sync: string | null;
  latest_game_sync: string | null;
}

export interface SyncStatusResponse {
  sources: SyncSourceStatus[];
  total_running_syncs: number;
}

// SSE Event types for sync progress
export interface SyncStartEvent {
  event: 'start';
  phase: string;
  total: number;
  skipped: number;
}

export interface SyncProgressEvent {
  event: 'progress';
  current: number;
  total: number;
  game_id: string;
  status: string;
}

export interface SyncSyncedEvent {
  event: 'synced';
  game_id: string;
}

export interface SyncErrorEvent {
  event: 'error';
  game_id: string;
  error: string;
}

export interface SyncCompleteEvent {
  event: 'complete';
  sync_log: SyncLog;
}

export type SyncEvent =
  | SyncStartEvent
  | SyncProgressEvent
  | SyncSyncedEvent
  | SyncErrorEvent
  | SyncCompleteEvent;
