import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ENV } from '../utils/env';

/**
 * Axios client for Rally API
 * Handles Flask session cookies for authentication
 */

const SESSION_TOKEN_KEY = '@rally_session_token';
const COOKIE_KEY = '@rally_session_cookies';

// Create axios instance with base configuration
export const apiClient = axios.create({
  baseURL: ENV.apiBaseUrl,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  // Enable credentials for cookie support
  withCredentials: true,
});

/**
 * Request interceptor
 * Attaches stored cookies to requests for session authentication
 */
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    // Try to get stored cookies from AsyncStorage
    try {
      const storedCookies = await AsyncStorage.getItem(COOKIE_KEY);
      if (storedCookies) {
        // Attach cookies to Cookie header
        config.headers = config.headers || {};
        config.headers['Cookie'] = storedCookies;
      }
    } catch (error) {
      console.error('❌ Error reading cookies:', error);
    }
    
    // Log request in development
    if (__DEV__) {
      console.log('🌐 API Request:', {
        method: config.method?.toUpperCase(),
        url: config.url,
        hasCookies: !!config.headers?.['Cookie'],
      });
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor
 * Handles cookies from Set-Cookie headers and errors
 */
apiClient.interceptors.response.use(
  async (response: AxiosResponse) => {
    // Extract cookies from Set-Cookie headers
    // Note: In React Native, Set-Cookie headers may not be accessible directly
    // We'll try multiple methods to access them
    let setCookieHeaders: string | string[] | undefined;
    
    // Try different header access methods (React Native/Expo may normalize differently)
    if (response.headers) {
      setCookieHeaders = 
        response.headers['set-cookie'] || 
        response.headers['Set-Cookie'] ||
        (response.headers as any).get?.('set-cookie'); // Some implementations use .get()
    }
    
    if (setCookieHeaders) {
      try {
        // Handle both array and string formats
        let cookieString: string;
        if (Array.isArray(setCookieHeaders)) {
          // For multiple Set-Cookie headers, extract the session cookie
          // Flask uses 'rally_session' cookie name (from server.py line 222)
          const sessionCookie = setCookieHeaders.find(cookie => 
            cookie.toLowerCase().includes('rally_session=')
          );
          cookieString = sessionCookie || setCookieHeaders[0];
        } else {
          cookieString = setCookieHeaders;
        }
        
        // Extract just the cookie value part (everything before ; for first cookie)
        const cookieValue = cookieString.split(';')[0].trim();
        
        if (cookieValue && cookieValue.includes('=')) {
          await AsyncStorage.setItem(COOKIE_KEY, cookieValue);
          
          if (__DEV__) {
            console.log('🍪 Stored session cookie:', cookieValue.substring(0, 50) + '...');
          }
        }
      } catch (error) {
        console.error('❌ Error storing cookies:', error);
      }
    }
    
    // Log response in development (including available headers for debugging)
    if (__DEV__) {
      console.log('✅ API Response:', {
        status: response.status,
        url: response.config.url,
        hasSetCookie: !!setCookieHeaders,
        headersKeys: Object.keys(response.headers || {}),
      });
    }
    
    return response;
  },
  async (error: AxiosError) => {
    // Handle 401 errors - clear cookies and force re-login
    if (error.response?.status === 401) {
      try {
        await AsyncStorage.removeItem(COOKIE_KEY);
        await AsyncStorage.removeItem(SESSION_TOKEN_KEY);
        
        if (__DEV__) {
          console.log('🔓 Cleared cookies due to 401');
        }
      } catch (storageError) {
        console.error('❌ Error clearing cookies:', storageError);
      }
    }
    
    if (__DEV__) {
      console.error('❌ API Error:', {
        status: error.response?.status,
        url: error.config?.url,
        message: error.message,
      });
    }
    
    return Promise.reject(error);
  }
);

/**
 * Helper function to clear session (for logout)
 */
export async function clearAuthCookies() {
  try {
    await AsyncStorage.removeItem(SESSION_TOKEN_KEY);
    await AsyncStorage.removeItem(COOKIE_KEY);
    if (__DEV__) {
      console.log('🧹 Cleared session and cookies');
    }
  } catch (error) {
    console.error('❌ Error clearing session:', error);
    throw error;
  }
}

/**
 * Helper function to check if user has session
 */
export async function hasSessionCookies(): Promise<boolean> {
  try {
    const cookies = await AsyncStorage.getItem(COOKIE_KEY);
    const token = await AsyncStorage.getItem(SESSION_TOKEN_KEY);
    return !!(cookies || token);
  } catch (error) {
    console.error('❌ Error checking session:', error);
    return false;
  }
}
