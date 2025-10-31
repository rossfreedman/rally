# Rally Schedule Screen - Pixel Perfect iOS UI

This is a pixel-perfect React Native implementation of the Schedule/Availability page UI.

## Structure

```
mobile/ios-app/
├── docs/
│   ├── reference/           # Reference screenshot (add schedule-web-reference.png)
│   └── schedule-spec.md    # Design specification and tokens
├── src/
│   ├── features/
│   │   └── schedule/
│   │       ├── components/  # Presentational components
│   │       ├── fixtures/   # Mock data
│   │       ├── tabs/       # Bottom tab bar
│   │       ├── utils/      # PixelOverlay dev utility
│   │       └── ScheduleScreen.tsx
│   └── theme/
│       └── tokens.ts       # Design tokens (colors, spacing, typography)
├── App.tsx                 # Main app with mock data
└── index.tsx              # Entry point
```

## Setup

```bash
cd mobile/ios-app
npm install
npm start
```

## Development

- All components are **pure presentational** - they accept props and render UI
- No API calls or network logic
- Mock data in `fixtures/mockData.ts`
- PixelOverlay utility for visual verification (dev mode only)

## Pixel Verification

1. Add reference screenshot to `docs/reference/schedule-web-reference.png`
2. Enable PixelOverlay in `App.tsx`: `<PixelOverlay enabled={true} />`
3. Adjust opacity with +/− buttons
4. Verify ≤1px variance on iPhone 15 Pro simulator

## Components

- **TopBar**: Logo, title, download button
- **FilterCard**: 3-chip filter (All, Matches, Practices)
- **PastEventsToggle**: Collapsible past events section
- **SectionHeader**: Practice/Match header bars
- **EventCard**: Two-column layout with availability buttons
- **AvailabilityButtons**: Count Me In / Sorry Can't / Not Sure
- **NoteButton**: Add/edit note functionality
- **TeamAvailabilityButton**: View team availability link
- **BottomTabBar**: 4-tab navigation

## Notes

- Typography locked to base sizes for pixel-perfect match
- Dynamic Type support: TODO (future enhancement)
- All spacing/colors derive from `tokens.ts`
- Minimum tap targets: 44pt × 44pt


