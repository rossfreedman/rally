// Rally Mobile JavaScript

// Single DOMContentLoaded handler
document.addEventListener('DOMContentLoaded', function() {
    console.log('Rally Mobile App Initialized');
    
    // Initialize mobile app
    initMobileApp();
    
    // Load any dynamic content
    loadDynamicContent();
    
    // Initialize loading indicator for all navigation
    initLoadingIndicator();
    
    // Add page visibility handling for loading indicator
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            // Page became visible again - hide loading indicator
            hideLoadingIndicator();
        }
    });
    
    // Handle page show event (back/forward navigation)
    window.addEventListener('pageshow', function() {
        hideLoadingIndicator();
    });
});

/**
 * Initialize mobile app features
 */
function initMobileApp() {
    // Check authentication
    checkAuthentication();
    
    // Add touch event listeners for better mobile experience
    addTouchListeners();
    
    // Handle device orientation changes
    handleOrientationChanges();
    
    // Initialize auto-scroll functionality for mobile home page
    initAutoScroll();
}

/**
 * Initialize loading indicator for all navigation elements
 */
function initLoadingIndicator() {
    console.log('Initializing loading indicator for all navigation');
    
    // Create loading overlay
    createLoadingOverlay();
    
    // Initialize home page buttons (on all pages that have them)
    // This ensures loading indicators work on both home_submenu and index templates
    initHomePageButtons();
    
    // Initialize navigation drawer links (on all pages)
    initNavDrawerLinks();
    
    // Initialize bottom dock navigation (on all pages)
    initDockNavigation();
}

/**
 * Initialize loading indicator for home page buttons
 */
function initHomePageButtons() {
    console.log('Initializing home page buttons');
    
    // Target all possible button types and also generic links with navigation
    const homePageButtons = document.querySelectorAll('a[href*="/mobile/"], .ios-card, .icon-btn, .logout-btn, .act-button, .analyze-button, .prepare-button, .play-button, .improve-button, .captain-button, .admin-button, .submenu-item');
    
    console.log(`Found ${homePageButtons.length} buttons to initialize`);
    
    homePageButtons.forEach((button, index) => {
        console.log(`Button ${index}: ${button.className} - href: ${button.href}`);
        
        // Skip if this button is inside the nav drawer
        if (button.closest('#navDrawer')) {
            console.log(`Skipping button ${index} - inside nav drawer`);
            return;
        }
        
        // Skip buttons that should not be treated as navigation buttons
        if (button.id === 'submit-lineup-btn' || button.classList.contains('non-navigation-btn')) {
            console.log(`Skipping button ${index} - non-navigation button (${button.id})`);
            return;
        }
        
        button.addEventListener('click', function(e) {
            console.log(`Home button clicked: ${this.href}`);
            handleNavigationClick(e, this, 'home-btn-loading');
        });
    });
}

/**
 * Initialize loading indicator for navigation drawer links
 */
function initNavDrawerLinks() {
    console.log('Initializing nav drawer links');
    
    // Wait for nav drawer to be rendered
    setTimeout(() => {
        const navDrawer = document.getElementById('navDrawer');
        if (navDrawer) {
            const navLinks = navDrawer.querySelectorAll('a[href]');
            
            navLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    handleNavigationClick(e, this, 'nav-link-loading');
                });
            });
        }
    }, 100);
}

/**
 * Initialize loading indicator for bottom dock navigation
 */
function initDockNavigation() {
    console.log('Initializing dock navigation');
    
    const dockItems = document.querySelectorAll('.dock-item');
    
    dockItems.forEach(item => {
        item.addEventListener('click', function(e) {
            handleNavigationClick(e, this, 'nav-link-loading');
        });
    });
}

/**
 * Handle navigation click with loading indicator
 */
function handleNavigationClick(event, element, loadingClass) {
    const href = element.getAttribute('href');
    
    // Skip if it's a logout link (handle immediately)
    if (href && href.includes('/logout')) {
        return; // Let logout happen normally
    }
    
    // Skip if it's a javascript: link or hash link
    if (!href || href.startsWith('javascript:') || href.startsWith('#')) {
        return;
    }
    
    // Prevent immediate navigation
    event.preventDefault();
    
    // Add visual feedback to the clicked element
    element.classList.add(loadingClass);
    
    // Show loading indicator
    showLoadingIndicator(getLoadingTextForUrl(href));
    
    // Navigate after a longer delay (allows loading indicator to show)
    setTimeout(() => {
        window.location.href = href;
    }, 800);
    
    // Safety timeout - hide loading indicator after 10 seconds if still showing
    setTimeout(() => {
        hideLoadingIndicator();
    }, 10000);
}

/**
 * Create the loading overlay HTML structure
 */
