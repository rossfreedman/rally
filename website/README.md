# Rally Website Home Page

This directory contains the marketing/landing page for the Rally platform tennis management application.

## Files

- `index.html` - Main home page following the wireframe specifications with Rally branding

## Features

The home page includes all sections from the wireframe:

### 1. **Hero Section**
- Rally logo and branding
- Compelling headline: "Master Your Platform Tennis Game"
- Hero message with call-to-action button "Let's Rally!"
- Statistics showcase (1000+ Active Players, 50+ Tennis Clubs, 10K+ Matches Tracked)

### 2. **About Rally Section**
- Description of Rally as a platform tennis management app
- Key benefits and differentiators
- Platform tennis-focused messaging
- App rating and uptime statistics

### 3. **Features Section**
- Six core features with icons:
  - **Schedule** - Match scheduling and court assignments
  - **My Series** - Performance tracking and standings
  - **Match Simulator** - Analyze matchups and predictions
  - **Improve My Game** - Training tips and guides
  - **Schedule Lesson with Pro** - Connect with professionals
  - **View Pickup Games** - Find local games and players
- "View More Features" button

### 4. **Explore Leagues Section**
Three league cards showcasing:
- **APTA Chicago** - Premier Chicagoland league (40+ teams)
- **CNSWPL** - Connecticut women's league (25+ teams) 
- **NSTF** - Northern suburban leagues (30+ teams)

### 5. **Pricing Section**
Two pricing tiers:
- **Rally Free** ($0/month) - Basic features for getting started
- **Rally Pro** ($50/season) - Advanced analytics and premium features

### 6. **Love to Rally Section**
- Final call-to-action with "Register Now" button
- Secondary "Learn More" button

## Design & Technology

- **Framework**: Tailwind CSS for modern, responsive styling
- **Icons**: Font Awesome for consistent iconography
- **Colors**: Rally brand colors (rally-blue, rally-green, rally-orange)
- **Typography**: Modern, clean fonts with proper hierarchy
- **Responsiveness**: Mobile-first design with responsive breakpoints
- **Animations**: Hover effects, smooth scrolling, and subtle transitions

## Branding Elements

- **Color Scheme**: 
  - Primary Blue (#2563eb)
  - Rally Green (#10b981) 
  - Rally Orange (#f59e0b)
  - Rally Dark (#1f2937)
- **Tennis Emojis**: 🏓 for Rally branding, sport-specific emojis for leagues
- **Platform Tennis Focus**: Copy specifically mentions platform tennis vs generic tennis
- **Professional Feel**: Clean, modern design reflecting the premium nature of the app

## Navigation

- **Smooth Scrolling**: JavaScript-powered smooth scrolling between sections
- **Mobile Menu**: Responsive hamburger menu for mobile devices
- **Logo Integration**: References Rally logo from `../static/rallylogo.png` with fallback
- **Login Link**: Direct link to `/login` for existing users

## Integration with Rally App

- Logo path references the main Rally app static files
- Login button links to existing authentication system
- Terms and Privacy links point to Rally app routes
- Consistent branding and messaging with the main application

## Usage

1. Open `index.html` in a web browser to view the home page
2. All styling is inline via Tailwind CDN - no additional CSS files needed
3. Font Awesome CDN provides all icons
4. Responsive design works on all device sizes
5. Can be deployed as a static site or integrated into the main Rally Flask application

## Future Enhancements

- Add mobile hamburger menu functionality
- Integrate with Rally's authentication system for seamless login
- Add contact forms and lead capture
- Include customer testimonials and case studies
- Add platform tennis action photos/videos
- Implement analytics tracking 