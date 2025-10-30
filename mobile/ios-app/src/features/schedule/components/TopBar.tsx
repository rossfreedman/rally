import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing, BorderRadius, Layout } from '../../../theme/tokens';

interface TopBarProps {
  onDownloadPress?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onDownloadPress }) => {
  return (
    <View style={styles.container}>
      <View style={styles.leftSection}>
        {/* Logo/Calendar Icon */}
        <View style={styles.logoContainer}>
          <Text style={styles.logoText}>25</Text>
        </View>
        
        {/* Title Stack */}
        <View style={styles.titleStack}>
          <Text style={styles.title}>View Schedule</Text>
          <Text style={styles.subtitle}>Manage your availability for matches & practices</Text>
        </View>
      </View>
      
      {/* Download Button */}
      <TouchableOpacity
        style={styles.downloadButton}
        onPress={onDownloadPress}
        accessibilityLabel="Download to calendar"
      >
        <Text style={styles.downloadIcon}>📅</Text>
        <Text style={styles.downloadText}>Download to calendar</Text>
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
    width: 40,
    height: 40,
    borderRadius: BorderRadius.small,
    backgroundColor: Colors.rallyDarkGreen,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: Spacing.standard,
  },
  logoText: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.white,
  },
  titleStack: {
    flex: 1,
  },
  title: {
    ...Typography.pageTitle,
    color: Colors.textPrimary,
    marginBottom: Spacing.base,
  },
  subtitle: {
    ...Typography.subtitle,
    color: Colors.textSecondary,
  },
  downloadButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.rallyDarkGreen,
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.small,
    borderRadius: BorderRadius.pill,
    height: 36,
  },
  downloadIcon: {
    fontSize: 16,
    marginRight: Spacing.small,
    color: Colors.white,
  },
  downloadText: {
    ...Typography.buttonText,
    color: Colors.white,
  },
});


