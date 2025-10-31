import React from 'react';
import { Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Colors, Typography, BorderRadius, Layout } from '../../../theme/tokens';

interface TeamAvailabilityButtonProps {
  date: string;
  onPress: () => void;
}

export const TeamAvailabilityButton: React.FC<TeamAvailabilityButtonProps> = ({
  date,
  onPress,
}) => {
  // Format date like "10/31" from "10/31/2025"
  const formatDate = (dateStr: string): string => {
    const parts = dateStr.split('/');
    if (parts.length >= 2) {
      return `${parseInt(parts[0])}/${parseInt(parts[1])}`;
    }
    return dateStr;
  };

  return (
    <TouchableOpacity
      style={styles.button}
      onPress={onPress}
      accessibilityLabel={`View Team Availability ${formatDate(date)}`}
    >
      <Text style={styles.text}>View Team Availability {formatDate(date)}</Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    height: Layout.buttonHeight,
    paddingHorizontal: 12,
    borderRadius: BorderRadius.pill,
    backgroundColor: Colors.blueMedium,
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: Layout.minTapTarget,
  },
  text: {
    ...Typography.buttonText,
    color: Colors.white,
  },
});


