import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import { TeamStatsSchema, type TeamStats } from '../types';

/**
 * React Query hooks for team data
 */

// Query keys
export const TEAM_KEYS = {
  stats: ['team', 'stats'],
  matches: ['team', 'matches'],
} as const;

/**
 * Hook to get team statistics
 * Uses get_mobile_team_data from backend
 */
export function useTeamStats() {
  return useQuery({
    queryKey: TEAM_KEYS.stats,
    queryFn: async (): Promise<TeamStats> => {
      const response = await apiClient.get(API_ENDPOINTS.TEAM_STATS);
      const data = TeamStatsSchema.parse(response.data);
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
  });
}

