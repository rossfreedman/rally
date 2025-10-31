import React, { useState, useMemo } from 'react';
import { View, Text, TouchableOpacity, ScrollView, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import LoadingSpinner from '../../components/ui/LoadingSpinner';
import EmptyState from '../../components/ui/EmptyState';
import { useAuthStore } from '../../state/auth.store';

type FilterType = 'all' | 'matches' | 'practices';

// Format date like "Saturday 9/20/25" (matches pretty_date_with_year filter)
function formatDateWithDay(dateStr: string): string {
  try {
    const [month, day, year] = dateStr.split('/');
    const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const dayName = dayNames[date.getDay()];
    const shortYear = year.length === 4 ? year.slice(-2) : year;
    return `${dayName} ${month}/${day}/${shortYear}`;
  } catch {
    return dateStr;
  }
}

// Format "View Team Availability 9/20"
function formatDateShort(dateStr: string): string {
  const [month, day] = dateStr.split('/');
  return `${parseInt(month)}/${parseInt(day)}`;
}

// Convert date from "M/D/YY" or "M/D/YYYY" to "YYYY-MM-DD" format for API
function convertDateToApiFormat(dateStr: string): string {
  try {
    const [month, day, year] = dateStr.split('/');
    // Handle 2-digit and 4-digit years
    const fullYear = year.length === 2 ? `20${year}` : year;
    // Pad month and day with leading zeros
    const paddedMonth = month.padStart(2, '0');
    const paddedDay = day.padStart(2, '0');
    return `${fullYear}-${paddedMonth}-${paddedDay}`;
  } catch (error) {
    console.error('Error converting date format:', error);
    return dateStr; // Return original if conversion fails
  }
}

export default function AvailabilityScreen() {
  const [filter, setFilter] = useState<FilterType>('all');
  const [showPastEvents, setShowPastEvents] = useState(false);
  const queryClient = useQueryClient();
  const { user } = useAuthStore();

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['mobile-availability'],
    queryFn: async () => {
      const response = await apiClient.get('/api/mobile-availability-data');
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
  });

  const setAvailabilityMutation = useMutation({
    mutationFn: async ({ date, status }: { date: string, status: number }) => {
      // Convert date from "M/D/YY" to "YYYY-MM-DD" format
      const apiDate = convertDateToApiFormat(date);
      
      // Build request payload with required fields
      const requestData: any = {
        match_date: apiDate,
        availability_status: status,
      };
      
      // Add tenniscores_player_id if available, otherwise use player_name from user
      if (user?.tenniscores_player_id) {
        requestData.tenniscores_player_id = user.tenniscores_player_id;
      } else if (user?.first_name && user?.last_name) {
        // Fallback to player_name for legacy support
        requestData.player_name = `${user.first_name} ${user.last_name}`;
      }
      
      // Add series if available
      if (user?.series) {
        requestData.series = user.series;
      }
      
      const response = await apiClient.post('/api/availability', requestData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mobile-availability'] });
    },
  });

  const handleSetAvailability = (date: string, status: 'available' | 'unavailable' | 'not_sure') => {
    const numericStatus = status === 'available' ? 1 : status === 'unavailable' ? 2 : 3;
    setAvailabilityMutation.mutate({ date, status: numericStatus });
  };

  // Group events by date and separate past/future - matches HTML structure exactly
  const { futureEvents, pastEvents } = useMemo(() => {
    if (!data?.match_avail_pairs) return { futureEvents: [], pastEvents: [] };

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const parseDate = (dateStr: string) => {
      const [month, day, year] = dateStr.split('/');
      return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    };

    const allEvents = data.match_avail_pairs as any[];
    const future: any[] = [];
    const past: any[] = [];

    allEvents.forEach(([match, avail]: any) => {
      const eventDate = parseDate(match.date);
      if (eventDate >= today) {
        future.push([match, avail]);
      } else {
        past.push([match, avail]);
      }
    });

    // Group by date (matches .schedule-date-group structure)
    const groupedFuture = future.reduce((acc: any, [match, avail]: any) => {
      const date = match.date;
      if (!acc[date]) acc[date] = [];
      acc[date].push([match, avail]);
      return acc;
    }, {});

    const groupedPast = past.reduce((acc: any, [match, avail]: any) => {
      const date = match.date;
      if (!acc[date]) acc[date] = [];
      acc[date].push([match, avail]);
      return acc;
    }, {});

    return {
      futureEvents: Object.entries(groupedFuture).map(([date, events]: [string, any]) => ({
        date,
        events,
        isPractice: events[0]?.[0]?.type === 'practice',
      })),
      pastEvents: Object.entries(groupedPast).map(([date, events]: [string, any]) => ({
        date,
        events,
        isPractice: events[0]?.[0]?.type === 'practice',
      })),
    };
  }, [data]);

  // Filter future events
  const filteredFutureEvents = useMemo(() => {
    return futureEvents.filter((group) => {
      if (filter === 'all') return true;
      if (filter === 'matches') return !group.isPractice;
      if (filter === 'practices') return group.isPractice;
      return true;
    });
  }, [futureEvents, filter]);

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 bg-gray-50">
        <LoadingSpinner message="Loading schedule..." />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: '#f9fafb' }}>
      <ScrollView
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor="#045454" />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Header - matches web app */}
        <View style={{ backgroundColor: '#ffffff', borderBottomWidth: 1, borderBottomColor: '#f3f4f6' }}>
          <View className="flex-row items-center px-4 py-6">
            <View 
              className="w-12 h-12 rounded-full items-center justify-center"
              style={{ backgroundColor: '#10645c' }}
            >
              <Text style={{ fontSize: 20, color: '#ffffff' }}>📅</Text>
            </View>
            <View className="ml-4 flex-1">
              <Text style={{ fontSize: 20, fontWeight: '700', color: '#111827' }}>View Schedule</Text>
              <Text style={{ fontSize: 14, color: '#6b7280' }}>
                Manage your availability for matches & practices
              </Text>
            </View>
          </View>
        </View>

        <View className="px-4 py-6">
          {/* Download Calendar Button */}
          <View className="items-end mb-6">
            <TouchableOpacity 
              className="flex-row items-center px-2 py-1 rounded-full"
              style={{ 
                backgroundColor: '#045454',
                shadowColor: '#000',
                shadowOffset: { width: 0, height: 1 },
                shadowOpacity: 0.05,
                shadowRadius: 2,
                elevation: 1,
              }}
            >
              <Text style={{ fontSize: 14, color: '#bff863', marginRight: 4 }}>📅</Text>
              <Text style={{ fontSize: 14, fontWeight: '500', color: '#bff863' }}>
                Download to calendar
              </Text>
            </TouchableOpacity>
          </View>

          {/* Filter Section - matches web app structure */}
          <View 
            className="bg-white rounded-xl overflow-hidden mb-6"
            style={{
              borderWidth: 1,
              borderColor: '#f3f4f6',
              shadowColor: '#000',
              shadowOffset: { width: 0, height: 1 },
              shadowOpacity: 0.05,
              shadowRadius: 2,
              elevation: 1,
            }}
          >
            <View 
              className="px-6 py-4"
              style={{ borderBottomWidth: 1, borderBottomColor: '#f9fafb' }}
            >
              <View className="flex-row items-center">
                <Text style={{ fontSize: 18, color: '#3b82f6', marginRight: 8 }}>🔍</Text>
                <Text style={{ fontSize: 18, fontWeight: '600', color: '#111827' }}>Filter Events</Text>
              </View>
            </View>
            <View className="px-6 py-6">
              <View style={{ flexDirection: 'row' }}>
                <TouchableOpacity
                  onPress={() => setFilter('all')}
                  style={{ 
                    flex: 1, 
                    paddingVertical: 12,
                    borderRadius: 8,
                    backgroundColor: filter === 'all' ? '#bff863' : '#10645c',
                    borderWidth: 1,
                    borderColor: filter === 'all' ? '#bff863' : '#10645c',
                    marginRight: 8,
                  }}
                >
                  <Text
                    style={{ 
                      textAlign: 'center',
                      fontWeight: '500',
                      color: filter === 'all' ? '#10645c' : '#bff863',
                      fontSize: 14,
                    }}
                  >
                    All
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => setFilter('matches')}
                  style={{ 
                    flex: 1,
                    paddingVertical: 12,
                    borderRadius: 8,
                    backgroundColor: filter === 'matches' ? '#bff863' : '#10645c',
                    borderWidth: 1,
                    borderColor: filter === 'matches' ? '#bff863' : '#10645c',
                    marginHorizontal: 8,
                  }}
                >
                  <Text
                    style={{ 
                      textAlign: 'center',
                      fontWeight: '500',
                      color: filter === 'matches' ? '#10645c' : '#bff863',
                      fontSize: 14,
                    }}
                  >
                    Matches
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={() => setFilter('practices')}
                  style={{ 
                    flex: 1,
                    paddingVertical: 12,
                    borderRadius: 8,
                    backgroundColor: filter === 'practices' ? '#bff863' : '#10645c',
                    borderWidth: 1,
                    borderColor: filter === 'practices' ? '#bff863' : '#10645c',
                    marginLeft: 8,
                  }}
                >
                  <Text
                    style={{ 
                      textAlign: 'center',
                      fontWeight: '500',
                      color: filter === 'practices' ? '#10645c' : '#bff863',
                      fontSize: 14,
                    }}
                  >
                    Practices
                  </Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>

          {/* Past Events Accordion - matches web app */}
          {pastEvents.length > 0 && (
            <TouchableOpacity
              onPress={() => setShowPastEvents(!showPastEvents)}
              className="bg-gray-100 rounded-xl mb-6 overflow-hidden"
              style={{
                borderWidth: 2,
                borderColor: '#045454',
              }}
            >
              <View className="flex-row items-center justify-between px-4 py-4">
                <View className="flex-row items-center">
                  <Text style={{ fontSize: 16, color: '#4b5563', marginRight: 12 }}>🕒</Text>
                  <Text style={{ fontSize: 16, fontWeight: '600', color: '#374151' }}>
                    Past Events ({pastEvents.length} date{pastEvents.length !== 1 ? 's' : ''})
                  </Text>
                </View>
                <Text style={{ fontSize: 14, color: '#4b5563' }}>
                  {showPastEvents ? '▼' : '▶'}
                </Text>
              </View>
            </TouchableOpacity>
          )}

          {/* Future Events - matches .schedule-date-group structure */}
          {filteredFutureEvents.length === 0 ? (
            <EmptyState
              message="No upcoming events"
              description="Your future matches and practices will appear here"
            />
          ) : (
            <View>
              {filteredFutureEvents.map((group, idx) => (
                <View key={group.date} style={{ marginBottom: idx < filteredFutureEvents.length - 1 ? 24 : 0 }}>
                  <DateGroup
                    key={group.date}
                    date={group.date}
                    events={group.events}
                    isPractice={group.isPractice}
                    onSetAvailability={handleSetAvailability}
                    isUpdating={setAvailabilityMutation.isPending}
                  />
                </View>
              ))}
            </View>
          )}

          {/* Past Events (if expanded) */}
          {showPastEvents && pastEvents.length > 0 && (
            <View className="mt-2">
              {pastEvents.map((group, idx) => (
                <View key={`past-${group.date}`} style={{ marginBottom: idx < pastEvents.length - 1 ? 24 : 0 }}>
                  <DateGroup
                    key={`past-${group.date}`}
                    date={group.date}
                    events={group.events}
                    isPractice={group.isPractice}
                    onSetAvailability={handleSetAvailability}
                    isUpdating={setAvailabilityMutation.isPending}
                  />
                </View>
              ))}
            </View>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

// Date Group Component - matches .schedule-date-group exactly
function DateGroup({
  date,
  events,
  isPractice,
  onSetAvailability,
  isUpdating,
}: {
  date: string;
  events: any[];
  isPractice: boolean;
  onSetAvailability: (date: string, status: 'available' | 'unavailable' | 'not_sure') => void;
  isUpdating: boolean;
}) {
  return (
    <View>
      {/* Date Header - matches .schedule-date-header (rounded-xl p-4 mb-4) */}
      <View
        className="flex-row items-center px-4 py-4 mb-4 rounded-xl"
        style={{ 
          backgroundColor: isPractice ? '#bff863' : '#045454',
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.1,
          shadowRadius: 6,
          elevation: 4,
        }}
      >
        <View className="flex-row items-center">
          <Text style={{ fontSize: 18, marginRight: 12 }}>
            {isPractice ? '🏋️' : '🏆'}
          </Text>
          <Text
            style={{ 
              fontSize: 18,
              fontWeight: '600',
              color: isPractice ? '#045454' : '#bff863'
            }}
          >
            {isPractice ? 'Practice' : 'Match'}
          </Text>
        </View>
      </View>

      {/* Event Cards - matches .schedule-card structure */}
      {events.map(([match, avail]: any, index: number) => (
        <EventCard
          key={`${date}-${index}`}
          match={match}
          availability={avail}
          onSetAvailability={onSetAvailability}
          isUpdating={isUpdating}
        />
      ))}
    </View>
  );
}

// Event Card Component - matches HTML structure EXACTLY
function EventCard({
  match,
  availability,
  onSetAvailability,
  isUpdating = false,
}: {
  match: any;
  availability: any;
  onSetAvailability: (date: string, status: 'available' | 'unavailable' | 'not_sure') => void;
  isUpdating?: boolean;
}) {
  const currentStatus = availability?.status;
  const notes = availability?.notes;
  const isPractice = match.type === 'practice';

  return (
    <View 
      className="bg-white rounded-xl mb-4 p-6"
      style={{
        borderWidth: 1,
        borderColor: '#f3f4f6',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 2,
        elevation: 1,
      }}
    >
      {/* Two Column Layout - flex flex-row gap-6 */}
      <View style={{ flexDirection: 'row' }}>
        {/* Column 1: Match Info - flex flex-col gap-4 flex-1 */}
        <View style={{ flex: 1, marginRight: 24 }}>
          {/* Date and Time - text-lg font-medium */}
          <View style={{ marginBottom: 16 }}>
            <Text style={{ fontSize: 18, fontWeight: '700', color: '#111827' }}>
              {formatDateWithDay(match.date)}
            </Text>
            {match.time && (
              <Text style={{ fontSize: 16, color: '#4b5563' }}>{match.time}</Text>
            )}
          </View>

          {/* Match Details - text-sm font-bold */}
          {!isPractice && match.home_team && match.away_team && (
            <View style={{ marginBottom: 16 }}>
              <Text style={{ fontSize: 14, fontWeight: '700', color: '#111827' }}>
                {match.home_team.split(' - ')[0]} vs.
              </Text>
              <Text style={{ fontSize: 14, fontWeight: '700', color: '#111827' }}>
                {match.away_team.split(' - ')[0]}
              </Text>
            </View>
          )}

          {/* Location - flex items-center gap-2 mt-4 */}
          {!isPractice && match.location && match.location !== 'All Clubs' && (
            <View className="flex-row items-center mt-4">
              <Text style={{ fontSize: 14, color: '#ef4444', marginRight: 8 }}>📍</Text>
              <Text style={{ fontSize: 14, fontWeight: '700', color: '#4b5563' }}>
                {match.location}
              </Text>
            </View>
          )}

          {/* Get Directions Button - mt-3 */}
          {!isPractice && match.club_address && match.location && (
            <View className="mt-3">
              <TouchableOpacity 
                className="px-2 py-1.5 rounded-md self-start"
                style={{ backgroundColor: '#10b981' }}
              >
                <Text style={{ color: '#ffffff', fontSize: 12, fontWeight: '500' }}>
                  🧭 Get Directions
                </Text>
              </TouchableOpacity>
            </View>
          )}
        </View>

        {/* Column 2: Availability Column - width: 187px, gap: 1rem (16px) */}
        <View style={{ width: 187, flexShrink: 0 }}>
          
          {/* Availability Buttons Container - matches .availability-container */}
          <View 
            className="rounded-lg p-4"
            style={{
              width: 187,
              borderWidth: 1,
              borderColor: '#e5e7eb',
              backgroundColor: '#f9fafb',
              marginBottom: 16,
            }}
          >
            {/* Count Me In - matches .availability-button.selected-available */}
            <TouchableOpacity
              onPress={() => onSetAvailability(match.date, 'available')}
              disabled={isUpdating}
              className="rounded-lg"
              style={{
                width: '100%',
                paddingVertical: 10,
                backgroundColor: currentStatus === 'available' ? '#22c55e' : '#f3f4f6',
                borderWidth: 1,
                borderColor: currentStatus === 'available' ? '#22c55e' : '#d1d5db',
                marginBottom: 12,
              }}
            >
              <Text
                style={{
                  textAlign: 'center',
                  fontSize: 12,
                  fontWeight: '600',
                  color: currentStatus === 'available' ? '#ffffff' : '#374151',
                }}
              >
                ✓ Count Me In!
              </Text>
            </TouchableOpacity>

            {/* Sorry, Can't */}
            <TouchableOpacity
              onPress={() => onSetAvailability(match.date, 'unavailable')}
              disabled={isUpdating}
              className="rounded-lg"
              style={{
                width: '100%',
                paddingVertical: 10,
                backgroundColor: currentStatus === 'unavailable' ? '#ef4444' : '#f3f4f6',
                borderWidth: 1,
                borderColor: currentStatus === 'unavailable' ? '#ef4444' : '#d1d5db',
                marginBottom: 12,
              }}
            >
              <Text
                style={{
                  textAlign: 'center',
                  fontSize: 12,
                  fontWeight: '600',
                  color: currentStatus === 'unavailable' ? '#ffffff' : '#374151',
                }}
              >
                × Sorry, Can't
              </Text>
            </TouchableOpacity>

            {/* Not Sure */}
            <TouchableOpacity
              onPress={() => onSetAvailability(match.date, 'not_sure')}
              disabled={isUpdating}
              className="rounded-lg"
              style={{
                width: '100%',
                paddingVertical: 10,
                backgroundColor: currentStatus === 'not_sure' ? '#f59e0b' : '#f3f4f6',
                borderWidth: 1,
                borderColor: currentStatus === 'not_sure' ? '#f59e0b' : '#d1d5db',
              }}
            >
              <Text
                style={{
                  textAlign: 'center',
                  fontSize: 12,
                  fontWeight: '600',
                  color: currentStatus === 'not_sure' ? '#ffffff' : '#374151',
                }}
              >
                ? Not Sure
              </Text>
            </TouchableOpacity>
          </View>

          {/* Add Note Container - separate container, conditional display */}
          {!notes && (
            <View 
              className="rounded-lg p-4"
              style={{
                width: 187,
                borderWidth: 1,
                borderColor: '#e5e7eb',
                backgroundColor: '#f9fafb',
                marginBottom: 16,
              }}
            >
              <TouchableOpacity 
                className="rounded-lg"
                style={{
                  width: '100%',
                  paddingVertical: 10,
                  backgroundColor: '#e5e7eb',
                  borderWidth: 1,
                  borderColor: '#d1d5db',
                }}
              >
                <Text style={{ textAlign: 'center', fontSize: 12, fontWeight: '600', color: '#374151' }}>
                  ✏️ Add a note
                </Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Note Display - separate container, conditional display */}
          {notes && (
            <View 
              className="rounded-lg p-4"
              style={{
                width: 187,
                borderWidth: 1,
                borderColor: '#e5e7eb',
                backgroundColor: '#f9fafb',
                marginBottom: 16,
              }}
            >
              <View className="mb-2">
                <View className="flex-row items-center justify-between mb-1">
                  <View className="flex-row items-center">
                    <Text style={{ fontSize: 10, color: '#9ca3af', marginRight: 4 }}>📝</Text>
                    <Text style={{ fontSize: 12, fontWeight: '500', color: '#374151' }}>Note</Text>
                  </View>
                  <TouchableOpacity>
                    <Text style={{ fontSize: 12, color: '#3b82f6' }}>✏️</Text>
                  </TouchableOpacity>
                </View>
                <Text style={{ fontSize: 12, color: '#374151' }}>{notes}</Text>
              </View>
            </View>
          )}

          {/* View Team Availability - matches .blue-container CSS */}
          <View 
            className="rounded-lg p-4"
            style={{
              width: 187,
              borderWidth: 1,
              borderColor: '#e5e7eb',
              backgroundColor: '#eff6ff',
            }}
          >
            <TouchableOpacity>
              <Text 
                style={{ 
                  textAlign: 'center', 
                  fontSize: 10, // 0.625rem = 10px
                  fontWeight: '600', 
                  color: '#3b82f6',
                }}
              >
                View Team Availability {formatDateShort(match.date)}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </View>
  );
}
