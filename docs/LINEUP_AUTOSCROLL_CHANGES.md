# Lineup Page Autoscroll Enhancement

## Overview
Added autoscroll functionality to the mobile lineup page (`/mobile/lineup`) to improve user experience when building lineups.

## Changes Made

### 1. Updated Instruction Text
**Location**: Under "Lineup Builder" heading in `templates/mobile/lineup.html`
**Change**: Replaced old instruction text with clearer, more focused instructions
- **Removed**: "Drag players to courts OR tap a player, then tap a court position:"
- **Added**: "Tap a player name to choose a player. Then, tap a court to choose a court for that player."

### 2. Player Selection Autoscroll (Down 400px)
**Location**: `handlePlayerTap()` function in `templates/mobile/lineup.html`
**Trigger**: When user clicks/taps an available player
**Action**: Smooth scroll down 400px to bring court positions into view

```javascript
// Auto scroll down 400px when player is selected
window.scrollBy({
  top: 400,
  behavior: 'smooth'
});
```

### 3. Court Assignment Autoscroll (Up 400px)
**Location**: Multiple functions in `templates/mobile/lineup.html`
**Trigger**: When user adds a player to a court position
**Action**: Smooth scroll up 400px to return focus to available players

#### Functions Updated:
- `handleCourtPositionTap()` - For tap-to-assign functionality
- `handleDrop()` - For drag and drop functionality  
- `handleTouchEnd()` - For touch-based drag and drop

```javascript
// Auto scroll up 400px when player is added to court
window.scrollBy({
  top: -400,
  behavior: 'smooth'
});
```

## User Experience Flow

1. **User clicks available player** → Page scrolls down 400px to show court positions
2. **User assigns player to court** → Page scrolls up 400px to return to available players
3. **Smooth animations** → All scrolling uses `behavior: 'smooth'` for polished UX

## Technical Details

- **Scroll Method**: `window.scrollBy()` with smooth behavior
- **Scroll Distance**: 400px (configurable)
- **Browser Support**: Modern browsers with smooth scrolling support
- **Fallback**: Graceful degradation on older browsers (scrolls without animation)

## Testing

The autoscroll functionality has been implemented and tested on:
- ✅ Desktop drag and drop
- ✅ Mobile tap-to-assign
- ✅ Touch-based drag and drop
- ✅ All court positions (Court 1-4)

## Files Modified

- `templates/mobile/lineup.html` - Added autoscroll functionality to player interaction functions

## Deployment

These changes are ready for deployment and will enhance the user experience on the mobile lineup builder page.
