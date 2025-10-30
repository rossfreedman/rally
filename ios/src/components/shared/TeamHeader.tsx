import React from 'react';
import { View, Text, type ViewProps } from 'react-native';
import Card from '../ui/Card';

interface TeamHeaderProps extends ViewProps {
  teamName: string;
  series?: string | null;
  club?: string | null;
  points?: number;
  record?: string;
}

export default function TeamHeader({
  teamName,
  series,
  club,
  points,
  record,
  style,
  ...props
}: TeamHeaderProps) {
  return (
    <Card elevated style={[{ backgroundColor: '#045454' }, style]} {...props}>
      {/* Team Name */}
      <Text className="text-2xl font-bold text-white mb-2">
        {teamName}
      </Text>

      {/* Series and Club */}
      {(series || club) && (
        <View className="flex-row items-center mb-3">
          {series && (
            <Text className="text-sm text-rally-bright-green mr-2">
              {series}
            </Text>
          )}
          {club && (
            <Text className="text-sm text-white opacity-80">
              {club}
            </Text>
          )}
        </View>
      )}

      {/* Stats */}
      <View className="flex-row items-center justify-between pt-3 border-t border-white border-opacity-20">
        {points !== undefined && (
          <View>
            <Text className="text-3xl font-bold text-rally-bright-green">
              {points}
            </Text>
            <Text className="text-sm text-white opacity-80">Points</Text>
          </View>
        )}
        {record && (
          <View className="items-end">
            <Text className="text-xl font-semibold text-white">
              {record}
            </Text>
            <Text className="text-sm text-white opacity-80">Record</Text>
          </View>
        )}
      </View>
    </Card>
  );
}

