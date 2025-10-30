import React from 'react';
import { TouchableOpacity, Text, ActivityIndicator, type TouchableOpacityProps } from 'react-native';

interface ButtonProps extends TouchableOpacityProps {
  title: string;
  variant?: 'primary' | 'secondary' | 'outline';
  loading?: boolean;
  disabled?: boolean;
}

export default function Button({
  title,
  variant = 'primary',
  loading = false,
  disabled = false,
  style,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  const baseStyle = 'py-4 px-6 rounded-lg items-center justify-center';
  const variantStyles = {
    primary: 'bg-rally-dark-green',
    secondary: 'bg-rally-bright-green',
    outline: 'border-2 border-rally-dark-green bg-transparent',
  };
  const disabledStyle = 'opacity-50';

  const textBaseStyle = 'text-base font-semibold';
  const textVariantStyles = {
    primary: 'text-white',
    secondary: 'text-rally-dark-green',
    outline: 'text-rally-dark-green',
  };

  return (
    <TouchableOpacity
      className={`${baseStyle} ${variantStyles[variant]} ${isDisabled ? disabledStyle : ''}`}
      style={style}
      disabled={isDisabled}
      {...props}
    >
      {loading ? (
        <ActivityIndicator color={variant === 'primary' ? '#fff' : '#045454'} />
      ) : (
        <Text className={`${textBaseStyle} ${textVariantStyles[variant]}`}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

