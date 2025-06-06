function contactSub(lastName, firstName) {
    // Navigate to the contact sub page with params matching the HTML expectations
    window.location.href = `/contact-sub?first=${encodeURIComponent(firstName)}&last=${encodeURIComponent(lastName)}`;
}

// Function to load and display team statistics
async function loadTeamStats() {
    const teamSelect = document.getElementById('teamSelect');
    const teamAnalysis = document.getElementById('teamAnalysis');
    const seriesStatsCharts = document.getElementById('seriesStatsCharts');
    
    console.log('Starting loadTeamStats function');
    console.log('Selected team:', teamSelect.value);
    
    if (!teamSelect.value) {
        console.log('No team selected');
        teamAnalysis.innerHTML = `
            <div class="text-center text-muted">
                <p>Select a team to view detailed analysis</p>
            </div>`;
        return;
    }
    
    try {
        console.log('Showing loading state');
        teamAnalysis.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>`;
            
        // Fetch team statistics from the server using the correct endpoint
        const url = `/api/series-stats?team=${encodeURIComponent(teamSelect.value)}`;
        console.log('Fetching from URL:', url);
        
        const response = await fetch(url);
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Full server response:', data);
        
        if (!data) {
            throw new Error('No data received from server');
        }
        
        if (!data.team_analysis) {
            console.error('Missing team_analysis in response:', data);
            throw new Error('Response missing team_analysis data');
        }
        
        const stats = data.team_analysis;
        console.log('Team analysis stats:', stats);
        
        if (!stats.overview) {
            console.error('Missing overview in stats:', stats);
            throw new Error('Missing overview data');
        }
        
        if (!stats.match_patterns) {
            console.error('Missing match_patterns in stats:', stats);
            throw new Error('Missing match patterns data');
        }
        
        console.log('Generating HTML with stats');
        const html = generateTeamAnalysisHTML(stats);
        console.log('Generated HTML length:', html.length);
        
        // Update team analysis section
        teamAnalysis.innerHTML = html;
        console.log('Updated DOM with team analysis');
        
        // Update charts if we have the data
        if (data.dates && data.scores) {
            console.log('Updating charts with dates and scores');
            updateSeriesCharts(data);
        } else {
            console.log('No chart data available');
        }
        
    } catch (error) {
        console.error('Detailed error in loadTeamStats:', {
            message: error.message,
            stack: error.stack,
            name: error.name
        });
        
        teamAnalysis.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <p><strong>Failed to load team statistics:</strong> ${error.message}</p>
                <p>Please check the console for more details.</p>
            </div>`;
    }
}

