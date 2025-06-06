// research-my-team.js
// Handles displaying team statistics and analysis for the user's current team (My Team)

console.log('[DEBUG] runMyTeamDualColumnDashboard called');

let lastTeamPlayers = [];

// === Dual-Column My Team Dashboard Logic (No Team Picklist) ===
async function runMyTeamDualColumnDashboard() {
    resetMyTeamRightColumn();
    console.log('[MyTeam] runMyTeamDualColumnDashboard called');
    // Fetch user info to get team
    let userTeam = null;
    let userSeries = null;
    let userClub = null;
    try {
        const authResp = await fetch('/api/check-auth');
        const authData = await authResp.json();
        if (!authData.authenticated || !authData.user) throw new Error('Not authenticated');
        userTeam = authData.user.team || (authData.user.club + ' - ' + (authData.user.series ? authData.user.series.match(/\d+/)?.[0] : ''));
        userSeries = authData.user.series;
        userClub = authData.user.club;
        // Update header info
        document.getElementById('userSeriesMyTeam').textContent = userSeries || '';
        document.getElementById('userClubMyTeam').textContent = userClub || '';
        // Update team name in the disabled select (or replace with plain text)
        const teamSelectDiv = document.getElementById('myTeamSelect');
        if (teamSelectDiv) {
            // Replace the select with a span showing the team name
            const parent = teamSelectDiv.parentElement;
            const label = parent.querySelector('label');
            if (label) label.textContent = 'Your Team';
            const span = document.createElement('span');
            span.className = 'form-control-plaintext';
            span.textContent = userTeam;
            teamSelectDiv.replaceWith(span);
        }
    } catch (e) {
        document.getElementById('userSeriesMyTeam').textContent = '[error]';
        document.getElementById('userClubMyTeam').textContent = '[error]';
        document.getElementById('myTeamStats').innerHTML = '<div class="alert alert-danger">Error loading user info.</div>';
        return;
    }
    // Fetch team stats and matches
    let stats = null;
    let matchesData = [];
    try {
        const statsResp = await fetch(`/api/research-my-team`);
        stats = await statsResp.json();
        if (!stats || !stats.overview) throw new Error('No stats available for this team');
    } catch (e) {
        document.getElementById('myTeamStats').innerHTML = `<div class="alert alert-danger">Error loading team stats: ${e.message}</div>`;
        return;
    }
    try {
        const matchesResp = await fetch(`/api/team-matches?team=${encodeURIComponent(userTeam)}`);
        matchesData = await matchesResp.json();
    } catch (e) {
        // fallback: empty matches
        matchesData = [];
    }
    // Render the full dashboard for My Team
    await renderMyTeamDashboard(userTeam, matchesData, stats);
    // Fetch players for this team
    let players = [];
    try {
        const resp = await fetch(`/api/team-players/${encodeURIComponent(userTeam)}`);
        const data = await resp.json();
        if (data.players && data.players.length > 0) {
            players = data.players;
        } else {
            throw new Error('No players found for this team');
        }
    } catch (e) {
        document.getElementById('myTeamPlayerSelect').innerHTML = `<option value="">Error loading players</option>`;
        return;
    }
    // Populate player picklist
    const playerSelect = document.getElementById('myTeamPlayerSelect');
    playerSelect.innerHTML = '<option value="">Choose a player...</option>';
    players.forEach(player => {
        const option = document.createElement('option');
        option.value = player.name;
        option.textContent = player.name;
        playerSelect.appendChild(option);
    });
    // Add event listener for player selection
    playerSelect.onchange = function() {
        const playerName = this.value;
        showMyTeamPlayerStats(playerName, players);
    };
    // Optionally, auto-select the first player
    // if (players.length > 0) {
    //     playerSelect.value = players[0].name;
    //     showMyTeamPlayerStats(players[0].name, players);
    // }
}
// Helper to show player stats for My Team
async function showMyTeamPlayerStats(playerName, players) {
    const statsDiv = document.getElementById('myTeamPlayerStats');
    const detailsCard = document.getElementById('myTeamPlayerDetailsCard');
    const detailsBody = document.getElementById('myTeamPlayerDetailsBody');
    const courtBreakdownCards = document.getElementById('myTeamCourtBreakdownCards');
    statsDiv.innerHTML = '';
    detailsCard.style.display = 'none';
    courtBreakdownCards.style.display = 'none';
    if (!playerName) return;
    // Find player object
    const player = players.find(p => p.name === playerName);
    if (!player) {
        statsDiv.innerHTML = '<div class="alert alert-warning">No stats found for this player.</div>';
        return;
    }
    // Fetch player history for more details
    let playerHistory = null;
    try {
        const resp = await fetch('/api/player-history');
        const data = await resp.json();
        playerHistory = data.find(p => p.name && p.name.trim().toLowerCase() === playerName.trim().toLowerCase());
    } catch (e) {}
    // Render player stats
    const totalMatches = player.matches ?? (player.wins + player.losses);
    const wins = player.wins ?? 0;
    const losses = totalMatches - wins;
    const winRate = totalMatches > 0 ? ((wins / totalMatches) * 100).toFixed(1) : '0.0';
    const pti = player.pti ?? player.rating ?? 'N/A';
    const html = generateOverallCards({
        totalMatches,
        wins,
        losses,
        winRate,
        pti,
        heading: 'Player Details',
        name: player.name
    });
    statsDiv.innerHTML = html;
    detailsBody.innerHTML = html;
    detailsCard.style.display = '';
    // Optionally, render court breakdown if available
    if (playerHistory && playerHistory.courts) {
        // Use the same renderCourtBreakdownCards as research-team.js
        courtBreakdownCards.innerHTML = renderCourtBreakdownCards(playerHistory);
        courtBreakdownCards.style.display = '';
    }
}
// Run the dashboard logic when the My Team page is shown
function setupMyTeamPageListener() {
    // Listen for navigation to My Team page
    const origShowContent = window.showContent;
    window.showContent = function(contentId) {
        origShowContent.apply(this, arguments);
        if (contentId === 'research-my-team') {
            if (typeof runMyTeamDualColumnDashboard === 'function') {
                runMyTeamDualColumnDashboard();
            }
        }
    };
}
setupMyTeamPageListener();

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
            const partner = players[playerName].partners[partnerName];
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
        // Try to parse date in MM/DD/YYYY or similar
        const parseDate = (d) => {
            if (!d) return new Date(0);
            const parts = d.split("/");
            if (parts.length === 3) {
                // MM/DD/YYYY
                return new Date(parts[2], parts[0] - 1, parts[1]);
            }
            return new Date(d);
        };
        const dateA = parseDate(a.date || a.Date);
        const dateB = parseDate(b.date || b.Date);
        return dateA - dateB;
    });
    // Get current date
    const currentDate = new Date();
    // Filter for upcoming matches
    return sortedMatches.filter(match => {
        const matchDate = (() => {
            const d = match.date || match.Date;
            if (!d) return new Date(0);
            const parts = d.split("/");
            if (parts.length === 3) {
                // MM/DD/YYYY
                return new Date(parts[2], parts[0] - 1, parts[1]);
            }
            return new Date(d);
        })();
        return matchDate >= currentDate;
    }).slice(0, 3); // Get next 3 matches
}

