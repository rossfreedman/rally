// Click tracking functionality - DISABLED
(function() {
    // Create a disabled version of the activity tracker that still allows HTMX to work
    window.activityTrackerReady = Promise.resolve();
    window.clickTrackingInitialized = true;
    window.trackClick = function() {
        // No-op function when tracking is disabled
        console.debug('Click tracking is disabled');
    };

    // Add HTMX event listeners to handle transitions
    document.addEventListener('htmx:configRequest', function(evt) {
        // Let HTMX handle its own requests
        evt.detail.headers['X-Requested-With'] = 'XMLHttpRequest';
    });
    
    console.log('Activity tracking is disabled, HTMX support enabled');
})(); 