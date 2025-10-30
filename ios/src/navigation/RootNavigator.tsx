import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { ActivityIndicator, View } from 'react-native';
import { useAuthStore } from '../state/auth.store';
import type { RootStackParamList, AuthStackParamList, MainTabParamList } from './types';

// Screens
import LoginScreen from '../screens/Auth/LoginScreen';
import DashboardScreen from '../screens/Dashboard/DashboardScreen';
import AvailabilityScreen from '../screens/Availability/AvailabilityScreen';
import TeamScreen from '../screens/Team/TeamScreen';
import SettingsScreen from '../screens/Auth/LoginScreen'; // Placeholder

const RootStack = createNativeStackNavigator<RootStackParamList>();
const AuthStack = createNativeStackNavigator<AuthStackParamList>();
const MainTab = createBottomTabNavigator<MainTabParamList>();

/**
 * Auth Stack Navigator
 * Screens available before authentication
 */
function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
    </AuthStack.Navigator>
  );
}

/**
 * Main Tab Navigator
 * Screens available after authentication
 */
function MainNavigator() {
  return (
    <MainTab.Navigator
      screenOptions={{
        headerShown: true,
        headerStyle: {
          backgroundColor: '#045454', // Rally dark green
        },
        headerTintColor: '#fff',
        tabBarActiveTintColor: '#bff863', // Rally bright green
        tabBarInactiveTintColor: '#999',
      }}
    >
      <MainTab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          title: 'Rally',
          tabBarLabel: 'Home',
        }}
      />
      <MainTab.Screen
        name="Availability"
        component={AvailabilityScreen}
        options={{
          title: 'Schedule',
          tabBarLabel: 'Schedule',
        }}
      />
      <MainTab.Screen
        name="Team"
        component={TeamScreen}
        options={{
          title: 'My Team',
        }}
      />
      <MainTab.Screen
        name="Settings"
        component={SettingsScreen}
        options={{
          title: 'Settings',
        }}
      />
    </MainTab.Navigator>
  );
}

/**
 * Loading Screen
 * Shown while checking authentication status
 */
function LoadingScreen() {
  return (
    <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
      <ActivityIndicator size="large" color="#045454" />
    </View>
  );
}

/**
 * Root Navigator
 * Conditionally renders Auth or Main based on authentication status
 */
export default function RootNavigator() {
  const { isAuthenticated, isLoading, loadAuth } = useAuthStore();

  // Load authentication state on mount
  useEffect(() => {
    loadAuth();
  }, [loadAuth]);

  // Show loading screen while checking auth
  if (isLoading) {
    return (
      <NavigationContainer>
        <LoadingScreen />
      </NavigationContainer>
    );
  }

  return (
    <NavigationContainer>
      <RootStack.Navigator screenOptions={{ headerShown: false }}>
        {isAuthenticated ? (
          <RootStack.Screen name="Main" component={MainNavigator} />
        ) : (
          <RootStack.Screen name="Auth" component={AuthNavigator} />
        )}
      </RootStack.Navigator>
    </NavigationContainer>
  );
}

