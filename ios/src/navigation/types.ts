import type { NavigatorScreenParams } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { BottomTabScreenProps } from '@react-navigation/bottom-tabs';

/**
 * Type-safe navigation for Rally iOS app
 */

// Auth Stack Navigator Params
export type AuthStackParamList = {
  Login: undefined;
};

// Main Tab Navigator Params
export type MainTabParamList = {
  Dashboard: undefined;
  Availability: undefined;
  Team: undefined;
  Settings: undefined;
};

// Root Navigator Params
export type RootStackParamList = {
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
};

// Screen Props Types

// Auth Stack
export type LoginScreenProps = NativeStackScreenProps<AuthStackParamList, 'Login'>;

// Main Tabs
export type DashboardScreenProps = BottomTabScreenProps<MainTabParamList, 'Dashboard'>;
export type AvailabilityScreenProps = BottomTabScreenProps<MainTabParamList, 'Availability'>;
export type TeamScreenProps = BottomTabScreenProps<MainTabParamList, 'Team'>;
export type SettingsScreenProps = BottomTabScreenProps<MainTabParamList, 'Settings'>;

// Navigation declarations for useNavigation hook
declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}

