import { ExpoConfig, ConfigContext } from 'expo/config';

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'Rally Schedule UI',
  slug: 'rally-schedule-ui',
  version: '1.0.0',
  orientation: 'portrait',
  // Icons will be added later; omit to avoid missing-asset errors in dev
  userInterfaceStyle: 'automatic',
  main: 'index.tsx',
  // No custom splash while developing UI-only package
  assetBundlePatterns: ['**/*'],
  ios: {
    supportsTablet: false,
    bundleIdentifier: 'com.rally.schedule-ui',
  },
  android: {
    package: 'com.rally.schedule-ui',
  },
  web: {
    // Default favicon
  },
  scheme: 'rally-schedule',
});


