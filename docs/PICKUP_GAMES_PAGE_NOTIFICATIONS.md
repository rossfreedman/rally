# Pickup Games Page Notifications

## Overview

The pickup games page (`/mobile/pickup-games`) now includes a dedicated notifications section that displays available pickup games where the user meets the criteria. This provides immediate visibility of relevant games without having to navigate away from the page.

## Features

### 1. Dedicated Notifications Section
- **Location**: Top of the pickup-games page, below the header
- **Title**: "🎾 Available Games" with decorative borders
- **Purpose**: Shows pickup games that match the user's criteria

### 2. Smart Filtering
The notifications section only shows pickup games where the user:
- Meets the PTI range requirements
- Fulfills series restrictions (if any)
- Is from the same club (if club-only games)
- Hasn't already joined the game
- Game has available spots

### 3. Real-time Updates
- **Auto-refresh**: Notifications update every 2 minutes
- **Dynamic loading**: Shows loading state while fetching data
- **Empty state**: Friendly message when no games are available

## Technical Implementation

### Frontend Changes

**File**: `templates/mobile/pickup_games.html`

1. **HTML Structure**:
   ```html
   <!-- Pickup Games Notifications Section -->
   <div class="px-4 py-4">
       <div class="flex items-center justify-center mb-4">
           <div class="flex-grow border-t-2 border-gray-400"></div>
           <div class="section-header text-lg font-bold px-4 text-center">
               🎾 Available Games
           </div>
           <div class="flex-grow border-t-2 border-gray-400"></div>
       </div>
       
       <!-- Notifications Container -->
       <div id="pickup-notifications-container" class="space-y-4">
           <!-- Loading, empty, and list states -->
       </div>
   </div>
   ```

2. **JavaScript Functions**:
   - `loadPickupGamesNotifications()`: Fetches and filters notifications
   - `renderPickupNotifications()`: Renders notification cards
   - `getPickupNotificationIcon()`: Returns tennis court icon
   - Auto-refresh every 2 minutes

### Backend Integration

**API Endpoint**: `/api/home/notifications`

The notifications section uses the existing home notifications API and filters for pickup games notifications specifically:

```javascript
// Filter for pickup games notifications only
const pickupNotifications = notifications.filter(notification => 
    notification.type === 'match' && 
    notification.title && 
    notification.title.includes('Pickup Game')
);
```

## User Experience

### Visual Design
- **Consistent styling**: Matches the existing pickup games page design
- **Tennis court icon**: Uses the same icon as the pickup games button
- **Teal color scheme**: Consistent with the page's color palette
- **Smooth animations**: Fade-in effects with staggered delays

### Interaction
- **Click to join**: "Join Game" buttons link to the pickup games page
- **Real-time updates**: Notifications refresh automatically
- **Loading states**: Clear feedback during data fetching
- **Empty states**: Helpful messaging when no games are available

## Testing

### Test Script
**File**: `scripts/test_pickup_games_page_notifications.py`

The test script verifies:
1. Page loads correctly (handles authentication redirects)
2. Notifications API is accessible
3. Pickup games API is working
4. Template changes are applied

### Manual Testing
To test the feature manually:
1. Log in to the application
2. Navigate to `/mobile/pickup-games`
3. Look for the "🎾 Available Games" section at the top
4. Verify notifications appear if you meet game criteria
5. Test the "Join Game" buttons

## Benefits

1. **Immediate Visibility**: Users see relevant games without scrolling
2. **Reduced Navigation**: No need to go back to home page for notifications
3. **Contextual Information**: Notifications are shown in the right context
4. **Consistent Experience**: Matches the design patterns of other pages
5. **Real-time Updates**: Always shows current availability

## Future Enhancements

1. **Push Notifications**: Send browser notifications for new games
2. **Smart Filtering**: Learn user preferences and show more relevant games
3. **Game Recommendations**: Suggest games based on playing history
4. **Quick Join**: Allow joining games directly from notifications
5. **Game Reminders**: Remind users about games they've joined

## Troubleshooting

### Common Issues

1. **Notifications not showing**:
   - Check if user meets game criteria (PTI, series, club)
   - Verify pickup games exist in the database
   - Check browser console for JavaScript errors

2. **Page not loading**:
   - Ensure user is authenticated
   - Check server is running on port 8080
   - Verify template changes are applied

3. **API errors**:
   - Check server logs for backend errors
   - Verify database connectivity
   - Ensure pickup games tables exist

### Debug Commands

```bash
# Test the feature
python scripts/test_pickup_games_page_notifications.py

# Check server status
curl -I http://127.0.0.1:8080/mobile/pickup-games

# View server logs
tail -f logs/app.log
``` 