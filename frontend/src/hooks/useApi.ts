/**
 * React Query Hooks for API Data Fetching
 *
 * Provides type-safe hooks for all API endpoints with caching,
 * refetching, and loading states.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../api/client';
import type { TeamFilters, PlayerFilters, GameFilters, PbpFilters } from '../api/client';

// Query keys for cache management
export const queryKeys = {
  leagues: ['leagues'] as const,
  league: (id: string) => ['league', id] as const,
  leagueSeasons: (id: string) => ['league', id, 'seasons'] as const,
  teams: (filters: TeamFilters) => ['teams', filters] as const,
  team: (id: string) => ['team', id] as const,
  teamRoster: (id: string, seasonId?: string) =>
    ['team', id, 'roster', seasonId] as const,
  teamGames: (id: string, seasonId?: string) =>
    ['team', id, 'games', seasonId] as const,
  players: (filters: PlayerFilters) => ['players', filters] as const,
  player: (id: string) => ['player', id] as const,
  playerGames: (id: string, seasonId?: string) =>
    ['player', id, 'games', seasonId] as const,
  playerStats: (id: string) => ['player', id, 'stats'] as const,
  games: (filters: GameFilters) => ['games', filters] as const,
  game: (id: string) => ['game', id] as const,
  gameBoxScore: (id: string) => ['game', id, 'boxscore'] as const,
  gamePbp: (id: string, filters: PbpFilters) => ['game', id, 'pbp', filters] as const,
  syncStatus: ['sync', 'status'] as const,
  syncLogs: (filters: object) => ['sync', 'logs', filters] as const,
};

// League hooks
export function useLeagues(skip = 0, limit = 100) {
  return useQuery({
    queryKey: [...queryKeys.leagues, { skip, limit }],
    queryFn: () => api.getLeagues(skip, limit),
  });
}

export function useLeague(leagueId: string) {
  return useQuery({
    queryKey: queryKeys.league(leagueId),
    queryFn: () => api.getLeague(leagueId),
    enabled: !!leagueId,
  });
}

export function useLeagueSeasons(leagueId: string) {
  return useQuery({
    queryKey: queryKeys.leagueSeasons(leagueId),
    queryFn: () => api.getLeagueSeasons(leagueId),
    enabled: !!leagueId,
  });
}

// Team hooks
export function useTeams(filters: TeamFilters = {}, skip = 0, limit = 100) {
  return useQuery({
    queryKey: [...queryKeys.teams(filters), { skip, limit }],
    queryFn: () => api.getTeams(filters, skip, limit),
  });
}

export function useTeam(teamId: string) {
  return useQuery({
    queryKey: queryKeys.team(teamId),
    queryFn: () => api.getTeam(teamId),
    enabled: !!teamId,
  });
}

export function useTeamRoster(teamId: string, seasonId?: string) {
  return useQuery({
    queryKey: queryKeys.teamRoster(teamId, seasonId),
    queryFn: () => api.getTeamRoster(teamId, seasonId),
    enabled: !!teamId,
  });
}

export function useTeamGames(teamId: string, seasonId?: string) {
  return useQuery({
    queryKey: queryKeys.teamGames(teamId, seasonId),
    queryFn: () => api.getTeamGames(teamId, seasonId),
    enabled: !!teamId,
  });
}

// Player hooks
export function usePlayers(filters: PlayerFilters = {}, skip = 0, limit = 100) {
  return useQuery({
    queryKey: [...queryKeys.players(filters), { skip, limit }],
    queryFn: () => api.getPlayers(filters, skip, limit),
  });
}

export function usePlayer(playerId: string) {
  return useQuery({
    queryKey: queryKeys.player(playerId),
    queryFn: () => api.getPlayer(playerId),
    enabled: !!playerId,
  });
}

export function usePlayerGames(playerId: string, seasonId?: string) {
  return useQuery({
    queryKey: queryKeys.playerGames(playerId, seasonId),
    queryFn: () => api.getPlayerGames(playerId, seasonId),
    enabled: !!playerId,
  });
}

export function usePlayerStats(playerId: string) {
  return useQuery({
    queryKey: queryKeys.playerStats(playerId),
    queryFn: () => api.getPlayerStats(playerId),
    enabled: !!playerId,
  });
}

// Game hooks
export function useGames(filters: GameFilters = {}, skip = 0, limit = 50) {
  return useQuery({
    queryKey: [...queryKeys.games(filters), { skip, limit }],
    queryFn: () => api.getGames(filters, skip, limit),
  });
}

export function useGame(gameId: string) {
  return useQuery({
    queryKey: queryKeys.game(gameId),
    queryFn: () => api.getGame(gameId),
    enabled: !!gameId,
  });
}

export function useGameBoxScore(gameId: string) {
  return useQuery({
    queryKey: queryKeys.gameBoxScore(gameId),
    queryFn: () => api.getGameBoxScore(gameId),
    enabled: !!gameId,
  });
}

export function useGamePbp(gameId: string, filters: PbpFilters = {}) {
  return useQuery({
    queryKey: queryKeys.gamePbp(gameId, filters),
    queryFn: () => api.getGamePbp(gameId, filters),
    enabled: !!gameId,
  });
}

// Sync hooks
export function useSyncStatus() {
  return useQuery({
    queryKey: queryKeys.syncStatus,
    queryFn: api.getSyncStatus,
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

export function useSyncLogs(filters: object = {}) {
  return useQuery({
    queryKey: queryKeys.syncLogs(filters),
    queryFn: () => api.getSyncLogs(filters),
  });
}

export function useTriggerSync() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      source,
      seasonId,
      includePbp,
    }: {
      source: string;
      seasonId: string;
      includePbp?: boolean;
    }) => api.triggerSync(source, seasonId, includePbp),
    onSuccess: () => {
      // Invalidate sync-related queries
      queryClient.invalidateQueries({ queryKey: ['sync'] });
    },
  });
}
