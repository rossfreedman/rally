import React from 'react';
import { View, ActivityIndicator, Text, type ViewProps } from 'react-native';

interface LoadingSpinnerProps extends ViewProps {
  message?: string;
  size?: 'small' | 'large';
}

export default function LoadingSpinner({
  message,
  size = 'large',
  style,
  ...props
}: LoadingSpinnerProps) {
  return (
    <View
      className="flex-1 items-center justify-center py-12"
      style={style}
      {...props}
    >
      <ActivityIndicator size={size} color="#045454" />
      {message && (
        <Text className="text-base text-gray-600 mt-4">{message}</Text>
      )}
    </View>
  );
}

