import Constants from 'expo-constants';

/**
 * Environment configuration for Rally iOS app
 * Validates and provides type-safe access to environment variables
 */

interface EnvConfig {
  apiBaseUrl: string;
  env: 'development' | 'production';
  cookieDomain: string;
  sentryDsn: string;
}

/**
 * Get environment variable from Expo config
 */
function getEnvVar(key: string, defaultValue?: string): string {
  const value = Constants.expoConfig?.extra?.[key] || defaultValue;
  return value || '';
}

/**
 * Validate required environment variables
 * Throws error in production if required vars are missing
 */
function validateEnv(): EnvConfig {
  const env = getEnvVar('env', 'development');
  const apiBaseUrl = getEnvVar('apiBaseUrl', 'https://www.lovetorally.com');
  const cookieDomain = getEnvVar('cookieDomain', '.lovetorally.com');
  const sentryDsn = getEnvVar('sentryDsn', '');

  // Validate in production
  if (env === 'production') {
    if (!apiBaseUrl) {
      throw new Error('APP_API_BASE_URL is required in production');
    }
    if (!cookieDomain) {
      throw new Error('APP_COOKIE_DOMAIN is required in production');
    }
  }

  // Ensure apiBaseUrl doesn't end with slash
  const cleanApiBaseUrl = apiBaseUrl.replace(/\/$/, '');

  return {
    apiBaseUrl: cleanApiBaseUrl,
    env: env as 'development' | 'production',
    cookieDomain,
    sentryDsn,
  };
}

// Validate and export config
export const ENV = validateEnv();

// Helper functions
export const isDevelopment = ENV.env === 'development';
export const isProduction = ENV.env === 'production';

// Export for debugging (development only)
if (isDevelopment) {
  console.log('🔧 Rally Environment Config:', {
    env: ENV.env,
    apiBaseUrl: ENV.apiBaseUrl,
    cookieDomain: ENV.cookieDomain,
    sentryConfigured: !!ENV.sentryDsn,
  });
}

