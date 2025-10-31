import React from 'react';
import { View, Text, RefreshControl } from 'react-native';
import ScreenContainer from '../../components/ui/ScreenContainer';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import EmptyState from '../../components/ui/EmptyState';
import MatchCard from '../../components/shared/MatchCard';
import { useCurrentSeasonMatches } from '../../api/hooks/useMatches';
import type { ScheduleScreenProps } from '../../navigation/types';

export default function ScheduleScreen({}: ScheduleScreenProps) {
  const matches = useCurrentSeasonMatches();

  const handleRefresh = () => {
    matches.refetch();
  };

  // Loading state
  if (matches.isLoading) {
    return (
      <ScreenContainer scrollable={false}>
        <LoadingSpinner message="Loading schedule..." />
      </ScreenContainer>
    );
  }

  // Error state
  if (matches.isError) {
    return (
      <ScreenContainer scrollable={false}>
        <EmptyState
          message="Unable to load schedule"
          description="Please check your connection and try again"
        />
      </ScreenContainer>
    );
  }

  // No data state
  if (!matches.data || !matches.data.matches || matches.data.matches.length === 0) {
    return (
      <ScreenContainer scrollable={false}>
        <EmptyState
          message="No matches scheduled"
          description="Your upcoming matches will appear here"
        />
      </ScreenContainer>
    );
  }

  const allMatches = matches.data.matches;
  const nextMatch = allMatches[0];
  const upcomingMatches = allMatches.slice(1, 4);

  return (
    <ScreenContainer
      scrollable
      refreshControl={
        <RefreshControl
          refreshing={matches.isRefetching}
          onRefresh={handleRefresh}
          tintColor="#045454"
        />
      }
    >
      {/* Next Match (Featured) */}
      {nextMatch && (
        <View className="mb-4">
          <Text className="text-lg font-bold text-gray-900 mb-3">Next Match</Text>
          <MatchCard match={nextMatch} featured />
        </View>
      )}

      {/* Upcoming Matches */}
      {upcomingMatches.length > 0 && (
        <View className="mb-4">
          <Text className="text-lg font-bold text-gray-900 mb-3">Upcoming Matches</Text>
          {upcomingMatches.map((match, index) => (
            <View key={index} className="mb-3">
              <MatchCard match={match} />
            </View>
          ))}
        </View>
      )}

      {/* View All Link Placeholder */}
      {allMatches.length > 4 && (
        <Text className="text-sm text-rally-dark-green text-center py-2">
          {allMatches.length - 4} more matches this season
        </Text>
      )}
    </ScreenContainer>
  );
}

