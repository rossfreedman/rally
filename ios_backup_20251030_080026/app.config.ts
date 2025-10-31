import { ExpoConfig, ConfigContext } from 'expo/config';

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'Rally',
  slug: 'rally',
  version: '1.0.0',
  orientation: 'portrait',
  icon: './assets/icon.png',
  userInterfaceStyle: 'automatic',
  main: 'index.ts',
  splash: {
    image: './assets/splash-icon.png',
    resizeMode: 'contain',
    backgroundColor: '#045454', // Rally dark green
  },
  assetBundlePatterns: ['**/*'],
  ios: {
    supportsTablet: true,
    bundleIdentifier: 'com.lovetorally.rally',
    infoPlist: {
      UIBackgroundModes: ['remote-notification'],
    },
  },
  android: {
    adaptiveIcon: {
      foregroundImage: './assets/adaptive-icon.png',
      backgroundColor: '#045454', // Rally dark green
    },
    package: 'com.lovetorally.rally',
  },
  web: {
    favicon: './assets/favicon.png',
  },
  scheme: 'rally',
  extra: {
    apiBaseUrl: process.env.APP_API_BASE_URL || 'https://www.lovetorally.com',
    env: process.env.APP_ENV || 'development',
    cookieDomain: process.env.APP_COOKIE_DOMAIN || '.lovetorally.com',
    sentryDsn: process.env.APP_SENTRY_DSN || '',
  },
});

