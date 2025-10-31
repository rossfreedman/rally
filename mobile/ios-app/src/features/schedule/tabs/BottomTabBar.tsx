import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing, Layout, Shadows } from '../../../theme/tokens';

export type TabType = 'home' | 'search' | 'availability' | 'profile';

interface Tab {
  id: TabType;
  label: string;
  icon: string;
}

interface BottomTabBarProps {
  activeTab: TabType;
  onTabPress: (tab: TabType) => void;
}

const tabs: Tab[] = [
  { id: 'home', label: 'Home', icon: '🏠' },
  { id: 'search', label: 'Search', icon: '🔍' },
  { id: 'availability', label: 'Availability', icon: '📅' },
  { id: 'profile', label: 'Profile', icon: '👤' },
];

export const BottomTabBar: React.FC<BottomTabBarProps> = ({ activeTab, onTabPress }) => {
  return (
    <View style={styles.container}>
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <TouchableOpacity
            key={tab.id}
            style={styles.tab}
            onPress={() => onTabPress(tab.id)}
            accessibilityLabel={tab.label}
            accessibilityState={{ selected: isActive }}
          >
            <Text style={[styles.icon, isActive && styles.iconActive]}>
              {tab.icon}
            </Text>
            <Text style={[styles.label, isActive && styles.labelActive]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    height: Layout.tabBarHeight,
    backgroundColor: Colors.bgPrimary,
    borderTopWidth: 1,
    borderTopColor: Colors.borderLight,
    ...Shadows.tabBar,
    paddingBottom: 34, // Safe area bottom
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.micro,
    minHeight: Layout.minTapTarget,
    borderRadius: BorderRadius.pill,
    marginHorizontal: 6,
    paddingVertical: 6,
    paddingHorizontal: 8,
  },
  icon: {
    fontSize: Layout.tabIconSize,
    color: Colors.textTertiary,
  },
  iconActive: {
    color: Colors.rallyDarkGreen,
  },
  label: {
    ...Typography.tabLabel,
    color: Colors.textTertiary,
  },
  labelActive: {
    color: Colors.rallyDarkGreen,
  },
});


