/**
 * EMERGENCY TEXT COLOR FIX
 * This script runs immediately to directly modify all text in the sidebar to be white
 */

// Function to check if a color is gray
function isGrayColor(color) {
    // If it's a hex color like #666, #777, #999, etc.
    if (typeof color === 'string' && color.startsWith('#')) {
        // Extract RGB components
        const hex = color.substring(1);
        // Handle 3-digit hex
        if (hex.length === 3) {
            const r = parseInt(hex[0] + hex[0], 16);
            const g = parseInt(hex[1] + hex[1], 16);
            const b = parseInt(hex[2] + hex[2], 16);
            // Check if it's a grayscale color (R=G=B)
            return Math.abs(r - g) < 30 && Math.abs(r - b) < 30 && Math.abs(g - b) < 30;
        }
        // Handle 6-digit hex
        if (hex.length === 6) {
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);
            // Check if it's a grayscale color (R=G=B)
            return Math.abs(r - g) < 30 && Math.abs(r - b) < 30 && Math.abs(g - b) < 30;
        }
    }
    
    // If it's an rgb() color
    const rgbMatch = color && color.match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/i);
    if (rgbMatch) {
        const r = parseInt(rgbMatch[1], 10);
        const g = parseInt(rgbMatch[2], 10);
        const b = parseInt(rgbMatch[3], 10);
        // Check if it's a grayscale color (R=G=B)
        return Math.abs(r - g) < 30 && Math.abs(r - b) < 30 && Math.abs(g - b) < 30;
    }
    
    return false;
}

// Function to check the computed style of an element
function hasGrayText(element) {
    const computedStyle = window.getComputedStyle(element);
    const color = computedStyle.getPropertyValue('color');
    return isGrayColor(color);
}

// Run the gray text detector and fixer immediately
(function() {
    console.log("GRAY TEXT DETECTOR RUNNING");
    
    function fixGrayText() {
        const sidebar = document.querySelector('.sidebar');
        if (!sidebar) return;
        
        // Get all elements in the sidebar
        const elements = sidebar.querySelectorAll('*');
        
        // Check each element for gray text
        elements.forEach(el => {
            if (el.tagName !== 'IMG') {
                // If the element has gray text, force it to be white
                if (hasGrayText(el)) {
                    console.log("Found gray text, fixing:", el);
                    el.style.setProperty('color', 'white', 'important');
                    el.style.setProperty('-webkit-text-fill-color', 'white', 'important');
                    
                    // Ensure the new color is applied
                    const span = document.createElement('span');
                    span.style.cssText = "color: white !important; -webkit-text-fill-color: white !important;";
                    
                    // Move all child nodes to the span
                    while (el.firstChild) {
                        span.appendChild(el.firstChild);
                    }
                    
                    // Add the span back to the element
                    el.appendChild(span);
                }
            }
        });
    }
    
    // Run immediately
    fixGrayText();
    
    // And run again after a delay
    setTimeout(fixGrayText, 300);
    setTimeout(fixGrayText, 800);
})(); 