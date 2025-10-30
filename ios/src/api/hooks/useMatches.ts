import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import { MatchListSchema, type MatchList } from '../types';

/**
 * React Query hooks for match data
 */

// Query keys
export const MATCH_KEYS = {
  last3: ['matches', 'last3'],
  currentSeason: ['matches', 'currentSeason'],
  teamCurrentSeason: ['matches', 'teamCurrentSeason'],
} as const;

/**
 * Hook to get last 3 matches
 */
export function useLast3Matches() {
  return useQuery({
    queryKey: MATCH_KEYS.last3,
    queryFn: async (): Promise<MatchList> => {
      const response = await apiClient.get(API_ENDPOINTS.LAST_3_MATCHES);
      const data = MatchListSchema.parse(response.data);
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false, // Don't retry if not authenticated
  });
}

/**
 * Hook to get current season matches
 */
export function useCurrentSeasonMatches() {
  return useQuery({
    queryKey: MATCH_KEYS.currentSeason,
    queryFn: async (): Promise<MatchList> => {
      const response = await apiClient.get(API_ENDPOINTS.CURRENT_SEASON_MATCHES);
      const data = MatchListSchema.parse(response.data);
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false, // Don't retry if not authenticated
  });
}

