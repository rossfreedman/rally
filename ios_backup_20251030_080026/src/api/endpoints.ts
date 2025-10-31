/**
 * API Endpoint definitions for Rally
 * Maps to existing Flask backend routes
 */

export const API_ENDPOINTS = {
  // Authentication
  LOGIN: '/api/login',
  LOGOUT: '/api/logout',
  CHECK_AUTH: '/api/check-auth',
  
  // User Data
  GET_USER_SETTINGS: '/api/get-user-settings',
  UPDATE_SETTINGS: '/api/update-settings',
  
  // Team & Stats
  TEAM_STATS: '/api/team-stats',
  USER_WIN_STREAK: '/api/user-win-streak',
  
  // Matches
  LAST_3_MATCHES: '/api/last-3-matches',
  CURRENT_SEASON_MATCHES: '/api/current-season-matches',
  TEAM_CURRENT_SEASON_MATCHES: '/api/team-current-season-matches',
  
  // Availability
  AVAILABILITY: '/api/availability',
  GET_USER_AVAILABILITY: '/api/user-availability',
  
  // Leagues & Teams
  GET_LEAGUES: '/api/get-leagues',
  GET_TEAMS: '/api/teams',
  GET_TEAMS_WITH_IDS: '/api/teams-with-ids',
  
  // Series & Standings
  SERIES_STATS: '/api/series-stats',
  
  // Schedule
  TEAM_SCHEDULE_DATA: '/api/team-schedule-data',
  TEAM_SCHEDULE_GRID_DATA: '/api/team-schedule-grid-data',
  MOBILE_AVAILABILITY_DATA: '/api/mobile-availability-data',
} as const;

export type ApiEndpoint = typeof API_ENDPOINTS[keyof typeof API_ENDPOINTS];

// Request/Response type definitions for each endpoint

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UpdateSettingsRequest {
  email_notifications?: boolean;
  sms_notifications?: boolean;
  phone?: string;
}

export interface SetAvailabilityRequest {
  match_date: string;
  status: 'available' | 'unavailable' | 'not_sure';
  notes?: string;
}

