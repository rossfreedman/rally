import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ScrollView, Animated } from 'react-native';
import { Colors, Typography, Spacing, BorderRadius } from '../../../theme/tokens';

interface MenuItem {
  id: string;
  label: string;
  icon: string;
}

interface MenuDrawerProps {
  visible: boolean;
  onClose: () => void;
  selectedItemId?: string;
  onItemPress?: (itemId: string) => void;
}

const menuItems: MenuItem[] = [
  { id: 'home', label: 'Home', icon: '⌂' },
  { id: 'schedule', label: 'Schedule', icon: '⌚' },
  { id: 'availability', label: 'Availability', icon: '☑' },
  { id: 'polls', label: 'Polls', icon: '☰' },
  { id: 'stats', label: 'Stats', icon: '≣' },
  { id: 'scout', label: 'Scout', icon: '▦' },
  { id: 'play', label: 'Play', icon: '▶' },
  { id: 'improve', label: 'Improve', icon: '↗' },
  { id: 'support', label: 'Support', icon: '⚑' },
  // Use text variation selector to force monochrome rendering for the bag icon
  { id: 'merch', label: 'Rally Merch', icon: '\u{1F45C}\uFE0E' },
  { id: 'captain', label: "Captain's Corner", icon: '⚙' },
];

export const MenuDrawer: React.FC<MenuDrawerProps> = ({
  visible,
  onClose,
  selectedItemId,
  onItemPress,
}) => {
  const NAVBAR_HEIGHT = 147; // match TopBar height so drawer sits below it
  const slideAnim = React.useRef(new Animated.Value(-1000)).current;
  const overlayOpacity = React.useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    if (visible) {
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.timing(overlayOpacity, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: -1000,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.timing(overlayOpacity, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [visible, slideAnim, overlayOpacity]);

  if (!visible) return null;

  const handleItemPress = (itemId: string) => {
    onItemPress?.(itemId);
    onClose();
  };

  return (
    <View style={styles.container} pointerEvents={visible ? 'box-none' : 'none'}>
      {/* Overlay */}
      <Animated.View
        style={[
          styles.overlay,
          {
            opacity: overlayOpacity,
            top: NAVBAR_HEIGHT,
          },
        ]}
        pointerEvents={visible ? 'auto' : 'none'}
      >
        <TouchableOpacity
          style={StyleSheet.absoluteFill}
          onPress={onClose}
          activeOpacity={1}
        />
      </Animated.View>

      {/* Menu Drawer */}
      <Animated.View
        style={[
          styles.drawer,
          {
            transform: [{ translateX: slideAnim }],
            top: NAVBAR_HEIGHT,
            width: '100%',
          },
        ]}
      >
        {/* Menu Items */}
        <ScrollView
          style={styles.menuContent}
          contentContainerStyle={styles.menuContentContainer}
          showsVerticalScrollIndicator={true}
        >
          {menuItems.map((item) => {
            const isSelected = item.id === selectedItemId;
            return (
              <TouchableOpacity
                key={item.id}
                style={[styles.menuItem, isSelected && styles.menuItemSelected]}
                onPress={() => handleItemPress(item.id)}
                accessibilityLabel={item.label}
                accessibilityState={{ selected: isSelected }}
              >
                <Text style={styles.menuItemIcon}>{item.icon}</Text>
                <Text
                  style={[
                    styles.menuItemLabel,
                    isSelected && styles.menuItemLabelSelected,
                  ]}
                >
                  {item.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </Animated.View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 1000,
  },
  overlay: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  drawer: {
    position: 'absolute',
    left: 0,
    bottom: 0,
    backgroundColor: Colors.bgPrimary,
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 0 },
    shadowOpacity: 0.25,
    shadowRadius: 10,
    elevation: 10,
  },
  menuContent: {
    flex: 1,
  },
  menuContentContainer: {
    paddingVertical: Spacing.small,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.standard,
    paddingVertical: Spacing.base + 4,
    minHeight: 56,
  },
  menuItemSelected: {
    backgroundColor: Colors.rallyLightGreen,
  },
  menuItemIcon: {
    fontSize: 24,
    lineHeight: 24,
    marginRight: Spacing.base,
    width: 32,
    textAlign: 'center',
    color: Colors.rallyDarkGreen,
  },
  menuItemLabel: {
    ...Typography.buttonText,
    fontSize: 17,
    color: Colors.textPrimary,
    flex: 1,
  },
  menuItemLabelSelected: {
    color: Colors.textPrimary,
    fontWeight: '600',
  },
});