// Generate HTML for upcoming matches (copied/adapted from research-team.js)
function generateUpcomingMatchesHTML(upcomingMatches) {
    if (!upcomingMatches || upcomingMatches.length === 0) {
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
                        // Support both MM/DD/YYYY and Date fields
                        let dateObj = null;
                        if (match.date) {
                            const parts = match.date.split("/");
                            if (parts.length === 3) {
                                dateObj = new Date(parts[2], parts[0] - 1, parts[1]);
                            } else {
                                dateObj = new Date(match.date);
                            }
                        } else if (match.Date) {
                            const parts = match.Date.split("/");
                            if (parts.length === 3) {
                                dateObj = new Date(parts[2], parts[0] - 1, parts[1]);
                            } else {
                                dateObj = new Date(match.Date);
                            }
                        } else {
                            dateObj = new Date();
                        }
                        const formattedDate = dateObj.toLocaleDateString('en-US', {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric'
                        });
                        // Determine opponent
                        let opponent = '';
                        if (match["Home Team"] && match["Away Team"]) {
                            // If user's team is home, opponent is away, and vice versa
                            const isHome = match["Home Team"] === match.teamId;
                            opponent = isHome ? match["Away Team"] : match["Home Team"];
                        } else if (match.opponent) {
                            opponent = match.opponent;
                        } else {
                            opponent = 'TBD';
                        }
                        return `
                            <tr>
                                <td>${formattedDate}</td>
                                <td>${opponent}</td>
                                <td>${match.location || match.Location || 'TBD'}</td>
                                <td>${match.time || match.Time || 'TBD'}</td>
                                </tr>
                        `;
                    }).join('')}
                        </tbody>
                    </table>
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
                option.textContent = player.name;
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
    const courtBreakdownCards = document.getElementById('courtBreakdownCards');
    const playerHistoryCard = document.getElementById('playerHistoryCard');
    statsDiv.innerHTML = '<div class="text-center my-4">Loading player stats...</div>';
    detailsCard.style.display = 'none';
    if (courtBreakdownCards) courtBreakdownCards.style.display = 'none';
    if (playerHistoryCard) playerHistoryCard.style.display = 'none';
    if (!playerName) {
        statsDiv.innerHTML = '';
        detailsCard.style.display = 'none';
        if (courtBreakdownCards) courtBreakdownCards.innerHTML = '';
        if (playerHistoryCard) document.getElementById('player-history-dynamic').innerHTML = '';
        return;
    }
    // Find the player in lastTeamPlayers (which includes courts)
    const player = lastTeamPlayers.find(p => p.name && p.name.trim().toLowerCase() === playerName.trim().toLowerCase());
    console.log('Selected player (from team-players):', player);
    if (!player) {
        statsDiv.innerHTML = '<div class="alert alert-warning">No stats found for this player.</div>';
        detailsCard.style.display = 'none';
        if (courtBreakdownCards) courtBreakdownCards.style.display = 'none';
        if (playerHistoryCard) playerHistoryCard.style.display = 'none';
        return;
    }
    // Show overall stats (use player object from team-players, which has matches, wins, losses, winRate, pti)
    const totalMatches = player.matches ?? (player.wins + player.losses);
    const wins = player.wins ?? 0;
    const losses = totalMatches - wins;
    const winRate = totalMatches > 0 ? ((wins / totalMatches) * 100).toFixed(1) : '0.0';
    const pti = player.pti ?? player.rating ?? 'N/A';
    const html = generateOverallCards({
        totalMatches,
        wins,
        losses,
        winRate,
        pti,
        heading: 'Player Details',
        name: player.name
    });
    statsDiv.innerHTML = html;
    detailsBody.innerHTML = html;
    detailsCard.style.display = '';
    // Render court breakdown cards in their own div
    if (courtBreakdownCards) {
        let courtHtml = renderCourtBreakdownCards(player); // Use the same function as research-team
        courtBreakdownCards.innerHTML = courtHtml;
        courtBreakdownCards.style.display = '';
    }
    // Show and render the player history card if present
    if (playerHistoryCard) {
        playerHistoryCard.style.display = '';
        if (typeof renderPlayerHistory === 'function') {
            renderPlayerHistory(player.name);
        }
    }
}

