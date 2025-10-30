# Schedule Screen - Pixel Perfect Design Specification

## Target Device
- **iPhone 15 Pro**: 393 × 852 points @ 3x resolution
- Safe area insets: Top ~59pt, Bottom ~34pt (home indicator)

## Typography Scale (SF Pro)

| Element | Size | Weight | Line Height | Letter Spacing | Usage |
|---------|------|--------|-------------|----------------|-------|
| Page Title | 28pt | Bold (700) | 34pt | 0 | "View Schedule" |
| Subtitle | 14pt | Regular (400) | 20pt | 0.15 | "Manage your availability..." |
| Filter Title | 16pt | Semibold (600) | 22pt | 0 | "Filter Events" |
| Chip Label | 15pt | Medium (500) | 20pt | 0 | Filter chips, buttons |
| Section Header | 18pt | Semibold (600) | 24pt | 0 | "Practice", "Match" |
| Event Date | 18pt | Bold (700) | 24pt | 0 | "Friday 10/31/25" |
| Event Time | 16pt | Regular (400) | 22pt | 0 | "4:30 PM" |
| Button Text | 15pt | Medium (500) | 20pt | 0 | All buttons |
| Note Label | 12pt | Regular (400) | 16pt | 0 | "Note" label |
| Tab Label | 11pt | Medium (500) | 13pt | 0 | Bottom tab labels |

## Spacing Scale

| Value | Usage |
|-------|-------|
| 4pt | Micro spacing (icon padding, tight gaps) |
| 8pt | Small spacing (icon to text, button internal padding) |
| 12pt | Base unit spacing (between related elements) |
| 16pt | Standard spacing (card padding, section gaps) |
| 20pt | Medium spacing (between cards, filter to content) |
| 24pt | Large spacing (section headers, major divisions) |
| 32pt | Extra large (top app bar margin, major sections) |

## Color Palette (Extracted from Screenshot)

### Primary Colors
- **Rally Dark Green**: `#045454` (top bar elements, selected states)
- **Rally Light Green**: `#bff863` (selected chip, selected availability button)
- **Lime Green**: `#32CD32` (section headers)

### Grayscale
- **Text Primary**: `#1F1F1F` (dark gray, event dates, titles)
- **Text Secondary**: `#6B7280` (time, subtitle, secondary text)
- **Text Tertiary**: `#9CA3AF` (disabled states)
- **Background Primary**: `#FFFFFF` (card backgrounds)
- **Background Secondary**: `#F9FAFB` (screen background)
- **Border Light**: `#E5E7EB` (card borders, dividers)
- **Gray Button BG**: `#F3F4F6` (default button background)
- **Gray Button BG Dark**: `#D1D5DB` (pressed/unavailable button)

### Accent Colors
- **Blue Medium**: `#3B82F6` (team availability button)
- **Blue Light**: `#EFF6FF` (info boxes)
- **Red Marker**: `#EF4444` (location pin icon)
- **Green Button**: `#10B981` (Count Me In selected)

## Component Specifications

### Top App Bar
- **Height**: 104pt (includes safe area + content)
- **Padding**: 16pt horizontal, 12pt vertical (content area)
- **Logo**: 40pt × 40pt, rounded 8pt, dark green background `#045454`
- **Title Stack**: 12pt gap between title and subtitle
- **Download Button**: 
  - Height: 36pt
  - Padding: 12pt horizontal, 8pt vertical
  - Border radius: 18pt (pill)
  - Background: `#045454`
  - Text: 15pt Medium, white

### Filter Card
- **Container**: White background, rounded 12pt, shadow (0, 2, 8, rgba(0,0,0,0.08))
- **Padding**: 16pt all sides
- **Title**: 16pt Semibold, 12pt margin bottom
- **Chip Container**: Flex row, 8pt gap between chips
- **Chip**:
  - Height: 36pt
  - Padding: 12pt horizontal, 8pt vertical
  - Border radius: 18pt (pill)
  - **Selected**: Background `#bff863`, text `#1F1F1F`
  - **Default**: Background `#045454`, text white

