// Logout functionality
(function() {
    // Define the main logout function
    window.handleLogout = async function(event) {
        if (event) {
            event.preventDefault();
        }
        
        console.log('\n=== LOGOUT FUNCTION CALLED ===');
        
        try {
            // First attempt the API logout
            console.log('Making logout request...');
            const response = await fetch('/api/logout', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Cache-Control': 'no-cache, no-store, must-revalidate'
                }
            });

            console.log('Logout response status:', response.status);
            
            if (response.ok) {
                const data = await response.json();
                console.log('Logout successful:', data);
                
                // Clear any client-side state
                console.log('Clearing client-side storage...');
                sessionStorage.clear();
                localStorage.clear();
                
                // Force clear any cookies
                document.cookie.split(";").forEach(function(c) { 
                    document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
                });
                
                // Use the redirect URL from the server response if available
                const redirectUrl = data.redirect || '/login';
                console.log('Redirecting to:', redirectUrl);
                window.location.href = redirectUrl;
            } else {
                console.error('Logout failed:', response.status);
                // Fallback to direct logout
                console.log('Attempting fallback logout...');
                window.location.href = '/logout';
            }
        } catch (error) {
            console.error('Logout error:', error);
            // Final fallback - direct to logout page
            window.location.href = '/logout';
        }
    };

    // For backward compatibility
    window.logout = window.handleLogout;

    // Log that the script is loaded
    console.log('Logout script loaded successfully');
    console.log('Logout functions available:', {
        handleLogout: typeof window.handleLogout === 'function',
        logout: typeof window.logout === 'function'
    });

    // Ensure the function is available globally
    if (typeof window !== 'undefined') {
        window.handleLogout = window.handleLogout || handleLogout;
        
        // Add event listener for logout links if DOM is ready
        if (document.readyState === 'complete' || document.readyState === 'interactive') {
            const logoutLinks = document.querySelectorAll('.logout-link');
            logoutLinks.forEach(link => {
                link.addEventListener('click', handleLogout);
            });
        } else {
            document.addEventListener('DOMContentLoaded', function() {
                const logoutLinks = document.querySelectorAll('.logout-link');
                logoutLinks.forEach(link => {
                    link.addEventListener('click', handleLogout);
                });
            });
        }
    }
})();

// Test that the function is available
console.log('Logout function defined:', typeof window.logout === 'function');

// Add a simple test function
window.testLogout = function() {
    console.log('Test logout function called');
    console.log('Logout function available:', typeof window.logout === 'function');
    return 'Logout function is ' + (typeof window.logout === 'function' ? 'available' : 'not available');
}; 