// club-dashboard.js

// Call this when the research-dashboard page is shown
function setupClubDashboardPageListener() {
    const origShowContent = window.showContent;
    window.showContent = function(contentId) {
        origShowContent.apply(this, arguments);
        if (contentId === 'research-dashboard') {
            if (typeof loadClubDashboard === 'function') {
                loadClubDashboard();
            }
        }
    };
}
setupClubDashboardPageListener();

async function loadClubDashboard() {
    // Show loading states
    document.getElementById('clubOverviewCardsRow').innerHTML = `<div class="col-12 text-center"><div class="spinner-border text-primary" role="status"></div></div>`;
    document.querySelector('#clubTeamsTable tbody').innerHTML = `<tr><td colspan="6" class="text-center">Loading teams...</td></tr>`;
    document.getElementById('clubTopPerformers').innerHTML = `<div class="text-center"><div class="spinner-border text-primary" role="status"></div></div>`;
    document.getElementById('clubTrends').innerHTML = `<div class="text-center"><div class="spinner-border text-primary" role="status"></div></div>`;
    try {
        // 1. Get user's club and series
        const authResp = await fetch('/api/check-auth');
        const authData = await authResp.json();
        if (!authData.authenticated || !authData.user) throw new Error('Not authenticated');
        const userClub = authData.user.club;
        const userSeries = authData.user.series;
        // 2. Load all teams for this club from stats file
        const statsResp = await fetch('/data/Chicago_22_stats_20250425.json');
        const stats = await statsResp.json();
        // Filter teams for this club
        const clubTeams = stats.filter(t => t.team && t.team.startsWith(userClub));
        if (!clubTeams.length) throw new Error('No teams found for this club');
        // Overview cards
        const totalTeams = clubTeams.length;
        const totalPoints = clubTeams.reduce((sum, t) => sum + (t.points || 0), 0);
        const avgPoints = totalTeams > 0 ? (totalPoints / totalTeams).toFixed(1) : '0.0';
        const bestTeam = clubTeams.reduce((a, b) => (a.points > b.points ? a : b));
        const bestWinRate = Math.max(...clubTeams.map(t => parseFloat((t.matches?.percentage||'0').replace('%',''))));
        // Render overview cards
        document.getElementById('clubOverviewCardsRow').innerHTML = `
            <div class="col-md-3 mb-4">
                <div class="card h-100 text-center">
                    <div class="card-header"><h5 class="mb-0"><i class="fas fa-users me-2"></i>Total Teams</h5></div>
                    <div class="card-body"><h2 class="display-4 mb-0 fw-bold">${totalTeams}</h2></div>
                </div>
            </div>
            <div class="col-md-3 mb-4">
                <div class="card h-100 text-center">
                    <div class="card-header"><h5 class="mb-0"><i class="fas fa-star me-2"></i>Total Points</h5></div>
                    <div class="card-body"><h2 class="display-4 mb-0 fw-bold">${totalPoints}</h2></div>
                </div>
            </div>
            <div class="col-md-3 mb-4">
                <div class="card h-100 text-center">
                    <div class="card-header"><h5 class="mb-0"><i class="fas fa-chart-bar me-2"></i>Avg Points/Team</h5></div>
                    <div class="card-body"><h2 class="display-4 mb-0 fw-bold">${avgPoints}</h2></div>
                </div>
            </div>
            <div class="col-md-3 mb-4">
                <div class="card h-100 text-center">
                    <div class="card-header"><h5 class="mb-0"><i class="fas fa-trophy me-2"></i>Best Team</h5></div>
                    <div class="card-body"><h4 class="mb-0">${bestTeam.team}</h4><p class="mb-0">${bestTeam.points} pts</p></div>
                </div>
            </div>
        `;
        // Teams table
        const tbody = document.querySelector('#clubTeamsTable tbody');
        tbody.innerHTML = clubTeams.map(team => `
            <tr>
                <td>${team.team}</td>
                <td>${team.points}</td>
                <td>${team.matches?.won || 0}-${team.matches?.lost || 0}</td>
                <td>${team.matches?.percentage || '0%'}</td>
                <td>${team.sets?.percentage || '0%'}</td>
                <td>${team.games?.percentage || '0%'}</td>
            </tr>
        `).join('');
        // Top performers (by win rate, min 5 matches)
        const playersResp = await fetch(`/api/players?series=${encodeURIComponent(userSeries)}`);
        const players = await playersResp.json();
        // For each player, get their win rate and matches played
        const topPlayers = players
            .filter(p => p.club === userClub || (p.name && p.name.includes(userClub)))
            .map(p => ({
                name: p.name,
                winRate: parseFloat(p.winRate),
                matches: parseInt(p.wins) + parseInt(p.losses),
                rating: p.rating
            }))
            .filter(p => p.matches >= 5)
            .sort((a, b) => b.winRate - a.winRate)
            .slice(0, 5);
        document.getElementById('clubTopPerformers').innerHTML = topPlayers.length ? `
            <table class="table table-sm table-hover">
                <thead><tr><th>Name</th><th>Win Rate</th><th>Matches</th><th>PTI</th></tr></thead>
                <tbody>
                    ${topPlayers.map(p => `<tr><td>${p.name}</td><td>${p.winRate}%</td><td>${p.matches}</td><td>${p.rating}</td></tr>`).join('')}
                </tbody>
            </table>
        ` : '<div class="alert alert-info">No top performers found.</div>';
        // Club trends: bar chart of team points
        const teamNames = clubTeams.map(t => t.team);
        const teamPoints = clubTeams.map(t => t.points);
        const chartDiv = document.createElement('div');
        chartDiv.id = 'clubPointsBarChart';
        chartDiv.style.height = '400px';
        document.getElementById('clubTrends').innerHTML = '';
        document.getElementById('clubTrends').appendChild(chartDiv);
        if (window.Plotly) {
            Plotly.newPlot('clubPointsBarChart', [{
                x: teamNames,
                y: teamPoints,
                type: 'bar',
                marker: { color: '#2196F3' }
            }], {
                title: 'Team Points by Team',
                xaxis: { title: 'Team', tickangle: -45 },
                yaxis: { title: 'Points' },
                margin: { b: 150 }
            }, {responsive: true});
        } else {
            chartDiv.innerHTML = '<div class="alert alert-warning">Plotly not loaded.</div>';
        }
    } catch (error) {
        document.getElementById('clubOverviewCardsRow').innerHTML = `<div class="col-12"><div class="alert alert-danger">Error loading club data: ${error.message}</div></div>`;
        document.querySelector('#clubTeamsTable tbody').innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error loading teams: ${error.message}</td></tr>`;
        document.getElementById('clubTopPerformers').innerHTML = `<div class="alert alert-danger">Error loading top performers: ${error.message}</div>`;
        document.getElementById('clubTrends').innerHTML = `<div class="alert alert-danger">Error loading trends: ${error.message}</div>`;
    }
}

// --- Tennaqua Club Stats Section Logic ---
async function loadTennaquaClubStats() {
    // Show loading states
    document.getElementById('clubStatsOverviewCardsRow').innerHTML = `<div class="col-12 text-center"><div class="spinner-border text-primary" role="status"></div></div>`;
    document.querySelector('#clubStatsTeamsTable tbody').innerHTML = `<tr><td colspan="6" class="text-center">Loading teams...</td></tr>`;
    document.getElementById('clubStatsTopPerformers').innerHTML = `<div class="text-center"><div class="spinner-border text-primary" role="status"></div></div>`;
    document.getElementById('clubStatsTrends').innerHTML = `<div class="text-center"><div class="spinner-border text-primary" role="status"></div></div>`;
    try {
        // 1. Load all teams for Tennaqua from stats file
        const statsResp = await fetch('/data/Chicago_22_stats_20250425.json');
        const stats = await statsResp.json();
        // Filter teams for Tennaqua
        const clubTeams = stats.filter(t => t.team && t.team.startsWith('Tennaqua'));
        if (!clubTeams.length) throw new Error('No teams found for Tennaqua');
        // Overview cards
        const totalTeams = clubTeams.length;
        const totalPoints = clubTeams.reduce((sum, t) => sum + (t.points || 0), 0);
        const avgPoints = totalTeams > 0 ? (totalPoints / totalTeams).toFixed(1) : '0.0';
        const bestTeam = clubTeams.reduce((a, b) => (a.points > b.points ? a : b));
        // Render overview cards
        document.getElementById('clubStatsOverviewCardsRow').innerHTML = `
            <div class="col-md-3 mb-4">
                <div class="card h-100 text-center">
                    <div class="card-header"><h5 class="mb-0"><i class="fas fa-users me-2"></i>Total Teams</h5></div>
                    <div class="card-body"><h2 class="display-4 mb-0 fw-bold">${totalTeams}</h2></div>
                </div>
            </div>
            <div class="col-md-3 mb-4">
                <div class="card h-100 text-center">
                    <div class="card-header"><h5 class="mb-0"><i class="fas fa-star me-2"></i>Total Points</h5></div>
                    <div class="card-body"><h2 class="display-4 mb-0 fw-bold">${totalPoints}</h2></div>
                </div>
            </div>
            <div class="col-md-3 mb-4">
                <div class="card h-100 text-center">
                    <div class="card-header"><h5 class="mb-0"><i class="fas fa-chart-bar me-2"></i>Avg Points/Team</h5></div>
                    <div class="card-body"><h2 class="display-4 mb-0 fw-bold">${avgPoints}</h2></div>
                </div>
            </div>
            <div class="col-md-3 mb-4">
                <div class="card h-100 text-center">
                    <div class="card-header"><h5 class="mb-0"><i class="fas fa-trophy me-2"></i>Best Team</h5></div>
                    <div class="card-body"><h4 class="mb-0">${bestTeam.team}</h4><p class="mb-0">${bestTeam.points} pts</p></div>
                </div>
            </div>
        `;
        // Teams table
        const tbody = document.querySelector('#clubStatsTeamsTable tbody');
        tbody.innerHTML = clubTeams.map(team => `
            <tr>
                <td>${team.team}</td>
                <td>${team.points}</td>
                <td>${team.matches?.won || 0}-${team.matches?.lost || 0}</td>
                <td>${team.matches?.percentage || '0%'}</td>
                <td>${team.sets?.percentage || '0%'}</td>
                <td>${team.games?.percentage || '0%'}</td>
            </tr>
        `).join('');
        // Top performers (placeholder: just show a message for now)
        document.getElementById('clubStatsTopPerformers').innerHTML = `<div class="alert alert-info">Top performers feature coming soon.</div>`;
        // Club trends: bar chart of team points
        const teamNames = clubTeams.map(t => t.team);
        const teamPoints = clubTeams.map(t => t.points);
        const chartDiv = document.createElement('div');
        chartDiv.id = 'clubStatsPointsBarChart';
        chartDiv.style.height = '400px';
        document.getElementById('clubStatsTrends').innerHTML = '';
        document.getElementById('clubStatsTrends').appendChild(chartDiv);
        if (window.Plotly) {
            Plotly.newPlot('clubStatsPointsBarChart', [{
                x: teamNames,
                y: teamPoints,
                type: 'bar',
                marker: { color: '#2196F3' }
            }], {
                title: 'Team Points by Team',
                xaxis: { title: 'Team', tickangle: -45 },
                yaxis: { title: 'Points' },
                margin: { b: 150 }
            }, {responsive: true});
        } else {
            chartDiv.innerHTML = '<div class="alert alert-warning">Plotly not loaded.</div>';
        }
    } catch (error) {
        document.getElementById('clubStatsOverviewCardsRow').innerHTML = `<div class="col-12"><div class="alert alert-danger">Error loading club data: ${error.message}</div></div>`;
        document.querySelector('#clubStatsTeamsTable tbody').innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error loading teams: ${error.message}</td></tr>`;
        document.getElementById('clubStatsTopPerformers').innerHTML = `<div class="alert alert-danger">Error loading top performers: ${error.message}</div>`;
        document.getElementById('clubStatsTrends').innerHTML = `<div class="alert alert-danger">Error loading trends: ${error.message}</div>`;
    }
}

// Call this when the club-stats page is shown
function setupClubStatsPageListener() {
    const origShowContent = window.showContent;
    window.showContent = function(contentId) {
        origShowContent.apply(this, arguments);
        if (contentId === 'club-stats') {
            loadTennaquaClubStats();
        }
    };
}
setupClubStatsPageListener(); 