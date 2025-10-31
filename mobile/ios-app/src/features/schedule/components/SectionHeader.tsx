import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing, BorderRadius, Layout } from '../../../theme/tokens';

interface SectionHeaderProps {
  label: 'Practice' | 'Match';
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({ label }) => {
  const icon = label === 'Practice' ? '🏋️' : '🏆';
  
  return (
    <View style={styles.container}>
      <Text style={styles.icon}>{icon}</Text>
      <Text style={styles.label}>{label}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    height: Layout.sectionHeaderHeight,
    paddingHorizontal: Spacing.standard,
    paddingVertical: Spacing.base,
    backgroundColor: Colors.bgPrimary,
    borderTopLeftRadius: BorderRadius.large,
    borderTopRightRadius: BorderRadius.large,
    marginBottom: Spacing.standard,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderSubtle,
  },
  icon: {
    fontSize: 20,
    marginRight: Spacing.base,
  },
  label: {
    ...Typography.sectionHeader,
    color: Colors.textPrimary,
  },
});


