import { z } from 'zod';
import {
  AuthResponseSchema,
  UserSessionSchema,
  TeamStatsSchema,
  MatchSchema,
  UserSettingsSchema,
  AvailabilitySchema,
} from '../src/api/types';

/**
 * API Contract tests - validates zod schemas with mock data
 */
describe('API Contract Validation', () => {
  describe('AuthResponseSchema', () => {
    it('validates valid auth response', () => {
      const validData = {
        success: true,
        user: {
          id: 1,
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
          tenniscores_player_id: 'player123',
          team_id: 1,
          league_id: 1,
          club: 'Test Club',
          series: 'Series 1',
        },
      };

      const result = AuthResponseSchema.safeParse(validData);
      expect(result.success).toBe(true);
    });

    it('validates auth response with null values', () => {
      const validData = {
        success: true,
        user: {
          id: 1,
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
          tenniscores_player_id: null,
          team_id: null,
          league_id: null,
          club: null,
          series: null,
        },
      };

      const result = AuthResponseSchema.safeParse(validData);
      expect(result.success).toBe(true);
    });
  });

  describe('TeamStatsSchema', () => {
    it('validates valid team stats', () => {
      const validData = {
        success: true,
        points: 10,
        matches_won: 5,
        matches_lost: 3,
        total_matches: 8,
        win_rate: 62.5,
        team_name: 'Test Team',
        series: 'Series 1',
        club: 'Test Club',
      };

      const result = TeamStatsSchema.safeParse(validData);
      expect(result.success).toBe(true);
    });
  });

  describe('MatchSchema', () => {
    it('validates valid match data', () => {
      const validData = {
        id: 1,
        match_date: '2024-01-15',
        home_team: 'Team A',
        away_team: 'Team B',
        court: '1',
        result: 'Win',
        score: '6-2, 6-3',
      };

      const result = MatchSchema.safeParse(validData);
      expect(result.success).toBe(true);
    });

    it('validates match with null values', () => {
      const validData = {
        id: 1,
        match_date: '2024-01-15',
        home_team: 'Team A',
        away_team: 'Team B',
        court: null,
        result: null,
        score: null,
      };

      const result = MatchSchema.safeParse(validData);
      expect(result.success).toBe(true);
    });
  });

  describe('UserSessionSchema', () => {
    it('validates authenticated session', () => {
      const validData = {
        authenticated: true,
        user: {
          id: 1,
          email: 'test@example.com',
          first_name: 'John',
          last_name: 'Doe',
          tenniscores_player_id: 'player123',
          team_id: 1,
          league_id: 1,
          club: 'Test Club',
          series: 'Series 1',
        },
      };

      const result = UserSessionSchema.safeParse(validData);
      expect(result.success).toBe(true);
    });

    it('validates unauthenticated session', () => {
      const validData = {
        authenticated: false,
      };

      const result = UserSessionSchema.safeParse(validData);
      expect(result.success).toBe(true);
    });
  });
});