function createLoadingOverlay() {
    // Check if overlay already exists
    if (document.getElementById('home-loading-overlay')) {
        return;
    }
    
    const overlay = document.createElement('div');
    overlay.id = 'home-loading-overlay';
    overlay.className = 'loading-overlay';
    
    overlay.innerHTML = `
        <div class="loading-spinner"></div>
        <div class="loading-text" id="loading-text">Loading...</div>
        <div class="loading-subtext">Hang tight...</div>
        <div class="loading-dots">
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
        </div>
    `;
    
    document.body.appendChild(overlay);
}

/**
 * Show loading indicator with custom text
 */
function showLoadingIndicator(text = 'Loading...') {
    const overlay = document.getElementById('home-loading-overlay');
    const loadingText = document.getElementById('loading-text');
    
    if (overlay && loadingText) {
        loadingText.textContent = text;
        overlay.classList.add('show');
    }
}

/**
 * Hide loading indicator
 */
function hideLoadingIndicator() {
    const overlay = document.getElementById('home-loading-overlay');
    if (overlay) {
        overlay.classList.remove('show');
        
        // Remove loading state from all navigation elements
        document.querySelectorAll('.home-btn-loading, .nav-link-loading').forEach(btn => {
            btn.classList.remove('home-btn-loading', 'nav-link-loading');
        });
    }
}

/**
 * Get appropriate loading text based on the destination URL
 */
function getLoadingTextForUrl(url) {
    const loadingMessages = {
        // Home navigation
        '/mobile': 'Loading Home...',
        '/mobile/': 'Loading Home...',
        '/mobile/home_submenu': 'Loading Home...',
        
        // Act section
        '/mobile/availability': 'Loading Schedule...',
        '/mobile/availability-calendar': 'Loading Calendar...',
        '/mobile/find-people-to-play': 'Search Players...',
        '/mobile/pickup-games': 'Loading Pickup Games...',
        '/mobile/schedule-lesson': 'Loading Lesson Booking...',
        '/mobile/polls': 'Loading Team Polls...',
        '/mobile/improve': 'Loading Improvement Tools...',
        '/mobile/reserve-court': 'Loading Court Reservations...',
        
        // Analyze section
        '/mobile/analyze-me': 'Loading Your Analysis...',
        '/mobile/my-team': 'Loading Team Data...',
        '/mobile/my-series': 'Loading Series Data...',
        '/mobile/my-club': 'Loading Club Information...',
        '/mobile/player-search': 'Searching Players...',
        '/mobile/teams-players': 'Loading Teams...',
        '/mobile/matchup-simulator': 'Loading Matchup Simulator...',
        
        // Captain section
        '/mobile/team-schedule': 'Loading Team Schedule...',
    '/mobile/all-teams-schedule': 'Loading All Teams Schedule...',
        '/mobile/find-subs': 'Finding Substitutes...',
        '/mobile/lineup-selection': 'Loading Lineup Options...',
        '/mobile/lineup': 'Loading Lineup Builder...',
        '/mobile/lineup-confirmation': 'Loading Lineup Confirmation...',
    '/mobile/lineup-ai': 'Loading AI Lineup Creator...',
        '/mobile/practice-times': 'Loading Practice Times...',
        
        // Additional pages
        '/mobile/create-lineup': 'Loading Create Lineup...',
        '/mobile/email-team': 'Loading Email Tool...',
        '/mobile/training-videos': 'Loading Training Videos...',
        '/mobile/settings': 'Loading Profile...',
        '/mobile/track-byes-courts': 'Loading Court Tracking...',
        
        // Admin
        '/admin': 'Loading Admin Panel...'
    };
    
    return loadingMessages[url] || 'Loading...';
}

/**
 * Check if the user is authenticated
 */
function checkAuthentication() {
    // Skip authentication check for routes that don't require login
    const currentPath = window.location.pathname;
    const publicRoutes = [
        '/login',
        '/register', 
        '/forgot-password',
        '/mobile/lineup-escrow-opposing',
        '/mobile/lineup-escrow-view'
    ];
    
    // Check if current path matches any public route
    const isPublicRoute = publicRoutes.some(route => currentPath.includes(route));
    
    if (isPublicRoute) {
        console.log('Skipping authentication check for public route:', currentPath);
        return;
    }
    
    // If we don't have session data, check authentication status
    if (!window.sessionData || !window.sessionData.authenticated) {
        fetch('/api/check-auth')
            .then(response => response.json())
            .then(data => {
                if (data.authenticated) {
                    window.sessionData = {
                        authenticated: true,
                        user: data.user
                    };
                    console.log('User authenticated:', data.user.email);
                } else {
                    // Redirect to login if not on login page
                    if (!window.location.pathname.includes('/login')) {
                        window.location.href = '/login';
                    }
                }
            })
            .catch(error => {
                console.error('Error checking authentication:', error);
            });
    } else if (window.sessionData.user) {
        console.log('User authenticated:', window.sessionData.user.email);
    }
}

