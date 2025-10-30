import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, clearAuthCookies } from '../client';
import { API_ENDPOINTS, LoginRequest } from '../endpoints';
import { AuthResponseSchema, UserSessionSchema, type AuthResponse, type UserSession } from '../types';
import { useAuthStore } from '../../state/auth.store';

/**
 * React Query hooks for authentication
 */

// Query keys
export const AUTH_KEYS = {
  session: ['auth', 'session'],
  user: ['auth', 'user'],
} as const;

/**
 * Hook to check current authentication status
 */
export function useCheckAuth() {
  const { setAuth, clearAuth } = useAuthStore();
  
  return useQuery({
    queryKey: AUTH_KEYS.session,
    queryFn: async (): Promise<UserSession> => {
      const response = await apiClient.get(API_ENDPOINTS.CHECK_AUTH);
      const data = UserSessionSchema.parse(response.data);
      
      // Update auth store
      if (data.authenticated && data.user) {
        setAuth(data.user);
      } else {
        clearAuth();
      }
      
      return data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false, // Don't retry auth checks
  });
}

/**
 * Hook to login user
 */
export function useLogin() {
  const queryClient = useQueryClient();
  const { setAuth } = useAuthStore();
  
  return useMutation({
    mutationFn: async (credentials: LoginRequest): Promise<AuthResponse> => {
      const response = await apiClient.post(API_ENDPOINTS.LOGIN, credentials);
      const data = AuthResponseSchema.parse(response.data);
      return data;
    },
    onSuccess: (data) => {
      if (data.status === 'success' && data.user) {
        // Update auth store with user data
        setAuth({
          id: 0, // Will be set from session check
          ...data.user,
          team_id: null,
          league_id: null,
        } as any);
        
        // Invalidate session query
        queryClient.invalidateQueries({ queryKey: AUTH_KEYS.session });
        
        if (__DEV__) {
          console.log('✅ Login successful:', data.user.email);
        }
      }
    },
    onError: (error) => {
      console.error('❌ Login failed:', error);
    },
  });
}

/**
 * Hook to logout user
 */
export function useLogout() {
  const queryClient = useQueryClient();
  const { clearAuth } = useAuthStore();
  
  return useMutation({
    mutationFn: async () => {
      // Call logout endpoint
      await apiClient.post(API_ENDPOINTS.LOGOUT);
      
      // Clear cookies
      await clearAuthCookies();
    },
    onSuccess: () => {
      // Clear auth store
      clearAuth();
      
      // Clear all queries
      queryClient.clear();
      
      if (__DEV__) {
        console.log('✅ Logout successful');
      }
    },
    onError: (error) => {
      console.error('❌ Logout failed:', error);
      
      // Even if API call fails, clear local state
      clearAuth();
      clearAuthCookies();
      queryClient.clear();
    },
  });
}

