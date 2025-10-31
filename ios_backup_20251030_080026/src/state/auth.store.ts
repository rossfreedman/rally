import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * Zustand store for authentication state
 * Syncs with AsyncStorage for persistence across app restarts
 */

export interface UserData {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  tenniscores_player_id: string | null;
  team_id: number | null;
  league_id: number | null;
  club: string | null;
  series: string | null;
}

interface AuthState {
  isAuthenticated: boolean;
  user: UserData | null;
  isLoading: boolean;
}

interface AuthActions {
  setAuth: (user: UserData) => void;
  clearAuth: () => void;
  loadAuth: () => Promise<void>;
  setLoading: (loading: boolean) => void;
}

type AuthStore = AuthState & AuthActions;

const AUTH_STORAGE_KEY = '@rally_auth';

export const useAuthStore = create<AuthStore>((set, get) => ({
  // Initial state
  isAuthenticated: false,
  user: null,
  isLoading: true,

  // Set authenticated user
  setAuth: async (user: UserData) => {
    try {
      // Save to AsyncStorage
      await AsyncStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
      
      // Update state
      set({
        isAuthenticated: true,
        user,
        isLoading: false,
      });
      
      if (__DEV__) {
        console.log('🔐 Auth state updated:', user.email);
      }
    } catch (error) {
      console.error('❌ Error saving auth to AsyncStorage:', error);
    }
  },

  // Clear authentication
  clearAuth: async () => {
    try {
      // Remove from AsyncStorage
      await AsyncStorage.removeItem(AUTH_STORAGE_KEY);
      
      // Clear state
      set({
        isAuthenticated: false,
        user: null,
        isLoading: false,
      });
      
      if (__DEV__) {
        console.log('🔓 Auth state cleared');
      }
    } catch (error) {
      console.error('❌ Error clearing auth from AsyncStorage:', error);
    }
  },

  // Load authentication from AsyncStorage
  loadAuth: async () => {
    try {
      set({ isLoading: true });
      
      const storedAuth = await AsyncStorage.getItem(AUTH_STORAGE_KEY);
      
      if (storedAuth) {
        const user: UserData = JSON.parse(storedAuth);
        set({
          isAuthenticated: true,
          user,
          isLoading: false,
        });
        
        if (__DEV__) {
          console.log('🔐 Auth loaded from storage:', user.email);
        }
      } else {
        set({
          isAuthenticated: false,
          user: null,
          isLoading: false,
        });
        
        if (__DEV__) {
          console.log('🔓 No stored auth found');
        }
      }
    } catch (error) {
      console.error('❌ Error loading auth from AsyncStorage:', error);
      set({
        isAuthenticated: false,
        user: null,
        isLoading: false,
      });
    }
  },

  // Set loading state
  setLoading: (loading: boolean) => {
    set({ isLoading: loading });
  },
}));

// Export selectors for convenience
export const selectIsAuthenticated = (state: AuthStore) => state.isAuthenticated;
export const selectUser = (state: AuthStore) => state.user;
export const selectIsLoading = (state: AuthStore) => state.isLoading;

