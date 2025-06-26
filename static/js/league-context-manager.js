/**
 * Rally League Context Manager
 * ===========================
 * 
 * Provides consistent league context switching and page refresh functionality
 * across all pages in the Rally application.
 * 
 * Features:
 * - Auto-refresh pages when returning after league switching
 * - Consistent league switching behavior
 * - Debug logging for troubleshooting
 * - Graceful error handling
 */

class LeagueContextManager {
    constructor() {
        this.debugMode = false; // Set to true for debug logging
        this.refreshDelay = 500; // Delay before refreshing (ms)
        this.lastLeagueSwitch = null; // Track when last switch occurred
        
        this.init();
    }
    
    init() {
        this.log('🎯 League Context Manager initialized');
        this.setupAutoRefresh();
        this.setupLeagueSwitchDetection();
    }
    
    /**
     * Setup auto-refresh functionality for pages when they become visible
     * This handles back navigation after league switching
     */
    setupAutoRefresh() {
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.log('🔄 Page became visible - checking if refresh needed');
                this.checkAndRefreshIfNeeded();
            }
        });
        
        window.addEventListener('focus', () => {
            this.log('🔄 Window got focus - checking if refresh needed');
            this.checkAndRefreshIfNeeded();
        });
    }
    
    /**
     * Detect when league switching occurs to mark pages for refresh
     */
    setupLeagueSwitchDetection() {
        // Listen for successful league switches
        document.addEventListener('league-switched', (event) => {
            this.log('📡 League switch detected:', event.detail);
            this.lastLeagueSwitch = Date.now();
            localStorage.setItem('rally_last_league_switch', this.lastLeagueSwitch);
        });
        
        // Check if there was a recent league switch when page loads
        const storedSwitchTime = localStorage.getItem('rally_last_league_switch');
        if (storedSwitchTime) {
            this.lastLeagueSwitch = parseInt(storedSwitchTime);
        }
    }
    
    /**
     * Check if page needs refresh due to recent league switch
     */
    checkAndRefreshIfNeeded() {
        const now = Date.now();
        const switchThreshold = 10000; // 10 seconds
        
        if (this.lastLeagueSwitch && (now - this.lastLeagueSwitch) < switchThreshold) {
            this.log('🔄 Recent league switch detected - refreshing page');
            setTimeout(() => {
                window.location.reload();
            }, this.refreshDelay);
        }
    }
    
    /**
     * Enhanced league switching with proper event handling
     */
    switchLeague(leagueId) {
        this.log(`🔄 Switching to league: ${leagueId}`);
        
        // Mark switch time
        this.lastLeagueSwitch = Date.now();
        localStorage.setItem('rally_last_league_switch', this.lastLeagueSwitch);
        
        // Update UI to show loading
        this.updateUIForSwitch();
        
        return fetch('/api/switch-league', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                league_id: leagueId
            })
        })
        .then(response => {
            this.log(`📡 Switch API Response status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            this.log(`📊 Switch API Response data:`, data);
            
            if (data.success) {
                this.log(`✅ Successfully switched to ${data.user.league_name}`);
                
                // Dispatch custom event for other components
                document.dispatchEvent(new CustomEvent('league-switched', {
                    detail: { 
                        leagueId: leagueId, 
                        leagueName: data.user.league_name,
                        timestamp: Date.now()
                    }
                }));
                
                // Show success briefly then reload
                this.showSwitchSuccess(data.user.league_name);
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
                
                return data;
            } else {
                throw new Error(data.error || 'League switch failed');
            }
        })
        .catch(error => {
            this.log('❌ League switch error:', error);
            this.showSwitchError(error.message);
            this.resetUIAfterSwitch();
            throw error;
        });
    }
    
    /**
     * Update UI elements during league switch
     */
    updateUIForSwitch() {
        // Disable league buttons
        const leagueButtons = document.querySelectorAll('.league-switch-btn');
        leagueButtons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.5';
        });
        
        // Update trigger button if it exists
        const trigger = document.getElementById('leagueSwitcherTrigger');
        if (trigger) {
            trigger.innerHTML = '<i class="fas fa-spinner fa-spin text-xs"></i>';
            trigger.disabled = true;
        }
    }
    
    /**
     * Reset UI elements after switch
     */
    resetUIAfterSwitch() {
        const leagueButtons = document.querySelectorAll('.league-switch-btn');
        leagueButtons.forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = '1';
        });
        
        const trigger = document.getElementById('leagueSwitcherTrigger');
        if (trigger) {
            trigger.disabled = false;
            trigger.innerHTML = '<i class="fas fa-edit text-sm"></i>';
        }
    }
    
    /**
     * Show success message
     */
    showSwitchSuccess(leagueName) {
        const trigger = document.getElementById('leagueSwitcherTrigger');
        if (trigger) {
            trigger.innerHTML = '<i class="fas fa-check text-xs text-green-400"></i>';
        }
        
        // Show toast if available
        if (window.showToast) {
            window.showToast(`Switched to ${leagueName}`, 'success');
        }
    }
    
    /**
     * Show error message
     */
    showSwitchError(errorMessage) {
        if (window.showToast) {
            window.showToast(`League switch failed: ${errorMessage}`, 'error');
        } else {
            alert(`Failed to switch leagues: ${errorMessage}`);
        }
    }
    
    /**
     * Debug logging helper
     */
    log(...args) {
        if (this.debugMode || window.location.hostname === 'localhost') {
            console.log('[LeagueContextManager]', ...args);
        }
    }
    
    /**
     * Clean up old switch timestamps
     */
    cleanup() {
        const now = Date.now();
        const maxAge = 24 * 60 * 60 * 1000; // 24 hours
        
        if (this.lastLeagueSwitch && (now - this.lastLeagueSwitch) > maxAge) {
            localStorage.removeItem('rally_last_league_switch');
            this.lastLeagueSwitch = null;
        }
    }
}

// Initialize global instance
window.leagueContextManager = new LeagueContextManager();

// Enhanced global switchLeague function that uses the manager
window.switchLeague = function(leagueId) {
    return window.leagueContextManager.switchLeague(leagueId);
};

// Cleanup old data on page load
window.addEventListener('load', () => {
    window.leagueContextManager.cleanup();
});

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LeagueContextManager;
} 