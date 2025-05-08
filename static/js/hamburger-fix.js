/**
 * Dedicated hamburger menu fix for mobile devices
 * This script ensures the hamburger menu is always clickable
 */

(function() {
    // Execute as soon as possible - don't wait for DOMContentLoaded
    function applyHamburgerFix() {
        console.log('[HAMBURGER-FIX] Applying hamburger menu fix');
        
        // Flag to prevent immediate toggle
        let lastToggleTime = 0;
        const TOGGLE_THRESHOLD = 300; // ms
        
        function toggleSidebar() {
            console.log('[HAMBURGER-FIX] Toggle sidebar called');
            
            const now = Date.now();
            if (now - lastToggleTime < TOGGLE_THRESHOLD) {
                console.log('[HAMBURGER-FIX] Ignoring rapid toggle');
                return;
            }
            lastToggleTime = now;
            
            // Toggle body class
            document.body.classList.toggle('sidebar-open');
            
            // Handle overlay
            const overlay = document.getElementById('sidebar-overlay');
            if (overlay) {
                if (document.body.classList.contains('sidebar-open')) {
                    overlay.style.display = 'block';
                    setTimeout(() => overlay.style.opacity = '1', 10);
                } else {
                    overlay.style.opacity = '0';
                    setTimeout(() => overlay.style.display = 'none', 300);
                }
            }
        }
        
        function closeSidebar() {
            console.log('[HAMBURGER-FIX] Close sidebar called');
            
            const now = Date.now();
            if (now - lastToggleTime < TOGGLE_THRESHOLD) {
                console.log('[HAMBURGER-FIX] Ignoring rapid close');
                return;
            }
            lastToggleTime = now;
            
            // Remove sidebar-open class
            document.body.classList.remove('sidebar-open');
            
            // Handle overlay
            const overlay = document.getElementById('sidebar-overlay');
            if (overlay) {
                overlay.style.opacity = '0';
                setTimeout(() => overlay.style.display = 'none', 300);
            }
        }
        
        // Make functions globally available
        window.hamburgerToggleSidebar = toggleSidebar;
        window.hamburgerCloseSidebar = closeSidebar;
        
        // Set up direct event listeners using both methods
        function setupDirectEventHandlers() {
            const sidebarToggler = document.getElementById('sidebar-toggler');
            const touchTarget = document.getElementById('hamburger-touch-target');
            const sidebar = document.querySelector('.sidebar');
            
            if (!sidebarToggler && !touchTarget) {
                console.log('[HAMBURGER-FIX] Neither toggler nor touch target found, will try again');
                setTimeout(setupDirectEventHandlers, 100);
                return;
            }
            
            console.log('[HAMBURGER-FIX] Setting up direct event handlers');
            
            // Add events to the main toggler
            if (sidebarToggler) {
                // Method 1: Direct attribute
                sidebarToggler.setAttribute('onclick', 'window.hamburgerToggleSidebar()');
                
                // Add click event (use only click, not touchstart or mousedown)
                sidebarToggler.addEventListener('click', function(e) {
                    console.log('[HAMBURGER-FIX] Click event triggered');
                    e.preventDefault();
                    e.stopPropagation();
                    toggleSidebar();
                    return false;
                }, {capture: true, passive: false});
                
                // Also add to the icon inside
                const icon = sidebarToggler.querySelector('.fas.fa-bars');
                if (icon) {
                    icon.addEventListener('click', function(e) {
                        console.log('[HAMBURGER-FIX] Icon click event triggered');
                        e.preventDefault();
                        e.stopPropagation();
                        toggleSidebar();
                        return false;
                    }, {capture: true, passive: false});
                }
                
                // Add visual feedback for touch
                sidebarToggler.addEventListener('touchstart', function() {
                    sidebarToggler.classList.add('toggler-active');
                }, { passive: true });
                
                sidebarToggler.addEventListener('touchend', function() {
                    sidebarToggler.classList.remove('toggler-active');
                }, { passive: true });
            }
            
            // Add events to the extra touch target if it exists
            if (touchTarget) {
                console.log('[HAMBURGER-FIX] Adding events to extra touch target');
                
                // Direct attribute
                touchTarget.setAttribute('onclick', 'window.hamburgerToggleSidebar()');
                
                // Use only click event
                touchTarget.addEventListener('click', function(e) {
                    console.log('[HAMBURGER-FIX] Touch target click event triggered');
                    e.preventDefault();
                    e.stopPropagation();
                    toggleSidebar();
                    return false;
                }, {capture: true, passive: false});
                
                // Add visual feedback for touch
                touchTarget.addEventListener('touchstart', function() {
                    if (sidebarToggler) sidebarToggler.classList.add('toggler-active');
                }, { passive: true });
                
                touchTarget.addEventListener('touchend', function() {
                    if (sidebarToggler) sidebarToggler.classList.remove('toggler-active');
                }, { passive: true });
            }
            
            // Handle the overlay clicks
            const overlay = document.getElementById('sidebar-overlay');
            if (overlay) {
                overlay.addEventListener('click', function() {
                    closeSidebar();
                });
            }
            
            // Close sidebar when clicking any link inside it
            if (sidebar) {
                const sidebarLinks = sidebar.querySelectorAll('a');
                sidebarLinks.forEach(function(link) {
                    link.addEventListener('click', function() {
                        console.log('[HAMBURGER-FIX] Sidebar link clicked, closing sidebar');
                        closeSidebar();
                    });
                });
                console.log('[HAMBURGER-FIX] Added close handlers to', sidebarLinks.length, 'sidebar links');
            } else {
                console.log('[HAMBURGER-FIX] Sidebar not found, will try again');
                setTimeout(function() {
                    const sidebar = document.querySelector('.sidebar');
                    if (sidebar) {
                        const sidebarLinks = sidebar.querySelectorAll('a');
                        sidebarLinks.forEach(function(link) {
                            link.addEventListener('click', function() {
                                console.log('[HAMBURGER-FIX] Sidebar link clicked, closing sidebar');
                                closeSidebar();
                            });
                        });
                        console.log('[HAMBURGER-FIX] Added close handlers to', sidebarLinks.length, 'sidebar links (retry)');
                    }
                }, 1000);
            }
            
            console.log('[HAMBURGER-FIX] Direct event handlers set up successfully');
        }
        
        // Try setting up event handlers immediately
        setupDirectEventHandlers();
        
        // Also try again when DOM is fully loaded
        document.addEventListener('DOMContentLoaded', setupDirectEventHandlers);
        
        // And once more after a short delay
        setTimeout(setupDirectEventHandlers, 1000);
    }
    
    // Run the fix immediately
    applyHamburgerFix();
    
    // Also run again when DOM is loaded
    document.addEventListener('DOMContentLoaded', applyHamburgerFix);
    
    // And once more on window load to be super sure
    window.addEventListener('load', applyHamburgerFix);
})(); 