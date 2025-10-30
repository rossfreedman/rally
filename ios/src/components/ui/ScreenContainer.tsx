import React from 'react';
import { SafeAreaView, ScrollView, View, type ViewProps } from 'react-native';

interface ScreenContainerProps extends ViewProps {
  children: React.ReactNode;
  scrollable?: boolean;
}

export default function ScreenContainer({
  children,
  scrollable = true,
  style,
  ...props
}: ScreenContainerProps) {
  const content = (
    <View className="flex-1 bg-gray-50 px-4 py-4" style={style} {...props}>
      {children}
    </View>
  );

  if (scrollable) {
    return (
      <SafeAreaView className="flex-1 bg-gray-50">
        <ScrollView
          className="flex-1"
          contentContainerStyle={{ paddingBottom: 20 }}
          showsVerticalScrollIndicator={false}
        >
          {content}
        </ScrollView>
      </SafeAreaView>
    );
  }

  return <SafeAreaView className="flex-1 bg-gray-50">{content}</SafeAreaView>;
}

