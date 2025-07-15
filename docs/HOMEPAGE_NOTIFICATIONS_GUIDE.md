# HomePageNotifications Module

## Overview

The HomePageNotifications module provides personalized, dynamic notifications on the mobile home page that display relevant Rally user data and highlights. It's positioned above the ACT section and shows up to 3 prioritized notifications based on user activity and team context.

## Features

### 1. Personalized Notifications
- **Next match date/time and availability status**
- **Results from your last match** (personal performance)
- **Results from your last match** (team performance)
- **PTI change since last match** (with trend indicators)
- **Latest team poll** (with captain name and timing)
- **Message from your captain** (sample messages included)

### 2. Smart Prioritization
Notifications are prioritized in this order:
1. **Urgent match-related updates** (tonight's match, availability updates)
2. **Captain polls and messages** (latest team poll, captain communication)
3. **Recent match results** (personal and team performance)
4. **Personal performance highlights** (PTI changes, win streaks)
5. **Team performance highlights** (playoff position, team success)

### 3. Modern UI/UX
- **Mobile-optimized design** using Tailwind CSS
- **Smooth fade-in animations** with staggered delays
- **Color-coded icons** for different notification types
- **Call-to-action buttons** for relevant actions
- **Auto-refresh** every 5 minutes

## Technical Implementation

### Backend API

**Endpoint:** `/api/home/notifications`

**Response Format:**
```typescript
type Notification = {
  id: string
  type: "match" | "captain" | "result" | "personal" | "team"
  title: string
  message: string
  cta?: { label: string, href: string }
  priority: number
}

type Response = {
  notifications: Notification[]
}
```

**Notification Types:**
- `match`: Tonight's matches, availability updates
- `captain`: New team polls, captain messages
- `result`: Recent match results
- `personal`: Win streaks, PTI changes
- `team`: Playoff position, team success

### Database Queries

The module queries several tables:
- `match_scores`: For match results and tonight's matches
- `player_availability`: For availability status
- `polls`: For captain polls
- `players`: For PTI changes
- `series_stats`: For team standings

### Frontend Components

**Location:** `templates/mobile/index.html`

**Key Elements:**
- `#homepage-notifications`: Main container
- `#notifications-container`: Dynamic notifications
- `#notifications-loading`: Loading state
- `#notifications-empty`: Empty state

**JavaScript Functions:**
- `initializeHomePageNotifications()`: Main initialization
- `renderNotifications()`: Renders notification cards
- `createNotificationElement()`: Creates individual cards
- `getNotificationIcon()`: Returns appropriate SVG icons
- `getNotificationBgColor()`: Returns color-coded backgrounds

## Usage Examples

### Personal Match Result
```json
{
  "id": "personal_result_2025-07-15",
  "type": "personal",
  "title": "Your Last Match - Won",
  "message": "On Jul 15, you won playing for Tennaqua",
  "cta": {"label": "View Your Stats", "href": "/mobile/analyze-me"},
  "priority": 3
}
```

### Team Match Result
```json
{
  "id": "team_result_2025-07-15",
  "type": "team",
  "title": "Team Won",
  "message": "Tennaqua vs Glenbrook RC - Tennaqua took the win",
  "cta": {"label": "View Team Stats", "href": "/mobile/myteam"},
  "priority": 3
}
```

### PTI Rating Update
```json
{
  "id": "pti_change",
  "type": "personal",
  "title": "📈 PTI Rating Update",
  "message": "Your rating increased by 15 points since your last match",
  "cta": {"label": "View Your Progress", "href": "/mobile/analyze-me"},
  "priority": 4
}
```

### Latest Team Poll
```json
{
  "id": "poll_123",
  "type": "captain",
  "title": "Latest Team Poll",
  "message": "John Smith asked: Who's available for practice this week? (2 days ago)",
  "cta": {"label": "Respond Now", "href": "/mobile/polls/123"},
  "priority": 2
}
```

### Captain's Message
```json
{
  "id": "captain_message_sample",
  "type": "captain",
  "title": "🏆 Captain's Message",
  "message": "Great work in practice this week! Let's keep the momentum going into our next match.",
  "cta": {"label": "View Team Chat", "href": "/mobile/polls"},
  "priority": 2
}
```

## Configuration

### Auto-refresh Interval
Notifications automatically refresh every 5 minutes:
```javascript
setInterval(() => {
    initializeHomePageNotifications();
}, 5 * 60 * 1000);
```

### Maximum Notifications
The system shows a maximum of 3 notifications at a time, prioritized by importance.

### Error Handling
- Graceful fallback to empty state on API errors
- Loading states during data fetching
- Console logging for debugging

## Styling

### Color Scheme
- **Match notifications**: Blue (`bg-blue-500`)
- **Captain notifications**: Purple (`bg-purple-500`)
- **Result notifications**: Green (`bg-green-500`)
- **Personal notifications**: Orange (`bg-orange-500`)
- **Team notifications**: Indigo (`bg-indigo-500`)

### Animation
- Fade-in with staggered delays (100ms between each)
- Smooth transitions for all interactive elements
- Transform animations for hover states

## Future Enhancements

### Potential Additions
1. **Push notifications** for urgent updates
2. **Notification preferences** (user can choose what to see)
3. **Dismiss functionality** (mark as read)
4. **Rich media** (team logos, player photos)
5. **Social features** (teammate achievements)

### Performance Optimizations
1. **Caching** of notification data
2. **Lazy loading** for older notifications
3. **WebSocket updates** for real-time notifications
4. **Background sync** for offline support

## Troubleshooting

### Common Issues

**No notifications showing:**
- Check user authentication
- Verify database connectivity
- Review browser console for JavaScript errors

**Notifications not updating:**
- Check auto-refresh interval
- Verify API endpoint is accessible
- Review server logs for errors

**Styling issues:**
- Ensure Tailwind CSS is loaded
- Check for CSS conflicts
- Verify mobile viewport settings

### Debug Mode
Enable debug logging by adding to browser console:
```javascript
localStorage.setItem('debug_notifications', 'true');
```

## Dependencies

### Backend
- Flask routes (`app/routes/api_routes.py`)
- Database utilities (`database_utils.py`)
- User session management

### Frontend
- Tailwind CSS for styling
- Vanilla JavaScript for functionality
- SVG icons for visual elements

### Database
- `match_scores` table
- `player_availability` table
- `polls` table
- `players` table
- `series_stats` table

## Security Considerations

- All endpoints require authentication (`@login_required`)
- User data is filtered by current team/league context
- No sensitive information is exposed in notifications
- API responses are properly sanitized

## Testing

### Manual Testing
1. Log in as a user with match history
2. Navigate to mobile home page
3. Verify notifications appear
4. Test CTA buttons work correctly
5. Check auto-refresh functionality

### Automated Testing
- API endpoint returns 401 for unauthenticated requests
- Notifications are properly prioritized
- Error states are handled gracefully
- UI animations work as expected 