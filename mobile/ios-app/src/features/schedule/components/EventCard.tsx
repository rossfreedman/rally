import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing, BorderRadius, Layout, Shadows } from '../../../theme/tokens';
import { AvailabilityButtons, AvailabilityStatus } from './AvailabilityButtons';
import { NoteButton } from './NoteButton';
import { TeamAvailabilityButton } from './TeamAvailabilityButton';

export type EventType = 'practice' | 'match';

export interface EventData {
  id: string;
  type: EventType;
  date: string; // "Friday 10/31/25"
  time: string; // "4:30 PM"
  location?: string;
  homeTeam?: string;
  awayTeam?: string;
  availabilityStatus: AvailabilityStatus;
  note?: string;
  otherTeamsAtHome?: string[]; // For home matches
  isAway?: boolean; // For away matches with directions
}

interface EventCardProps {
  event: EventData;
  onAvailabilityChange: (status: AvailabilityStatus) => void;
  onNotePress: () => void;
  onTeamAvailabilityPress: () => void;
}

export const EventCard: React.FC<EventCardProps> = ({
  event,
  onAvailabilityChange,
  onNotePress,
  onTeamAvailabilityPress,
}) => {
  return (
    <View style={styles.container}>
      {/* Two Column Layout */}
      <View style={styles.content}>
        {/* Left Column: Date and Time */}
        <View style={styles.leftColumn}>
          <Text style={styles.date}>{event.date}</Text>
          <Text style={styles.time}>{event.time}</Text>
          
          {/* Match Info */}
          {event.type === 'match' && (
            <View style={styles.matchInfo}>
              <Text style={styles.matchText}>
                {event.homeTeam || 'TBD'} vs.{'\n'}
                {event.awayTeam || 'TBD'}
              </Text>
              {event.location && (
                <View style={styles.locationRow}>
                  <Text style={styles.locationIcon}>📍</Text>
                  <Text style={styles.locationText}>{event.location}</Text>
                </View>
              )}
              
              {/* Home match: Show other teams */}
              {event.otherTeamsAtHome && event.otherTeamsAtHome.length > 0 && (
                <View style={styles.homeTeamsBox}>
                  <Text style={styles.homeIcon}>🏠</Text>
                  <Text style={styles.homeLabel}>Also at home:</Text>
                  {event.otherTeamsAtHome.map((team, idx) => (
                    <Text key={idx} style={styles.homeTeam}>{team}</Text>
                  ))}
                </View>
              )}
              
              {/* Away match: Show directions button */}
              {event.isAway && event.location && (
                <View style={styles.directionsContainer}>
                  <TouchableOpacity
                    style={styles.directionsButton}
                    onPress={() => {}}
                    accessibilityLabel={`Get directions to ${event.location}`}
                  >
                    <Text style={styles.directionsIcon}>🧭</Text>
                    <Text style={styles.directionsText}>Get Directions</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          )}
        </View>
        
        {/* Right Column: Availability Buttons */}
        <View style={styles.rightColumn}>
          <AvailabilityButtons
            status={event.availabilityStatus}
            onStatusChange={onAvailabilityChange}
          />
          <View style={styles.buttonSpacer} />
          <NoteButton
            hasNote={!!event.note}
            noteText={event.note}
            onPress={onNotePress}
          />
          <View style={styles.buttonSpacer} />
          <TeamAvailabilityButton
            date={event.date.split(' ')[1]} // Extract "10/31/25"
            onPress={onTeamAvailabilityPress}
          />
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.bgPrimary,
    borderRadius: BorderRadius.medium,
    padding: Layout.eventCardPadding,
    marginBottom: Spacing.standard,
    ...Shadows.card,
  },
  content: {
    flexDirection: 'row',
    gap: Spacing.large,
  },
  leftColumn: {
    flex: 1,
    gap: Spacing.base,
  },
  rightColumn: {
    width: Layout.availabilityColumnWidth,
  },
  date: {
    ...Typography.eventDate,
    color: Colors.textPrimary,
  },
  time: {
    ...Typography.eventTime,
    color: Colors.textSecondary,
  },
  matchInfo: {
    marginTop: Spacing.standard,
  },
  matchText: {
    ...Typography.eventTime,
    color: Colors.textPrimary,
    fontWeight: '700',
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: Spacing.standard,
    gap: Spacing.small,
  },
  locationIcon: {
    fontSize: 16,
    color: Colors.redMarker,
  },
  locationText: {
    ...Typography.eventTime,
    color: Colors.textSecondary,
    fontWeight: '700',
  },
  homeTeamsBox: {
    marginTop: Spacing.standard,
    padding: Spacing.small,
    backgroundColor: Colors.blueLight,
    borderRadius: BorderRadius.small,
    borderWidth: 1,
    borderColor: Colors.blueMedium,
  },
  homeIcon: {
    fontSize: 12,
    color: Colors.blueMedium,
    marginBottom: Spacing.micro,
  },
  homeLabel: {
    ...Typography.noteLabel,
    color: Colors.blueMedium,
    fontWeight: '600',
    marginBottom: Spacing.micro,
  },
  homeTeam: {
    ...Typography.noteLabel,
    color: Colors.blueMedium,
  },
  directionsContainer: {
    marginTop: Spacing.standard,
  },
  directionsButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.greenButton,
    paddingHorizontal: Spacing.small,
    paddingVertical: Spacing.small,
    borderRadius: BorderRadius.small,
    alignSelf: 'flex-start',
  },
  directionsIcon: {
    fontSize: 12,
    marginRight: Spacing.micro,
    color: Colors.white,
  },
  directionsText: {
    ...Typography.noteLabel,
    color: Colors.white,
    fontWeight: '600',
  },
  buttonSpacer: {
    height: Spacing.base,
  },
});

