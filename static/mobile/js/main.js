// Rally Mobile JavaScript

// Single DOMContentLoaded handler
document.addEventListener('DOMContentLoaded', function() {
    console.log('Rally Mobile App Initialized');
    
    // Initialize mobile app
    initMobileApp();
    
    // Load any dynamic content
    loadDynamicContent();
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
    loadDynamicContent
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
}

// Initialize Socket.IO when the script loads
initializeSocketIO(); 