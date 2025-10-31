import React from 'react';
import { View, Text, type ViewProps } from 'react-native';

interface StatRowProps extends ViewProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  highlighted?: boolean;
}

export default function StatRow({
  label,
  value,
  icon,
  highlighted = false,
  style,
  ...props
}: StatRowProps) {
  return (
    <View
      className={`flex-row items-center justify-between py-3 ${
        highlighted ? 'bg-rally-bright-green bg-opacity-10 px-3 rounded-lg' : ''
      }`}
      style={style}
      {...props}
    >
      <View className="flex-row items-center flex-1">
        {icon && <View className="mr-2">{icon}</View>}
        <Text className={`text-base ${highlighted ? 'font-semibold' : ''} text-gray-700`}>
          {label}
        </Text>
      </View>
      <Text
        className={`text-base ${
          highlighted ? 'font-bold text-rally-dark-green' : 'font-semibold text-gray-900'
        }`}
      >
        {value}
      </Text>
    </View>
  );
}

