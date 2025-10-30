import React from 'react';
import { View, Text, type ViewProps } from 'react-native';

interface BadgeProps extends ViewProps {
  label: string;
  variant?: 'success' | 'error' | 'warning' | 'info';
  size?: 'small' | 'medium' | 'large';
}

export default function Badge({
  label,
  variant = 'info',
  size = 'medium',
  style,
  ...props
}: BadgeProps) {
  const baseStyle = 'rounded-full items-center justify-center';

  const sizeStyles = {
    small: 'px-2 py-1',
    medium: 'px-3 py-1.5',
    large: 'px-4 py-2',
  };

  const variantStyles = {
    success: 'bg-green-100',
    error: 'bg-red-100',
    warning: 'bg-yellow-100',
    info: 'bg-blue-100',
  };

  const textSizeStyles = {
    small: 'text-xs',
    medium: 'text-sm',
    large: 'text-base',
  };

  const textVariantStyles = {
    success: 'text-green-800',
    error: 'text-red-800',
    warning: 'text-yellow-800',
    info: 'text-blue-800',
  };

  return (
    <View
      className={`${baseStyle} ${sizeStyles[size]} ${variantStyles[variant]}`}
      style={style}
      {...props}
    >
      <Text className={`font-semibold ${textSizeStyles[size]} ${textVariantStyles[variant]}`}>
        {label}
      </Text>
    </View>
  );
}

