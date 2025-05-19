// Rally Mobile JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('Rally Mobile App Initialized');
    
    // Initialize mobile app
    initMobileApp();
    
    // Set up navigation drawer
    setupNavDrawer();
    
    // Load any dynamic content
    loadDynamicContent();
    
    // Setup event listeners
    setupEventListeners();
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
    
    // You can add specific layout adjustments for landscape/portrait here
}

/**
 * Track page visit analytics
 */
function trackPageVisit() {
    if (window.sessionData && window.sessionData.user) {
        const data = {
            action_type: 'page_visit',
            action_text: document.title || 'Page Visit',
            action_href: window.location.pathname,
            page: window.location.pathname
        };
        
        // Use fetch with proper headers
        fetch('/api/log-click', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data),
            credentials: 'same-origin'
        }).catch(error => {
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
    trackPageVisit,
    checkAuthentication,
    loadDynamicContent
};

// Mobile app JavaScript

// DOM-ready function
document.addEventListener('DOMContentLoaded', function() {
    console.log('Rally Mobile App Initialized');
    
    // Initialize mobile app
    initMobileApp();
    
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
            if (drawer.classList.contains('translate-x-0') && 
                !drawer.contains(event.target) && 
                !toggleButton.contains(event.target)) {
                toggleDrawer();
            }
        });

        // Handle navigation links
        const navLinks = drawer.querySelectorAll('a.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                // Close the drawer
                toggleDrawer();
                
                // Let the navigation happen
                return true;
            });
        });
    }
}

// Load dynamic content based on the current page
function loadDynamicContent() {
    if (window.sessionData && window.sessionData.user) {
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
    // Log activity on important clicks without preventing navigation
    document.addEventListener('click', function(e) {
        const target = e.target.closest('a, button');
        if (!target) return;
        
        // Skip tracking for elements with data-no-log attribute
        if (target.getAttribute('data-no-log')) {
            return;
        }
        
        // Regular click logging for non-logout elements
        const data = {
            action_type: target.tagName.toLowerCase(),
            action_text: target.innerText.trim(),
            action_href: target.href || '',
            page: window.location.pathname
        };
        
        // Use fetch with proper headers
        fetch('/api/log-click', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data),
            credentials: 'same-origin'
        }).catch(error => {
            console.error('Error logging click:', error);
        });
    });
}

function toggleDrawer() {
    const drawer = document.getElementById('navDrawer');
    const overlay = document.getElementById('drawerOverlay');
    const hamburger = document.getElementById('hamburgerToggle');
    const isOpen = drawer.classList.contains('translate-x-0');
    if (isOpen) {
        drawer.classList.remove('translate-x-0');
        drawer.classList.add('translate-x-full');
        overlay.classList.add('hidden');
        if (hamburger) hamburger.classList.remove('open');
    } else {
        drawer.classList.remove('translate-x-full');
        drawer.classList.add('translate-x-0');
        overlay.classList.remove('hidden');
        if (hamburger) hamburger.classList.add('open');
    }
} 