/**
 * EMERGENCY WHITE TEXT FIX
 * This script directly modifies the DOM to force all sidebar text to be white
 */

(function() {
    // Function to make all text in the sidebar white
    function forceWhiteText() {
        console.log("EXECUTING WHITE TEXT FIX");
        
        // Get all text nodes in the sidebar
        function getAllTextNodes(element) {
            if (!element) return [];
            
            let result = [];
            
            // For each child node of the element
            for (let i = 0; i < element.childNodes.length; i++) {
                let node = element.childNodes[i];
                
                // If it's a text node and has content, add it to results
                if (node.nodeType === 3 && node.nodeValue.trim()) {
                    result.push(node);
                }
                
                // If it's an element (not an image), recursively process
                if (node.nodeType === 1 && node.tagName !== 'IMG') {
                    result = result.concat(getAllTextNodes(node));
                }
            }
            
            return result;
        }
        
        // Apply white style to every element in the sidebar
        function applyWhiteStyle() {
            const sidebar = document.querySelector('.sidebar');
            if (!sidebar) {
                // Retry in case the sidebar hasn't loaded yet
                setTimeout(applyWhiteStyle, 100);
                return;
            }
            
            // Get all elements in the sidebar
            const elements = sidebar.querySelectorAll('*');
            
            // Apply the style to each element
            elements.forEach(el => {
                if (el.tagName !== 'IMG') {
                    // Set multiple color properties to ensure coverage
                    el.style.setProperty('color', 'white', 'important');
                    el.style.setProperty('-webkit-text-fill-color', 'white', 'important');
                    el.style.setProperty('text-shadow', 'none', 'important');
                    
                    // Add direct inline style attribute for maximum override
                    const currentStyle = el.getAttribute('style') || '';
                    if (!currentStyle.includes('color: white !important')) {
                        el.setAttribute('style', currentStyle + 
                            '; color: white !important; ' + 
                            '-webkit-text-fill-color: white !important;' +
                            'text-shadow: none !important;');
                    }
                }
            });
            
            // Find all text nodes and wrap them with white-colored spans
            const textNodes = getAllTextNodes(sidebar);
            textNodes.forEach(textNode => {
                if (textNode.parentNode && textNode.nodeValue.trim() && 
                    textNode.parentNode.tagName !== 'SCRIPT' && 
                    textNode.parentNode.tagName !== 'STYLE') {
                    
                    const span = document.createElement('span');
                    span.style.color = 'white';
                    span.style.setProperty('color', 'white', 'important');
                    span.style.setProperty('-webkit-text-fill-color', 'white', 'important');
                    span.setAttribute('style', 'color: white !important; -webkit-text-fill-color: white !important;');
                    
                    const textContent = textNode.nodeValue;
                    span.textContent = textContent;
                    
                    textNode.parentNode.replaceChild(span, textNode);
                }
            });
        }
        
        // Run initially
        applyWhiteStyle();
        
        // Set up a MutationObserver to watch for changes
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            const observer = new MutationObserver(function(mutations) {
                applyWhiteStyle();
            });
            
            observer.observe(sidebar, {
                childList: true,
                subtree: true,
                characterData: true,
                attributes: true
            });
        }
    }
    
    // Run when DOM is loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', forceWhiteText);
    } else {
        forceWhiteText();
    }
    
    // Run again after a delay to catch any dynamic content
    setTimeout(forceWhiteText, 500);
    setTimeout(forceWhiteText, 1000);
})(); 