/**
 * Add mobile-specific touch listeners
 */
function addTouchListeners() {
    // Add tap and swipe listeners for improved mobile UX
    const cards = document.querySelectorAll('.card');
    
    cards.forEach(card => {
        // Tap feedback effect
        card.addEventListener('touchstart', function() {
            this.classList.add('card-tapped');
        });
        
        card.addEventListener('touchend', function() {
            this.classList.remove('card-tapped');
        });
    });
}

/**
 * Handle device orientation changes
 */
function handleOrientationChanges() {
    window.addEventListener('orientationchange', function() {
        // Adjust layout based on orientation
        setTimeout(adjustLayoutForOrientation, 100);
    });
    
    // Initial adjustment
    adjustLayoutForOrientation();
}

/**
 * Adjust layout based on device orientation
 */
function adjustLayoutForOrientation() {
    const isPortrait = window.innerHeight > window.innerWidth;
    
    // Add orientation-specific classes
    document.body.classList.toggle('portrait', isPortrait);
    document.body.classList.toggle('landscape', !isPortrait);
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, error, info, warning)
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container fixed bottom-4 right-4 z-50 flex flex-col gap-2';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} shadow-lg max-w-xs`;
    
    // Set toast content
    toast.innerHTML = `
        <div>
            <span>${message}</span>
        </div>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

// Export functions for use in other scripts
window.app = {
    showToast,
    checkAuthentication,
    loadDynamicContent,
    showLoadingIndicator,
    hideLoadingIndicator
};

// Socket.IO initialization
function initializeSocketIO() {
    try {
        if (typeof io !== 'undefined') {
            const socket = io();
            
            socket.on('connect', function() {
                console.log('Socket.IO connected');
            });
            
            socket.on('disconnect', function() {
                console.log('Socket.IO disconnected');
            });
            
            // Store socket in window for global access
            window.rallySocket = socket;
        }
    } catch (error) {
        console.error('Error initializing Socket.IO:', error);
    }
}

/**
 * Load dynamic content for the current page
 */
function loadDynamicContent() {
    // Load any dynamic content needed for the current page
    // This will be called on initial load and after navigation
    
    // Hide loading indicator if it's still showing (safety net)
    setTimeout(() => {
        hideLoadingIndicator();
    }, 100);
}

// Initialize Socket.IO when the script loads
initializeSocketIO();

/**
 * Initialize auto-scroll functionality for mobile home page
 */
function initAutoScroll() {
    console.log('🔍 Setting up auto-scroll for mobile home page...');
    
    // Only run on the main mobile home page
    if (!window.location.pathname.endsWith('/mobile') && !window.location.pathname.endsWith('/mobile/')) {
        console.log('⏭️ Not on mobile home page, skipping auto-scroll setup');
        return;
    }
    
    // Simple auto-scroll function
    function autoScrollOnNavigation() {
        console.log('🔄 Auto-scroll triggered - scrolling 200px');
        window.scrollBy({
            top: 200,
            behavior: 'smooth'
        });
        console.log('✅ Auto-scroll completed');
    }
    
          // Target section headers (Act, Analyze, Prepare, etc.)
      const sectionHeaders = document.querySelectorAll('.section-header');
      console.log(`📋 Found ${sectionHeaders.length} section headers:`, sectionHeaders);
      
      // Debug: Let's also check for any elements with "Captain" in the text
      const allElements = document.querySelectorAll('*');
      const captainElements = Array.from(allElements).filter(el => 
        el.textContent && el.textContent.toLowerCase().includes('captain')
      );
      console.log(`🔍 Found ${captainElements.length} elements containing "captain":`, captainElements);
      
      // Look for Captain's Corner button by ID
      const captainSectionHeader = document.getElementById('captain-corner-button');
      
      if (captainSectionHeader) {
        console.log(`🏴‍☠️ Found Captain's Corner button by ID:`, captainSectionHeader);
        console.log(`🏴‍☠️ Captain's Corner classes:`, captainSectionHeader.className);
        
        // Add our enhanced click handler
        captainSectionHeader.addEventListener('click', function(e) {
          console.log(`🏴‍☠️ Captain's Corner button clicked - enhanced click handler`);
          
          // Get current scroll position
          const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
          const windowHeight = window.innerHeight;
          const documentHeight = document.documentElement.scrollHeight;
          const maxScrollTop = documentHeight - windowHeight;
          
          console.log(`🏴‍☠️ Current scroll: ${currentScrollTop}px`);
          console.log(`🏴‍☠️ Window height: ${windowHeight}px`);
          console.log(`🏴‍☠️ Document height: ${documentHeight}px`);
          console.log(`🏴‍☠️ Max scroll: ${maxScrollTop}px`);
          console.log(`🏴‍☠️ At bottom: ${currentScrollTop >= maxScrollTop - 10}`);
          
          // Call the original toggleSubmenu function only if not already in progress
          if (typeof toggleSubmenu === 'function' && !window.submenuToggleInProgress) {
            console.log(`🏴‍☠️ Calling toggleSubmenu('captain-submenu')`);
            toggleSubmenu('captain-submenu');
          } else if (window.submenuToggleInProgress) {
            console.log(`🏴‍☠️ Skipping toggleSubmenu call - already in progress`);
          }
          
          // If we're at the bottom, scroll up to show the captains corner section better
          if (currentScrollTop >= maxScrollTop - 10) {
            console.log(`🏴‍☠️ At bottom of page, scrolling up to show captains corner better`);
            const captainsCornerSection = captainSectionHeader.closest('.category-section');
            if (captainsCornerSection) {
              const sectionTop = captainsCornerSection.offsetTop;
              const navbarHeight = 60;
              const scrollPosition = sectionTop - navbarHeight - 100; // 100px padding from top
              
              console.log(`🏴‍☠️ Scrolling to captains corner section at position: ${scrollPosition}px`);
              window.scrollTo({
                top: Math.max(0, scrollPosition),
                behavior: 'smooth'
              });
            }
          }
        });
        
        console.log(`🏴‍☠️ Added enhanced click handler to Captain's Corner button`);
      } else {
        console.log(`🏴‍☠️ Captain's Corner button NOT found by ID`);
      }
    
    if (sectionHeaders.length === 0) {
        console.warn('⚠️ No section headers found! Checking for alternative selectors...');
        
        // Try alternative selectors
        const alternativeSelectors = [
            '.section-header',
            '[class*="section"]',
            '[class*="header"]',
            'h2',
            'h3',
            '.text-xl',
            '.font-bold'
        ];
        
        for (const selector of alternativeSelectors) {
            const elements = document.querySelectorAll(selector);
            console.log(`🔍 Selector "${selector}": found ${elements.length} elements`);
            if (elements.length > 0) {
                console.log(`📋 Elements with "${selector}":`, elements);
            }
        }
    }
    
    sectionHeaders.forEach((header, index) => {
        console.log(`🎯 Adding click listener to section header ${index + 1}:`, header.textContent?.trim() || header.className);
        
        // Debug each section header individually
        console.log(`🔍 Section header ${index + 1} details:`);
        console.log(`  - textContent: "${header.textContent}"`);
        console.log(`  - innerText: "${header.innerText}"`);
        console.log(`  - innerHTML: "${header.innerHTML}"`);
        console.log(`  - className: "${header.className}"`);
        console.log(`  - element:`, header);
        
        header.addEventListener('click', function(e) {
            console.log(`🖱️ Section header clicked:`, header.textContent?.trim() || header.className);
            
            // Get the text content more reliably
            const headerText = header.textContent || header.innerText || '';
            const trimmedText = headerText.trim();
            
            console.log(`🔍 Section header clicked - text: "${trimmedText}"`);
            
            // Special handling for Captain's Corner section
            if (trimmedText === "Captain's Corner") {
                console.log(`🏴‍☠️ Captain's Corner section header clicked - triggering submenu toggle`);
                
                // Trigger the same submenu functionality that works in the navigation drawer
                if (typeof toggleSubmenu === 'function' && !window.submenuToggleInProgress) {
                    console.log(`🏴‍☠️ Calling toggleSubmenu('captain-submenu')`);
                    toggleSubmenu('captain-submenu');
                } else if (window.submenuToggleInProgress) {
                    console.log(`🏴‍☠️ Skipping toggleSubmenu call - already in progress`);
                } else {
                    console.log(`🏴‍☠️ toggleSubmenu function not found, using fallback autoscroll`);
                    // Fallback to standard autoscroll
                    autoScrollOnNavigation();
                }
            } else {
                console.log(`📝 Other section header clicked: "${trimmedText}" - using standard autoscroll`);
                // Standard autoscroll for other sections
                autoScrollOnNavigation();
            }
        });
    });
    
    // Add auto-scroll to main menu buttons (Act, Analyze, Prepare, etc.)
    // Note: Excluding .captain-button since those are navigation links that should not autoscroll
    const mainMenuButtons = document.querySelectorAll('.act-button, .analyze-button, .prepare-button, .play-button, .improve-button, .admin-button');
    console.log(`📋 Found ${mainMenuButtons.length} main menu buttons:`, mainMenuButtons);
    
    mainMenuButtons.forEach((button, index) => {
        console.log(`🎯 Adding click listener to main menu button ${index + 1}:`, button.textContent?.trim() || button.className);
        button.addEventListener('click', function(e) {
            console.log(`🖱️ Main menu button clicked:`, button.textContent?.trim() || button.className);
            autoScrollOnNavigation();
        });
    });
    

} 