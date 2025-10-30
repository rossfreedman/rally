import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing, BorderRadius, Layout, Shadows } from '../../../theme/tokens';

export type FilterMode = 'all' | 'matches' | 'practices';

interface FilterCardProps {
  mode: FilterMode;
  onModeChange: (mode: FilterMode) => void;
}

export const FilterCard: React.FC<FilterCardProps> = ({ mode, onModeChange }) => {
  const chips: { label: string; value: FilterMode }[] = [
    { label: 'All', value: 'all' },
    { label: 'Matches', value: 'matches' },
    { label: 'Practices', value: 'practices' },
  ];

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Filter Events</Text>
      <View style={styles.chipContainer}>
        {chips.map((chip) => {
          const isSelected = chip.value === mode;
          return (
            <TouchableOpacity
              key={chip.value}
              style={[
                styles.chip,
                isSelected ? styles.chipSelected : styles.chipDefault,
              ]}
              onPress={() => onModeChange(chip.value)}
              accessibilityLabel={`Filter by ${chip.label}`}
              accessibilityState={{ selected: isSelected }}
            >
              <Text
                style={[
                  styles.chipLabel,
                  isSelected ? styles.chipLabelSelected : styles.chipLabelDefault,
                ]}
              >
                {chip.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bgPrimary,
    borderRadius: BorderRadius.medium,
    padding: Layout.filterCardPadding,
    ...Shadows.cardElevated,
    marginBottom: Spacing.standard,
  },
  title: {
    ...Typography.filterTitle,
    color: Colors.textPrimary,
    marginBottom: Spacing.base,
  },
  chipContainer: {
    flexDirection: 'row',
    gap: Spacing.small,
  },
  chip: {
    height: Layout.chipHeight,
    paddingHorizontal: Layout.chipPaddingH,
    paddingVertical: Layout.chipPaddingV,
    borderRadius: BorderRadius.pill,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: Layout.minTapTarget,
    minHeight: Layout.minTapTarget,
  },
  chipSelected: {
    backgroundColor: Colors.rallyLightGreen,
  },
  chipDefault: {
    backgroundColor: Colors.rallyDarkGreen,
  },
  chipLabel: {
    ...Typography.chipLabel,
  },
  chipLabelSelected: {
    color: Colors.textPrimary,
  },
  chipLabelDefault: {
    color: Colors.white,
  },
});


