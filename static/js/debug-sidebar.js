// Debug script for sidebar toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('[DEBUG] debug-sidebar.js loaded');
    
    // Check if sidebar-toggler exists
    const sidebarToggler = document.getElementById('sidebar-toggler');
    console.log('[DEBUG] sidebar-toggler exists:', sidebarToggler !== null);
    
    // Check if sidebar-overlay exists
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    console.log('[DEBUG] sidebar-overlay exists:', sidebarOverlay !== null);
    
    // Check if sidebar exists
    const sidebar = document.querySelector('.sidebar');
    console.log('[DEBUG] sidebar exists:', sidebar !== null);
    
    // Keep track of last toggle to prevent immediate closing
    let lastToggleTime = 0;
    const TOGGLE_THRESHOLD = 300; // ms
    
    // Define our own toggleSidebar function to ensure it works
    window.toggleSidebar = function() {
        console.log('[DEBUG] toggleSidebar called');
        
        // Check if it's too soon since last toggle
        const now = Date.now();
        if (now - lastToggleTime < TOGGLE_THRESHOLD) {
            console.log('[DEBUG] Ignoring rapid toggle');
            return;
        }
        lastToggleTime = now;
        
        document.body.classList.toggle('sidebar-open');
        
        // Update overlay visibility
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
    };
    
    // Define close sidebar function
    window.closeSidebar = function() {
        console.log('[DEBUG] closeSidebar called');
        
        // Check if it's too soon since last toggle
        const now = Date.now();
        if (now - lastToggleTime < TOGGLE_THRESHOLD) {
            console.log('[DEBUG] Ignoring rapid close');
            return;
        }
        lastToggleTime = now;
        
        document.body.classList.remove('sidebar-open');
        
        const overlay = document.getElementById('sidebar-overlay');
        if (overlay) {
            overlay.style.opacity = '0';
            setTimeout(() => overlay.style.display = 'none', 300);
        }
    };
    
    // Check if hamburger-fix.js has already set up event handlers
    if (typeof window.hamburgerToggleSidebar === 'function') {
        console.log('[DEBUG] Using hamburgerToggleSidebar from hamburger-fix.js');
        window.toggleSidebar = window.hamburgerToggleSidebar;
    }
    
    // Use hamburgerCloseSidebar if available
    if (typeof window.hamburgerCloseSidebar === 'function') {
        console.log('[DEBUG] Using hamburgerCloseSidebar from hamburger-fix.js');
        window.closeSidebar = window.hamburgerCloseSidebar;
    } else {
        // Improved hamburger menu event handling
        if (sidebarToggler) {
            // Remove all existing event listeners
            const newToggler = sidebarToggler.cloneNode(true);
            sidebarToggler.parentNode.replaceChild(newToggler, sidebarToggler);
            
            // Add only click event for better reliability
            newToggler.addEventListener('click', function(e) {
                console.log('[DEBUG] sidebar-toggler click event fired');
                e.preventDefault();
                e.stopPropagation();
                window.toggleSidebar();
                
                // Add active class for visual feedback
                this.classList.add('toggler-active');
                setTimeout(() => this.classList.remove('toggler-active'), 300);
            });
            
            // Add touch feedback events
            newToggler.addEventListener('touchstart', function() {
                this.classList.add('toggler-active');
            }, { passive: true });
            
            newToggler.addEventListener('touchend', function() {
                this.classList.remove('toggler-active');
            }, { passive: true });
            
            // Also ensure the icon inside is clickable
            const hamburgerIcon = newToggler.querySelector('.fas.fa-bars');
            if (hamburgerIcon) {
                hamburgerIcon.addEventListener('click', function(e) {
                    console.log('[DEBUG] hamburger icon click event fired');
                    e.preventDefault();
                    e.stopPropagation();
                    window.toggleSidebar();
                });
            }
            
            console.log('[DEBUG] Added enhanced event listeners to sidebar toggler');
        }
    }
    
    // Add click handler to sidebar-overlay
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            console.log('[DEBUG] sidebar-overlay clicked');
            window.closeSidebar();
        });
    }
    
    // Make sure the sidebar closes when navigation links are clicked
    if (sidebar) {
        const sidebarLinks = sidebar.querySelectorAll('a');
        sidebarLinks.forEach(function(link) {
            link.addEventListener('click', function() {
                console.log('[DEBUG] Sidebar link clicked, closing sidebar');
                window.closeSidebar();
            });
        });
        console.log('[DEBUG] Added close handlers to', sidebarLinks.length, 'sidebar links');
    }
    
    // Add click handler to body to close sidebar when clicking outside
    document.body.addEventListener('click', function(e) {
        if (document.body.classList.contains('sidebar-open')) {
            // Check if click was not inside the sidebar and not the toggle button
            const sidebar = document.querySelector('.sidebar');
            const toggler = document.getElementById('sidebar-toggler');
            if (sidebar && !sidebar.contains(e.target) && 
                toggler && !toggler.contains(e.target)) {
                console.log('[DEBUG] Clicked outside sidebar, closing');
                window.closeSidebar();
            }
        }
    });
    
    // Monitor body class changes
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'class') {
                console.log('[DEBUG] body class changed to:', document.body.className);
            }
        });
    });
    
    observer.observe(document.body, { attributes: true });
}); 