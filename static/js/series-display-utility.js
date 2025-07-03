/**
 * Series Display Utility
 * =====================
 * 
 * Simplified utility that uses the display_name from the backend.
 * No more client-side transformations needed.
 */

/**
 * Transform series name from database format to display format.
 * Now just returns the display_name provided by the backend.
 * 
 * @param {string} databaseSeries - Series name from database 
 * @returns {string} User-friendly display name
 */
function formatSeriesForDisplay(databaseSeries) {
    if (!databaseSeries) return '';
    
    // The display name should now be provided in the data-display-name attribute
    const element = document.querySelector(`[data-series="${databaseSeries}"]`);
    if (element && element.getAttribute('data-display-name')) {
        return element.getAttribute('data-display-name');
    }
    
    // Fallback to database name if no display name provided
    return databaseSeries;
}

/**
 * Transform series name in DOM elements with the data-series attribute
 * Usage: <span data-series="Chicago 22" data-display-name="Series 22">Loading...</span>
 */
function transformSeriesInDOM() {
    const seriesElements = document.querySelectorAll('[data-series]');
    
    seriesElements.forEach(element => {
        const databaseSeries = element.getAttribute('data-series');
        const displayName = formatSeriesForDisplay(databaseSeries);
        element.textContent = displayName;
    });
}

/**
 * Extract series number from any format for comparison/sorting
 * 
 * @param {string} seriesName - Series name in any format
 * @returns {number} Numeric part for sorting
 */
function extractSeriesNumber(seriesName) {
    if (!seriesName) return 0;
    
    const match = seriesName.match(/(\d+)/);
    return match ? parseInt(match[1]) : 0;
}

/**
 * Check if two series names refer to the same series
 * Now relies on backend matching via data attributes
 * 
 * @param {string} series1 - First series name
 * @param {string} series2 - Second series name
 * @returns {boolean} True if they represent the same series
 */
function seriesMatch(series1, series2) {
    if (!series1 || !series2) return false;
    
    // Check for exact match first
    if (series1 === series2) return true;
    
    // Look for elements with matching database/display names
    const element1 = document.querySelector(`[data-series="${series1}"], [data-display-name="${series1}"]`);
    const element2 = document.querySelector(`[data-series="${series2}"], [data-display-name="${series2}"]`);
    
    if (element1 && element2) {
        const dbName1 = element1.getAttribute('data-series');
        const displayName1 = element1.getAttribute('data-display-name');
        const dbName2 = element2.getAttribute('data-series');
        const displayName2 = element2.getAttribute('data-display-name');
        
        return dbName1 === dbName2 || 
               dbName1 === displayName2 || 
               displayName1 === dbName2 || 
               displayName1 === displayName2;
    }
    
    return false;
}

/**
 * Auto-transform series display on page load
 */
function initSeriesDisplayTransforms() {
    transformSeriesInDOM();
    
    // Set up observer for dynamically added content
    if (window.MutationObserver) {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            const newSeriesElements = node.querySelectorAll('[data-series]');
                            newSeriesElements.forEach(element => {
                                const databaseSeries = element.getAttribute('data-series');
                                const displayName = formatSeriesForDisplay(databaseSeries);
                                element.textContent = displayName;
                            });
                        }
                    });
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSeriesDisplayTransforms);
} else {
    initSeriesDisplayTransforms();
}

// Export for use in other scripts
window.SeriesDisplay = {
    formatSeriesForDisplay,
    transformSeriesInDOM,
    extractSeriesNumber,
    seriesMatch,
    initSeriesDisplayTransforms
}; 