import React, { useState } from 'react';
import { View, Image, TouchableOpacity, Text, StyleSheet } from 'react-native';

interface PixelOverlayProps {
  referenceImage?: any; // Image source (require() result or { uri: string })
  enabled?: boolean;
}

/**
 * Dev-only utility for pixel-perfect verification
 * Overlays the reference screenshot at adjustable opacity
 * to visually diff against the rendered screen
 */
export const PixelOverlay: React.FC<PixelOverlayProps> = ({
  referenceImage,
  enabled: initialEnabled = false,
}) => {
  const [enabled, setEnabled] = useState(initialEnabled);
  const [opacity, setOpacity] = useState(0.5);

  if (!referenceImage || !enabled) {
    return (
      <View style={styles.toggleContainer}>
        <TouchableOpacity
          style={styles.toggleButton}
          onPress={() => setEnabled(true)}
        >
          <Text style={styles.toggleText}>Show Overlay</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <>
      <View
        style={[
          styles.overlay,
          { opacity },
        ]}
        pointerEvents="none"
      >
        <Image
          source={referenceImage}
          style={styles.referenceImage}
          resizeMode="cover"
        />
      </View>
      
      <View style={styles.controls}>
        <TouchableOpacity
          style={styles.controlButton}
          onPress={() => setOpacity(Math.max(0.1, opacity - 0.1))}
        >
          <Text style={styles.controlText}>−</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={styles.controlButton}
          onPress={() => setOpacity(Math.min(1, opacity + 0.1))}
        >
          <Text style={styles.controlText}>+</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={styles.controlButton}
          onPress={() => setEnabled(false)}
        >
          <Text style={styles.controlText}>✕</Text>
        </TouchableOpacity>
      </View>
    </>
  );
};

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 9999,
    pointerEvents: 'none',
  },
  referenceImage: {
    width: '100%',
    height: '100%',
  },
  toggleContainer: {
    position: 'absolute',
    top: 60,
    right: 16,
    zIndex: 10000,
  },
  toggleButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  toggleText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '600',
  },
  controls: {
    position: 'absolute',
    top: 60,
    right: 16,
    flexDirection: 'row',
    gap: 8,
    zIndex: 10000,
  },
  controlButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  controlText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});

