/**
 * Enhanced League & Team Context Manager
 * =====================================
 * 
 * Extends the existing league context switching to also support team switching
 * for users who belong to multiple teams in the same league (like Rob Werman).
 * 
 * Features:
 * - Seamless league and team switching
 * - Works with existing league_context system
 * - Auto-detects when team selector is needed
 * - Maintains backwards compatibility
 * - Unified UI for both league and team selection
 */

class EnhancedLeagueTeamContextManager extends LeagueContextManager {
    constructor() {
        super();
        this.currentUserTeams = [];
        this.currentTeamInfo = null;
        this.isTeamSwitchingEnabled = false;
        
        this.initTeamSwitching();
    }
    
    /**
     * Initialize team switching functionality
     */
    initTeamSwitching() {
        this.log('🎯 Initializing enhanced league + team context manager');
        this.loadUserTeamsData();
        this.setupTeamSwitchDetection();
    }
    
    /**
     * Load user's team data to determine if team switching is needed
     */
    async loadUserTeamsData() {
        try {
            const response = await fetch('/api/get-user-teams-in-current-league');
            const data = await response.json();
            
            if (data.success) {
                this.currentUserTeams = data.teams || [];
                // Find current team from teams list (new API doesn't return current_team separately)
                this.currentTeamInfo = this.currentUserTeams.find(team => team.is_current) || null;
                this.isTeamSwitchingEnabled = this.currentUserTeams.length > 1;
                
                this.log(`📊 User teams loaded: ${this.currentUserTeams.length} teams, switching ${this.isTeamSwitchingEnabled ? 'enabled' : 'disabled'}`);
                
                // Update UI to show team options if needed
                this.updateContextSelectorUI();
            }
        } catch (error) {
            this.log('❌ Error loading user teams:', error);
            // Graceful fallback - disable team switching
            this.isTeamSwitchingEnabled = false;
        }
    }
    
    /**
     * Setup team switch detection
     */
    setupTeamSwitchDetection() {
        // Listen for successful team switches
        document.addEventListener('team-switched', (event) => {
            this.log('📡 Team switch detected:', event.detail);
            this.lastLeagueSwitch = Date.now(); // Use same refresh mechanism
            localStorage.setItem('rally_last_context_switch', this.lastLeagueSwitch);
        });
    }
    
    /**
     * Enhanced league switching that also handles team context
     */
    async switchLeague(leagueId) {
        this.log(`🔄 Enhanced switching to league: ${leagueId}`);
        
        // Use parent class for league switching
        try {
            const result = await super.switchLeague(leagueId);
            
            // After successful league switch, reload team data
            await this.loadUserTeamsData();
            
            return result;
        } catch (error) {
            this.log('❌ Enhanced league switch error:', error);
            throw error;
        }
    }
    
