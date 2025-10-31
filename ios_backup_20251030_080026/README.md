# Rally iOS Mobile App

A React Native (Expo) iOS application for the Rally platform tennis league management system.

## 🏗️ Architecture

### Tech Stack
- **Framework**: React Native with Expo
- **Language**: TypeScript (strict mode)
- **Navigation**: React Navigation (Native Stack + Bottom Tabs)
- **State Management**: 
  - React Query for server state
  - Zustand for client state (auth, settings)
- **Styling**: NativeWind (Tailwind CSS for React Native)
- **API Client**: Axios with cookie-based authentication
- **Validation**: Zod schemas for runtime type safety
- **Testing**: Jest + React Native Testing Library

### Project Structure
```
ios/
├── src/
│   ├── api/              # API client, endpoints, hooks
│   ├── components/       # UI components (primitives + domain)
│   ├── navigation/       # Navigation configuration
│   ├── screens/          # Screen components
│   ├── state/            # Zustand stores
│   ├── theme/            # Tailwind config, Rally brand colors
│   └── utils/            # Utility functions
├── __tests__/            # Jest tests
└── App.tsx               # Root component
```

## 🚀 Getting Started

### Prerequisites
- Node.js 18.20.4 (see `.nvmrc` in root)
- iOS Simulator (Xcode) or physical iPhone
- Expo CLI

### Installation
```bash
cd ios
npm install
```

### Environment Setup
Copy `.env.example` to `.env.development`:
```bash
cp .env.example .env.development
```

Edit `.env.development` with your configuration:
```bash
APP_API_BASE_URL=https://rally-staging.up.railway.app  # or http://localhost:8080
APP_ENV=development
APP_COOKIE_DOMAIN=.lovetorally.com
```

### Running the App
```bash
# Start Metro bundler
npm start

# Run on iOS Simulator
npm run ios

# Run on Android (not yet configured)
npm run android
```

## 🔐 Authentication

The app uses **cookie-based authentication** matching the Flask backend session system:

1. User logs in with email/password
2. Backend sets session cookie with domain `.lovetorally.com`
3. Axios client automatically attaches cookies to all requests
4. On 401 response, cookies are cleared and user is logged out

### Cookie Handling
- Uses `@react-native-cookies/cookies` for native cookie management
- Session cookies persist across app restarts
- Logout clears all cookies

## 📡 API Integration

### Existing Endpoints Used
All endpoints map to existing Rally backend (no new endpoints created):

- `POST /api/login` - Authenticate user
- `POST /api/logout` - End session
- `GET /api/check-auth` - Verify session
- `GET /api/team-stats` - Team statistics
- `GET /api/last-3-matches` - Recent matches
- `GET /api/current-season-matches` - Season schedule
- `GET /api/user-win-streak` - Win streak data
- `GET /api/get-user-settings` - User settings
- `POST /api/availability` - Set match availability

### API Client Configuration
- **Base URL**: From `APP_API_BASE_URL` environment variable
- **Timeout**: 30 seconds
- **Retries**: 2 attempts for queries, 1 for mutations
- **Cache**: 5 min stale time, 30 min cache time
- **Error Handling**: Automatic 401 logout, retry with exponential backoff

## 🎨 Styling & Theming

### Rally Brand Colors
- **Dark Green**: `#045454` (primary buttons, headers)
- **Bright Green**: `#bff863` (accents, highlights)

### NativeWind Usage
```tsx
// Use Tailwind className prop on React Native components
<View className="bg-rally-dark-green p-4 rounded-lg">
  <Text className="text-white font-bold">Rally</Text>
</View>
```

## 🧪 Testing

### Run Tests
```bash
npm test                  # Run all tests
npm run test:watch        # Watch mode
npm run test:coverage     # With coverage report
```

### Test Structure
- **Smoke Tests**: App renders without crashing
- **API Contract Tests**: Zod schemas validate responses
- **Component Tests**: UI components render correctly

## 🚢 Building & Deployment

### EAS Build Profiles

#### Development (Internal Testing)
```bash
eas build --platform ios --profile development
```
- Creates development client
- For internal testing only
- Can run on simulator

#### Preview (TestFlight)
```bash
eas build --platform ios --profile preview
```
- Distribution: Internal (TestFlight)
- Bundle ID: `com.lovetorally.rally`
- For beta testing with external users

#### Production (App Store)
```bash
eas build --platform ios --profile production
```
- Production-ready build
- Bundle ID: `com.lovetorally.rally`
- Submit to App Store

### Submit to App Store
```bash
eas submit --platform ios
```

### Environment Switching
Edit `.env.production` to point to production API:
```bash
APP_API_BASE_URL=https://www.lovetorally.com
APP_ENV=production
```

## 📝 Development Workflow

### Adding a New Screen
1. Create screen component in `src/screens/`
2. Add route to navigation types in `src/navigation/types.ts`
3. Register in `RootNavigator.tsx`
4. Create necessary API hooks if needed

### Adding a New API Endpoint
1. Add endpoint path to `src/api/endpoints.ts`
2. Create/update zod schema in `src/api/types.ts`
3. Create React Query hook in `src/api/hooks/`
4. Use hook in screen component

### Coding Standards
- Use TypeScript strict mode
- Follow ESLint rules (`npm run lint`)
- Format with Prettier
- Write tests for critical flows
- Use proper error handling and loading states

## 🐛 Debugging

### Enable Debug Mode
In development, the app logs API requests/responses to console:
```typescript
// Automatically enabled when __DEV__ is true
console.log('🌐 API Request:', {...});
console.log('✅ API Response:', {...});
```

### Common Issues

**Issue**: Cookies not persisting
- **Solution**: Check `APP_COOKIE_DOMAIN` matches backend domain
- Verify iOS Simulator allows cookies
- Test on physical device

**Issue**: 401 errors immediately after login
- **Solution**: Backend session cookie not being set
- Check CORS configuration allows credentials
- Verify `withCredentials: true` in Axios config

**Issue**: Build fails
- **Solution**: Clear cache and reinstall
```bash
rm -rf node_modules ios/.expo
npm install
```

## 📚 Additional Resources

- [Expo Documentation](https://docs.expo.dev/)
- [React Navigation](https://reactnavigation.org/)
- [React Query](https://tanstack.com/query/latest)
- [NativeWind](https://www.nativewind.dev/)
- [Rally Web App](../mobile/) - Existing Flask web app

## 🔒 Security Notes

- Never store passwords in AsyncStorage
- Session data stored in AsyncStorage (non-sensitive)
- Consider using `expo-secure-store` for sensitive data
- Use HTTPS only (enforced in production)
- Implement biometric auth for sensitive actions (future)

## 🎯 Next Steps

1. ✅ Test login against staging backend
2. ✅ Verify cookie persistence
3. ⏳ Add more API endpoints (availability, settings)
4. ⏳ Implement write operations with optimistic updates
5. ⏳ Add push notifications
6. ⏳ Implement deep linking
7. ⏳ TestFlight beta testing
8. ⏳ App Store submission

## 📞 Support

For issues or questions:
- Check existing Flask backend API documentation
- Review error logs in Expo console
- Test API endpoints with Postman/curl first
- Verify backend is running and accessible

