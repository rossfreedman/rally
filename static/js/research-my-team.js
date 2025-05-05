// research-my-team.js
// Handles displaying team statistics and analysis for the user's current team (My Team)

let lastTeamPlayers = [];

document.addEventListener('DOMContentLoaded', function() {
    // Load team data when the research-my-team section is shown
    if (document.getElementById('research-my-team-content') && document.getElementById('research-my-team-content').classList.contains('active')) {
        loadMyTeamData();
    }
    
    // Add listener for any navigation that might show this section
    const navTeamItem = document.getElementById('nav-research-my-team');
    if (navTeamItem) {
        navTeamItem.addEventListener('click', function() {
            loadMyTeamData();
        });
    }

    if (document.getElementById('research-my-team-content')) {
        setUserTeamInfoMyTeam();
    }
});

// Main function to load and display team data
async function loadMyTeamData() {
    try {
        // Show loading state
        const teamStatsContainer = document.getElementById('research-my-team-content');
        teamStatsContainer.innerHTML = `
            <div class="content-header">
                <h1>My Team</h1>
                <p class="text-muted">Loading team data...</p>
            </div>
            <div class="d-flex justify-content-center mt-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
        
        // Fetch user's team info from session
        const authResponse = await fetch('/api/check-auth');
        const authData = await authResponse.json();
        
        if (!authData.authenticated) {
            window.location.href = '/login';
            return;
        }
        
        const userClub = authData.user.club;
        const userSeries = authData.user.series;
        const teamId = `${userClub} - ${userSeries.split(' ')[1]}`;
        
        console.log(`Loading my team data for: ${teamId}`);
        
        // Get team stats and match data in parallel
        const [matchesResponse, statsResponse] = await Promise.all([
            fetch('/api/team-matches?team=' + encodeURIComponent(teamId)),
            fetch('/api/research-team?team=' + encodeURIComponent(teamId))
        ]);
        
        // If either request failed, use local data instead
        let matchesData = [];
        let statsData = {};
        
        if (!matchesResponse.ok) {
            console.warn("Could not fetch team matches from API, using local data");
            // Read local data
            matchesData = await loadLocalMatchesDataMyTeam(teamId);
        } else {
            matchesData = await matchesResponse.json();
        }
        
        if (!statsResponse.ok) {
            console.warn("Could not fetch team stats from API, using local data");
            // Read local data
            statsData = await loadLocalStatsDataMyTeam(teamId);
        } else {
            statsData = await statsResponse.json();
        }
        
        // Render team dashboard
        renderMyTeamDashboard(teamId, matchesData, statsData);
        
    } catch (error) {
        console.error("Error loading my team data:", error);
        const teamStatsContainer = document.getElementById('research-my-team-content');
        teamStatsContainer.innerHTML = `
            <div class="content-header">
                <h1>My Team</h1>
                <p class="text-muted">Error loading team data</p>
            </div>
            <div class="alert alert-danger">
                There was an error loading your team data. Please try again later.
            </div>
        `;
    }
}

// Function to load matches data from local files when API fails
async function loadLocalMatchesDataMyTeam(teamId) {
    try {
        const response = await fetch('/data/tennis_matches_20250416.json');
        if (!response.ok) {
            throw new Error('Could not load local matches data');
        }
        
        const allMatches = await response.json();
        
        // Filter matches for the user's team
        return allMatches.filter(match => 
            match["Home Team"] === teamId || match["Away Team"] === teamId
        );
    } catch (error) {
        console.error("Error loading local matches data:", error);
        return [];
    }
}

// Function to load stats data from local files when API fails
async function loadLocalStatsDataMyTeam(teamId) {
    try {
        const response = await fetch('/data/Chicago_22_stats_20250425.json');
        if (!response.ok) {
            throw new Error('Could not load local stats data');
        }
        
        const allStats = await response.json();
        
        // Find stats for the user's team
        const teamStats = allStats.find(team => team.team === teamId);
        return teamStats || {};
    } catch (error) {
        console.error("Error loading local stats data:", error);
        return {};
    }
}

// Render the team dashboard with all components
function renderMyTeamDashboard(teamId, matchesData, statsData) {
    const container = document.getElementById('research-my-team-content');
    
    // Extract team name from teamId
    const teamName = teamId.split(' - ')[0];
    
    // Create team win/loss analysis
    const teamRecord = statsData.matches || { won: 0, lost: 0, percentage: "0%" };
    const teamSets = statsData.sets || { won: 0, lost: 0, percentage: "0%" };
    const teamGames = statsData.games || { won: 0, lost: 0, percentage: "0%" };
    
    // Calculate court-specific stats
    const courtStats = calculateCourtStats(matchesData, teamId);
    
    // Calculate player performance
    const playerStats = calculatePlayerStats(matchesData, teamId);
    
    // Calculate upcoming matches
    const upcomingMatches = getUpcomingMatches(matchesData, teamId);
    
    // Assemble the HTML for the dashboard
    container.innerHTML = `
        <div class="content-header">
            <h1>${teamName} Team Analysis</h1>
            <p class="text-muted">Comprehensive statistics and performance analysis for your team</p>
        </div>
        
        <!-- Team Overview Cards -->
        <div class="row mb-4">
            <!-- Team Record Card -->
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-trophy me-2"></i>Team Record</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                            <h2 class="display-4 mb-0 fw-bold">${teamRecord.percentage}</h2>
                            <p class="text-muted mb-2">Win Rate</p>
                            <h4>${teamRecord.won}-${teamRecord.lost}</h4>
                            <p>Match Record</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Points Card -->
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-star me-2"></i>Team Points</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                            <h2 class="display-4 mb-0 fw-bold">${statsData.points || 0}</h2>
                            <p class="text-muted mb-2">Total Points</p>
                            <div class="progress w-100 mt-2" style="height: 10px;">
                                <div class="progress-bar progress-bar-striped bg-success" 
                                     role="progressbar" 
                                     style="width: ${teamGames.percentage}%"
                                     aria-valuenow="${teamGames.percentage.replace('%', '')}" 
                                     aria-valuemin="0" 
                                     aria-valuemax="100"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Court Stats Card -->
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-map-marked-alt me-2"></i>Court Stats</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                            <h2 class="display-4 mb-0 fw-bold">${courtStats.percentage}</h2>
                            <p class="text-muted mb-2">Win Rate</p>
                            <div class="progress w-100 mt-2" style="height: 10px;">
                                <div class="progress-bar progress-bar-striped bg-success" 
                                     role="progressbar" 
                                     style="width: ${courtStats.percentage}%"
                                     aria-valuenow="${courtStats.percentage.replace('%', '')}" 
                                     aria-valuemin="0" 
                                     aria-valuemax="100"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Player Stats Card -->
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-user-friends me-2"></i>Player Stats</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                            <h2 class="display-4 mb-0 fw-bold">${playerStats.percentage}</h2>
                            <p class="text-muted mb-2">Win Rate</p>
                            <div class="progress w-100 mt-2" style="height: 10px;">
                                <div class="progress-bar progress-bar-striped bg-success" 
                                     role="progressbar" 
                                     style="width: ${playerStats.percentage}%"
                                     aria-valuenow="${playerStats.percentage.replace('%', '')}" 
                                     aria-valuemin="0" 
                                     aria-valuemax="100"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Upcoming Matches -->
        <div class="row mb-4">
            <div class="col-md-12">
                <h2 class="mb-4">Upcoming Matches</h2>
                <div class="table-responsive">
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Opponent</th>
                                <th>Court</th>
                                <th>Result</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${upcomingMatches.map(match => `
                                <tr>
                                    <td>${match.date}</td>
                                    <td>${match.opponent}</td>
                                    <td>${match.court}</td>
                                    <td>${match.result}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

async function populatePlayerPicklist(teamId) {
    const playerSelect = document.getElementById('playerSelect');
    playerSelect.innerHTML = '<option value="">Choose a player...</option>';
    playerSelect.disabled = true;
    document.getElementById('playerStats').innerHTML = '';
    if (!teamId) return;
    try {
        const resp = await fetch(`/api/team-players/${encodeURIComponent(teamId)}`);
        const data = await resp.json();
        if (data.players && data.players.length > 0) {
            lastTeamPlayers = data.players; // Store for later use
            // Sort players by matches played (descending) and then alphabetically
            data.players.sort((a, b) => b.matches - a.matches || a.name.localeCompare(b.name));
            data.players.forEach(player => {
                const option = document.createElement('option');
                option.value = player.name;
                option.textContent = `${player.name} (${player.winRate}%)`;
                playerSelect.appendChild(option);
            });
            playerSelect.disabled = false;
        } else {
            lastTeamPlayers = [];
            playerSelect.innerHTML = '<option value="">No players found</option>';
        }
    } catch (e) {
        lastTeamPlayers = [];
        playerSelect.innerHTML = '<option value="">Error loading players</option>';
    }
}

async function showPlayerStats(playerName) {
    const statsDiv = document.getElementById('playerStats');
    const detailsCard = document.getElementById('playerDetailsCard');
    const detailsBody = document.getElementById('playerDetailsBody');
    statsDiv.innerHTML = '<div class="text-center my-4">Loading player stats...</div>';
    detailsCard.style.display = 'none';
    if (!playerName) {
        statsDiv.innerHTML = '';
        detailsCard.style.display = 'none';
        return;
    }
    // Find the player in lastTeamPlayers (which includes courts)
    const player = lastTeamPlayers.find(p => p.name && p.name.trim().toLowerCase() === playerName.trim().toLowerCase());
    console.log('Selected player (from team-players):', player);
    if (!player) {
        statsDiv.innerHTML = '<div class="alert alert-warning">No stats found for this player.</div>';
        detailsCard.style.display = 'none';
        return;
    }
    console.log('Player courts:', player.courts);
    // Show overall stats (use player object from team-players, which has matches, wins, losses, winRate, pti)
    const totalMatches = player.matches ?? 0;
    const wins = player.wins ?? 0;
    const losses = totalMatches - wins;
    const winRate = player.winRate ?? 0;
    const pti = player.pti ?? player.rating ?? 'N/A';
    let html = `<div class='player-analysis'>
        <div class='overall-stats mb-4'>
            <h6>Overall Performance</h6>
            <p><span class='stat-label'>Total Matches</span><span class='stat-value'>${totalMatches}</span></p>
            <p><span class='stat-label'>Overall Record</span><span class='stat-value'>${wins}-${losses}</span></p>
            <p><span class='stat-label'>Win Rate</span><span class='stat-value'>${winRate}%</span></p>
            <p><span class='stat-label'>PTI</span><span class='stat-value'>${pti}</span></p>
        </div>
    </div>`;
    statsDiv.innerHTML = html;
    // --- Court breakdown cards ---
    let courtHtml = `<div class='row g-3'>`;
    if (player.courts) {
        Object.entries(player.courts).forEach(([court, stats]) => {
            const courtNum = court.replace('court', 'Court ');
            // Skip rendering if courtNum is 'Unknown' or matches the unwanted card
            if (courtNum === 'Unknown' || (stats.matches === 35 && stats.wins === 0 && stats.winRate === 0)) return;
            function winRateClass(rate) {
                if (rate >= 60) return 'win-rate-high';
                if (rate >= 40) return 'win-rate-medium';
                return 'win-rate-low';
            }
            courtHtml += `<div class='col-md-6'>
                <div class='court-card card h-100'>
                    <div class='card-body'>
                        <h6>${courtNum}</h6>
                        <p><span class='stat-label'>Matches</span><span class='stat-value'>${stats.matches}</span></p>
                        <p><span class='stat-label'>Record</span><span class='stat-value'>${stats.wins}-${stats.matches - stats.wins}</span></p>
                        <p><span class='stat-label'>Win Rate</span><span class='stat-value ${winRateClass(stats.winRate)}'>${stats.winRate}%</span></p>`;
            if (stats.partners && stats.partners.length > 0) {
                courtHtml += `<div class='partner-info mt-2'>
                    <strong>Most Common Partners:</strong>
                    <ul class='partner-list'>`;
                stats.partners.forEach(ptn => {
                    const partnerLosses = ptn.matches - ptn.wins;
                    courtHtml += `<li>${ptn.name} (${ptn.wins}-${partnerLosses}, ${ptn.winRate}%)</li>`;
                });
                courtHtml += `</ul></div>`;
            }
            courtHtml += `</div></div></div>`;
        });
    }
    courtHtml += `</div>`;
    // Insert courtHtml after the overall stats in detailsHtml:
    let detailsHtml = `<div class='player-analysis'>
        <div class='overall-stats mb-4'>
            <h6>Player Details</h6>
            <p><span class='stat-label'>Name</span><span class='stat-value'>${player.name}</span></p>
            <p><span class='stat-label'>Total Matches</span><span class='stat-value'>${totalMatches}</span></p>
            <p><span class='stat-label'>Record</span><span class='stat-value'>${wins}-${losses}</span></p>
            <p><span class='stat-label'>Win Rate</span><span class='stat-value'>${winRate}%</span></p>
            <p><span class='stat-label'>PTI</span><span class='stat-value'>${pti}</span></p>
        </div>
        ${courtHtml}
    </div>`;
    console.log('Inserted details HTML:', detailsHtml);
    detailsBody.innerHTML = detailsHtml;
    detailsCard.style.display = '';
} 