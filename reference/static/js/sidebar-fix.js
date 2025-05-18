/**
 * CRITICAL TEXT COLOR FIX
 * This script directly modifies ALL text nodes in the sidebar to ensure they are white
 * regardless of any other CSS.
 */

(function() {
    console.log('SIDEBAR FIX LOADING...');
    
    // Run this function immediately
    function fixSidebarNow() {
        console.log('Fixing sidebar text color NOW');
        
        // Target all links in the sidebar
        const sidebarLinks = document.querySelectorAll('.sidebar a, .nav-item, .sidebar-nav a');
        sidebarLinks.forEach(link => {
            // Force inline color with maximum specificity
            link.setAttribute('style', 'color: white !important; -webkit-text-fill-color: white !important; text-shadow: none !important');
            
            // Replace all text nodes with new ones that have a span wrapper
            Array.from(link.childNodes).forEach(node => {
                if (node.nodeType === 3 && node.textContent.trim()) { // Text node with content
                    const span = document.createElement('span');
                    span.textContent = node.textContent.trim();
                    span.style.color = 'white';
                    span.style.setProperty('color', 'white', 'important');
                    span.style.setProperty('-webkit-text-fill-color', 'white', 'important');
                    
                    // Create a font element for maximum compatibility
                    const font = document.createElement('font');
                    font.setAttribute('color', 'white');
                    font.appendChild(document.createTextNode(node.textContent.trim()));
                    
                    // Clear span and add font
                    span.textContent = '';
                    span.appendChild(font);
                    
                    node.parentNode.replaceChild(span, node);
                }
            });
            
            // Also make all icons white
            const icons = link.querySelectorAll('i');
            icons.forEach(icon => {
                icon.setAttribute('style', 'color: white !important');
            });
        });
        
        // Target all section headers too
        const sectionHeaders = document.querySelectorAll('.nav-section-header');
        sectionHeaders.forEach(header => {
            header.setAttribute('style', 'color: white !important');
            
            // Process all child text nodes
            Array.from(header.childNodes).forEach(node => {
                if (node.nodeType === 3 && node.textContent.trim()) {
                    const span = document.createElement('span');
                    span.style.color = 'white';
                    span.style.setProperty('color', 'white', 'important');
                    
                    // Create a font element for maximum compatibility
                    const font = document.createElement('font');
                    font.setAttribute('color', 'white');
                    font.appendChild(document.createTextNode(node.textContent.trim()));
                    
                    // Add font to span
                    span.appendChild(font);
                    
                    node.parentNode.replaceChild(span, node);
                }
            });
            
            // Make icons white
            const icons = header.querySelectorAll('i');
            icons.forEach(icon => {
                icon.setAttribute('style', 'color: white !important');
            });
        });
    }
    
    // Run immediately if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixSidebarNow);
    } else {
        fixSidebarNow();
    }
    
    // Run multiple times with delays to catch any dynamic changes
    setTimeout(fixSidebarNow, 100);
    setTimeout(fixSidebarNow, 500);
    setTimeout(fixSidebarNow, 1000);
    
    // Create a MutationObserver to watch for changes to the sidebar
    const observer = new MutationObserver(fixSidebarNow);
    
    // Start observing once the DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            observer.observe(sidebar, {
                childList: true,
                subtree: true,
                characterData: true,
                attributes: true
            });
        }
    });
})(); 