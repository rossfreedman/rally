import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { API_ENDPOINTS, UpdateSettingsRequest } from '../endpoints';
import { UserSettingsSchema, type UserSettings } from '../types';

/**
 * React Query hooks for user settings
 */

// Query keys
export const SETTINGS_KEYS = {
  user: ['settings', 'user'],
} as const;

/**
 * Hook to get user settings
 */
export function useUserSettings() {
  return useQuery({
    queryKey: SETTINGS_KEYS.user,
    queryFn: async (): Promise<UserSettings> => {
      const response = await apiClient.get(API_ENDPOINTS.GET_USER_SETTINGS);
      const data = UserSettingsSchema.parse(response.data);
      return data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes (settings don't change often)
    cacheTime: 30 * 60 * 1000, // 30 minutes
  });
}

/**
 * Hook to update user settings
 */
export function useUpdateSettings() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (settings: UpdateSettingsRequest) => {
      const response = await apiClient.post(API_ENDPOINTS.UPDATE_SETTINGS, settings);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate settings query to refetch
      queryClient.invalidateQueries({ queryKey: SETTINGS_KEYS.user });
      
      if (__DEV__) {
        console.log('✅ Settings updated successfully');
      }
    },
    onError: (error) => {
      console.error('❌ Failed to update settings:', error);
    },
  });
}

