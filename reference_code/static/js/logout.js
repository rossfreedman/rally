// Logout functionality
async function logout() {
    console.log('Logout function called');
    try {
        const response = await fetch('/api/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        console.log('Logout response status:', response.status);
        
        if (response.ok) {
            // Clear any local state
            sessionStorage.clear();
            localStorage.clear();
            
            // Redirect to login page
            window.location.href = '/login';
        } else {
            console.error('Logout failed:', response.status);
            const data = await response.json();
            console.error('Error details:', data);
        }
    } catch (error) {
        console.error('Logout error:', error);
    }
}

// Verify script loading
console.log('Logout script loaded'); 