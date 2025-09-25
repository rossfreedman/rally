# Rally Platform Tennis Management

Platform tennis league management application built with Flask and PostgreSQL.

## Recent Updates

### ✅ Simple League Switching System (December 2024)

Replaced complex multi-context system with a simple, unified approach:

**Key Changes:**
- **Single Source of Truth**: `users.league_context` field controls which league data is shown
- **Unified Session Management**: `app/services/session_service.py` handles all session building
- **Consistent Switching**: Registration, settings, and toggles all use the same mechanism

**How It Works:**
1. **Registration**: Finds player → creates association → sets `league_context` → builds session
2. **Settings Update**: Changes league → updates `league_context` → rebuilds session  
3. **League Toggle**: API call → updates `league_context` → rebuilds session → page reload

**API Endpoints:**
- `POST /api/switch-league` - Simple league switching
- `POST /api/update-settings` - Handles league changes in settings
- `GET /api/get-user-settings` - Returns current league context

**Benefits:**
- ✅ No more complex ContextService or UserContext table
- ✅ League switching works consistently everywhere
- ✅ Session data always matches database state
- ✅ Simple to debug and maintain

**Migration Notes:**
- Old `ContextService` is deprecated but functional
- Session structure remains backward compatible
- URL parameters like `?league_id=APTA_CHICAGO` still work

## Architecture
# Force deployment Sat Sep 13 17:25:58 EDT 2025
# Trigger production deployment for Lake Forest Series 20 players
# Force deployment Wed Sep 24 20:44:21 CDT 2025