// Set the user's series and club in the My Team header
async function setUserTeamInfoMyTeam() {
    try {
        const authResponse = await fetch('/api/check-auth');
        const authData = await authResponse.json();
        if (authData.authenticated && authData.user) {
            document.getElementById('userSeriesMyTeam').textContent = authData.user.series || '';
            document.getElementById('userClubMyTeam').textContent = authData.user.club || '';
        }
    } catch (e) {
        document.getElementById('userSeriesMyTeam').textContent = '[error]';
        document.getElementById('userClubMyTeam').textContent = '[error]';
    }
}

// Render team analysis card (copy/adapt from research-team.js)
function renderMyTeamAnalysisCard(statsData, teamId) {
    if (!statsData || !statsData.overview) {
        return '<div class="alert alert-warning">No analysis available for this team.</div>';
    }
    const analysis = statsData;
    // Use the same HTML structure as research-team, but unique IDs are not needed here
    return `
    <div class="team-analysis">
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Analysis</h5>
                    </div>
                    <div class="card-body">
                        <p>
                            ${teamId} has accumulated ${analysis.overview.points} points this season with a 
                            ${analysis.overview.match_win_rate}% match win rate. The team shows 
                            strong resilience with ${analysis.match_patterns.comeback_wins} comeback victories 
                            and has won ${analysis.match_patterns.straight_set_wins} matches in straight sets.
                        </p>
                        <p>
                            Their performance metrics show a ${analysis.overview.game_win_rate}% game win rate and 
                            ${analysis.overview.set_win_rate}% set win rate, with particularly 
                            ${analysis.overview.line_win_rate >= 50 ? 'strong' : 'consistent'} line play at 
                            ${analysis.overview.line_win_rate}%.
                        </p>
                        <p>
                            In three-set matches, the team has a record of ${analysis.match_patterns.three_set_record}, 
                            demonstrating their ${parseInt(analysis.match_patterns.three_set_record.split('-')[0]) > parseInt(analysis.match_patterns.three_set_record.split('-')[1]) ? 'strength' : 'areas for improvement'} 
                            in extended matches.
                        </p>
                    </div>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-12 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Team Overview</h5>
                    </div>
                    <div class="card-body">
                        <div class="stat-item">
                            <strong>Points:</strong> ${analysis.overview.points}
                        </div>
                        <div class="stat-item">
                            <strong>Match Record:</strong> ${analysis.overview.match_record}
                        </div>
                        <div class="stat-item">
                            <strong>Match Win Rate:</strong> ${analysis.overview.match_win_rate}%
                        </div>
                        <div class="stat-item">
                            <strong>Line Win Rate:</strong> ${analysis.overview.line_win_rate}%
                        </div>
                        <div class="stat-item">
                            <strong>Set Win Rate:</strong> ${analysis.overview.set_win_rate}%
                        </div>
                        <div class="stat-item">
                            <strong>Game Win Rate:</strong> ${analysis.overview.game_win_rate}%
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-12 mb-4">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Match Patterns</h5>
                    </div>
                    <div class="card-body">
                        <div class="overall-stats mb-4">
                            <h6 class="mb-3">Overall Performance</h6>
                            <div class="stat-item">
                                <strong>Total Matches:</strong> ${analysis.match_patterns.total_matches}
                            </div>
                            <div class="stat-item">
                                <strong>Set Win Rate:</strong> ${analysis.match_patterns.set_win_rate}%
                            </div>
                            <div class="stat-item">
                                <strong>Three-Set Record:</strong> ${analysis.match_patterns.three_set_record}
                            </div>
                            <div class="stat-item">
                                <strong>Straight Set Wins:</strong> ${analysis.match_patterns.straight_set_wins}
                            </div>
                            <div class="stat-item">
                                <strong>Comeback Wins:</strong> ${analysis.match_patterns.comeback_wins}
                            </div>
                        </div>
                        <div class="court-analysis">
                            <h6 class="mb-3">Court Analysis</h6>
                            ${Object.entries(analysis.match_patterns.court_analysis || {}).map(([court, data]) => {
                                const courtNumber = court.replace(/\D/g, '');
                                const winRate = data.win_rate;
                                const performanceClass = winRate >= 60 ? 'strong-performance' : 
                                                       winRate >= 45 ? 'average-performance' : 
                                                       'needs-improvement';
                                return `
                                    <div class="court-section mb-4 ${performanceClass}">
                                        <h6 class="court-header">Court ${courtNumber}</h6>
                                        <div class="stat-item">
                                            <strong>Record:</strong> ${data.wins}-${data.losses} (${data.win_rate}%)
                                        </div>
                                        <div class="stat-item">
                                            <strong>Key Players:</strong>
                                            <ul class="key-players-list">
                                                ${data.key_players.map(player => `
                                                    <li>${player.name} (${player.win_rate}% win rate in ${player.matches} matches)</li>
                                                `).join('')}
                                            </ul>
                                        </div>
                                        <div class="court-summary">
                                            ${generateMyTeamCourtSummary(data.win_rate, data.key_players)}
                                        </div>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>`;
}
function generateMyTeamCourtSummary(winRate, keyPlayers) {
    if (!keyPlayers || keyPlayers.length === 0) {
        return 'No consistent players identified for this court.';
    }
    const performanceLevel = winRate >= 60 ? 'strong' : 
                           winRate >= 45 ? 'solid' : 
                           'challenging';
    const playerSummary = keyPlayers.map(player => 
        `${player.name} (${player.win_rate}% in ${player.matches} matches)`
    ).join(' and ');
    return `This court has shown ${performanceLevel} performance with a ${winRate}% win rate. Key contributors: ${playerSummary}.`;
}
// Render player stats summary
function renderMyTeamPlayerStats(player) {
    const totalMatches = player.matches ?? 0;
    const wins = player.wins ?? 0;
    const losses = totalMatches - wins;
    const winRate = player.winRate ?? 0;
    const pti = player.pti ?? player.rating ?? 'N/A';
    // Determine win-rate color class
    const winRateClass = winRate >= 60 ? 'win-rate-high' : (winRate >= 40 ? 'win-rate-medium' : 'win-rate-low');
    return `<div class='player-analysis'>
        <div class='overall-stats mb-4'>
            <h6>Overall Performance</h6>
            <div class='row row-cols-2 row-cols-md-4 g-2'>
                <div class='col'>
                    <div class='card text-center h-100 py-2'>
                        <p class='small text-muted mb-1'>Total Matches</p>
                        <h6 class='mb-0'>${totalMatches}</h6>
                    </div>
                </div>
                <div class='col'>
                    <div class='card text-center h-100 py-2'>
                        <p class='small text-muted mb-1'>Overall Record</p>
                        <h6 class='mb-0'>${wins}-${losses}</h6>
                    </div>
                </div>
                <div class='col'>
                    <div class='card text-center h-100 py-2'>
                        <p class='small text-muted mb-1'>Win Rate</p>
                        <h6 class='mb-0 ${winRateClass}'>${winRate}%</h6>
                    </div>
                </div>
                <div class='col'>
                    <div class='card text-center h-100 py-2'>
                        <p class='small text-muted mb-1'>PTI</p>
                        <h6 class='mb-0'>${pti}</h6>
                    </div>
                </div>
            </div>
        </div>
    </div>`;
}
// Render player details (with court breakdown)
function renderMyTeamPlayerDetails(player) {
    const totalMatches = player.matches ?? 0;
    const wins = player.wins ?? 0;
    const losses = totalMatches - wins;
    const winRate = player.winRate ?? 0;
    const pti = player.pti ?? player.rating ?? 'N/A';
    let courtHtml = `<div class='row g-3'>`;
    if (player.courts) {
        Object.entries(player.courts).forEach(([court, stats]) => {
            const courtNum = court.replace('court', 'Court ');
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
    return `<div class='player-analysis'>
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
}
// Render court breakdown cards (for future expansion)
function renderMyTeamCourtBreakdownCards(player) {
    // For now, just return empty or reuse the court breakdown from details
    return '';
}
// New: Render Team Analysis Cards (replaces old team analysis cards)
async function renderTeamAnalysisCards(container) {
    console.log('[DEBUG] renderTeamAnalysisCards called');
    const teamName = 'Tennaqua - 22';
    // Load match and stats data
    const [matches, stats] = await Promise.all([
        fetch('/data/match_history.json').then(r => r.json()),
        fetch('/data/series_stats.json').then(r => r.json())
    ]);
    console.log('[DEBUG] matches:', matches);
    console.log('[DEBUG] stats:', stats);
    // Team Record
    const teamMatches = matches.filter(
        m => m["Home Team"] === teamName || m["Away Team"] === teamName
    );
    let wins = 0, losses = 0;
    teamMatches.forEach(m => {
        const isHome = m["Home Team"] === teamName;
        const didWin = (isHome && m.Winner === "home") || (!isHome && m.Winner === "away");
        if (didWin) wins++;
        else losses++;
    });
    const total = wins + losses;
    const winRate = total > 0 ? ((wins / total) * 100).toFixed(1) : "0.0";
    // Team Points
    const teamStats = stats.find(t => t.team === teamName);
    const points = teamStats ? teamStats.points : 0;
    // Points Behind First Place
    const firstPlace = Math.max(...stats.map(t => t.points));
    const pointsBehind = firstPlace - points;
    // Average Points Per Week
    // Group matches by week (use ISO week number)
    function getWeekKey(dateStr) {
        // Accepts both '24-Sep-24' and 'MM/DD/YYYY' formats
        let d;
        if (dateStr.includes('-')) {
            // '24-Sep-24' format
            const [day, mon, year] = dateStr.split('-');
            d = new Date(`${mon} ${day}, 20${year.slice(-2)}`);
        } else if (dateStr.includes('/')) {
            // 'MM/DD/YYYY' format
            const [month, day, year] = dateStr.split('/');
            d = new Date(`${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`);
        } else {
            d = new Date(dateStr);
        }
        // Get ISO week number
        const temp = new Date(d.getTime());
        temp.setHours(0,0,0,0);
        temp.setDate(temp.getDate() + 4 - (temp.getDay()||7));
        const yearStart = new Date(temp.getFullYear(),0,1);
        const weekNo = Math.ceil((((temp - yearStart) / 86400000) + 1)/7);
        return `${temp.getFullYear()}-W${weekNo}`;
    }
    // For each match, assign to week
    const weekSet = new Set();
    teamMatches.forEach(m => {
        const week = getWeekKey(m.Date || m.date);
        weekSet.add(week);
    });
    const numWeeks = weekSet.size;
    const avgPointsPerWeek = numWeeks > 0 ? (points / numWeeks).toFixed(2) : '0.00';
    // Render cards
    container.innerHTML = `
        <div class="row mb-4">
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-trophy me-2"></i>Team Record</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                            <h2 class="display-4 mb-0 fw-bold">${winRate}%</h2>
                            <p class="text-muted mb-2">Win Rate</p>
                            <h4>${wins}-${losses}</h4>
                            <p>Match Record</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-star me-2"></i>Team Points</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                            <h2 class="display-4 mb-0 fw-bold">${points}</h2>
                            <p class="text-muted mb-2">Total Points</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-arrow-down me-2"></i>Points Behind 1st</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                            <h2 class="display-4 mb-0 fw-bold" ${pointsBehind < 5 ? 'style="color: green;"' : pointsBehind <= 10 ? 'style="color: #f0ad4e;"' : 'style="color: red;"'}>${pointsBehind}</h2>
                            <p class="text-muted mb-2">Behind First Place</p>
                            <h4>${points} pts</h4>
                            <p>Your Points</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card h-100">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-chart-bar me-2"></i>Avg Points Per Week</h5>
                    </div>
                    <div class="card-body">
                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                            <h2 class="display-4 mb-0 fw-bold">${avgPointsPerWeek}</h2>
                            <p class="text-muted mb-2">Average Points/Week</p>
                            <h4>${numWeeks} weeks</h4>
                            <p>Counted Weeks</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    console.log('[DEBUG] About to insert Team Analysis HTML into #myTeamStats');
}

// Patch renderMyTeamDashboard to use the new cards
async function renderMyTeamDashboard(teamId, matchesData, statsData) {
    const container = document.getElementById('myTeamStats');
    // Render new team analysis cards
    await renderTeamAnalysisCards(container);
    // Calculate court-specific stats
    const courtStats = calculateCourtStats(matchesData, teamId);
    // Calculate player performance
    const playerStats = calculatePlayerStats(matchesData, teamId);
    // Calculate upcoming matches
    const upcomingMatches = getUpcomingMatches(matchesData, teamId);
    // Append the rest of the dashboard below the new cards
    container.innerHTML += `
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
// Generate HTML for court cards (copied/adapted from research-team.js)
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
// Generate HTML for player rows (copied/adapted from research-team.js)
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
function resetMyTeamRightColumn() {
    const detailsCard = document.getElementById('myTeamPlayerDetailsCard');
    const detailsBody = document.getElementById('myTeamPlayerDetailsBody');
    const courtBreakdownCards = document.getElementById('myTeamCourtBreakdownCards');
    if (detailsCard) { detailsCard.style.display = 'none'; if (detailsBody) detailsBody.innerHTML = ''; }
    if (courtBreakdownCards) { courtBreakdownCards.style.display = 'none'; courtBreakdownCards.innerHTML = ''; }
}
// Helper: generate horizontal mini-cards for overall metrics
function generateOverallCards({totalMatches, wins, losses, winRate, pti, heading = 'Overall Performance', name = null}) {
    const winRateClass = winRate >= 60 ? 'win-rate-high' : (winRate >= 40 ? 'win-rate-medium' : 'win-rate-low');
    return `
        <div class='player-analysis'>
            <div class='overall-stats mb-4'>
                <h6>${heading}</h6>
                ${name ? `<p class='mb-2'><span class='stat-label'>Name</span><span class='stat-value'>${name}</span></p>` : ''}
                <div class='row row-cols-2 row-cols-md-4 g-2'>
                    <div class='col'>
                        <div class='card text-center h-100 py-2'>
                            <p class='small text-muted mb-1'>Total Matches</p>
                            <h6 class='mb-0'>${totalMatches}</h6>
                        </div>
                    </div>
                    <div class='col'>
                        <div class='card text-center h-100 py-2'>
                            <p class='small text-muted mb-1'>Overall Record</p>
                            <h6 class='mb-0'>${wins}-${losses}</h6>
                        </div>
                    </div>
                    <div class='col'>
                        <div class='card text-center h-100 py-2'>
                            <p class='small text-muted mb-1'>Win Rate</p>
                            <h6 class='mb-0 ${winRateClass}'>${winRate}%</h6>
                        </div>
                    </div>
                    <div class='col'>
                        <div class='card text-center h-100 py-2'>
                            <p class='small text-muted mb-1'>PTI</p>
                            <h6 class='mb-0'>${pti}</h6>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
} 