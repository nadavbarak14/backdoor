/**
 * API Client for Basketball Analytics Platform
 *
 * Provides typed fetch functions for all API endpoints.
 * Uses the Vite proxy in development (/api -> localhost:8000).
 */

import type {
  PaginatedResponse,
  League,
  Season,
  Team,
  TeamRoster,
  TeamGameHistory,
  Player,
  PlayerWithHistory,
  PlayerGameStats,
  PlayerCareerStats,
  Game,
  GameBoxScore,
  SyncLog,
  SyncStatusResponse,
} from '../types';

const API_BASE = '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API Error: ${response.status} - ${error}`);
  }

  return response.json();
}

// League endpoints
export async function getLeagues(
  skip = 0,
  limit = 100
): Promise<PaginatedResponse<League>> {
  return fetchJson(`${API_BASE}/leagues?skip=${skip}&limit=${limit}`);
}

export async function getLeague(leagueId: string): Promise<League> {
  return fetchJson(`${API_BASE}/leagues/${leagueId}`);
}

export async function getLeagueSeasons(
  leagueId: string,
  skip = 0,
  limit = 100
): Promise<Season[]> {
  return fetchJson(
    `${API_BASE}/leagues/${leagueId}/seasons?skip=${skip}&limit=${limit}`
  );
}

// Team endpoints
export interface TeamFilters {
  league_id?: string;
  season_id?: string;
  country?: string;
  search?: string;
}

export async function getTeams(
  filters: TeamFilters = {},
  skip = 0,
  limit = 100
): Promise<PaginatedResponse<Team>> {
  const params = new URLSearchParams();
  if (filters.league_id) params.set('league_id', filters.league_id);
  if (filters.season_id) params.set('season_id', filters.season_id);
  if (filters.country) params.set('country', filters.country);
  if (filters.search) params.set('search', filters.search);
  params.set('skip', skip.toString());
  params.set('limit', limit.toString());
  return fetchJson(`${API_BASE}/teams?${params}`);
}

export async function getTeam(teamId: string): Promise<Team> {
  return fetchJson(`${API_BASE}/teams/${teamId}`);
}

export async function getTeamRoster(
  teamId: string,
  seasonId?: string
): Promise<TeamRoster> {
  const params = seasonId ? `?season_id=${seasonId}` : '';
  return fetchJson(`${API_BASE}/teams/${teamId}/roster${params}`);
}

export async function getTeamGames(
  teamId: string,
  seasonId?: string,
  skip = 0,
  limit = 50
): Promise<TeamGameHistory> {
  const params = new URLSearchParams();
  if (seasonId) params.set('season_id', seasonId);
  params.set('skip', skip.toString());
  params.set('limit', limit.toString());
  return fetchJson(`${API_BASE}/teams/${teamId}/games?${params}`);
}

// Player endpoints
export interface PlayerFilters {
  team_id?: string;
  season_id?: string;
  position?: string;
  nationality?: string;
  search?: string;
}

export async function getPlayers(
  filters: PlayerFilters = {},
  skip = 0,
  limit = 100
): Promise<PaginatedResponse<Player>> {
  const params = new URLSearchParams();
  if (filters.team_id) params.set('team_id', filters.team_id);
  if (filters.season_id) params.set('season_id', filters.season_id);
  if (filters.position) params.set('position', filters.position);
  if (filters.nationality) params.set('nationality', filters.nationality);
  if (filters.search) params.set('search', filters.search);
  params.set('skip', skip.toString());
  params.set('limit', limit.toString());
  return fetchJson(`${API_BASE}/players?${params}`);
}

export async function getPlayer(playerId: string): Promise<PlayerWithHistory> {
  return fetchJson(`${API_BASE}/players/${playerId}`);
}

export async function getPlayerGames(
  playerId: string,
  seasonId?: string,
  skip = 0,
  limit = 50
): Promise<PaginatedResponse<PlayerGameStats>> {
  const params = new URLSearchParams();
  if (seasonId) params.set('season_id', seasonId);
  params.set('skip', skip.toString());
  params.set('limit', limit.toString());
  return fetchJson(`${API_BASE}/players/${playerId}/games?${params}`);
}

export async function getPlayerStats(playerId: string): Promise<PlayerCareerStats> {
  return fetchJson(`${API_BASE}/players/${playerId}/stats`);
}

// Game endpoints
export interface GameFilters {
  season_id?: string;
  team_id?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}

export async function getGames(
  filters: GameFilters = {},
  skip = 0,
  limit = 50
): Promise<PaginatedResponse<Game>> {
  const params = new URLSearchParams();
  if (filters.season_id) params.set('season_id', filters.season_id);
  if (filters.team_id) params.set('team_id', filters.team_id);
  if (filters.status) params.set('status', filters.status);
  if (filters.start_date) params.set('start_date', filters.start_date);
  if (filters.end_date) params.set('end_date', filters.end_date);
  params.set('skip', skip.toString());
  params.set('limit', limit.toString());
  return fetchJson(`${API_BASE}/games?${params}`);
}

export async function getGame(gameId: string): Promise<Game> {
  return fetchJson(`${API_BASE}/games/${gameId}`);
}

export async function getGameBoxScore(gameId: string): Promise<GameBoxScore> {
  return fetchJson(`${API_BASE}/games/${gameId}/boxscore`);
}

// Sync endpoints
export async function getSyncStatus(): Promise<SyncStatusResponse> {
  return fetchJson(`${API_BASE}/sync/status`);
}

export async function getSyncLogs(
  filters: {
    source?: string;
    status?: string;
    page?: number;
    page_size?: number;
  } = {}
): Promise<PaginatedResponse<SyncLog>> {
  const params = new URLSearchParams();
  if (filters.source) params.set('source', filters.source);
  if (filters.status) params.set('status', filters.status);
  params.set('page', (filters.page ?? 1).toString());
  params.set('page_size', (filters.page_size ?? 20).toString());
  return fetchJson(`${API_BASE}/sync/logs?${params}`);
}

export async function triggerSync(
  source: string,
  seasonId: string,
  includePbp = false
): Promise<SyncLog> {
  return fetchJson(
    `${API_BASE}/sync/${source}/season/${seasonId}?include_pbp=${includePbp}`,
    { method: 'POST' }
  );
}

// SSE endpoint for streaming sync
export function createSyncStream(
  source: string,
  seasonId: string,
  includePbp = false
): EventSource {
  // For SSE, we need to use a workaround since EventSource only supports GET
  // We'll use fetch with streaming instead
  const url = `${API_BASE}/sync/${source}/season/${seasonId}/stream?include_pbp=${includePbp}`;
  return new EventSource(url);
}

// Alternative: Fetch-based SSE for POST requests
export async function* streamSync(
  source: string,
  seasonId: string,
  includePbp = false
): AsyncGenerator<{ event: string; data: unknown }> {
  const url = `${API_BASE}/sync/${source}/season/${seasonId}/stream?include_pbp=${includePbp}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Sync failed: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events
    while (buffer.includes('\n\n')) {
      const [eventStr, rest] = buffer.split('\n\n', 2);
      buffer = rest || '';

      let eventType = 'message';
      let eventData: unknown = null;

      for (const line of eventStr.split('\n')) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7);
        } else if (line.startsWith('data: ')) {
          try {
            eventData = JSON.parse(line.slice(6));
          } catch {
            eventData = line.slice(6);
          }
        }
      }

      if (eventData !== null) {
        yield { event: eventType, data: eventData };
      }
    }
  }
}
