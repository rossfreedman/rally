import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing, BorderRadius, Layout } from '../../../theme/tokens';

export type AvailabilityStatus = 'available' | 'unavailable' | 'not_sure';

interface AvailabilityButtonsProps {
  status: AvailabilityStatus;
  onStatusChange: (status: AvailabilityStatus) => void;
}

export const AvailabilityButtons: React.FC<AvailabilityButtonsProps> = ({
  status,
  onStatusChange,
}) => {
  const buttons: {
    label: string;
    value: AvailabilityStatus;
    icon: string;
  }[] = [
    { label: 'Count Me In!', value: 'available', icon: '✓' },
    { label: 'Sorry, Can\'t', value: 'unavailable', icon: '✕' },
    { label: 'Not Sure', value: 'not_sure', icon: '?' },
  ];

  const getButtonStyle = (buttonStatus: AvailabilityStatus, isSelected: boolean) => {
    if (isSelected) {
      switch (buttonStatus) {
        case 'available':
          return { backgroundColor: Colors.greenButton, textColor: Colors.white, iconColor: Colors.white };
        case 'unavailable':
          return { backgroundColor: Colors.redMarker, textColor: Colors.white, iconColor: Colors.white };
        case 'not_sure':
          return { backgroundColor: Colors.yellowButton, textColor: Colors.textPrimary, iconColor: Colors.textPrimary };
        default:
          return { backgroundColor: Colors.buttonGrayBG, textColor: Colors.textSecondary, iconColor: Colors.textSecondary };
      }
    } else {
      return { 
        backgroundColor: buttonStatus === 'not_sure' ? Colors.bgSecondary : Colors.buttonGrayBG,
        textColor: Colors.textSecondary,
        iconColor: Colors.textTertiary,
      };
    }
  };

  return (
    <View style={styles.container}>
      {buttons.map((button) => {
        const isSelected = status === button.value;
        const buttonStyle = getButtonStyle(button.value, isSelected);
        
        return (
          <TouchableOpacity
            key={button.value}
            style={[
              styles.button,
              { backgroundColor: buttonStyle.backgroundColor },
            ]}
            onPress={() => onStatusChange(button.value)}
            accessibilityLabel={button.label}
            accessibilityState={{ selected: isSelected }}
          >
            <Text style={[styles.icon, { color: buttonStyle.iconColor }] }>
              {button.icon}
            </Text>
            <Text style={[styles.label, { color: buttonStyle.textColor }]}>
              {button.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: Layout.availabilityColumnWidth,
    gap: Spacing.base,
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    height: Layout.buttonHeight,
    paddingHorizontal: Layout.buttonPaddingH,
    borderRadius: BorderRadius.pill,
    minHeight: Layout.minTapTarget,
    borderWidth: 1,
    borderColor: Colors.borderLight,
  },
  icon: {
    fontSize: 16,
    marginRight: Spacing.small,
  },
  label: {
    ...Typography.buttonText,
    flex: 1,
  },
});


