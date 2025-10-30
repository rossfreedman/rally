import { z } from 'zod';

/**
 * Zod schemas for Rally API responses
 * Provides runtime validation and TypeScript types
 */

// Auth Response Schema
export const AuthResponseSchema = z.object({
  status: z.string(),
  message: z.string(),
  redirect: z.string(),
  has_temporary_password: z.boolean().optional(),
  user: z.object({
    email: z.string().email(),
    first_name: z.string(),
    last_name: z.string(),
    club: z.string(),
    series: z.string(),
    tenniscores_player_id: z.string(),
  }),
});

export type AuthResponse = z.infer<typeof AuthResponseSchema>;

// User Session Schema
export const UserSessionSchema = z.object({
  authenticated: z.boolean(),
  user: z.object({
    id: z.number(),
    email: z.string(),
    first_name: z.string(),
    last_name: z.string(),
    tenniscores_player_id: z.string().nullable(),
    team_id: z.number().nullable(),
    league_id: z.number().nullable(),
    club: z.string().nullable(),
    series: z.string().nullable(),
  }).optional(),
});

export type UserSession = z.infer<typeof UserSessionSchema>;

// Team Stats Schema (from /api/team-stats)
export const TeamStatsSchema = z.object({
  success: z.boolean(),
  points: z.number(),
  matches_won: z.number(),
  matches_lost: z.number(),
  win_rate: z.number(),
  team_name: z.string(),
});

export type TeamStats = z.infer<typeof TeamStatsSchema>;

// Match Schema
export const MatchSchema = z.object({
  date: z.string(),
  home_team: z.string(),
  away_team: z.string(),
  scores: z.string().nullable(),
  player_was_home: z.boolean(),
  player_won: z.boolean(),
  current_player_name: z.string().optional(),
  partner_name: z.string().optional(),
  opponent1_name: z.string().optional(),
  opponent2_name: z.string().optional(),
  match_result: z.string(),
  court_number: z.number().nullable().optional(),
});

export type Match = z.infer<typeof MatchSchema>;

// Match List Schema
export const MatchListSchema = z.object({
  matches: z.array(MatchSchema),
  total_matches: z.number().optional(),
});

export type MatchList = z.infer<typeof MatchListSchema>;

// User Settings Schema
export const UserSettingsSchema = z.object({
  success: z.boolean(),
  settings: z.object({
    email_notifications: z.boolean().optional(),
    sms_notifications: z.boolean().optional(),
    phone: z.string().nullable().optional(),
    leagues: z.array(z.object({
      league_id: z.number(),
      league_name: z.string(),
      club: z.string(),
      series: z.string(),
    })).optional(),
  }),
});

export type UserSettings = z.infer<typeof UserSettingsSchema>;

// Availability Schema
export const AvailabilitySchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  availability: z.object({
    match_date: z.string(),
    status: z.enum(['available', 'unavailable', 'not_sure']),
    notes: z.string().nullable(),
  }).optional(),
});

export type Availability = z.infer<typeof AvailabilitySchema>;

// Win Streak Schema
export const WinStreakSchema = z.object({
  success: z.boolean(),
  current_streak: z.number(),
  longest_streak: z.number(),
  recent_matches: z.array(z.object({
    match_date: z.string(),
    opponent: z.string(),
    result: z.string(),
  })).optional(),
});

export type WinStreak = z.infer<typeof WinStreakSchema>;

// Generic API Error Schema
export const ApiErrorSchema = z.object({
  error: z.string(),
  success: z.boolean().optional(),
});

export type ApiError = z.infer<typeof ApiErrorSchema>;

// League Schema
export const LeagueSchema = z.object({
  id: z.number(),
  name: z.string(),
  display_name: z.string().optional(),
});

export type League = z.infer<typeof LeagueSchema>;

// Team Schema
export const TeamSchema = z.object({
  id: z.number(),
  name: z.string(),
  league_id: z.number(),
  series: z.string().nullable(),
  club: z.string().nullable(),
});

export type Team = z.infer<typeof TeamSchema>;

