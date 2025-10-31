import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing, BorderRadius, Layout, Shadows } from '../../../theme/tokens';

interface TopBarProps {
  onDownloadPress?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onDownloadPress }) => {
  return (
    <View style={styles.container}>
      <View style={styles.leftSection}>
        <View style={styles.logoContainer}>
          <Text style={styles.logoText}>📅</Text>
        </View>
        <View style={styles.titleStack}>
          <Text style={styles.title}>Schedule</Text>
          <Text style={styles.subtitle}>Manage availability for matches and practices</Text>
        </View>
      </View>

      <TouchableOpacity
        style={styles.downloadButton}
        onPress={onDownloadPress}
        accessibilityLabel="Download to calendar"
      >
        <Text style={styles.downloadIcon}>⇩</Text>
        <Text style={styles.downloadText}>Add to Calendar</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.standard,
    paddingVertical: Spacing.base,
    minHeight: Layout.topBarHeight,
    backgroundColor: Colors.bgPrimary,
  },
  leftSection: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  logoContainer: {
    width: 44,
    height: 44,
    borderRadius: BorderRadius.large,
    backgroundColor: Colors.rallyTealSoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: Spacing.standard,
    borderWidth: 1,
    borderColor: Colors.borderSubtle,
    ...Shadows.card,
  },
  logoText: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.rallyTeal,
  },
  titleStack: {
    flex: 1,
  },
  title: {
    ...Typography.pageTitle,
    color: Colors.textPrimary,
    marginBottom: Spacing.micro,
  },
  subtitle: {
    ...Typography.subtitle,
    color: Colors.textSecondary,
  },
  downloadButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.bgPrimary,
    paddingHorizontal: Spacing.standard,
    paddingVertical: Spacing.small,
    borderRadius: BorderRadius.pill,
    height: 38,
    borderWidth: 1,
    borderColor: Colors.borderLight,
  },
  downloadIcon: {
    fontSize: 16,
    marginRight: Spacing.small,
    color: Colors.rallyDarkGreen,
  },
  downloadText: {
    ...Typography.buttonText,
    color: Colors.rallyDarkGreen,
  },
});


