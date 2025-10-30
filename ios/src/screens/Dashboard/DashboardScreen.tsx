import React from 'react';
import { View, Text, RefreshControl } from 'react-native';
import ScreenContainer from '../../components/ui/ScreenContainer';
import Card from '../../components/ui/Card';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import EmptyState from '../../components/ui/EmptyState';
import StatRow from '../../components/shared/StatRow';
import TeamHeader from '../../components/shared/TeamHeader';
import { useTeamStats } from '../../api/hooks/useTeam';
import { useLast3Matches } from '../../api/hooks/useMatches';
import { formatRecord, formatPercentage } from '../../utils/format';
import type { DashboardScreenProps } from '../../navigation/types';

export default function DashboardScreen({}: DashboardScreenProps) {
  const teamStats = useTeamStats();
  const lastMatches = useLast3Matches();

  const handleRefresh = () => {
    teamStats.refetch();
    lastMatches.refetch();
  };

  // Loading state
  if (teamStats.isLoading) {
    return (
      <ScreenContainer scrollable={false}>
        <LoadingSpinner message="Loading your stats..." />
      </ScreenContainer>
    );
  }

  // Error state
  if (teamStats.isError) {
    return (
      <ScreenContainer scrollable={false}>
        <EmptyState
          message="Unable to load stats"
          description="Please check your connection and try again"
        />
      </ScreenContainer>
    );
  }

  // No data state
  if (!teamStats.data?.success || !teamStats.data) {
    return (
      <ScreenContainer scrollable={false}>
        <EmptyState
          message="No stats available"
          description="Your team stats will appear here once available"
        />
      </ScreenContainer>
    );
  }

  const stats = teamStats.data;
  const totalMatches = stats.matches_won + stats.matches_lost;

  return (
    <ScreenContainer
      scrollable
      refreshControl={
        <RefreshControl
          refreshing={teamStats.isRefetching}
          onRefresh={handleRefresh}
          tintColor="#045454"
        />
      }
    >
      {/* Team Header */}
      <TeamHeader
        teamName={stats.team_name}
        points={stats.points}
        record={formatRecord(stats.matches_won, stats.matches_lost)}
      />

      {/* Season Stats */}
      <Card className="mt-4">
        <Text className="text-lg font-bold text-gray-900 mb-3">Season Stats</Text>
        <StatRow label="Total Matches" value={totalMatches} />
        <StatRow label="Matches Won" value={stats.matches_won} highlighted={stats.matches_won > 0} />
        <StatRow label="Matches Lost" value={stats.matches_lost} />
        <StatRow label="Win Rate" value={formatPercentage(stats.win_rate)} highlighted />
      </Card>

      {/* Recent Matches */}
      {lastMatches.data && lastMatches.data.matches.length > 0 && (
        <Card className="mt-4">
          <Text className="text-lg font-bold text-gray-900 mb-3">Last Match</Text>
          {lastMatches.data.matches.slice(0, 1).map((match, index) => (
            <View key={index}>
              <StatRow
                label={match.player_was_home ? `vs ${match.away_team}` : `vs ${match.home_team}`}
                value={match.match_result}
              />
              {match.scores && (
                <Text className="text-sm text-gray-600 mt-1">Score: {match.scores}</Text>
              )}
            </View>
          ))}
        </Card>
      )}

      {/* Placeholder for future features */}
      <Card className="mt-4">
        <Text className="text-sm text-gray-600 text-center py-2">
          More stats and features coming soon!
        </Text>
      </Card>
    </ScreenContainer>
  );
}

