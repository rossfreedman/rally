// Rally Mobile JavaScript

// Single DOMContentLoaded handler
document.addEventListener('DOMContentLoaded', function() {
    console.log('Rally Mobile App Initialized');
    
    // Initialize mobile app
    initMobileApp();
    
    // Load any dynamic content
    loadDynamicContent();
    
    // Initialize loading indicator for home page
    initHomePageLoadingIndicator();
    
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
}

/**
 * Initialize loading indicator specifically for home page buttons
 */
function initHomePageLoadingIndicator() {
    // Only run on home page (index.html)
    if (!window.location.pathname.endsWith('/mobile') && !window.location.pathname.endsWith('/mobile/')) {
        return;
    }
    
    console.log('Initializing home page loading indicator');
    
    // Create loading overlay
    createLoadingOverlay();
    
    // Add event listeners to home page buttons only (not nav drawer buttons)
    const homePageButtons = document.querySelectorAll('.icon-btn, .logout-btn');
    
    homePageButtons.forEach(button => {
        // Skip if this button is inside the nav drawer
        if (button.closest('#navDrawer')) {
            return;
        }
        
        button.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            
            // Skip if it's a logout link (handle immediately)
            if (href && href.includes('/logout')) {
                return; // Let logout happen normally
            }
            
            // Skip if it's a javascript: link or hash link
            if (!href || href.startsWith('javascript:') || href.startsWith('#')) {
                return;
            }
            
            // Prevent immediate navigation
            e.preventDefault();
            
            // Add visual feedback to the clicked button
            this.classList.add('home-btn-loading');
            
            // Show loading indicator
            showLoadingIndicator(getLoadingTextForUrl(href));
            
            // Navigate after a short delay (allows loading indicator to show)
            setTimeout(() => {
                window.location.href = href;
            }, 150);
            
            // Safety timeout - hide loading indicator after 10 seconds if still showing
            setTimeout(() => {
                hideLoadingIndicator();
            }, 10000);
        });
    });
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
        <div class="loading-subtext">Please wait a moment</div>
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
        
        // Remove loading state from buttons
        document.querySelectorAll('.home-btn-loading').forEach(btn => {
            btn.classList.remove('home-btn-loading');
        });
    }
}

/**
 * Get appropriate loading text based on the destination URL
 */
function getLoadingTextForUrl(url) {
    const loadingMessages = {
        '/mobile/availability': 'Loading Schedule...',
        '/mobile/availability-calendar': 'Loading Calendar...',
        '/mobile/improve': 'Loading Improvement Tools...',
        '/mobile/find-people-to-play': 'Finding Club Members...',
        '/mobile/reserve-court': 'Loading Court Reservations...',
        '/mobile/settings': 'Loading Profile...',
        '/mobile/analyze-me': 'Loading Your Analysis...',
        '/mobile/myteam': 'Loading Team Data...',
        '/mobile/myseries': 'Loading Series Data...',
        '/mobile/my-club': 'Loading Club Information...',
        '/mobile/player-search': 'Searching Players...',
        '/mobile/teams-players': 'Loading Teams...',
        '/mobile/team-schedule': 'Loading Team Schedule...',
        '/mobile/find-subs': 'Finding Substitutes...',
        '/mobile/lineup': 'Loading Lineup Builder...',
        '/mobile/lineup-escrow': 'Loading Lineup Escrow...',
        '/mobile/practice-times': 'Loading Practice Times...',
        '/mobile/email-team': 'Loading Email Tool...',
        '/admin': 'Loading Admin Panel...'
    };
    
    return loadingMessages[url] || 'Loading...';
}

/**
 * Check if the user is authenticated
 */
function checkAuthentication() {
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