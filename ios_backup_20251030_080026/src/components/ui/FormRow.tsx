import React from 'react';
import { View, Text, TextInput, type TextInputProps } from 'react-native';

interface FormRowProps extends TextInputProps {
  label: string;
  error?: string;
  required?: boolean;
}

export default function FormRow({
  label,
  error,
  required = false,
  style,
  ...props
}: FormRowProps) {
  return (
    <View className="mb-4">
      <Text className="text-sm font-semibold text-gray-700 mb-2">
        {label}
        {required && <Text className="text-red-500"> *</Text>}
      </Text>
      <TextInput
        className={`border rounded-lg px-4 py-3 text-base ${
          error ? 'border-red-500' : 'border-gray-300'
        }`}
        style={style}
        placeholderTextColor="#9CA3AF"
        {...props}
      />
      {error && <Text className="text-red-500 text-sm mt-1">{error}</Text>}
    </View>
  );
}

