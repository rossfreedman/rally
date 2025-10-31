import React from 'react';
import { View, Text, type ViewProps } from 'react-native';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import { formatDate } from '../../utils/format';
import type { Match } from '../../api/types';

interface MatchCardProps extends ViewProps {
  match: Match;
  featured?: boolean;
}

export default function MatchCard({ match, featured = false, style, ...props }: MatchCardProps) {
  const isWin = match.match_result?.toLowerCase() === 'won';
  const isLoss = match.match_result?.toLowerCase() === 'lost';

  return (
    <Card
      elevated
      style={[featured && { borderWidth: 2, borderColor: '#045454' }, style]}
      {...props}
    >
      {/* Date */}
      <Text className="text-sm text-gray-600 mb-2">{formatDate(match.date)}</Text>

      {/* Teams */}
      <View className="flex-row items-center justify-between mb-2">
        <View className="flex-1">
          <Text className="text-base font-semibold text-gray-900">
            {match.home_team}
          </Text>
          <Text className="text-sm text-gray-600 mt-1">vs</Text>
          <Text className="text-base font-semibold text-gray-900 mt-1">
            {match.away_team}
          </Text>
        </View>

        {/* Result Badge */}
        {match.match_result && (
          <Badge
            label={match.match_result}
            variant={isWin ? 'success' : isLoss ? 'error' : 'info'}
            size="medium"
          />
        )}
      </View>

      {/* Court and Score */}
      <View className="flex-row items-center justify-between mt-2 pt-2 border-t border-gray-200">
        {match.court_number && (
          <Text className="text-sm text-gray-600">
            Court {match.court_number}
          </Text>
        )}
        {match.scores && (
          <Text className="text-sm text-gray-900 font-medium">
            {match.scores}
          </Text>
        )}
      </View>
    </Card>
  );
}

