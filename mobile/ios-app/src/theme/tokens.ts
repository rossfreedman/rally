/**
 * Design Tokens - Schedule Screen
 * Extracted from pixel-perfect specification
 */

export const Colors = {
  // Primary
  rallyDarkGreen: '#045454',
  rallyLightGreen: '#bff863',
  limeGreen: '#32CD32',
  rallyTeal: '#0E7C7B',
  rallyTealSoft: '#E6F3F3',
  
  // Text
  textPrimary: '#111827',
  textSecondary: '#6B7280',
  textTertiary: '#9CA3AF',
  
  // Backgrounds
  bgPrimary: '#FFFFFF',
  bgSecondary: '#F7F8FA',
  borderLight: '#E5E7EB',
  borderSubtle: '#EEF1F4',
  
  // Button States
  buttonGrayBG: '#F3F4F6',
  buttonGrayBGDark: '#D1D5DB',
  
  // Accents
  blueMedium: '#3B82F6',
  blueLight: '#EFF6FF',
  redMarker: '#EF4444',
  greenButton: '#10B981',
  yellowButton: '#FCD34D',
  
  // Overlays
  overlay: 'rgba(0,0,0,0.04)',
  
  // Special
  white: '#FFFFFF',
  black: '#000000',
} as const;

export const Spacing = {
  micro: 4,
  small: 8,
  base: 12,
  standard: 16,
  medium: 20,
  large: 24,
  xlarge: 32,
} as const;

export const Typography = {
  pageTitle: {
    fontSize: 28,
    fontWeight: '700' as const,
    lineHeight: 34,
    letterSpacing: 0,
  },
  subtitle: {
    fontSize: 14,
    fontWeight: '400' as const,
    lineHeight: 20,
    letterSpacing: 0.15,
  },
  filterTitle: {
    fontSize: 16,
    fontWeight: '600' as const,
    lineHeight: 22,
    letterSpacing: 0,
  },
  chipLabel: {
    fontSize: 15,
    fontWeight: '500' as const,
    lineHeight: 20,
    letterSpacing: 0,
  },
  sectionHeader: {
    fontSize: 18,
    fontWeight: '600' as const,
    lineHeight: 24,
    letterSpacing: 0,
  },
  eventDate: {
    fontSize: 18,
    fontWeight: '700' as const,
    lineHeight: 24,
    letterSpacing: 0,
  },
  eventTime: {
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 22,
    letterSpacing: 0,
  },
  buttonText: {
    fontSize: 15,
    fontWeight: '500' as const,
    lineHeight: 20,
    letterSpacing: 0,
  },
  noteLabel: {
    fontSize: 12,
    fontWeight: '400' as const,
    lineHeight: 16,
    letterSpacing: 0,
  },
  tabLabel: {
    fontSize: 11,
    fontWeight: '500' as const,
    lineHeight: 13,
    letterSpacing: 0,
  },
} as const;

export const BorderRadius = {
  small: 10,
  medium: 14,
  large: 20,
  pill: 22,
} as const;

export const Shadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  cardElevated: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 6,
  },
  tabBar: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 8,
  },
} as const;

export const Layout = {
  topBarHeight: 104,
  filterCardPadding: Spacing.standard,
  chipHeight: 38,
  chipPaddingH: Spacing.base,
  chipPaddingV: Spacing.small,
  pastEventsHeight: 48,
  sectionHeaderHeight: 44,
  eventCardPadding: Spacing.large,
  availabilityColumnWidth: 200,
  buttonHeight: 44,
  buttonPaddingH: Spacing.base,
  tabBarHeight: 90,
  tabIconSize: 24,
  minTapTarget: 44,
} as const;


