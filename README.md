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

## 📱 iOS Mobile App

Rally now includes a native iOS mobile application built with React Native (Expo)!

### Quick Start
```bash
cd ios
npm install
npx expo start
# Press 'i' to open iOS Simulator
```

### Key Features
- **Native iOS Experience**: Built with React Native + Expo for optimal performance
- **Same Backend**: Uses existing Rally API endpoints - no backend changes required
- **Cookie Authentication**: Seamless session management matching web app
- **Rally Branding**: Dark green (#045454) and bright green (#bff863) theme
- **Core Features**: Login, Dashboard, Schedule, Team Stats

### Tech Stack
- **Framework**: React Native with Expo SDK
- **Navigation**: React Navigation (tabs + stack)
- **State**: React Query (server) + Zustand (client)
- **Styling**: NativeWind (Tailwind for RN)
- **API**: Axios with cookie-based auth
- **Testing**: Jest + React Native Testing Library

### Environment Configuration
The mobile app uses `.env` files for configuration:
- `.env.development` - Points to staging (rally-staging.up.railway.app)
- `.env.production` - Points to production (www.lovetorally.com)

### Deployment
The iOS app deploys separately via EAS (Expo Application Services):
```bash
# TestFlight (beta testing)
eas build --platform ios --profile preview

# App Store (production)
eas build --platform ios --profile production
eas submit --platform ios
```

### Railway Exclusion
The `ios/` directory is excluded from Railway deployments via `.dockerignore` to prevent unnecessary uploads of ~500MB+ node_modules. The mobile app deploys independently to the App Store.

### Documentation
See [ios/README.md](ios/README.md) for detailed documentation including:
- Architecture overview
- API endpoint mapping
- Cookie authentication details
- Development workflow
- TestFlight & App Store deployment

### CI/CD
Mobile CI runs automatically on PRs touching `ios/**`:
- ESLint code quality checks
- TypeScript type checking
- Jest unit & integration tests
- Runs only when mobile code changes

---

## Architecture
# Force deployment Sat Sep 13 17:25:58 EDT 2025
# Trigger production deployment for Lake Forest Series 20 players
# Force deployment Wed Sep 24 20:44:21 CDT 2025
