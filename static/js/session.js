// Handle session data
document.addEventListener('DOMContentLoaded', async function() {
    try {
        // Check authentication status first
        const authResponse = await fetch('/api/check-auth', {
            credentials: 'include'  // Important for sending cookies
        });
        const authData = await authResponse.json();
        
        if (!authData.authenticated) {
            console.warn('Not authenticated, redirecting to login');
            window.location.href = '/login';
            return;
        }

        // If we have session data in the window object, use it
        if (window.sessionData) {
            console.log('Using injected session data:', window.sessionData);
            updateUI(window.sessionData);
        } else {
            // If no injected data, use the auth response data
            console.log('Using auth response data:', authData);
            updateUI({ user: authData.user, authenticated: true });
        }
    } catch (error) {
        console.error('Error checking authentication:', error);
        window.location.href = '/login';
    }
});

function updateUI(sessionData) {
    if (!sessionData || !sessionData.user) {
        console.warn('No valid session data for UI update');
        return;
    }

    // Update UI elements with user info if they exist
    const userNameElement = document.getElementById('userName');
    if (userNameElement) {
        userNameElement.textContent = `${sessionData.user.first_name} ${sessionData.user.last_name}`;
    }
    
    // Update series info if it exists
    const seriesElement = document.getElementById('currentSeries');
    if (seriesElement) {
        seriesElement.textContent = sessionData.user.series;
    }
    
    // Update club info if it exists
    const clubElement = document.getElementById('currentClub');
    if (clubElement) {
        clubElement.textContent = sessionData.user.club;
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

// Function to update the welcome message in the navbar
function updateWelcomeMessage() {
    fetch('/api/check-auth')
        .then(response => response.json())
        .then(data => {
            console.log('[DEBUG] updateWelcomeMessage data:', data);
            if (data.authenticated) {
                const user = data.user;
                const welcomeMsg = `Welcome back, ${user.first_name} ${user.last_name} (${user.series} at ${user.club})`;
                const welcomeElem = document.getElementById('welcomeMessage');
                if (welcomeElem) {
                    welcomeElem.textContent = welcomeMsg;
                } else {
                    console.warn('[DEBUG] #welcomeMessage element not found');
                }
            } else {
                console.warn('[DEBUG] User not authenticated');
            }
        })
        .catch(error => {
            console.error('[DEBUG] Error fetching user data:', error);
        });
} 