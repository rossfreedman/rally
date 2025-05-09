// Rally Mobile JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile features
    initMobileApp();
    
    // Track page visit on initial load
    trackPageVisit();
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
    const isLandscape = window.innerWidth > window.innerHeight;
    
    // Add orientation-specific classes
    document.body.classList.toggle('landscape', isLandscape);
    document.body.classList.toggle('portrait', !isLandscape);
    
    // You can add specific layout adjustments for landscape/portrait here
}

/**
 * Track page visit analytics
 */
function trackPageVisit() {
    // Get current page
    const path = window.location.pathname;
    const page = path.split('/').pop() || 'home';
    
    // Only track if authenticated
    if (window.sessionData && window.sessionData.authenticated) {
        // Log page visit
        fetch('/api/log-click', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: 'page_visit',
                page: page,
                details: `Visited mobile ${page} page`
            })
        })
        .catch(error => {
            console.error('Error logging page visit:', error);
        });
    }
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
    trackPageVisit
};

// Mobile app JavaScript

// DOM-ready function
document.addEventListener('DOMContentLoaded', function() {
    console.log('Rally Mobile App Initialized');
    
    // Initialize Socket.IO if available
    initializeSocketIO();
    
    // Set up navigation drawer
    setupNavDrawer();
    
    // Load any dynamic content
    loadDynamicContent();
    
    // Setup event listeners
    setupEventListeners();
});

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
        console.error('Socket.IO initialization error:', error);
    }
}

// Navigation drawer setup
function setupNavDrawer() {
    const drawer = document.getElementById('navDrawer');
    const toggleButton = document.querySelector('[onclick="toggleDrawer()"]');
    
    if (drawer && toggleButton) {
        // Add click outside to close
        document.addEventListener('click', function(event) {
            if (drawer.classList.contains('open') && 
                !drawer.contains(event.target) && 
                !toggleButton.contains(event.target)) {
                drawer.classList.remove('open');
            }
        });
    }
}

// Load dynamic content based on the current page
function loadDynamicContent() {
    // Check if we have session data
    if (window.sessionData && window.sessionData.user) {
        console.log('User authenticated:', window.sessionData.user.email);
        
        // Load upcoming matches if we're on the home page
        if (document.querySelector('.upcoming-matches')) {
            fetchUpcomingMatches();
        }
    }
}

// Fetch upcoming matches data
function fetchUpcomingMatches() {
    const matchesContainer = document.querySelector('.upcoming-matches');
    if (!matchesContainer) return;
    
    fetch('/api/schedule')
        .then(response => response.json())
        .then(data => {
            // Clear loading skeletons
            matchesContainer.innerHTML = '';
            
            if (data && data.length > 0) {
                // Display up to 3 upcoming matches
                const upcomingMatches = data.slice(0, 3);
                
                upcomingMatches.forEach(match => {
                    const matchElement = document.createElement('div');
                    matchElement.className = 'p-3 mb-2 bg-base-200 rounded-lg';
                    
                    const date = new Date(match.date);
                    const formattedDate = date.toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric'
                    });
                    
                    matchElement.innerHTML = `
                        <div class="flex justify-between items-center">
                            <div>
                                <span class="font-bold">${formattedDate}</span>
                                <p class="text-sm">${match.opponent || 'TBD'}</p>
                            </div>
                            <a href="/mobile/matches" class="btn btn-sm btn-outline">Details</a>
                        </div>
                    `;
                    
                    matchesContainer.appendChild(matchElement);
                });
            } else {
                matchesContainer.innerHTML = '<p class="text-center p-4">No upcoming matches found</p>';
            }
        })
        .catch(error => {
            console.error('Error fetching matches:', error);
            matchesContainer.innerHTML = '<p class="text-center text-error p-4">Failed to load matches</p>';
        });
}

// Set up global event listeners
function setupEventListeners() {
    // Log activity on important clicks
    document.addEventListener('click', function(e) {
        const target = e.target.closest('a, button');
        if (target && !target.getAttribute('data-no-log')) {
            logUserActivity(target);
        }
    });
}

// Log user activity to the server
function logUserActivity(element) {
    try {
        const actionType = element.tagName.toLowerCase();
        const actionText = element.innerText.trim();
        const actionHref = element.href || '';
        
        fetch('/api/log-click', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action_type: actionType,
                action_text: actionText,
                action_href: actionHref,
                page: window.location.pathname
            }),
            credentials: 'include'
        }).catch(err => console.error('Error logging activity:', err));
    } catch (error) {
        console.error('Error in logUserActivity:', error);
    }
} 