### Past Events Toggle
- **Height**: 48pt
- **Padding**: 16pt horizontal
- **Background**: `#F9FAFB`
- **Border**: Bottom 1pt solid `#E5E7EB`
- **Gap**: 12pt between icon and text, 12pt from text to chevron
- **Chevron**: 16pt × 16pt, rotates 180deg when expanded

### Section Header (Practice/Match)
- **Height**: 44pt
- **Padding**: 16pt horizontal, 12pt vertical
- **Background**: `#32CD32` (lime green)
- **Border Radius**: 12pt top corners only
- **Icon**: 20pt × 20pt, white
- **Text**: 18pt Semibold, white
- **Gap**: 12pt between icon and text

### Event Card
- **Container**: White background, rounded 12pt, shadow (0, 1, 3, rgba(0,0,0,0.1))
- **Padding**: 24pt all sides
- **Margin Bottom**: 16pt
- **Layout**: Two-column flex row
  - **Left Column**: Flex: 1, gap 12pt vertical
  - **Right Column**: Fixed width 187pt
- **Date**: 18pt Bold, `#1F1F1F`
- **Time**: 16pt Regular, `#6B7280`, 8pt margin top
- **Location**: 14pt Regular, `#6B7280`, icon 16pt, gap 8pt

### Availability Buttons (Right Column Stack)
- **Container Width**: 187pt (fixed)
- **Button Height**: 40pt
- **Button Padding**: 12pt horizontal
- **Gap Between Buttons**: 12pt vertical
- **Border Radius**: 8pt
- **Font**: 15pt Medium
- **Icon Size**: 16pt × 16pt, 8pt gap to text

#### Button States:
- **Count Me In (Selected)**: `#10B981` background, white text, white checkmark
- **Count Me In (Default)**: `#F3F4F6` background, `#6B7280` text, gray checkmark
- **Sorry Can't (Default)**: `#F3F4F6` background, `#6B7280` text, gray X
- **Sorry Can't (Selected)**: `#EF4444` background, white text
- **Not Sure (Default)**: `#F9FAFB` background, `#9CA3AF` text, light gray question mark
- **Not Sure (Selected)**: `#FCD34D` background, `#1F1F1F` text

### Note Button
- **Height**: 40pt
- **Background**: `#F9FAFB`
- **Text**: 15pt Medium, `#6B7280`
- **Icon**: 16pt, `#9CA3AF`
- **Border Radius**: 8pt

### Team Availability Button
- **Height**: 40pt
- **Background**: `#3B82F6` (medium blue)
- **Text**: 15pt Medium, white
- **Border Radius**: 8pt

### Bottom Tab Bar
- **Height**: 83pt (includes safe area, 49pt content + 34pt safe area)
- **Background**: White
- **Border**: Top 1pt solid `#E5E7EB`
- **Icon Size**: 24pt × 24pt
- **Tab Spacing**: Equal distribution
- **Selected Tab**: 
  - Icon: Dark green `#045454`
  - Label: 11pt Medium, `#045454`
- **Default Tab**:
  - Icon: `#9CA3AF`
  - Label: 11pt Medium, `#9CA3AF`
- **Active Indicator**: Optional green dot above icon (4pt × 4pt)

## Shadows & Elevation

| Element | Shadow |
|---------|--------|
| Top App Bar | None (flat) |
| Filter Card | `0, 2, 8, rgba(0,0,0,0.08)` |
| Event Card | `0, 1, 3, rgba(0,0,0,0.1)` |
| Buttons | None (flat) |
| Tab Bar | `0, -2, 8, rgba(0,0,0,0.08)` |

## Border Radius

| Element | Radius |
|---------|--------|
| Logo Container | 8pt |
| Download Button (Pill) | 18pt |
| Filter Chips | 18pt |
| Event Card | 12pt |
| Section Header (top) | 12pt |
| Buttons | 8pt |

## Accessibility
- Minimum tap target: 44pt × 44pt
- All interactive elements have `accessibilityLabel`
- Dynamic Type: Locked to base sizes for pixel-perfect match (TODO: support scaling later)


