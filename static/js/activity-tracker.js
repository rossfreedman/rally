// Click tracking functionality
function logClick(event) {
    // Only track clicks on interactive elements
    const interactiveElements = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'];
    const target = event.target.closest(interactiveElements.join(','));
    
    if (!target) return; // Not an interactive element
    
    // Skip if it's a logout link - let the main logout handler work
    if (target.classList.contains('logout-link')) {
        return;
    }
    
    // Prepare click data
    const data = {
        elementId: target.id,
        elementText: target.textContent.trim() || target.value,
        elementType: target.tagName.toLowerCase(),
        pageUrl: window.location.pathname
    };
    
    // Send click data to server
    fetch('/api/log-click', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(data)
    }).catch(error => {
        console.error('Error logging click:', error);
    });
}

// Initialize click tracking
document.addEventListener('DOMContentLoaded', function() {
    // Add click listener to document
    document.addEventListener('click', logClick);
    
    console.log('Click tracking initialized');
}); 