// Helper function to generate team analysis HTML
function generateTeamAnalysisHTML(stats) {
    let html = '<div class="team-analysis-container">';

    // Analysis Summary Section
    html += '<div class="analysis-section">';
    html += '<h4>Analysis Summary</h4>';
    html += `<p>${stats.analysis_summary}</p>`;
    html += '</div>';

    // Team Overview Section
    html += '<div class="analysis-section">';
    html += '<h4>Team Overview</h4>';
    html += `<p>Total Matches: ${stats.total_matches}</p>`;
    html += `<p>Wins: ${stats.wins}</p>`;
    html += `<p>Losses: ${stats.losses}</p>`;
    html += `<p>Win Rate: ${(stats.win_rate * 100).toFixed(1)}%</p>`;
    html += `<p>Total Points: ${stats.total_points}</p>`;
    html += '</div>';

    // Match Patterns Section
    html += '<div class="analysis-section">';
    html += '<h4>Match Patterns</h4>';
    
    // Court Analysis
    html += '<h5>Court Analysis</h5>';
    html += '<div class="court-analysis-grid">';
    
    Object.entries(stats.match_patterns.court_analysis).forEach(([court, data]) => {
        html += '<div class="court-card">';
        html += `<h5>Court ${court}</h5>`;
        
        const winRate = data.wins / (data.wins + data.losses) * 100 || 0;
        html += `<p>Record: ${data.wins}-${data.losses} (${winRate.toFixed(1)}%)</p>`;
        
        if (data.key_players && data.key_players.length > 0) {
            html += '<h6>Key Players:</h6>';
            html += '<ul class="key-players-list">';
            data.key_players.forEach(player => {
                const playerWinRate = (player.win_rate * 100).toFixed(1);
                html += `<li class="player-stat">`;
                html += `<div class="player-name">${player.name}</div>`;
                html += `<div class="player-record">${player.matches} matches, ${playerWinRate}% win rate</div>`;
                
                // Add partner information if available
                if (player.top_partners && player.top_partners.length > 0) {
                    html += '<div class="partner-info">';
                    html += '<strong>Best Partners:</strong>';
                    html += '<ul class="partner-list">';
                    player.top_partners.forEach(partner => {
                        const partnerWinRate = (partner.win_rate * 100).toFixed(1);
                        html += `<li>${partner.name} - ${partner.matches} matches, ${partnerWinRate}% win rate</li>`;
                    });
                    html += '</ul>';
                    html += '</div>';
                }
                
                html += '</li>';
            });
            html += '</ul>';
        } else {
            html += '<p>No key players data available</p>';
        }
        
        html += '</div>';
    });
    
    html += '</div>'; // Close court-analysis-grid
    html += '</div>'; // Close analysis-section
    html += '</div>'; // Close team-analysis-container

    return html;
}

function generateCourtAnalysis(courtStats) {
    let html = '';
    for (let i = 1; i <= 4; i++) {
        const court = courtStats[`court${i}`];
        const total = court.wins + court.losses;
        const winRate = total > 0 ? (court.wins / total * 100).toFixed(1) : 0;
        
        html += `
            <div class="court-stat mb-3">
                <h6>Court ${i}</h6>
                <div class="stat-item">
                    <strong>Record:</strong> ${court.wins}-${court.losses} (${winRate}%)
                </div>
                <div class="stat-item">
                    <strong>Key Players:</strong>
                    ${generateKeyPlayersList(court.key_players)}
                </div>
            </div>`;
    }
    return html;
}

function generateKeyPlayersList(players) {
    if (!players || players.length === 0) return 'No data available';
    
    return players.map(player => 
        `${player.name} (${player.wins}-${player.matches - player.wins}, ${(player.win_rate * 100).toFixed(1)}%)`
    ).join(', ');
}

function generateHeadToHeadList(headToHead) {
    if (!headToHead) return 'No head-to-head data available';
    
    return Object.entries(headToHead)
        .map(([team, record]) => `
            <div class="stat-item">
                <strong>${team}:</strong> ${record.wins}-${record.losses}
            </div>
        `).join('');
}

// Helper function to update series charts
function updateSeriesCharts(stats) {
    const seriesStatsCharts = document.getElementById('seriesStatsCharts');
    
    // Create performance trend chart
    const performanceTrend = {
        x: stats.dates,
        y: stats.scores,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Performance Trend'
    };
    
    Plotly.newPlot('seriesStatsCharts', [performanceTrend], {
        title: 'Team Performance Trend',
        xaxis: { title: 'Date' },
        yaxis: { title: 'Score' }
    });
}

