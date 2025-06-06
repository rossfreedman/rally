// Handle session data
document.addEventListener('DOMContentLoaded', async function() {
    try {
        // If we have session data in the window object, use it
        if (window.sessionData) {
            console.log('Using injected session data:', window.sessionData);
            updateUI(window.sessionData);
            return;
        }

        // Only check auth if we're not on the login page
        if (!window.location.pathname.includes('/login')) {
            const authResponse = await fetch('/api/check-auth', {
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            const authData = await authResponse.json();
            
            if (authData.authenticated) {
                console.log('Auth check successful:', authData);
                updateUI({ user: authData.user, authenticated: true });
            } else {
                console.warn('Not authenticated');
                // Don't redirect - let the server handle auth redirects
            }
        }
    } catch (error) {
        console.error('Error checking authentication:', error);
        // Don't redirect on error - let the server handle auth
    }
});

// Function to update UI with session data
function updateUI(sessionData) {
    if (!sessionData || !sessionData.user) return;
    
    // Update welcome message if element exists
    const welcomeElem = document.getElementById('welcomeMessage');
    if (welcomeElem) {
        const user = sessionData.user;
        welcomeElem.textContent = `Welcome back, ${user.first_name} ${user.last_name} (${user.series} at ${user.club})`;
    }
}

async function saveAvailabilityChange(button, playerName, date) {
    const loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.style.display = 'flex';
    
    try {
        const isAvailable = button.getAttribute('data-state') === 'available';
        
        const response = await fetch('/api/availability', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                player_name: playerName,
                match_date: date,
                is_available: isAvailable,
                series: selectedSeries
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to save availability');
        }
        
        // Show success indicator
        const successIndicator = document.createElement('span');
        successIndicator.className = 'success-indicator';
        successIndicator.textContent = '✓';
        button.appendChild(successIndicator);
        
        setTimeout(() => {
            successIndicator.remove();
        }, 1000);
        
    } catch (error) {
        console.error('Error saving availability:', error);
        // Revert the button state
        const currentState = button.getAttribute('data-state');
        const newState = currentState === 'available' ? 'unavailable' : 'available';
        button.setAttribute('data-state', newState);
        button.className = `availability-btn ${newState}`;
        button.textContent = newState === 'available' ? 'Available' : 'Not Available';
        
        alert('Error saving availability. Please try again.');
    } finally {
        loadingOverlay.style.display = 'none';
    }
}

// Add default fetch configuration
window.fetchWithCredentials = (url, options = {}) => {
    return fetch(url, {
        ...options,
        credentials: 'include',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            ...(options.headers || {})
        }
    });
};

// Export session utilities
window.sessionUtils = {
    updateUI
}; 