import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { API_ENDPOINTS, SetAvailabilityRequest } from '../endpoints';
import { AvailabilitySchema, type Availability } from '../types';

/**
 * React Query hooks for player availability
 */

// Query keys
export const AVAILABILITY_KEYS = {
  user: ['availability', 'user'],
  byDate: (date: string) => ['availability', 'date', date],
} as const;

/**
 * Hook to get user availability
 */
export function useUserAvailability() {
  return useQuery({
    queryKey: AVAILABILITY_KEYS.user,
    queryFn: async () => {
      const response = await apiClient.get(API_ENDPOINTS.GET_USER_AVAILABILITY);
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes (availability changes frequently)
    cacheTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to set availability for a specific match
 */
export function useSetAvailability() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (request: SetAvailabilityRequest): Promise<Availability> => {
      const response = await apiClient.post(API_ENDPOINTS.AVAILABILITY, request);
      const data = AvailabilitySchema.parse(response.data);
      return data;
    },
    onSuccess: (data) => {
      // Invalidate availability queries
      queryClient.invalidateQueries({ queryKey: AVAILABILITY_KEYS.user });
      
      if (data.availability?.match_date) {
        queryClient.invalidateQueries({ 
          queryKey: AVAILABILITY_KEYS.byDate(data.availability.match_date) 
        });
      }
      
      if (__DEV__) {
        console.log('✅ Availability updated successfully');
      }
    },
    onError: (error) => {
      console.error('❌ Failed to update availability:', error);
    },
  });
}

