import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing, Layout } from '../../../theme/tokens';

interface PastEventsToggleProps {
  expanded: boolean;
  count: number;
  onToggle: () => void;
}

export const PastEventsToggle: React.FC<PastEventsToggleProps> = ({
  expanded,
  count,
  onToggle,
}) => {
  return (
    <TouchableOpacity
      style={styles.container}
      onPress={onToggle}
      accessibilityLabel={`Past Events, ${count} dates. Tap to ${expanded ? 'collapse' : 'expand'}`}
      accessibilityRole="button"
      accessibilityState={{ expanded }}
    >
      <View style={styles.iconContainer}>
        <Text style={styles.icon}>🔄</Text>
      </View>
      <Text style={styles.text}>Past Events ({count} dates)</Text>
      <View style={[styles.chevron, expanded && styles.chevronExpanded]}>
        <Text style={styles.chevronIcon}>▼</Text>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    height: Layout.pastEventsHeight,
    paddingHorizontal: Spacing.standard,
    backgroundColor: Colors.bgSecondary,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderLight,
  },
  iconContainer: {
    marginRight: Spacing.base,
  },
  icon: {
    fontSize: 16,
  },
  text: {
    ...Typography.buttonText,
    color: Colors.textPrimary,
    flex: 1,
  },
  chevron: {
    width: 16,
    height: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chevronExpanded: {
    transform: [{ rotate: '180deg' }],
  },
  chevronIcon: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
});


