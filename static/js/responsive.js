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
    
    // Force hide sidebar on mobile when page loads
    forceMobileLayout();
    
    // Patch the showContent function if it exists
    patchShowContentFunction();
    
    // Directly modify sidebar link behavior
    modifySidebarLinkBehavior();
});

// Modify all sidebar links to explicitly close the sidebar on click
function modifySidebarLinkBehavior() {
    // Get all links in the sidebar
    const sidebarLinks = document.querySelectorAll('.sidebar a, .sidebar .nav-item');
    
    sidebarLinks.forEach(link => {
        // Store the original onclick handler if it exists
        const originalOnClick = link.onclick;
        
        // Replace with our own handler that calls the original and then closes the sidebar
        link.onclick = function(e) {
            // Call the original handler if it exists
            if (typeof originalOnClick === 'function') {
                // If original handler returns false, we should respect that
                const result = originalOnClick.call(this, e);
                if (result === false) return false;
            }
            
            // Only close the sidebar on mobile
            if (window.innerWidth < 768) {
                // Close the sidebar
                closeSidebar();
                console.log('Sidebar closed by modified link onclick handler');
            }
        };
    });
    
    console.log('Modified all sidebar links to close sidebar on click');
}

// Patch the showContent function to ensure it closes the sidebar
function patchShowContentFunction() {
    // Wait a short time to ensure the original function is defined
    setTimeout(function() {
        if (typeof window.showContent === 'function') {
            // Store the original function
            const originalShowContent = window.showContent;
            
            // Replace it with our patched version
            window.showContent = function(contentId) {
                // Call the original function
                originalShowContent(contentId);
                
                // Close the sidebar if in mobile view
                if (window.innerWidth < 768) {
                    closeSidebar();
                    console.log('Sidebar closed by patched showContent function');
                }
            };
            console.log('Successfully patched showContent function');
        } else {
            console.log('showContent function not found, will try again');
            // Try again a bit later
            setTimeout(patchShowContentFunction, 500);
        }
    }, 100);
}

// Force mobile layout if screen size is mobile
function forceMobileLayout() {
    if (window.innerWidth < 768) {
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (sidebar) {
            sidebar.style.display = 'none';
            sidebar.classList.remove('active');
            sidebar.setAttribute('aria-hidden', 'true');
        }
        
        if (mainContent) {
            mainContent.style.width = '100%';
            mainContent.style.marginLeft = '0';
            mainContent.style.padding = '10px';
        }
        
        // Mark the body to indicate we're in mobile mode
        document.body.classList.add('mobile-view');
    }
}

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

// Helper function to close the sidebar
function closeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const sidebarOverlay = document.querySelector('.sidebar-overlay');
    
    if (sidebar && sidebarOverlay) {
        sidebar.classList.remove('active');
        sidebarOverlay.classList.remove('active');
        document.body.classList.remove('sidebar-open');
        
        // Hide after transition
        setTimeout(function() {
            sidebar.style.display = 'none';
            sidebar.setAttribute('aria-hidden', 'true');
        }, 300);
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
            
            // Toggle display property
            if (sidebar.classList.contains('active')) {
                sidebar.style.display = 'block';
                sidebar.setAttribute('aria-hidden', 'false');
            } else {
                setTimeout(function() {
                    sidebar.style.display = 'none';
                    sidebar.setAttribute('aria-hidden', 'true');
                }, 300); // Wait for transition to complete
            }
        });
        
        // Close sidebar when overlay is clicked
        sidebarOverlay.addEventListener('click', closeSidebar);
        
        // Close sidebar when ANY navigation link is clicked
        // Target all clickable links in the sidebar, including section links
        const allSidebarLinks = sidebar.querySelectorAll('a[href], .nav-item, .sidebar-nav a');
        
        allSidebarLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                if (window.innerWidth < 768) {
                    // Close the sidebar
                    closeSidebar();
                    console.log('Sidebar closed by link click');
                }
            });
        });
    }
    
    // Add global document click handler for navigation links that might be dynamically added
    document.addEventListener('click', function(e) {
        // Check if we're in mobile view
        if (window.innerWidth >= 768) return;
        
        // Check if the clicked element is a navigation link or inside the sidebar
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;
        
        // If click target is a link inside the sidebar or has class nav-item
        const isNavLink = e.target.closest('.sidebar a') || 
                          e.target.closest('.sidebar .nav-item') ||
                          e.target.matches('.sidebar a') || 
                          e.target.matches('.sidebar .nav-item');
        
        if (isNavLink) {
            // Close the sidebar
            closeSidebar();
            console.log('Sidebar closed by global click handler');
        }
    });
    
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
            const sidebar = document.querySelector('.sidebar');
            const sidebarOverlay = document.querySelector('.sidebar-overlay');
            const mainContent = document.querySelector('.main-content');
            
            // Reset sidebar state on resize to desktop
            if (window.innerWidth >= 768) {
                if (sidebar && sidebarOverlay) {
                    sidebarOverlay.classList.remove('active');
                    document.body.classList.remove('sidebar-open');
                    document.body.classList.remove('mobile-view');
                    
                    // Show sidebar on desktop
                    sidebar.style.display = 'block';
                    sidebar.classList.remove('active');
                    sidebar.setAttribute('aria-hidden', 'false');
                }
                
                // Reset main content layout for desktop
                if (mainContent) {
                    mainContent.style.marginLeft = '';
                    mainContent.style.width = '';
                }
            } else {
                // We're in mobile view now
                document.body.classList.add('mobile-view');
                
                // On mobile, hide sidebar unless it's explicitly active
                if (sidebar && !sidebar.classList.contains('active')) {
                    sidebar.style.display = 'none';
                    sidebar.setAttribute('aria-hidden', 'true');
                }
                
                // Ensure main content uses full width on mobile
                if (mainContent) {
                    mainContent.style.width = '100%';
                    mainContent.style.marginLeft = '0';
                    mainContent.style.padding = '10px';
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
    adjustContentHeights: adjustContentHeights,
    forceMobileLayout: forceMobileLayout,
    closeSidebar: closeSidebar
}; 