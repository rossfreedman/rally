import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Colors, Typography, Spacing, BorderRadius, Layout } from '../../../theme/tokens';

interface NoteButtonProps {
  hasNote: boolean;
  noteText?: string;
  onPress: () => void;
}

export const NoteButton: React.FC<NoteButtonProps> = ({ hasNote, noteText, onPress }) => {
  if (hasNote && noteText) {
    return (
      <View style={styles.noteDisplay}>
        <View style={styles.noteHeader}>
          <View style={styles.noteHeaderLeft}>
            <Text style={styles.noteIcon}>📝</Text>
            <Text style={styles.noteLabel}>Note</Text>
          </View>
          <TouchableOpacity
            onPress={onPress}
            accessibilityLabel="Edit note"
            style={styles.editButton}
          >
            <Text style={styles.editIcon}>✏️</Text>
            <Text style={styles.editText}>Edit</Text>
          </TouchableOpacity>
        </View>
        <Text style={styles.noteText}>{noteText}</Text>
      </View>
    );
  }

  return (
    <TouchableOpacity
      style={styles.addNoteButton}
      onPress={onPress}
      accessibilityLabel="Add a note"
    >
      <Text style={styles.addNoteIcon}>✏️</Text>
      <Text style={styles.addNoteText}>Add a note</Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  addNoteButton: {
    flexDirection: 'row',
    alignItems: 'center',
    height: Layout.buttonHeight,
    paddingHorizontal: Layout.buttonPaddingH,
    borderRadius: BorderRadius.small,
    backgroundColor: Colors.bgSecondary,
    minHeight: Layout.minTapTarget,
  },
  addNoteIcon: {
    fontSize: 16,
    marginRight: Spacing.small,
    color: Colors.textTertiary,
  },
  addNoteText: {
    ...Typography.buttonText,
    color: Colors.textSecondary,
  },
  noteDisplay: {
    backgroundColor: Colors.bgSecondary,
    borderRadius: BorderRadius.small,
    padding: Spacing.base,
  },
  noteHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: Spacing.small,
  },
  noteHeaderLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  noteIcon: {
    fontSize: 10,
    marginRight: Spacing.small,
    color: Colors.textTertiary,
  },
  noteLabel: {
    ...Typography.noteLabel,
    color: Colors.textSecondary,
  },
  editButton: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  editIcon: {
    fontSize: 14,
    marginRight: Spacing.micro,
    color: Colors.textSecondary,
  },
  editText: {
    ...Typography.noteLabel,
    color: Colors.textSecondary,
  },
  noteText: {
    ...Typography.eventTime,
    color: Colors.textPrimary,
  },
});


