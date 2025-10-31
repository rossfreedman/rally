import { create } from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * Zustand store for app settings (client-side preferences)
 * Separate from server-side user settings
 */

interface SettingsState {
  // Theme preferences
  theme: 'light' | 'dark' | 'system';
  
  // Notification preferences (local to app)
  localNotificationsEnabled: boolean;
  
  // API environment (development/production)
  apiEnvironment: 'development' | 'production';
  
  // Loading state
  isLoading: boolean;
}

interface SettingsActions {
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setLocalNotifications: (enabled: boolean) => void;
  setApiEnvironment: (env: 'development' | 'production') => void;
  loadSettings: () => Promise<void>;
  resetSettings: () => Promise<void>;
}

type SettingsStore = SettingsState & SettingsActions;

const SETTINGS_STORAGE_KEY = '@rally_settings';

const DEFAULT_SETTINGS: SettingsState = {
  theme: 'system',
  localNotificationsEnabled: true,
  apiEnvironment: 'production',
  isLoading: false,
};

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  // Initial state
  ...DEFAULT_SETTINGS,

  // Set theme
  setTheme: async (theme: 'light' | 'dark' | 'system') => {
    try {
      const currentSettings = { ...get(), theme };
      await AsyncStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(currentSettings));
      set({ theme });
      
      if (__DEV__) {
        console.log('🎨 Theme updated:', theme);
      }
    } catch (error) {
      console.error('❌ Error saving theme:', error);
    }
  },

  // Set local notifications
  setLocalNotifications: async (enabled: boolean) => {
    try {
      const currentSettings = { ...get(), localNotificationsEnabled: enabled };
      await AsyncStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(currentSettings));
      set({ localNotificationsEnabled: enabled });
      
      if (__DEV__) {
        console.log('🔔 Local notifications:', enabled ? 'enabled' : 'disabled');
      }
    } catch (error) {
      console.error('❌ Error saving notification setting:', error);
    }
  },

  // Set API environment
  setApiEnvironment: async (env: 'development' | 'production') => {
    try {
      const currentSettings = { ...get(), apiEnvironment: env };
      await AsyncStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(currentSettings));
      set({ apiEnvironment: env });
      
      if (__DEV__) {
        console.log('🌐 API environment:', env);
      }
    } catch (error) {
      console.error('❌ Error saving API environment:', error);
    }
  },

  // Load settings from AsyncStorage
  loadSettings: async () => {
    try {
      set({ isLoading: true });
      
      const storedSettings = await AsyncStorage.getItem(SETTINGS_STORAGE_KEY);
      
      if (storedSettings) {
        const settings = JSON.parse(storedSettings);
        set({
          ...settings,
          isLoading: false,
        });
        
        if (__DEV__) {
          console.log('⚙️ Settings loaded from storage');
        }
      } else {
        set({
          ...DEFAULT_SETTINGS,
          isLoading: false,
        });
        
        if (__DEV__) {
          console.log('⚙️ Using default settings');
        }
      }
    } catch (error) {
      console.error('❌ Error loading settings:', error);
      set({
        ...DEFAULT_SETTINGS,
        isLoading: false,
      });
    }
  },

  // Reset to default settings
  resetSettings: async () => {
    try {
      await AsyncStorage.removeItem(SETTINGS_STORAGE_KEY);
      set(DEFAULT_SETTINGS);
      
      if (__DEV__) {
        console.log('🔄 Settings reset to defaults');
      }
    } catch (error) {
      console.error('❌ Error resetting settings:', error);
    }
  },
}));

// Export selectors
export const selectTheme = (state: SettingsStore) => state.theme;
export const selectLocalNotificationsEnabled = (state: SettingsStore) =>
  state.localNotificationsEnabled;
export const selectApiEnvironment = (state: SettingsStore) => state.apiEnvironment;

