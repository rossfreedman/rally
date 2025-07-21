/**
 * Session Manager - Handle ETL Session Version Changes
 * ===================================================
 * 
 * This module detects when ETL runs have invalidated session data
 * and automatically refreshes user sessions to prevent stale data.
 * 
 * Issue: After ETL runs, users see league selection modal because
 * their browser has stale Flask session data, even though the backend
 * can build correct sessions.
 * 
 * Solution: Check session_version from database and refresh when needed.
 */

class SessionManager {
    constructor() {
        this.lastKnownSessionVersion = null;
        this.lastKnownSeriesCacheVersion = null;
        this.checkInterval = 30000; // Check every 30 seconds
        this.maxRetries = 3;
        this.isChecking = false;
    }

    /**
     * Initialize session version monitoring
     */
    init() {
        console.log('🔄 SessionManager: Initializing session version monitoring...');
        
        // Check immediately on load
        this.checkSessionVersion();
        
        // Set up periodic checking
        setInterval(() => {
            this.checkSessionVersion();
        }, this.checkInterval);
        
        // Check when page regains focus (user returns to tab)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.checkSessionVersion();
            }
        });
        
        console.log('✅ SessionManager: Monitoring started');
    }

    /**
     * Check if session version has changed and refresh if needed
     */
    async checkSessionVersion() {
        if (this.isChecking) return;
        
        this.isChecking = true;
        
        try {
            const response = await fetch('/api/get-session-version', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                console.warn('⚠️ SessionManager: Could not check session version');
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                await this.handleSessionVersionResponse(data);
            }
            
        } catch (error) {
            console.warn('⚠️ SessionManager: Session version check failed:', error);
        } finally {
            this.isChecking = false;
        }
    }

    /**
     * Handle session version response and refresh if needed
     */
    async handleSessionVersionResponse(data) {
        const currentSessionVersion = data.session_version;
        const currentSeriesCacheVersion = data.series_cache_version;
        const lastEtlRun = data.last_etl_run;
        
        // First time initialization
        if (this.lastKnownSessionVersion === null) {
            this.lastKnownSessionVersion = currentSessionVersion;
            this.lastKnownSeriesCacheVersion = currentSeriesCacheVersion;
            console.log(`🔄 SessionManager: Initialized with session version ${currentSessionVersion}`);
            return;
        }
        
        // Check if session version has changed (indicates ETL ran)
        const sessionVersionChanged = currentSessionVersion > this.lastKnownSessionVersion;
        const seriesCacheVersionChanged = currentSeriesCacheVersion > this.lastKnownSeriesCacheVersion;
        
        if (sessionVersionChanged || seriesCacheVersionChanged) {
            console.log(`🚨 SessionManager: ETL detected! Session version ${this.lastKnownSessionVersion} → ${currentSessionVersion}`);
            console.log(`📋 SessionManager: Series cache version ${this.lastKnownSeriesCacheVersion} → ${currentSeriesCacheVersion}`);
            
            if (lastEtlRun) {
                console.log(`⏰ SessionManager: Last ETL run: ${lastEtlRun}`);
            }
            
            // Update our tracking
            this.lastKnownSessionVersion = currentSessionVersion;
            this.lastKnownSeriesCacheVersion = currentSeriesCacheVersion;
            
            // Refresh the user's session
            await this.refreshUserSession();
        }
    }

    /**
     * Refresh user session after ETL
     */
    async refreshUserSession() {
        console.log('🔄 SessionManager: Refreshing user session after ETL...');
        
        try {
            // Call the session refresh endpoint
            const response = await fetch('/api/refresh-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success) {
                    console.log('✅ SessionManager: Session refreshed successfully');
                    
                    // Show user-friendly notification
                    this.showRefreshNotification();
                    
                    // Reload the page after a brief delay to use fresh session
                    setTimeout(() => {
                        console.log('🔄 SessionManager: Reloading page with fresh session...');
                        window.location.reload();
                    }, 2000);
                } else {
                    console.warn('⚠️ SessionManager: Session refresh failed:', data.error);
                }
            } else {
                console.warn('⚠️ SessionManager: Session refresh request failed');
            }
            
        } catch (error) {
            console.error('❌ SessionManager: Error refreshing session:', error);
        }
    }

    /**
     * Show user-friendly notification about session refresh
     */
    showRefreshNotification() {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'session-refresh-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-icon">🔄</div>
                <div class="notification-text">
                    <div class="notification-title">Data Updated</div>
                    <div class="notification-message">Refreshing with latest information...</div>
                </div>
            </div>
        `;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
            padding: 16px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 9999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            max-width: 320px;
            animation: slideInRight 0.3s ease-out;
        `;
        
        // Add animation styles
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            .notification-content {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .notification-icon {
                font-size: 20px;
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            .notification-title {
                font-weight: 600;
                margin-bottom: 2px;
            }
            .notification-message {
                opacity: 0.9;
                font-size: 12px;
            }
        `;
        document.head.appendChild(style);
        
        // Show notification
        document.body.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideInRight 0.3s ease-out reverse';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
}

// Initialize session manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.sessionManager = new SessionManager();
    window.sessionManager.init();
});

// Export for testing/debugging
window.SessionManager = SessionManager; 