# Home Page Migration Summary

## Date: October 21, 2025

## Overview
Successfully migrated the Rally home page from the classic button-menu style to the modern dashboard view (main-alt), while preserving the classic version for rollback capability.

## Changes Made

### 1. Template Files Renamed
- **Old main-alt**: `templates/mobile/main_alt.html` → `templates/mobile/home.html` (now primary)
- **Old primary home**: `templates/mobile/home_submenu.html` → `templates/mobile/home_classic.html` (for rollback)
- **Preserved**: `templates/mobile/mobile_home_alt1.html` (white button style - alternate)
- **Preserved**: `templates/mobile/index.html` (grid layout - accessible at /mobile/grid-layout)

### 2. Route Updates (`app/routes/mobile_routes.py`)
- **`/mobile/home`**: Now renders the modern dashboard (`home.html` - was main_alt.html)
- **`/mobile/classic`**: Now renders the classic button-menu page (`home_classic.html` - was home_submenu.html)
- **`/mobile/main-alt`**: Redirects to `/mobile/home` for backwards compatibility
- **`/mobile/alt1`**: Redirects to `/mobile/home` for backwards compatibility
- **`/mobile/grid-layout`**: Renders the grid layout view (`index.html`)

### 3. Navigation Links Updated
- **New home page** (`home.html`): Contains link to "Switch to classic view" → `/mobile/classic`
- **Classic home page** (`home_classic.html`): Contains link to "Switch to new button style" → `/mobile/home`
- **Grid layout page** (`index.html`): Contains link to "Go to home dashboard" → `/mobile/home`

## Current URL Structure
| URL | Template | Description |
|-----|----------|-------------|
| `/mobile/home` | `home.html` | **PRIMARY**: Modern dashboard with hero section, PTI circle, cards |
| `/mobile/classic` | `home_classic.html` | Classic button-menu style for rollback |
| `/mobile/main-alt` | Redirects to `/mobile/home` | Backwards compatibility |
| `/mobile/alt1` | Redirects to `/mobile/home` | Backwards compatibility |
| `/mobile/grid-layout` | `index.html` | Grid layout alternative (admin access) |

## What is the "Home" Page Now?
The **home** page is now the modern dashboard design previously accessible at `/mobile/main-alt`. It features:
- Hero section with Rally branding
- Large PTI (Player Tennis Index) circle display
- Sticky navigation with smooth scrolling
- Card-based layout for matches, teammates, training videos, and lessons
- Modern, clean aesthetic with #045454 (Rally teal) and #bff863 (Rally green) colors

## Rollback Instructions
If you need to rollback to the classic home page:

### Option 1 (Quick - No Code Changes):
Direct users to `/mobile/classic` temporarily

### Option 2 (Permanent):
1. In `app/routes/mobile_routes.py`, update line ~207:
   ```python
   return render_template("mobile/home_classic.html", session_data=session_data)
   ```
2. Restart the server

### Option 3 (Full Revert):
1. Rename `home.html` back to `main_alt.html`
2. Rename `home_classic.html` back to `home_submenu.html`  
3. Update routes to use original template names
4. Restart the server

## Files Modified
- `app/routes/mobile_routes.py` - Updated route handlers and redirects
- `templates/mobile/home.html` - New primary home (was main_alt.html)
- `templates/mobile/home_classic.html` - Classic home for rollback (was home_submenu.html)
- `templates/mobile/index.html` - Updated link to point to /mobile/home

## Testing Checklist
- [ ] Visit `/mobile/home` and verify modern dashboard loads
- [ ] Click "Switch to classic view" link and verify classic page loads
- [ ] From classic page, click "Switch to new button style" and verify return to modern home
- [ ] Verify `/mobile/main-alt` redirects to `/mobile/home`
- [ ] Verify `/mobile/alt1` redirects to `/mobile/home`
- [ ] Test PTI display on modern dashboard
- [ ] Test sticky navigation on modern dashboard
- [ ] Test all card sections (matches, teammates, videos, lessons)
- [ ] Test league switching on both pages
- [ ] Test team switching on both pages
- [ ] Verify mobile responsiveness on both pages

## Notes
- The old `/mobile/main-alt` URL will continue to work via redirect
- All existing bookmarks to `/mobile/main-alt` will automatically redirect to `/mobile/home`
- The modern dashboard has significantly more dynamic content and JavaScript than the classic view
- Consider monitoring page load times and user engagement after migration

