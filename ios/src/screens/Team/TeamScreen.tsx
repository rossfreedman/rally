import React from 'react';
import { View, Text, RefreshControl } from 'react-native';
import ScreenContainer from '../../components/ui/ScreenContainer';
import Card from '../../components/ui/Card';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import EmptyState from '../../components/ui/EmptyState';
import StatRow from '../../components/shared/StatRow';
import TeamHeader from '../../components/shared/TeamHeader';
import { useTeamStats } from '../../api/hooks/useTeam';
import { formatRecord, formatPercentage } from '../../utils/format';
import type { TeamScreenProps } from '../../navigation/types';

export default function TeamScreen({}: TeamScreenProps) {
  const teamStats = useTeamStats();

  const handleRefresh = () => {
    teamStats.refetch();
  };

  // Loading state
  if (teamStats.isLoading) {
    return (
      <ScreenContainer scrollable={false}>
        <LoadingSpinner message="Loading team data..." />
      </ScreenContainer>
    );
  }

  // Error state
  if (teamStats.isError) {
    return (
      <ScreenContainer scrollable={false}>
        <EmptyState
          message="Unable to load team data"
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
          message="No team data available"
          description="Your team information will appear here once available"
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

      {/* Team Performance */}
      <Card className="mt-4">
        <Text className="text-lg font-bold text-gray-900 mb-3">Team Performance</Text>
        <StatRow label="League Points" value={stats.points} highlighted />
        <StatRow label="Matches Played" value={totalMatches} />
        <StatRow label="Matches Won" value={stats.matches_won} />
        <StatRow label="Matches Lost" value={stats.matches_lost} />
        <StatRow label="Win Percentage" value={formatPercentage(stats.win_rate)} />
      </Card>

      {/* Placeholder for roster */}
      <Card className="mt-4">
        <Text className="text-sm text-gray-600 text-center py-2">
          Team roster and player stats coming soon!
        </Text>
      </Card>
    </ScreenContainer>
  );
}

