import React, { useState } from 'react';
import { View, Text, KeyboardAvoidingView, Platform, Alert } from 'react-native';
import ScreenContainer from '../../components/ui/ScreenContainer';
import FormRow from '../../components/ui/FormRow';
import Button from '../../components/ui/Button';
import { useLogin } from '../../api/hooks/useAuth';
import type { LoginScreenProps } from '../../navigation/types';

export default function LoginScreen({}: LoginScreenProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');

  const login = useLogin();

  const validateForm = (): boolean => {
    let isValid = true;

    // Reset errors
    setEmailError('');
    setPasswordError('');

    // Validate email
    if (!email) {
      setEmailError('Email is required');
      isValid = false;
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      setEmailError('Please enter a valid email');
      isValid = false;
    }

    // Validate password
    if (!password) {
      setPasswordError('Password is required');
      isValid = false;
    }

    return isValid;
  };

  const handleLogin = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      await login.mutateAsync({
        email: email.trim().toLowerCase(),
        password,
      });
      // Navigation happens automatically via RootNavigator watching auth state
    } catch (error: any) {
      Alert.alert(
        'Login Failed',
        error.response?.data?.error || 'Invalid email or password. Please try again.',
        [{ text: 'OK' }]
      );
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      className="flex-1"
    >
      <ScreenContainer scrollable>
        {/* Header */}
        <View className="items-center mb-12 mt-8">
          <View className="w-24 h-24 bg-rally-dark-green rounded-full items-center justify-center mb-4">
            <Text className="text-4xl font-bold text-white">R</Text>
          </View>
          <Text className="text-3xl font-bold text-rally-dark-green">Rally</Text>
          <Text className="text-base text-gray-600 mt-2">Platform Tennis League Management</Text>
        </View>

        {/* Login Form */}
        <View className="mb-6">
          <FormRow
            label="Email"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="your@email.com"
            error={emailError}
            required
          />

          <FormRow
            label="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="Enter your password"
            error={passwordError}
            required
          />
        </View>

        {/* Login Button */}
        <Button
          title="Log In"
          onPress={handleLogin}
          loading={login.isPending}
          disabled={login.isPending}
        />

        {/* Footer */}
        <View className="items-center mt-8">
          <Text className="text-sm text-gray-600">
            Welcome to the Rally iOS app!
          </Text>
        </View>
      </ScreenContainer>
    </KeyboardAvoidingView>
  );
}

