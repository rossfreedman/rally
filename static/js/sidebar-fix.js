// Rally - Sidebar Navigation Fix for Mobile
// This script ensures navigation links close the sidebar on mobile

(function() {
    // Define the MutationObserver callback function
    function handleMutations(mutations) {
        mutations.forEach(function(mutation) {
            // Look for added nodes
            if (mutation.addedNodes && mutation.addedNodes.length > 0) {
                // Check if any of the added nodes are links or might contain links
                mutation.addedNodes.forEach(function(node) {
                    // Only process element nodes
                    if (node.nodeType !== Node.ELEMENT_NODE) return;
                    
                    // Check if the node itself is a link or nav-item
                    if (node.matches('.sidebar a, .sidebar .nav-item')) {
                        attachCloseHandler(node);
                    }
                    
                    // Check if node contains links
                    const links = node.querySelectorAll('.sidebar a, .sidebar .nav-item');
                    links.forEach(attachCloseHandler);
                });
            }
        });
    }
    
    // Function to attach close handler to a link
    function attachCloseHandler(link) {
        // Store original onclick
        const originalOnClick = link.onclick;
        
        // Replace with our custom handler
        link.onclick = function(e) {
            // Call original handler if it exists
            if (typeof originalOnClick === 'function') {
                const result = originalOnClick.call(this, e);
                if (result === false) return false;
            }
            
            // Only close on mobile
            if (window.innerWidth < 768) {
                // Close the sidebar using the global utility function
                if (typeof window.responsiveUtils === 'object' && 
                    typeof window.responsiveUtils.closeSidebar === 'function') {
                    window.responsiveUtils.closeSidebar();
                    console.log('Sidebar closed by dynamic link handler');
                } else {
                    // Fallback if utility function isn't available
                    const sidebar = document.querySelector('.sidebar');
                    const sidebarOverlay = document.querySelector('.sidebar-overlay');
                    
                    if (sidebar) {
                        sidebar.classList.remove('active');
                        sidebar.style.display = 'none';
                        console.log('Sidebar closed by fallback handler');
                    }
                    
                    if (sidebarOverlay) {
                        sidebarOverlay.classList.remove('active');
                    }
                    
                    document.body.classList.remove('sidebar-open');
                }
            }
        };
    }
    
    // Setup observer to watch for DOM changes
    function setupMutationObserver() {
        // Create an observer instance
        const observer = new MutationObserver(handleMutations);
        
        // Start observing the document for DOM changes
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('Mutation observer set up to watch for dynamic sidebar links');
    }
    
    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        // Fix any existing links first
        const existingLinks = document.querySelectorAll('.sidebar a, .sidebar .nav-item');
        existingLinks.forEach(attachCloseHandler);
        
        // Setup observer for future changes
        setupMutationObserver();
        
        console.log('Sidebar fix initialized');
    });
    
    // Also run immediately if DOM is already loaded
    if (document.readyState === 'interactive' || document.readyState === 'complete') {
        const existingLinks = document.querySelectorAll('.sidebar a, .sidebar .nav-item');
        existingLinks.forEach(attachCloseHandler);
        setupMutationObserver();
        console.log('Sidebar fix initialized (immediate)');
    }
})(); 