// Function to handle team selection and populate player picklist
async function handleTeamSelection() {
    const teamSelect = document.getElementById('teamSelect');
    const playerSelect = document.getElementById('playerSelect');
    const playerStats = document.getElementById('playerStats');
    
    // Clear current player selection and stats
    playerSelect.innerHTML = '<option value="">Choose a player...</option>';
    playerStats.innerHTML = '';
    
    const selectedTeam = teamSelect.value;
    if (!selectedTeam) return;
    
    try {
        const response = await fetch(`/api/team-players/${encodeURIComponent(selectedTeam)}`);
        if (!response.ok) throw new Error('Failed to fetch team players');
        
        const data = await response.json();
        const players = data.players;
        
        // Sort players by matches played (descending) and then alphabetically
        players.sort((a, b) => b.matches - a.matches || a.name.localeCompare(b.name));
        
        // Add players to select
        players.forEach(player => {
            const option = document.createElement('option');
            option.value = player.name;
            option.textContent = `${player.name} (${player.wins}-${player.matches - player.wins}, ${player.winRate}%)`;
            playerSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading team players:', error);
        playerSelect.innerHTML = `
            <option value="">Error loading players</option>
        `;
    }
}

// Function to handle player selection and display stats
function handlePlayerSelection() {
    const selectedTeam = document.getElementById('teamSelect').value;
    const selectedPlayer = document.getElementById('playerSelect').value;
    const playerStatsDiv = document.getElementById('playerStats');

    // Clear stats if no team or player selected
    if (!selectedTeam || !selectedPlayer) {
        playerStatsDiv.innerHTML = '';
        return;
    }

    // Show loading spinner
    playerStatsDiv.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';

    // Fetch player data
    fetch(`/api/team-players/${encodeURIComponent(selectedTeam)}`)
        .then(response => response.json())
        .then(data => {
            if (!data || !data.players) {
                throw new Error('No player data received');
            }

            const player = data.players.find(p => p.name === selectedPlayer);
            if (!player) {
                throw new Error('Player not found');
            }

            // Format win rates with one decimal place
            const overallWinRate = player.winRate.toFixed(1);
            const winRateClass = overallWinRate >= 65 ? 'win-rate-high' : overallWinRate >= 45 ? 'win-rate-medium' : 'win-rate-low';

            let html = `
<div class="player-analysis">
    <div class="overall-stats">
        <h6>Overall Performance</h6>
        <p><span class="stat-label">Total Matches</span><span class="stat-value">${player.matches}</span></p>
        <p><span class="stat-label">Overall Record</span><span class="stat-value">${player.wins}-${player.matches - player.wins}</span></p>
        <p><span class="stat-label">Win Rate</span><span class="stat-value ${winRateClass}">${overallWinRate}%</span></p>
        ${player.pti !== 'N/A' ? `<p><span class="stat-label">PTI Rating</span><span class="stat-value">${player.pti}</span></p>` : ''}
    </div>
    <div class="row g-3">`;

            // Add court performance cards
            for (let court = 1; court <= 4; court++) {
                const courtKey = `court${court}`;
                const courtStats = player.courts[courtKey];
                const courtWinRate = courtStats.winRate.toFixed(1);
                const courtWinRateClass = courtWinRate >= 65 ? 'win-rate-high' : courtWinRate >= 45 ? 'win-rate-medium' : 'win-rate-low';

                html += `
        <div class="col-md-6">
            <div class="court-card">
                <h6>Court ${court}</h6>
                <p><span class="stat-label">Matches</span><span class="stat-value">${courtStats.matches}</span></p>
                <p><span class="stat-label">Record</span><span class="stat-value">${courtStats.wins}-${courtStats.matches - courtStats.wins}</span></p>
                <p><span class="stat-label">Win Rate</span><span class="stat-value ${courtWinRateClass}">${courtWinRate}%</span></p>`;

                // Add partner information if available
                if (courtStats.partners && courtStats.partners.length > 0) {
                    html += `
                <div class="partner-info">
                    <strong>Most Common Partners:</strong>
                    <ul class="partner-list">`;
                    
                    courtStats.partners.forEach(partner => {
                        html += `
                        <li>${partner.name} (${partner.wins}-${partner.matches - partner.wins}, ${partner.winRate}%)</li>`;
                    });
                    
                    html += `
                    </ul>
                </div>`;
                }

                html += `
            </div>
        </div>`;
            }

            html += `
    </div>
</div>`;

            playerStatsDiv.innerHTML = html;
        })
        .catch(error => {
            console.error('Error fetching player data:', error);
            playerStatsDiv.innerHTML = '<div class="alert alert-danger">Error loading player statistics</div>';
        });
}

// Add event listeners when the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    const teamSelect = document.getElementById('teamSelect');
    const playerSelect = document.getElementById('playerSelect');
    
    if (teamSelect) {
        teamSelect.addEventListener('change', handleTeamSelection);
    }
    
    if (playerSelect) {
        playerSelect.addEventListener('change', handlePlayerSelection);
    }
    fetchAndRenderSubs();
});

