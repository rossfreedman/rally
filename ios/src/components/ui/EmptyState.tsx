import React from 'react';
import { View, Text, type ViewProps } from 'react-native';

interface EmptyStateProps extends ViewProps {
  message: string;
  description?: string;
}

export default function EmptyState({
  message,
  description,
  style,
  ...props
}: EmptyStateProps) {
  return (
    <View
      className="flex-1 items-center justify-center py-12 px-6"
      style={style}
      {...props}
    >
      <Text className="text-xl font-semibold text-gray-700 text-center mb-2">
        {message}
      </Text>
      {description && (
        <Text className="text-base text-gray-500 text-center">
          {description}
        </Text>
      )}
    </View>
  );
}

