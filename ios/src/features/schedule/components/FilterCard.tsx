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
      <Text style={styles.title}>Filter</Text>
      <View style={styles.segmentTrack}>
        {chips.map((chip) => {
          const isSelected = chip.value === mode;
          return (
            <TouchableOpacity
              key={chip.value}
              style={[styles.chip, isSelected ? styles.chipSelected : undefined]}
              onPress={() => onModeChange(chip.value)}
              accessibilityLabel={`Filter by ${chip.label}`}
              accessibilityState={{ selected: isSelected }}
            >
              <Text
                style={[styles.chipLabel, isSelected ? styles.chipLabelSelected : styles.chipLabelDefault]}
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
    borderRadius: BorderRadius.large,
    padding: Layout.filterCardPadding,
    ...Shadows.cardElevated,
    marginBottom: Spacing.standard,
    borderWidth: 1,
    borderColor: Colors.borderSubtle,
  },
  title: {
    ...Typography.filterTitle,
    color: Colors.textPrimary,
    marginBottom: Spacing.base,
  },
  segmentTrack: {
    flexDirection: 'row',
    backgroundColor: Colors.buttonGrayBG,
    borderRadius: BorderRadius.pill,
    padding: 4,
    borderWidth: 1,
    borderColor: Colors.borderLight,
  },
  chip: {
    flex: 1,
    height: Layout.chipHeight,
    paddingHorizontal: Layout.chipPaddingH,
    paddingVertical: Layout.chipPaddingV,
    borderRadius: BorderRadius.pill,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: Layout.minTapTarget,
  },
  chipSelected: {
    backgroundColor: Colors.bgPrimary,
    ...Shadows.card,
  },
  chipLabel: {
    ...Typography.chipLabel,
  },
  chipLabelSelected: {
    color: Colors.textPrimary,
  },
  chipLabelDefault: {
    color: Colors.textSecondary,
  },
});


