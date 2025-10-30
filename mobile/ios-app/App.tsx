import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { ScheduleScreen } from './src/features/schedule/ScheduleScreen';
import { PixelOverlay } from './src/features/schedule/utils/PixelOverlay';
import { mockEvents, mockPastEventsCount } from './src/features/schedule/fixtures/mockData';

/**
 * Main App Component
 * Renders ScheduleScreen with mock data for pixel-perfect UI verification
 */
export default function App() {
  const handleAvailabilityChange = (eventId: string, status: any) => {
    console.log('Availability changed:', eventId, status);
  };

  const handleNotePress = (eventId: string) => {
    console.log('Note pressed:', eventId);
  };

  const handleTeamAvailabilityPress = (eventId: string) => {
    console.log('Team availability pressed:', eventId);
  };

  const handleDownloadPress = () => {
    console.log('Download to calendar pressed');
  };

  const handleTabPress = (tab: string) => {
    console.log('Tab pressed:', tab);
  };

  return (
    <>
      <StatusBar style="dark" />
      <ScheduleScreen
        events={mockEvents}
        pastEventsCount={mockPastEventsCount}
        onAvailabilityChange={handleAvailabilityChange}
        onNotePress={handleNotePress}
        onTeamAvailabilityPress={handleTeamAvailabilityPress}
        onDownloadPress={handleDownloadPress}
        onTabPress={handleTabPress}
      />
      {/* PixelOverlay disabled by default - enable in dev mode */}
      {__DEV__ && (
        <PixelOverlay
          // referenceImage={require('./docs/reference/schedule-web-reference.png')}
          enabled={false}
        />
      )}
    </>
  );
}