    /**
     * Team switching functionality
     */
    async switchTeam(teamId, teamName) {
        this.log(`🔄 Switching to team: ${teamId} (${teamName})`);
        
        // Mark switch time
        this.lastLeagueSwitch = Date.now();
        localStorage.setItem('rally_last_context_switch', this.lastLeagueSwitch);
        
        // Update UI to show loading
        this.updateUIForTeamSwitch(teamName);
        
        try {
            const response = await fetch('/api/switch-team-context', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    team_id: teamId
                })
            });
            
            const data = await response.json();
            this.log(`📡 Team switch API Response:`, data);
            
            if (data.success) {
                this.log(`✅ Successfully switched to ${teamName}`);
                
                // Dispatch custom event for other components
                document.dispatchEvent(new CustomEvent('team-switched', {
                    detail: { 
                        teamId: teamId, 
                        teamName: teamName,
                        leagueId: data.league_id,
                        timestamp: Date.now()
                    }
                }));
                
                // Show success briefly then reload
                this.showSwitchSuccess(teamName);
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
                
                return data;
            } else {
                throw new Error(data.error || 'Team switch failed');
            }
        } catch (error) {
            this.log('❌ Team switch error:', error);
            this.showSwitchError(error.message);
            this.resetUIAfterSwitch();
            throw error;
        }
    }
    
    /**
     * Update UI elements during team switch
     */
    updateUIForTeamSwitch(teamName) {
        // Disable team buttons
        const teamButtons = document.querySelectorAll('.team-switch-btn');
        teamButtons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.5';
        });
        
        // Update trigger button if it exists
        const trigger = document.getElementById('leagueSwitcherTrigger');
        if (trigger) {
            trigger.innerHTML = `<i class="fas fa-spinner fa-spin text-xs mr-1"></i><span class="text-xs">Switching to ${teamName}...</span>`;
            trigger.disabled = true;
        }
        
        // Also call parent method for league buttons
        this.updateUIForSwitch();
    }
    
    /**
     * Update the context selector UI to include team options
     * DISABLED: Keep league and team switching separate for simplicity
     */
    updateContextSelectorUI() {
        // DISABLED: Don't add team options to league modal
        // League modal should only show leagues, team modal should only show teams
        return;
    }
    
    /**
     * Add team selector section to the league modal
     */
    addTeamSelectorToModal(modal, teams) {
        // Check if team section already exists
        let teamSection = modal.querySelector('#teamSelectorSection');
        
        if (!teamSection) {
            // Create team section
            teamSection = document.createElement('div');
            teamSection.id = 'teamSelectorSection';
            teamSection.className = 'p-4 bg-blue-50 border-t border-blue-100';
            
            // Insert before the existing league options
            const leagueSection = modal.querySelector('.bg-gray-50');
            if (leagueSection) {
                leagueSection.parentNode.insertBefore(teamSection, leagueSection);
            }
        }
        
        teamSection.innerHTML = `
            <div class="text-sm font-bold text-blue-800 mb-3 uppercase tracking-wide">
                <i class="fas fa-users mr-1"></i>
                Switch Team (Current League)
            </div>
            <div class="space-y-2">
                ${teams.map(team => `
                    <button onclick="window.enhancedContextManager.switchTeam(${team.team_id}, '${team.team_name}')" 
                            class="team-switch-btn w-full flex items-center justify-between p-3 rounded-lg bg-white hover:bg-blue-50 transition-all duration-200 border-2 border-blue-200 hover:border-blue-400 hover:shadow-md group
                                   ${this.isCurrentTeam(team) ? 'bg-blue-100 border-blue-400' : ''}">
                        <div class="text-left">
                            <div class="font-medium text-blue-900 group-hover:text-blue-900">${team.team_name}</div>
                            <div class="text-xs text-blue-700 group-hover:text-blue-700">${team.club_name} • ${team.series_name}</div>
                        </div>
                        <div class="text-xs ${this.isCurrentTeam(team) ? 'bg-blue-600 text-white px-2 py-1 rounded' : 'bg-blue-500 group-hover:bg-blue-600 text-white px-2 py-1 rounded'}">
                            ${this.isCurrentTeam(team) ? 'Current' : 'Switch'}
                        </div>
                    </button>
                `).join('')}
            </div>
        `;
    }
    
    /**
     * Check if a team is the current team
     */
    isCurrentTeam(team) {
        // Use is_current flag from the API response
        return team.is_current === true;
    }
    
    /**
     * Get current league ID from session data
     */
    getCurrentLeagueId() {
        // Try to get from window session data or DOM
        if (window.sessionData && window.sessionData.user && window.sessionData.user.league_id) {
            return window.sessionData.user.league_id;
        }
        
        // Fallback to checking DOM elements
        const leagueDisplay = document.querySelector('#userLeagueDisplay');
        if (leagueDisplay) {
            const text = leagueDisplay.textContent;
            if (text.includes('APTA Chicago')) return 'APTA_CHICAGO';
            if (text.includes('North Shore Tennis')) return 'NSTF';

    
        }
        
        return null;
    }
    
    /**
     * Enhanced show success message for team switches
     */
    showTeamSwitchSuccess(teamName) {
        const trigger = document.getElementById('leagueSwitcherTrigger');
        if (trigger) {
            trigger.innerHTML = `<i class="fas fa-check text-xs text-green-400 mr-1"></i><span class="text-xs">Switched to ${teamName}</span>`;
        }
        
        // Show toast if available
        if (window.showToast) {
            window.showToast(`Switched to team: ${teamName}`, 'success');
        }
    }
    
    /**
     * Enhanced cleanup method
     */
    cleanup() {
        super.cleanup();
        
        const now = Date.now();
        const maxAge = 24 * 60 * 60 * 1000; // 24 hours
        
        const lastContextSwitch = localStorage.getItem('rally_last_context_switch');
        if (lastContextSwitch && (now - parseInt(lastContextSwitch)) > maxAge) {
            localStorage.removeItem('rally_last_context_switch');
        }
    }
}

// Create API endpoint for getting user teams
window.createUserTeamsAPI = function() {
    // This would be added to the backend, but for now we'll simulate it
    // by using existing session data and user associations
    
    return {
        success: true,
        teams: window.userTeams || [],
        current_team: window.currentTeamInfo || null
    };
};

// DISABLED: Enhanced manager complicates the UI - keep league and team switching separate
document.addEventListener('DOMContentLoaded', function() {
    // DISABLED: Don't initialize enhanced manager to keep simple separation
    // League switching and team switching should be completely separate
    return;
    
    /*
    // Check if user has multiple teams before initializing enhanced manager
    fetch('/api/get-user-teams-in-current-league').then(response => response.json()).then(data => {
        if (data.success && data.teams && data.has_multiple_teams) {
            // Replace the simple league context manager with enhanced version
            window.enhancedContextManager = new EnhancedLeagueTeamContextManager();
            
            // Override global switchLeague function
            window.switchLeague = function(leagueId) {
                return window.enhancedContextManager.switchLeague(leagueId);
            };
            
            console.log('🎯 Enhanced League + Team Context Manager activated');
        } else {
            // Use simple league manager for single-team users
            console.log('🎯 Simple League Context Manager (single team user)');
        }
    }).catch(error => {
        console.log('🎯 Fallback to Simple League Context Manager');
    });
});

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnhancedLeagueTeamContextManager;
} 