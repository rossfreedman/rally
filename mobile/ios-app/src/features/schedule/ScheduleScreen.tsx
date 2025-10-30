import React, { useState } from 'react';
import { View, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { TopBar } from './components/TopBar';
import { FilterCard, FilterMode } from './components/FilterCard';
import { PastEventsToggle } from './components/PastEventsToggle';
import { SectionHeader } from './components/SectionHeader';
import { EventCard, EventData } from './components/EventCard';
import { BottomTabBar, TabType } from './tabs/BottomTabBar';
import { Colors, Spacing } from '../../theme/tokens';

interface ScheduleScreenProps {
  // Pure presentational - accepts data as props
  events: EventData[];
  pastEventsCount?: number;
  onDownloadPress?: () => void;
  onAvailabilityChange?: (eventId: string, status: EventData['availabilityStatus']) => void;
  onNotePress?: (eventId: string) => void;
  onTeamAvailabilityPress?: (eventId: string) => void;
  onTabPress?: (tab: TabType) => void;
}

export const ScheduleScreen: React.FC<ScheduleScreenProps> = ({
  events,
  pastEventsCount = 0,
  onDownloadPress,
  onAvailabilityChange,
  onNotePress,
  onTeamAvailabilityPress,
  onTabPress,
}) => {
  const [filterMode, setFilterMode] = useState<FilterMode>('all');
  const [showPastEvents, setShowPastEvents] = useState(false);

  // Filter events based on mode
  const filteredEvents = events.filter((event) => {
    if (filterMode === 'all') return true;
    if (filterMode === 'matches') return event.type === 'match';
    if (filterMode === 'practices') return event.type === 'practice';
    return true;
  });

  // Separate by event type and group by date for section headers
  const groupedEvents: {
    type: EventData['type'];
    events: EventData[];
  }[] = [];

  let currentType: EventData['type'] | null = null;
  let currentGroup: EventData[] = [];

  filteredEvents.forEach((event) => {
    if (currentType !== event.type) {
      if (currentGroup.length > 0) {
        groupedEvents.push({ type: currentType!, events: currentGroup });
      }
      currentType = event.type;
      currentGroup = [event];
    } else {
      currentGroup.push(event);
    }
  });

  if (currentGroup.length > 0 && currentType) {
    groupedEvents.push({ type: currentType, events: currentGroup });
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <TopBar onDownloadPress={onDownloadPress} />
      
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.content}>
          <FilterCard mode={filterMode} onModeChange={setFilterMode} />
          
          {pastEventsCount > 0 && (
            <PastEventsToggle
              expanded={showPastEvents}
              count={pastEventsCount}
              onToggle={() => setShowPastEvents(!showPastEvents)}
            />
          )}
          
          {showPastEvents && (
            <View style={styles.pastEventsSection}>
              {/* Past events would go here */}
            </View>
          )}

          {/* Render grouped events with section headers */}
          {groupedEvents.map((group, groupIdx) => (
            <View key={groupIdx} style={styles.eventGroup}>
              <SectionHeader
                label={group.type === 'practice' ? 'Practice' : 'Match'}
              />
              {group.events.map((event) => (
                <EventCard
                  key={event.id}
                  event={event}
                  onAvailabilityChange={(status) =>
                    onAvailabilityChange?.(event.id, status)
                  }
                  onNotePress={() => onNotePress?.(event.id)}
                  onTeamAvailabilityPress={() => onTeamAvailabilityPress?.(event.id)}
                />
              ))}
            </View>
          ))}
        </View>
      </ScrollView>

      <BottomTabBar activeTab="availability" onTabPress={onTabPress || (() => {})} />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.bgSecondary,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: Spacing.xlarge,
  },
  content: {
    paddingHorizontal: Spacing.standard,
    paddingTop: Spacing.standard,
  },
  pastEventsSection: {
    marginBottom: Spacing.standard,
  },
  eventGroup: {
    marginBottom: Spacing.large,
  },
});