// Remove the old event listeners
// document.getElementById('playerSelect').addEventListener('change', handlePlayerSelection);
// document.getElementById('teamSelect').addEventListener('change', handleTeamSelection); 

// Add this function to render the subs table with top player highlighting
function renderSubsTable(players) {
    const tableBody = document.getElementById('subsTableBody');
    tableBody.innerHTML = '';
    if (!players || players.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="8" class="text-center">No subs found</td></tr>`;
        return;
    }
    // Sort by composite score (highest to lowest)
    players.sort((a, b) => b.compositeScore - a.compositeScore);
    // Top 3 players
    const topPlayers = players.slice(0, 3);
    const restPlayers = players.slice(3);
    let html = '';
    if (topPlayers.length > 0) {
        html += `<tr id="top-player-label-row"><td colspan="8" class="top-player-label text-center" style="background:#145a32;color:#fff;font-weight:bold;">` +
            `<strong>Top recommended subs based upon Rally's algorithm</strong></td></tr>`;
        topPlayers.forEach(player => {
            html += `
            <tr class="top-player">
                <td style="font-weight:bold">${player.series}</td>
                <td style="font-weight:bold">${player.name}</td>
                <td class="text-end" style="font-weight:bold">${player.pti}</td>
                <td class="text-end" style="font-weight:bold">${player.wins}</td>
                <td class="text-end" style="font-weight:bold">${player.losses}</td>
                <td class="text-end" style="font-weight:bold">${player.winRate}%</td>
                <td class="text-center" style="font-weight:bold"><span class="composite-score">${player.compositeScore}</span></td>
                <td class="text-center" style="font-weight:bold">
                    <button class="btn btn-sm btn-primary" onclick="contactSub('${player.lastName}', '${player.firstName}')">Contact</button>
                </td>
            </tr>`;
        });
    }
    restPlayers.forEach(player => {
        html += `
        <tr>
            <td>${player.series}</td>
            <td>${player.name}</td>
            <td class="text-end">${player.pti}</td>
            <td class="text-end">${player.wins}</td>
            <td class="text-end">${player.losses}</td>
            <td class="text-end">${player.winRate}%</td>
            <td class="text-center"><span class="composite-score">${player.compositeScore}</span></td>
            <td class="text-center">
                <button class="btn btn-sm btn-primary" onclick="contactSub('${player.lastName}', '${player.firstName}')">Contact</button>
            </td>
        </tr>`;
    });
    tableBody.innerHTML = html;
}

// Helper: Calculate composite score (example logic, adjust as needed)
function calculateCompositeScore(pti, winRate, series) {
    // Example: composite = PTI * 0.5 + winRate * 0.5 (customize as needed)
    return (parseFloat(pti) || 0) * 0.5 + (parseFloat(winRate) || 0) * 0.5;
}

// Fetch and render subs table
async function fetchAndRenderSubs() {
    const tableBody = document.getElementById('subsTableBody');
    tableBody.innerHTML = `<tr><td colspan="8" class="text-center">Loading subs...</td></tr>`;
    try {
        // Example: fetch all subs (customize endpoint/params as needed)
        const response = await fetch('/api/players?all_subs=1');
        const players = await response.json();
        if (!players || players.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="8" class="text-center">No subs found</td></tr>`;
            return;
        }
        // Calculate composite scores
        const playersWithScores = players.map(player => ({
            ...player,
            compositeScore: calculateCompositeScore(player.pti, player.winRate, player.series)
        }));
        renderSubsTable(playersWithScores);
    } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Error loading subs</td></tr>`;
    }
} 