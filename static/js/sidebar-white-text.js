/**
 * DIRECT SIDEBAR TEXT COLOR FIX
 * This script forces all text in the sidebar to be white by directly modifying DOM elements
 */

(function() {
    // Function to apply white text to the sidebar
    function forceSidebarWhiteText() {
        console.log("EXECUTING SIDEBAR WHITE TEXT OVERRIDE");
        
        // Helper function to get computed style
        function getComputedColor(element) {
            const computedStyle = window.getComputedStyle(element);
            return computedStyle.getPropertyValue('color');
        }
        
        // Apply white text to a single element
        function makeElementWhite(element) {
            if (element.tagName !== 'IMG') {
                // Direct style modification with !important to override everything
                element.style.setProperty('color', 'white', 'important');
                element.style.setProperty('-webkit-text-fill-color', 'white', 'important');
                element.style.setProperty('text-shadow', 'none', 'important');
                
                // Create inline style text with all necessary overrides
                const inlineStyle = 'color: white !important; -webkit-text-fill-color: white !important; text-shadow: none !important;';
                
                // Apply the inline style directly
                const currentStyle = element.getAttribute('style') || '';
                if (!currentStyle.includes('color: white !important')) {
                    element.setAttribute('style', currentStyle + '; ' + inlineStyle);
                }
            }
        }
        
        // Find all text elements in the sidebar and make them white
        function processElements() {
            // Find the sidebar container
            const sidebar = document.querySelector('.sidebar');
            if (!sidebar) {
                setTimeout(processElements, 100); // Try again if sidebar not found
                return;
            }
            
            // Process all elements in the sidebar
            const elements = sidebar.querySelectorAll('*');
            elements.forEach(makeElementWhite);
            
            // Also process the sidebar element itself
            makeElementWhite(sidebar);
            
            // Find all pure text nodes and wrap them in spans with white color
            function wrapTextNodes(element) {
                if (element.hasChildNodes()) {
                    const childNodes = Array.from(element.childNodes);
                    
                    childNodes.forEach(node => {
                        if (node.nodeType === 3 && node.textContent.trim()) { // Text node with content
                            // Replace with styled span
                            const span = document.createElement('span');
                            span.style.setProperty('color', 'white', 'important');
                            span.style.setProperty('-webkit-text-fill-color', 'white', 'important');
                            span.textContent = node.textContent;
                            node.parentNode.replaceChild(span, node);
                        } else if (node.nodeType === 1 && node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE') {
                            // Process child elements that aren't scripts or styles
                            wrapTextNodes(node);
                        }
                    });
                }
            }
            
            // Process text nodes
            wrapTextNodes(sidebar);
        }
        
        // Set up a MutationObserver to detect DOM changes
        function setupObserver() {
            const sidebar = document.querySelector('.sidebar');
            if (!sidebar) {
                setTimeout(setupObserver, 100);
                return;
            }
            
            const observer = new MutationObserver(function(mutations) {
                processElements(); // Re-process elements when DOM changes
            });
            
            observer.observe(sidebar, {
                childList: true,
                subtree: true,
                characterData: true,
                attributes: true
            });
        }
        
        // Initial processing
        processElements();
        
        // Set up observer for ongoing changes
        setupObserver();
    }
    
    // Run function at different times to ensure it's applied
    
    // Run immediately if DOM already loaded
    if (document.readyState !== 'loading') {
        forceSidebarWhiteText();
    } else {
        // Run when DOM is loaded
        document.addEventListener('DOMContentLoaded', forceSidebarWhiteText);
    }
    
    // Run again after delays to catch any dynamically added elements
    setTimeout(forceSidebarWhiteText, 100);
    setTimeout(forceSidebarWhiteText, 500);
    setTimeout(forceSidebarWhiteText, 1000);
    
    // Create and inject a style element with universal white text for the sidebar
    function injectUniversalStyle() {
        const styleElement = document.createElement('style');
        styleElement.innerHTML = `
            /* Universal white text fix for sidebar */
            .sidebar, .sidebar *, .sidebar *:not(img), 
            html body .sidebar, html body .sidebar *:not(img),
            .nav-item, .nav-section-header, .nav-section,
            #nav-home, #nav-create-lineup, #nav-update-availability,
            #nav-find-sub, #nav-email-captain, #nav-research-me,
            #nav-research-my-team, #nav-series-stats, #nav-settings,
            .sidebar a, .sidebar a *, .sidebar i, .sidebar div, .sidebar span {
                color: white !important;
                -webkit-text-fill-color: white !important;
                text-shadow: none !important;
            }
        `;
        document.head.appendChild(styleElement);
    }
    
    // Inject the style as early as possible
    injectUniversalStyle();
})();

// Add an additional handler that runs immediately on script load
(function() {
    console.log("EXECUTING IMMEDIATE COLOR FIX ON LOAD");
    
    // Direct replacement approach - find and replace text nodes
    function replaceAllTextNodesNow() {
        // Check if sidebar exists
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;
        
        // Process all elements in sidebar
        const allElements = sidebar.querySelectorAll('*');
        
        // For each element, apply white color directly
        allElements.forEach(el => {
            if (el.tagName !== 'IMG') {
                // Force direct style
                el.style.color = 'white';
                el.style.setProperty('color', 'white', 'important');
                
                // Check for text nodes and replace them
                Array.from(el.childNodes).forEach(node => {
                    if (node.nodeType === 3 && node.textContent.trim()) {
                        // Replace with white-colored text
                        const span = document.createElement('span');
                        span.setAttribute('style', 'color: white !important');
                        
                        const whiteFontElement = document.createElement('font');
                        whiteFontElement.setAttribute('color', 'white');
                        whiteFontElement.textContent = node.textContent.trim();
                        
                        span.appendChild(whiteFontElement);
                        if (node.parentNode) {
                            node.parentNode.replaceChild(span, node);
                        }
                    }
                });
            }
        });
        
        console.log("IMMEDIATE TEXT NODE REPLACEMENT COMPLETE");
    }
    
    // Run immediately
    replaceAllTextNodesNow();
    
    // And again after a brief delay
    setTimeout(replaceAllTextNodesNow, 300);
})(); 