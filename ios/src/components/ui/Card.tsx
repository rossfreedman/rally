import React from 'react';
import { View, type ViewProps } from 'react-native';

interface CardProps extends ViewProps {
  children: React.ReactNode;
  elevated?: boolean;
}

export default function Card({ children, elevated = true, style, ...props }: CardProps) {
  const baseStyle = 'bg-white rounded-lg p-4';
  const elevatedStyle = elevated ? 'shadow-md' : '';

  return (
    <View className={`${baseStyle} ${elevatedStyle}`} style={style} {...props}>
      {children}
    </View>
  );
}

