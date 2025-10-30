import { EventData } from '../components/EventCard';

/**
 * Mock data fixture for ScheduleScreen
 * Matches the structure visible in the reference screenshot
 */
export const mockEvents: EventData[] = [
  {
    id: '1',
    type: 'practice',
    date: 'Friday 10/31/25',
    time: '4:30 PM',
    availabilityStatus: 'available',
  },
  {
    id: '2',
    type: 'practice',
    date: 'Sunday 11/2/25',
    time: '9:30 AM',
    availabilityStatus: 'available',
  },
  {
    id: '3',
    type: 'match',
    date: 'Tuesday 9/23/25',
    time: '6:30 PM',
    homeTeam: 'Indian Hill 20',
    awayTeam: 'Tennaqua 20',
    location: 'Tennaqua',
    availabilityStatus: 'available',
    otherTeamsAtHome: ['Series 32', 'Series 38'],
  },
  {
    id: '4',
    type: 'match',
    date: 'Tuesday 9/30/25',
    time: '6:30 PM',
    homeTeam: 'Westmoreland 20',
    awayTeam: 'Tennaqua 20',
    location: 'Tennaqua',
    availabilityStatus: 'available',
    otherTeamsAtHome: ['Series 26', 'Series 8'],
  },
  {
    id: '5',
    type: 'practice',
    date: 'Sunday 9/28/25',
    time: '9:30 AM',
    availabilityStatus: 'available',
  },
  {
    id: '6',
    type: 'practice',
    date: 'Sunday 9/21/25',
    time: '9:30 AM',
    availabilityStatus: 'not_sure',
    note: 'Sore calf',
  },
  {
    id: '7',
    type: 'match',
    date: 'Tuesday 10/7/25',
    time: '6:30 PM',
    homeTeam: 'Tennaqua 20',
    awayTeam: 'Evanston 20',
    location: 'Evanston',
    isAway: true,
    availabilityStatus: 'available',
  },
];

export const mockPastEventsCount = 14;


