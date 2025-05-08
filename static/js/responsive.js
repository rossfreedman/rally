// Rally - Responsive Behavior JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Create sidebar toggle button and overlay for mobile devices
    initializeMobileNavigation();
    
    // Add responsive behavior event listeners
    addResponsiveEventListeners();
    
    // Handle window resize events
    handleWindowResize();
    
    // Initialize viewport meta tag if needed
    ensureViewportMetaTag();
});

// Create and add the mobile navigation elements
function initializeMobileNavigation() {
    // Add the sidebar toggle button to the navbar
    const navbar = document.querySelector('.navbar-toggler');
    if (navbar) {
        // Create the sidebar toggle button if it doesn't exist
        if (!document.querySelector('.sidebar-toggle')) {
            const sidebarToggle = document.createElement('button');
            sidebarToggle.classList.add('sidebar-toggle', 'd-md-none');
            sidebarToggle.setAttribute('aria-label', 'Toggle sidebar');
            sidebarToggle.innerHTML = '<i class="fas fa-bars"></i>';
            navbar.parentNode.insertBefore(sidebarToggle, navbar);
        }
    }
    
    // Create the sidebar overlay if it doesn't exist
    if (!document.querySelector('.sidebar-overlay')) {
        const sidebarOverlay = document.createElement('div');
        sidebarOverlay.classList.add('sidebar-overlay');
        document.body.appendChild(sidebarOverlay);
    }
}

// Add event listeners for responsive behavior
function addResponsiveEventListeners() {
    // Toggle sidebar on mobile devices
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    
    if (sidebarToggle && sidebar && sidebarOverlay) {
        // Toggle sidebar when the button is clicked
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
            sidebarOverlay.classList.toggle('active');
            document.body.classList.toggle('sidebar-open');
        });
        
        // Close sidebar when overlay is clicked
        sidebarOverlay.addEventListener('click', function() {
            sidebar.classList.remove('active');
            sidebarOverlay.classList.remove('active');
            document.body.classList.remove('sidebar-open');
        });
        
        // Close sidebar when a navigation link is clicked
        const navLinks = sidebar.querySelectorAll('.nav-item');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth < 768) {
                    sidebar.classList.remove('active');
                    sidebarOverlay.classList.remove('active');
                    document.body.classList.remove('sidebar-open');
                }
            });
        });
    }
    
    // Make tables responsive
    const tables = document.querySelectorAll('table:not(.table-responsive)');
    tables.forEach(table => {
        // Only wrap tables that aren't already in a responsive container
        if (!table.closest('.table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.classList.add('table-responsive');
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
}

// Handle window resize events
function handleWindowResize() {
    let resizeTimer;
    
    window.addEventListener('resize', function() {
        // Clear the timeout if it's been set
        if (resizeTimer) clearTimeout(resizeTimer);
        
        // Set a new timeout to run after resize completes
        resizeTimer = setTimeout(function() {
            // Reset sidebar state on resize to desktop
            if (window.innerWidth >= 768) {
                const sidebar = document.querySelector('.sidebar');
                const sidebarOverlay = document.querySelector('.sidebar-overlay');
                
                if (sidebar && sidebarOverlay) {
                    sidebarOverlay.classList.remove('active');
                    document.body.classList.remove('sidebar-open');
                    
                    // Only on desktop, ensure sidebar is visible
                    sidebar.classList.remove('active'); // Remove mobile active class
                }
            }
            
            // Adjust content heights for different screen sizes
            adjustContentHeights();
            
        }, 250); // Debounce resize event
    });
    
    // Initial adjustment
    adjustContentHeights();
}

// Adjust heights of content elements based on screen size
function adjustContentHeights() {
    // Adjust chat card height
    const chatCards = document.querySelectorAll('.chat-card');
    chatCards.forEach(card => {
        if (window.innerWidth < 768) {
            // Mobile: fixed height with scrolling
            card.style.height = '500px';
        } else {
            // Desktop: percentage of viewport height
            card.style.height = 'calc(90vh - 130px)';
        }
    });
    
    // Adjust dashboard card heights
    const dashboardCards = document.querySelectorAll('.dashboard-cards .card');
    dashboardCards.forEach(card => {
        if (window.innerWidth < 768) {
            // Mobile: fixed height with scrolling
            card.style.height = '500px';
        } else {
            // Desktop: percentage of viewport height
            card.style.height = 'calc(90vh - 130px)';
        }
    });
}

// Ensure the viewport meta tag exists
function ensureViewportMetaTag() {
    if (!document.querySelector('meta[name="viewport"]')) {
        const meta = document.createElement('meta');
        meta.name = 'viewport';
        meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
        document.head.appendChild(meta);
    }
}

// Function to detect if the user is on a mobile device
function isMobileDevice() {
    return (window.innerWidth < 768) || 
           (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));
}

// Expose some utility functions globally
window.responsiveUtils = {
    isMobileDevice: isMobileDevice,
    adjustContentHeights: adjustContentHeights
}; 