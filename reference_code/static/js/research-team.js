// research-team.js
// Handles displaying team statistics and analysis for the user's current team

document.addEventListener('DOMContentLoaded', function() {
    // Load team data when the research-team section is shown
    if (document.getElementById('research-team-content').classList.contains('active')) {
        loadTeamData();
    }
    
    // Add listener for any navigation that might show this section
    const navTeamItem = document.getElementById('nav-research-team');
    if (navTeamItem) {
        navTeamItem.addEventListener('click', function() {
            loadTeamData();
        });
    }

    if (document.getElementById('research-team-content')) {
        setUserTeamInfo();
    }
});

// Main function to load and display team data
async function loadTeamData() {
    try {
        // Show loading state
        const teamStatsContainer = document.getElementById('research-team-content');
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
        
        console.log(`Loading team data for: ${teamId}`);
        
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
            matchesData = await loadLocalMatchesData(teamId);
        } else {
            matchesData = await matchesResponse.json();
        }
        
        if (!statsResponse.ok) {
            console.warn("Could not fetch team stats from API, using local data");
            // Read local data
            statsData = await loadLocalStatsData(teamId);
        } else {
            statsData = await statsResponse.json();
        }
        
        // Render team dashboard
        renderTeamDashboard(teamId, matchesData, statsData);
        
    } catch (error) {
        console.error("Error loading team data:", error);
        const teamStatsContainer = document.getElementById('research-team-content');
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
async function loadLocalMatchesData(teamId) {
    try {
        const response = await fetch('/data/match_history.json');
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
async function loadLocalStatsData(teamId) {
    try {
        const response = await fetch('/data/series_stats.json');
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
function renderTeamDashboard(teamId, matchesData, statsData) {
    const container = document.getElementById('research-team-content');
    
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
                                     aria-valuemax="100">
                                </div>
                            </div>
                            <p class="mt-2">${teamGames.percentage} of games won</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Set Performance Card -->
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-chart-line me-2"></i>Set Performance</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                            <h2 class="display-4 mb-0 fw-bold">${teamSets.percentage}</h2>
                            <p class="text-muted mb-2">Set Win Rate</p>
                            <h4>${teamSets.won}-${teamSets.lost}</h4>
                            <p>Set Record</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Line Performance Card -->
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-users me-2"></i>Line Performance</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                            <h2 class="display-4 mb-0 fw-bold">${statsData.lines?.percentage || "0%"}</h2>
                            <p class="text-muted mb-2">Line Win Rate</p>
                            <h4>${statsData.lines?.won || 0}-${statsData.lines?.lost || 0}</h4>
                            <p>Line Record</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Court Analysis Cards -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-table-tennis me-2"></i>Court Analysis</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            ${generateCourtCards(courtStats)}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Top Players Card -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-medal me-2"></i>Top Players</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>Player</th>
                                        <th class="text-center">Matches</th>
                                        <th class="text-center">Win Rate</th>
                                        <th class="text-center">Best Court</th>
                                        <th class="text-center">Best Partner</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${generatePlayerRows(playerStats)}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Upcoming Matches Card -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-calendar-alt me-2"></i>Upcoming Matches</h5>
                    </div>
                    <div class="card-body">
                        ${generateUpcomingMatchesHTML(upcomingMatches)}
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Calculate court-specific statistics
function calculateCourtStats(matches, teamId) {
    const courts = {
        "Court 1": { wins: 0, losses: 0, winRate: 0, topPlayers: [] },
        "Court 2": { wins: 0, losses: 0, winRate: 0, topPlayers: [] },
        "Court 3": { wins: 0, losses: 0, winRate: 0, topPlayers: [] },
        "Court 4": { wins: 0, losses: 0, winRate: 0, topPlayers: [] }
    };
    
    // Player performance by court
    const playerCourtPerformance = {};
    
    // Process each match
    matches.forEach(match => {
        const isHome = match["Home Team"] === teamId;
        const teamPlayers = isHome ? 
            [match["Home Player 1"], match["Home Player 2"]] : 
            [match["Away Player 1"], match["Away Player 2"]];
        
        // Determine if we won this match
        const winnerIsHome = match["Winner"] === "home";
        const teamWon = (isHome && winnerIsHome) || (!isHome && !winnerIsHome);
        
        // Figure out which court based on position in the match list
        // This is an approximation since the data doesn't explicitly label courts
        const courtIndex = matches.indexOf(match) % 4;
        const courtName = `Court ${courtIndex + 1}`;
        
        // Update court statistics
        if (teamWon) {
            courts[courtName].wins++;
        } else {
            courts[courtName].losses++;
        }
        
        // Update player-court statistics
        teamPlayers.forEach(player => {
            if (!player) return; // Skip if player is undefined
            
            if (!playerCourtPerformance[player]) {
                playerCourtPerformance[player] = {};
            }
            
            if (!playerCourtPerformance[player][courtName]) {
                playerCourtPerformance[player][courtName] = { matches: 0, wins: 0 };
            }
            
            playerCourtPerformance[player][courtName].matches++;
            if (teamWon) {
                playerCourtPerformance[player][courtName].wins++;
            }
        });
    });
    
    // Calculate win rates and top players for each court
    Object.keys(courts).forEach(courtName => {
        const court = courts[courtName];
        const totalMatches = court.wins + court.losses;
        court.winRate = totalMatches > 0 ? Math.round((court.wins / totalMatches) * 100) : 0;
        
        // Find top performers on this court
        const courtPlayers = [];
        Object.keys(playerCourtPerformance).forEach(player => {
            const performance = playerCourtPerformance[player][courtName];
            if (performance && performance.matches >= 2) {
                const winRate = Math.round((performance.wins / performance.matches) * 100);
                courtPlayers.push({
                    name: player,
                    matches: performance.matches,
                    wins: performance.wins,
                    winRate: winRate
                });
            }
        });
        
        // Sort by win rate and take top 2
        courtPlayers.sort((a, b) => b.winRate - a.winRate);
        court.topPlayers = courtPlayers.slice(0, 2);
    });
    
    return courts;
}

// Calculate player statistics
function calculatePlayerStats(matches, teamId) {
    // Player stats
    const players = {};
    
    // Partnership stats
    const partnerships = {};
    
    // Process each match
    matches.forEach(match => {
        const isHome = match["Home Team"] === teamId;
        
        // Player names
        const player1 = isHome ? match["Home Player 1"] : match["Away Player 1"];
        const player2 = isHome ? match["Home Player 2"] : match["Away Player 2"];
        
        if (!player1 || !player2) return; // Skip if missing player data
        
        // Determine if team won
        const winnerIsHome = match["Winner"] === "home";
        const teamWon = (isHome && winnerIsHome) || (!isHome && !winnerIsHome);
        
        // Figure out which court based on position in the match list
        const courtIndex = matches.indexOf(match) % 4;
        const courtName = `Court ${courtIndex + 1}`;
        
        // Update player stats
        [player1, player2].forEach(player => {
            if (!players[player]) {
                players[player] = {
                    matches: 0,
                    wins: 0,
                    courts: {},
                    partners: {}
                };
            }
            
            players[player].matches++;
            if (teamWon) players[player].wins++;
            
            // Update court stats
            if (!players[player].courts[courtName]) {
                players[player].courts[courtName] = { matches: 0, wins: 0 };
            }
            players[player].courts[courtName].matches++;
            if (teamWon) players[player].courts[courtName].wins++;
            
            // Update partner stats
            const partner = player === player1 ? player2 : player1;
            if (!players[player].partners[partner]) {
                players[player].partners[partner] = { matches: 0, wins: 0 };
            }
            players[player].partners[partner].matches++;
            if (teamWon) players[player].partners[partner].wins++;
        });
        
        // Track partnership stats
        const partnershipKey = [player1, player2].sort().join('/');
        if (!partnerships[partnershipKey]) {
            partnerships[partnershipKey] = {
                player1: player1,
                player2: player2,
                matches: 0,
                wins: 0,
                courts: {}
            };
        }
        
        partnerships[partnershipKey].matches++;
        if (teamWon) partnerships[partnershipKey].wins++;
        
        if (!partnerships[partnershipKey].courts[courtName]) {
            partnerships[partnershipKey].courts[courtName] = { matches: 0, wins: 0 };
        }
        partnerships[partnershipKey].courts[courtName].matches++;
        if (teamWon) partnerships[partnershipKey].courts[courtName].wins++;
    });
    
    // Calculate derived stats
    Object.keys(players).forEach(playerName => {
        const player = players[playerName];
        
        // Calculate win rate
        player.winRate = player.matches > 0 ? Math.round((player.wins / player.matches) * 100) : 0;
        
        // Find best court
        let bestCourt = null;
        let bestCourtWinRate = 0;
        Object.keys(player.courts).forEach(courtName => {
            const court = player.courts[courtName];
            if (court.matches >= 2) {
                const courtWinRate = Math.round((court.wins / court.matches) * 100);
                if (courtWinRate > bestCourtWinRate) {
                    bestCourtWinRate = courtWinRate;
                    bestCourt = {
                        name: courtName,
                        matches: court.matches,
                        wins: court.wins,
                        winRate: courtWinRate
                    };
                }
            }
        });
        player.bestCourt = bestCourt;
        
        // Find best partner
        let bestPartner = null;
        let bestPartnerWinRate = 0;
        Object.keys(player.partners).forEach(partnerName => {
            const partner = player.partners[partnerName];
            if (partner.matches >= 2) {
                const partnerWinRate = Math.round((partner.wins / partner.matches) * 100);
                if (partnerWinRate > bestPartnerWinRate) {
                    bestPartnerWinRate = partnerWinRate;
                    bestPartner = {
                        name: partnerName,
                        matches: partner.matches,
                        wins: partner.wins,
                        winRate: partnerWinRate
                    };
                }
            }
        });
        player.bestPartner = bestPartner;
    });
    
    return players;
}

// Get upcoming matches
function getUpcomingMatches(matches, teamId) {
    // Sort matches by date
    const sortedMatches = [...matches].sort((a, b) => {
        const dateA = new Date(a["Date"].split('-').reverse().join('-'));
        const dateB = new Date(b["Date"].split('-').reverse().join('-'));
        return dateA - dateB;
    });
    
    // Get current date
    const currentDate = new Date();
    
    // Filter for upcoming matches
    return sortedMatches.filter(match => {
        const matchDate = new Date(match["Date"].split('-').reverse().join('-'));
        return matchDate >= currentDate;
    }).slice(0, 3); // Get next 3 matches
}

// Generate HTML for court cards
function generateCourtCards(courtStats) {
    return Object.keys(courtStats).map(courtName => {
        const court = courtStats[courtName];
        const winRateClass = court.winRate >= 70 ? 'text-success' :
                            court.winRate >= 50 ? 'text-primary' :
                            court.winRate >= 30 ? 'text-warning' : 'text-danger';
        
        return `
            <div class="col-md-6 col-lg-3 mb-3">
                <div class="card h-100">
                    <div class="card-header bg-light">
                        <h6 class="mb-0">${courtName}</h6>
                    </div>
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <h3 class="${winRateClass}">${court.winRate}%</h3>
                            <p class="text-muted mb-0">Win Rate</p>
                        </div>
                        <p class="mb-1">Record: ${court.wins}-${court.losses}</p>
                        <p class="mb-2">Top Players:</p>
                        <ul class="list-unstyled">
                            ${court.topPlayers.map(player => 
                                `<li>
                                    ${player.name} 
                                    <span class="badge bg-secondary">${player.winRate}% (${player.wins}-${player.matches - player.wins})</span>
                                </li>`
                            ).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Generate HTML for player rows
function generatePlayerRows(playerStats) {
    // Sort players by win rate (minimum 3 matches)
    const qualifiedPlayers = Object.keys(playerStats)
        .map(name => ({
            name,
            ...playerStats[name]
        }))
        .filter(player => player.matches >= 3)
        .sort((a, b) => b.winRate - a.winRate);
    
    if (qualifiedPlayers.length === 0) {
        return `<tr><td colspan="5" class="text-center">No player data available</td></tr>`;
    }
    
    return qualifiedPlayers.map(player => {
        const winRateClass = player.winRate >= 70 ? 'text-success' :
                            player.winRate >= 50 ? 'text-primary' :
                            player.winRate >= 30 ? 'text-warning' : 'text-danger';
        
        return `
            <tr>
                <td>${player.name}</td>
                <td class="text-center">${player.matches} (${player.wins}-${player.matches - player.wins})</td>
                <td class="text-center ${winRateClass}">${player.winRate}%</td>
                <td class="text-center">${player.bestCourt ? 
                    `${player.bestCourt.name} (${player.bestCourt.winRate}%)` : 
                    'N/A'}</td>
                <td class="text-center">${player.bestPartner ? 
                    `${player.bestPartner.name} (${player.bestPartner.winRate}%)` : 
                    'N/A'}</td>
            </tr>
        `;
    }).join('');
}

// Generate HTML for upcoming matches
function generateUpcomingMatchesHTML(upcomingMatches) {
    if (upcomingMatches.length === 0) {
        return `<p class="text-center">No upcoming matches scheduled</p>`;
    }
    
    return `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Opponent</th>
                        <th>Location</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    ${upcomingMatches.map(match => {
                        const date = new Date(match["Date"].split('-').reverse().join('-'));
                        const formattedDate = date.toLocaleDateString('en-US', {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric'
                        });
                        
                        return `
                            <tr>
                                <td>${formattedDate}</td>
                                <td>${match["Away Team"]}</td>
                                <td>${match["Location"] || 'TBD'}</td>
                                <td>${match["Time"] || 'TBD'}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// After DOMContentLoaded or in loadTeamData, set the user's series and club in the header
async function setUserTeamInfo() {
    try {
        const authResponse = await fetch('/api/check-auth');
        const authData = await authResponse.json();
        if (authData.authenticated && authData.user) {
            document.getElementById('userSeries').textContent = authData.user.series || '';
            document.getElementById('userClub').textContent = authData.user.club || '';
        }
    } catch (e) {
        document.getElementById('userSeries').textContent = '[error]';
        document.getElementById('userClub').textContent = '[error]';
    }
}

// Dynamically render court breakdown cards for a selected player
function renderCourtBreakdownCards(player) {
    const courtBreakdownCards = document.getElementById('courtBreakdownCards');
    if (!player || !player.courts) {
        courtBreakdownCards.innerHTML = '';
        return;
    }
    let html = '';
    Object.entries(player.courts).forEach(([court, stats]) => {
        const courtNum = court.replace('court', 'Court ');
        // Skip rendering if courtNum or player is 'Unknown'
        if (courtNum === 'Unknown' || stats.matches === 35 && stats.wins === 0 && stats.winRate === 0) return;
        function winRateClass(rate) {
            if (rate >= 60) return 'win-rate-high';
            if (rate >= 40) return 'win-rate-medium';
            return 'win-rate-low';
        }
        html += `<div class='col-md-6'>
            <div class='court-card card h-100'>
                <div class='card-body'>
                    <h6>${courtNum}</h6>
                    <p><span class='stat-label'>Matches</span><span class='stat-value'>${stats.matches}</span></p>
                    <p><span class='stat-label'>Record</span><span class='stat-value'>${stats.wins}-${stats.matches - stats.wins}</span></p>
                    <p><span class='stat-label'>Win Rate</span><span class='stat-value ${winRateClass(stats.winRate)}'>${stats.winRate}%</span></p>`;
        if (stats.partners && stats.partners.length > 0) {
            html += `<div class='partner-info mt-2'>
                <strong>Most Common Partners:</strong>
                <ul class='partner-list'>`;
            stats.partners.forEach(ptn => {
                const partnerLosses = ptn.matches - ptn.wins;
                html += `<li>${ptn.name} (${ptn.wins}-${partnerLosses}, ${ptn.winRate}%)</li>`;
            });
            html += `</ul></div>`;
        }
        html += `</div></div></div>`;
    });
    courtBreakdownCards.innerHTML = `<div class='row g-3'>${html}</div>`;
}

// When a player is selected, render their court breakdown cards
const playerSelect = document.getElementById('playerSelect');
if (playerSelect) {
    playerSelect.addEventListener('change', function() {
        const playerName = this.value;
        // Find the player in lastTeamPlayers (which should be set when the team is selected)
        const player = (window.lastTeamPlayers || []).find(p => p.name && p.name.trim().toLowerCase() === playerName.trim().toLowerCase());
        renderCourtBreakdownCards(player);
    });
} 