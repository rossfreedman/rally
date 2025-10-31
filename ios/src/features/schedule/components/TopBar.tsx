import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Image } from 'react-native';
import { Colors, Typography, Spacing, BorderRadius, Layout, Shadows } from '../../../theme/tokens';

interface TopBarProps {
  onMenuPress?: () => void;
  onDownloadPress?: () => void;
}

export const TopBar: React.FC<TopBarProps> = ({ onMenuPress, onDownloadPress }) => {
  return (
    <View style={styles.navbar}>
      <TouchableOpacity accessibilityLabel="Back" style={styles.navIconLeft}>
        <Text style={styles.navIconText}>‹</Text>
      </TouchableOpacity>

      <View style={styles.brandContainer}>
        <Image
          source={require('../../../../assets/rallylogo.png')}
          style={styles.brandLogo}
          resizeMode="contain"
          accessible
          accessibilityLabel="Rally"
        />
      </View>

      <TouchableOpacity
        style={styles.navIconRight}
        onPress={onMenuPress}
        accessibilityLabel="Menu"
      >
        <Text style={styles.menuIconText}>☰</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  navbar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 147,
    backgroundColor: Colors.rallyDarkGreen,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.standard,
    paddingTop: 75,
    zIndex: 2000,
    ...Shadows.tabBar,
  },
  navIconLeft: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  navIconRight: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
  },
  navIconText: {
    fontSize: 26,
    color: Colors.white,
  },
  menuIconText: {
    fontSize: 22,
    color: Colors.white,
  },
  brandContainer: {
    flex: 1,
    alignItems: 'center',
  },
  brandLogo: {
    width: 320,
    height: 72,
  },
});


