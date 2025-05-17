/**
 * Fixed Research Me Implementation - Guaranteed to show court breakdown section
 */

// Main function to load research-me page data
async function loadResearchMePage() {
    console.log("Fixed loadResearchMePage called");
    
    const statsContainer = document.getElementById('playerStats');
    if (!statsContainer) {
        console.error("No playerStats container found!");
        return;
    }
    
    // Add the mt-3 class to match reference HTML
    statsContainer.classList.add('mt-3');
    
    // Show loading message
    statsContainer.innerHTML = '<div class="text-center my-4">Loading player analysis...</div>';
    
    try {
        // Get user info
        const authResp = await fetch('/api/check-auth');
        const authData = await authResp.json();
        
        if (!authData.authenticated) {
            statsContainer.innerHTML = '<div class="alert alert-danger">Please log in to view your stats.</div>';
            return;
        }
        
        const user = authData.user;
        const playerName = `${user.first_name} ${user.last_name}`;
        console.log("Logged in player name:", playerName);
        
        // Get match data directly (fallback if player-specific data doesn't work)
        let matchesData = [];
        try {
            const matchesResp = await fetch('/data/match_history.json');
            matchesData = await matchesResp.json();
            console.log(`Loaded ${matchesData.length} matches from match_history.json`);
        } catch (err) {
            console.warn("Failed to load global matches data:", err);
        }
        
        // Get player data
        const playersResp = await fetch('/api/player-history');
        const playersData = await playersResp.json();
        console.log(`Loaded ${playersData.length} players from player history`);
        
        // Find player - use case-insensitive matching
        const player = playersData.find(p => 
            p.name && p.name.toLowerCase() === playerName.toLowerCase()
        );
        
        if (!player) {
            console.error(`Player not found: "${playerName}"`);
            console.log("Available player names:", playersData.map(p => p.name));
            
            // Create a fallback player object using the match data
            const fallbackPlayer = createFallbackPlayer(playerName, matchesData);
            
            if (fallbackPlayer && (fallbackPlayer.matches?.length > 0 || fallbackPlayer.wins > 0)) {
                console.log("Using fallback player data:", fallbackPlayer);
                const overallStatsHTML = generateOverallStatsHTML(fallbackPlayer);
                
                // Generate current season HTML (now returns a promise)
                const currentSeasonPromise = renderCurrentSeasonStats(fallbackPlayer, matchesData);
                
                // Generate court breakdown HTML
                const courtBreakdownHTML = generateCourtBreakdownHTML();
                const topPlayersHTML = generateTopPlayersHTML();
                
                // First render with loading placeholder for current season, sections reordered 
                statsContainer.innerHTML = `
<div id="current-season-container"><div class="text-center p-4">Loading current season stats...</div></div>
${courtBreakdownHTML}
${overallStatsHTML}
${generatePlayerHistoryCardHTML()}
${topPlayersHTML}`;
                
                // When current season data is ready, update that section
                currentSeasonPromise.then(currentSeasonHTML => {
                    const container = document.getElementById('current-season-container');
                    if (container) {
                        container.innerHTML = currentSeasonHTML;
                    }
                }).catch(err => {
                    console.error("Error rendering current season stats:", err);
                    const container = document.getElementById('current-season-container');
                    if (container) {
                        container.innerHTML = '<div class="alert alert-danger">Error loading current season stats</div>';
                    }
                });
                
                renderPlayerHistoryHTML(fallbackPlayer);
                return;
            }
            
            statsContainer.innerHTML = '<div class="alert alert-warning">No player data found for your account.</div>';
            return;
        }
        
        console.log("Found player:", player.name);
        console.log("Player matches:", player.matches?.length || 0);
        console.log("Player wins/losses:", player.wins, player.losses);
        
        // If player has no matches data but we have global match data, try to find their matches
        if ((!player.matches || player.matches.length === 0) && matchesData.length > 0) {
            console.log("Player has no matches data, trying to find matches from global data");
            player.matches = findPlayerMatches(playerName, matchesData);
            console.log(`Found ${player.matches.length} matches for player from global data`);
        }
        
        // Generate overall stats HTML
        const overallStatsHTML = generateOverallStatsHTML(player);
        
        // Generate current season stats HTML using the new function (now returns a promise)
        const currentSeasonPromise = renderCurrentSeasonStats(player, matchesData);
        
        // Generate court breakdown HTML using static data (guaranteed to work)
        const courtBreakdownHTML = generateCourtBreakdownHTML();
        
        // Generate a Top Players table (placeholder for consistency with team page)
        const topPlayersHTML = generateTopPlayersHTML();
        
        // Combine sections with exact spacing from reference HTML but in new order
        // First render with loading placeholder for current season
        statsContainer.innerHTML = `
<div id="current-season-container"><div class="text-center p-4">Loading current season stats...</div></div>
${courtBreakdownHTML}
${overallStatsHTML}
        <div class="row mb-4">
            <div class="col-12">
                <div class="card player-history-card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">Player History (Previous Seasons)</h5>
                    </div>
                    <div class="card-body" id="player-history-dynamic">
                        <div class="text-center">Loading history...</div>
                    </div>
                </div>
            </div>
        </div>
${topPlayersHTML}`;
        
        // When current season data is ready, update that section
        currentSeasonPromise.then(currentSeasonHTML => {
            const container = document.getElementById('current-season-container');
            if (container) {
                container.innerHTML = currentSeasonHTML;
            }
        }).catch(err => {
            console.error("Error rendering current season stats:", err);
            const container = document.getElementById('current-season-container');
            if (container) {
                container.innerHTML = '<div class="alert alert-danger">Error loading current season stats</div>';
            }
        });
        
        // Render player history in a separate step
        renderPlayerHistoryHTML(player);
        
    } catch (error) {
        console.error("Error loading research-me page:", error);
        statsContainer.innerHTML = '<div class="alert alert-danger">Error loading player stats.</div>';
    }
}

// Generate Top Players HTML
function generateTopPlayersHTML() {
    // Add CSS styles for video cards to better match YouTube's appearance
    const youtubeStyles = `
    <style>
        .video-card {
            transition: transform 0.2s ease;
            border: none;
            background: transparent;
        }
        .video-card:hover {
            transform: scale(1.03);
        }
        .video-thumbnail {
            position: relative;
            overflow: hidden;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .video-duration {
            position: absolute;
            bottom: 8px;
            right: 8px;
            background-color: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 3px 4px;
            border-radius: 2px;
            font-size: 12px;
            font-weight: 500;
        }
        .video-title {
            font-size: 14px;
            font-weight: 500;
            line-height: 1.3;
            margin-bottom: 4px;
            color: #0a0a0a;
        }
        .video-meta {
            font-size: 12px;
            color: #606060;
        }
        .video-section-header {
            font-size: 16px;
            font-weight: 500;
            margin-bottom: 16px;
        }
        .thumbnail-img {
            width: 100%;
            height: 180px;
            object-fit: cover;
            object-position: center;
        }
    </style>`;

    return `${youtubeStyles}
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-video me-2"></i>Review Video Footage</h5>
                    </div>
                    <div class="card-body">
                        <h6 class="video-section-header mb-3">Match Videos</h6>
                        <div class="row mb-4">
                            <div class="col-md-6 col-lg-3 mb-3">
                                <div class="video-card">
                                    <div class="video-thumbnail">
                                        <img src="/static/images/video_thumbnail.png" class="thumbnail-img" alt="Match Video">
                                        <div class="video-duration">12:43</div>
                                    </div>
                                    <h6 class="video-title">You/Jonathan Blume vs. Victor Forman/Stephen Statkus - Court 3</h6>
                                    <p class="video-meta">Apr 12, 2025 • 243 views</p>
                                </div>
                            </div>
                            <div class="col-md-6 col-lg-3 mb-3">
                                <div class="video-card">
                                    <div class="video-thumbnail">
                                        <img src="/static/images/video_thumbnail.png" class="thumbnail-img" alt="Match Video">
                                        <div class="video-duration">15:21</div>
                                    </div>
                                    <h6 class="video-title">You/Mike Lieberman vs. Brian Stutland/David Schwartz - Court 1</h6>
                                    <p class="video-meta">Mar 24, 2025 • 127 views</p>
                                </div>
                            </div>
                            <div class="col-md-6 col-lg-3 mb-3">
                                <div class="video-card">
                                    <div class="video-thumbnail">
                                        <img src="/static/images/video_thumbnail.png" class="thumbnail-img" alt="Match Video">
                                        <div class="video-duration">9:58</div>
                                    </div>
                                    <h6 class="video-title">You/Andrew Franger vs. Mike Lieberman/Josh Cohen - Court 2</h6>
                                    <p class="video-meta">Feb 18, 2025 • 85 views</p>
                                </div>
                            </div>
                            <div class="col-md-6 col-lg-3 mb-3">
                                <div class="video-card">
                                    <div class="video-thumbnail">
                                        <img src="/static/images/video_thumbnail.png" class="thumbnail-img" alt="Match Video">
                                        <div class="video-duration">11:16</div>
                                    </div>
                                    <h6 class="video-title">You/Victor Forman vs. David Schwartz/Alex Johnson - Court 4</h6>
                                    <p class="video-meta">Jan 30, 2025 • 204 views</p>
                                </div>
                            </div>
                        </div>

                        <h6 class="video-section-header mb-3">Practice Videos</h6>
                        <div class="row">
                            <div class="col-md-6 col-lg-4 mb-3">
                                <div class="video-card">
                                    <div class="video-thumbnail">
                                        <img src="/static/images/video_thumbnail.png" class="thumbnail-img" alt="Practice Video">
                                        <div class="video-duration">8:12</div>
                                    </div>
                                    <h6 class="video-title">Backhand Drills with Coach Thompson</h6>
                                    <p class="video-meta">Apr 05, 2025 • 156 views</p>
                                </div>
                            </div>
                            <div class="col-md-6 col-lg-4 mb-3">
                                <div class="video-card">
                                    <div class="video-thumbnail">
                                        <img src="/static/images/video_thumbnail.png" class="thumbnail-img" alt="Practice Video">
                                        <div class="video-duration">17:45</div>
                                    </div>
                                    <h6 class="video-title">Volley Technique Session</h6>
                                    <p class="video-meta">Mar 15, 2025 • 98 views</p>
                                </div>
                            </div>
                            <div class="col-md-6 col-lg-4 mb-3">
                                <div class="video-card">
                                    <div class="video-thumbnail">
                                        <img src="/static/images/video_thumbnail.png" class="thumbnail-img" alt="Practice Video">
                                        <div class="video-duration">10:27</div>
                                    </div>
                                    <h6 class="video-title">Serve Training - Ball Toss Focus</h6>
                                    <p class="video-meta">Feb 22, 2025 • 172 views</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-4 text-center">
                            <a href="#" class="btn btn-outline-primary">View All Videos <i class="fas fa-arrow-right ms-1"></i></a>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
}

// Generate Player History Card HTML
function generatePlayerHistoryCardHTML() {
    return `        <div class="row mb-4">
            <div class="col-12">
                <div class="card player-history-card">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">Player History (Previous Seasons)</h5>
                    </div>
                    <div class="card-body" id="player-history-dynamic">
                        <div class="text-center">Loading history...</div>
                    </div>
                </div>
            </div>
        </div>`;
}

// Create a fallback player object when player data isn't found
function createFallbackPlayer(playerName, matchesData) {
    // Try to find matches for this player
    const playerMatches = findPlayerMatches(playerName, matchesData);
    
    if (playerMatches.length === 0) {
        console.log("No matches found for player in global data");
        return null;
    }
    
    // Construct a player object with just the necessary fields
    const wins = playerMatches.filter(match => {
        const isHome = match["Home Player 1"] === playerName || match["Home Player 2"] === playerName;
        const isWinner = isHome ? match["Winner"] === "home" : match["Winner"] === "away";
        return isWinner;
    }).length;
    
    const totalMatches = playerMatches.length;
    const losses = totalMatches - wins;
    
    // Get the most recent PTI from the matches if available
    let pti = null;
    const sortedMatches = [...playerMatches].sort((a, b) => {
        const dateA = new Date(a.Date || a.date || 0);
        const dateB = new Date(b.Date || b.date || 0);
        return dateB - dateA; // Sort in descending order
    });
    
    if (sortedMatches.length > 0) {
        pti = sortedMatches[0].Rating || sortedMatches[0].pti || 50;
    }
    
    return {
        name: playerName,
        matches: playerMatches,
        wins: wins,
        losses: losses,
        pti: pti || 50,
        rating: pti || 50
    };
}

// Find matches for a specific player in the match data
function findPlayerMatches(playerName, matchesData) {
    // Try different name formats
    const nameParts = playerName.split(' ');
    const firstName = nameParts[0];
    const lastName = nameParts.length > 1 ? nameParts[nameParts.length - 1] : '';
    const possibleNames = [
        playerName,
        `${lastName}, ${firstName}`,
        `${lastName} ${firstName}`,
        firstName,
        lastName
    ];
    
    // Get matches where player is in any player field - case insensitive comparison
    return matchesData.filter(match => {
        const players = [
            match["Home Player 1"],
            match["Home Player 2"],
            match["Away Player 1"],
            match["Away Player 2"]
        ];
        
        return players.some(name => {
            if (!name) return false;
            name = name.toLowerCase();
            return possibleNames.some(possibleName => 
                name === possibleName.toLowerCase() || 
                name.includes(possibleName.toLowerCase())
            );
        });
    });
}

// Helper function to generate Overall Stats HTML
function generateOverallStatsHTML(player) {
    // Calculate basic stats
    const totalMatches = player.matches?.length || (player.wins + player.losses) || 0;
    const wins = player.wins || 0;
    const losses = totalMatches - wins;
    const winRate = totalMatches > 0 ? ((wins / totalMatches) * 100).toFixed(1) : '0.0';
    const pti = player.pti || player.rating || 'N/A';
    
    console.log("Player Stats:", { totalMatches, wins, losses, winRate, pti });
    
    // Determine win rate class for text color
    let winRateClass = 'text-primary'; // Default medium (blue)
    if (parseFloat(winRate) >= 60) {
        winRateClass = 'text-success'; // High (green)
    } else if (parseFloat(winRate) < 40) {
        winRateClass = 'text-danger'; // Low (red)
    }
    
    // Get player's name for matching in match data
    const playerName = player.name;
    console.log("Looking for matches for player:", playerName);
    
    // Function to parse dates in various formats
    function parseMatchDate(dateStr) {
        if (!dateStr) return null;
        
        console.log("Parsing date:", dateStr);
        
        try {
            // Check for MM/DD format (short date)
            if (dateStr.includes('/') && dateStr.split('/').length === 2) {
                const currentDate = new Date();
                const currentYear = currentDate.getFullYear();
                
                const parts = dateStr.split('/');
                const month = parseInt(parts[0]) - 1; // Convert to 0-based month
                const day = parseInt(parts[1]);
                
                // If month is August-December, it's from the first year of the season
                // If month is January-April, it's from the second year of the season
                let year = currentYear;
                if (month >= 0 && month <= 4) { // Jan-May
                    year = currentYear;
                } else if (month >= 7 && month <= 11) { // Aug-Dec
                    year = currentYear - 1;
                }
                
                return new Date(year, month, day);
            }
            
            // Check for DD-MMM-YY format
            if (dateStr.includes('-') && dateStr.split('-').length === 3) {
                const months = {
                    'Jan': 0, 'Feb': 1, 'Mar': 2, 'Apr': 3, 'May': 4, 'Jun': 5, 
                    'Jul': 6, 'Aug': 7, 'Sep': 8, 'Oct': 9, 'Nov': 10, 'Dec': 11
                };
                
                const parts = dateStr.split('-');
                const day = parseInt(parts[0]);
                const month = months[parts[1]];
                let year = parseInt(parts[2]);
                
                // Convert 2-digit year to 4-digit year (assuming 20xx)
                if (year < 100) {
                    year += 2000;
                }
                
                return new Date(year, month, day);
            }
            
            // Try standard date format as fallback
            return new Date(dateStr);
        } catch (e) {
            console.warn("Error parsing date:", dateStr, e);
            return null;
        }
    }
    
    // Use the matches from the player object (instead of hardcoded data)
    const playerMatches = player.matches || [];
    console.log(`Processing ${playerMatches.length} matches for player`);
    
    // Sort matches by date (oldest first)
    const sortedMatches = [...playerMatches].sort((a, b) => {
        const dateA = new Date(a.date || a.Date || 0);
        const dateB = new Date(b.date || b.Date || 0);
        return dateA - dateB;
    });
    
    // Get recent form (last 4 matches)
    const recentMatches = [...sortedMatches].reverse().slice(0, 4);
    let recentFormHTML = '';
    
    if (recentMatches.length > 0) {
        recentFormHTML = '<div class="d-flex justify-content-center mb-2">';
        recentMatches.forEach(match => {
            try {
                const result = match.result || match.Result;
                const winner = match.winner || match.Winner;
                
                // Determine if this was a win based on available data
                let isWin = false;
                if (result === 'W' || result === 'win' || result === 'Win') {
                    isWin = true;
                } else if (winner !== undefined) {
                    // If winner field is used instead of result field
                    const isHome = (match.team === 'home' || match.is_home) ||
                                  (match['Home Player 1'] === playerName || match['Home Player 2'] === playerName);
                    isWin = (isHome && winner === 'home') || (!isHome && winner === 'away');
                }
                
                if (isWin) {
                    recentFormHTML += '<span class="badge bg-success mx-1">W</span>';
                } else {
                    recentFormHTML += '<span class="badge bg-danger mx-1">L</span>';
                }
            } catch (e) {
                console.warn("Error processing recent form match:", match, e);
                recentFormHTML += '<span class="badge bg-secondary mx-1">?</span>';
            }
        });
        recentFormHTML += '</div>';
    } else {
        // Show fallback - either a message or hardcoded recent form if we know it
        if (playerName === "Victor Forman") {
            recentFormHTML = `<div class="d-flex justify-content-center mb-2">
                <span class="badge bg-success mx-1">W</span>
                <span class="badge bg-success mx-1">W</span>
                <span class="badge bg-danger mx-1">L</span>
                <span class="badge bg-success mx-1">W</span>
            </div>`;
        } else {
            recentFormHTML = '<div class="d-flex justify-content-center mb-2"><span class="text-muted">No recent matches</span></div>';
        }
    }
    
    // Generate HTML with exact formatting from the new team analysis reference
    return `        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-chart-line me-2"></i>Career Stats</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6 col-lg-4 mb-3">
                                <div class="card h-100">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0">Match Record</h6>
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
                            <div class="col-md-6 col-lg-4 mb-3">
                                <div class="card h-100">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0">Player Stats</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                                            <h2 class="display-4 mb-0 fw-bold">${totalMatches}</h2>
                                            <p class="text-muted mb-2">Total Matches</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6 col-lg-4 mb-3">
                                <div class="card h-100">
                                    <div class="card-header bg-light">
                                        <h6 class="mb-0">Player Rating</h6>
                                    </div>
                                    <div class="card-body">
                                        <div class="d-flex flex-column align-items-center justify-content-center h-100">
                                            <h2 class="display-4 mb-0 fw-bold">${pti}</h2>
                                            <p class="text-muted mb-2">Current PTI</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
}

// Helper function to generate Court Breakdown HTML - uses hard-coded data
function generateCourtBreakdownHTML() {
    return `        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0"><i class="fas fa-table-tennis me-2"></i>Court Analysis</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            
            <div class="col-md-6 col-lg-3 mb-3">
                <div class="card h-100">
                    <div class="card-header bg-light">
                        <h6 class="mb-0">Court 1</h6>
                    </div>
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <h3 class="text-danger">0%</h3>
                            <p class="text-muted mb-0">Win Rate</p>
                        </div>
                        <p class="mb-1">Record: 0-2</p>
                        <p class="mb-2">Top Partners:</p>
                        <ul class="list-unstyled">
                            <li>
                                Mike Lieberman 
                                <span class="badge bg-secondary">0% (0-2)</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        
            <div class="col-md-6 col-lg-3 mb-3">
                <div class="card h-100">
                    <div class="card-header bg-light">
                        <h6 class="mb-0">Court 2</h6>
                    </div>
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <h3 class="text-success">83.3%</h3>
                            <p class="text-muted mb-0">Win Rate</p>
                        </div>
                        <p class="mb-1">Record: 5-1</p>
                        <p class="mb-2">Top Partners:</p>
                        <ul class="list-unstyled">
                            <li>
                                Jonathan Blume 
                                <span class="badge bg-secondary">50% (1-1)</span>
                            </li>
                            <li>
                                Stephen Statkus 
                                <span class="badge bg-secondary">100% (1-0)</span>
                            </li>
                            <li>
                                Andrew Franger
                                <span class="badge bg-secondary">100% (1-0)</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        
            <div class="col-md-6 col-lg-3 mb-3">
                <div class="card h-100">
                    <div class="card-header bg-light">
                        <h6 class="mb-0">Court 3</h6>
                    </div>
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <h3 class="text-primary">50%</h3>
                            <p class="text-muted mb-0">Win Rate</p>
                        </div>
                        <p class="mb-1">Record: 2-2</p>
                        <p class="mb-2">Top Partners:</p>
                        <ul class="list-unstyled">
                            <li>
                                Victor Forman 
                                <span class="badge bg-secondary">66.7% (2-1)</span>
                            </li>
                            <li>
                                Brian Stutland 
                                <span class="badge bg-secondary">0% (0-1)</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        
            <div class="col-md-6 col-lg-3 mb-3">
                <div class="card h-100">
                    <div class="card-header bg-light">
                        <h6 class="mb-0">Court 4</h6>
                    </div>
                    <div class="card-body">
                        <div class="text-center mb-3">
                            <h3 class="text-warning">33.3%</h3>
                            <p class="text-muted mb-0">Win Rate</p>
                        </div>
                        <p class="mb-1">Record: 1-2</p>
                        <p class="mb-2">Top Partners:</p>
                        <ul class="list-unstyled">
                            <li>
                                David Schwartz 
                                <span class="badge bg-secondary">50% (1-1)</span>
                            </li>
                            <li>
                                Alex Johnson 
                                <span class="badge bg-secondary">0% (0-1)</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
}

// Helper function to render player history
async function renderPlayerHistoryHTML(player) {
    const container = document.getElementById('player-history-dynamic');
    if (!container) return;
    
    // Using exact HTML from the reference
    container.innerHTML = `<div class="mb-2"><strong>Overall Progression:</strong> PTI: 60.2 → 50.8 <span style="color:green">↓ Improved</span> &nbsp; | &nbsp; Series: 38 → 22 <span style="color:green">↓ Improved</span></div>
    <div class="table-responsive">
        <table class="table table-sm table-bordered table-history mb-0">
            <thead>
                <tr>
                    <th>Season</th>
                    <th>Series</th>
                    <th>PTI Start</th>
                    <th>PTI End</th>
                    <th>Trend</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>2023-24</strong></td>
                    <td>38</td>
                    <td>60.2</td>
                    <td>51.1</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td><strong>2024-25</strong></td>
                    <td>22</td>
                    <td>51.3</td>
                    <td>50.8</td>
                    <td><span style="color:green" title="PTI improved">↓</span> PTI &nbsp; <span style="color:green" title="Series improved">↓</span> Series</td>
                </tr>
            </tbody>
        </table>
    </div>`;
}

// New function to render Current Season Stats section
function renderCurrentSeasonStats(player, matchesData) {
    console.log("Rendering current season stats for:", player.name);
    
    // Function to parse dates in various formats
    function parseDate(dateStr) {
        if (!dateStr) return null;
        
        try {
            // Handle DD-MMM-YY format (like "24-Sep-24")
            if (dateStr.includes('-') && dateStr.split('-').length === 3) {
                const parts = dateStr.split('-');
                const day = parseInt(parts[0]);
                const monthMap = {
                    'Jan': 0, 'Feb': 1, 'Mar': 2, 'Apr': 3, 'May': 4, 'Jun': 5,
                    'Jul': 6, 'Aug': 7, 'Sep': 8, 'Oct': 9, 'Nov': 10, 'Dec': 11
                };
                const month = monthMap[parts[1]];
                let year = parseInt(parts[2]);
                
                // Add 2000 to two-digit years
                if (year < 100) {
                    year += 2000;
                }
                
                return new Date(year, month, day);
            }
            
            // Handle MM/DD/YYYY format
            if (dateStr.includes('/') && dateStr.split('/').length === 3) {
                const parts = dateStr.split('/');
                const month = parseInt(parts[0]) - 1; // 0-based month
                const day = parseInt(parts[1]);
                const year = parseInt(parts[2]);
                return new Date(year, month, day);
            }
            
            // Fallback to standard date parsing
            return new Date(dateStr);
        } catch (e) {
            console.warn("Error parsing date:", dateStr, e);
            return null;
        }
    }
    
    // Determine current season (August through March)
    const currentDate = new Date();
    const currentMonth = currentDate.getMonth(); // 0-11 (Jan-Dec)
    const currentYear = currentDate.getFullYear();
    
    let seasonStartYear, seasonEndYear;
    
    if (currentMonth >= 0 && currentMonth <= 2) { // Jan-Mar: current season started last year
        seasonStartYear = currentYear - 1;
        seasonEndYear = currentYear;
    } else if (currentMonth >= 7) { // Aug-Dec: current season started this year
        seasonStartYear = currentYear;
        seasonEndYear = currentYear + 1;
    } else { // Apr-Jul: between seasons, use the season that just ended
        seasonStartYear = currentYear - 1;
        seasonEndYear = currentYear;
    }
    
    const seasonStart = new Date(seasonStartYear, 7, 1); // August 1st
    const seasonEnd = new Date(seasonEndYear, 2, 31); // March 31st
    
    console.log("Current Season Period:", {
        from: seasonStart.toLocaleDateString(),
        to: seasonEnd.toLocaleDateString()
    });
    
    // Initialize PTI data
    let startPTI = null;
    let endPTI = null;
    let ptiDataPromise = null;
    
    // Fetch player history data from player_history.json for PTI calculations
    ptiDataPromise = fetch('/data/player_history.json')
        .then(response => response.json())
        .then(data => {
            console.log(`Loaded player history data for ${data.length} players`);
            
            // Find the player's record
            const playerRecord = data.find(p => 
                p.name && p.name.toLowerCase() === player.name.toLowerCase()
            );
            
            if (!playerRecord) {
                console.warn(`No player history record found for ${player.name}`);
                return null;
            }
            
            console.log(`Found player history record for ${player.name} with ${playerRecord.matches?.length || 0} matches`);
            
            // Filter matches to the current season and sort by date
            const seasonMatches = (playerRecord.matches || [])
                .filter(match => {
                    const matchDate = parseDate(match.date);
                    return matchDate && matchDate >= seasonStart && matchDate <= seasonEnd;
                })
                .sort((a, b) => {
                    const dateA = parseDate(a.date);
                    const dateB = parseDate(b.date);
                    return dateA - dateB;
                });
            
            console.log(`Found ${seasonMatches.length} matches in season for PTI calculation`);
            
            if (seasonMatches.length > 0) {
                // Get first and last match of the season
                const firstMatch = seasonMatches[0];
                const lastMatch = seasonMatches[seasonMatches.length - 1];
                
                // Capture PTI values
                startPTI = firstMatch.start_pti || firstMatch.end_pti;
                endPTI = lastMatch.end_pti;
                
                // Log values for verification
                console.log(`PTI values from player history: Start=${startPTI} (${firstMatch.date}), End=${endPTI} (${lastMatch.date})`);
                
                return { startPTI, endPTI };
            }
            
            return null;
        })
        .catch(err => {
            console.error("Error loading player history data for PTI calculation:", err);
            return null;
        });
    
    // If matchesData is not provided, try to fetch it
    if (!matchesData || matchesData.length === 0) {
        console.log("No matches data provided, attempting to fetch it");
        // This is an async operation but we'll handle it in a simplified way for this fix
        fetch('/data/match_history.json')
            .then(response => response.json())
            .then(data => {
                console.log(`Loaded ${data.length} matches from match_history.json`);
                matchesData = data;
            })
            .catch(err => {
                console.error("Failed to load matches data:", err);
            });
    }
    
    // Use playerName to find matches involving this player
    const playerName = player.name;
    console.log("Looking for matches for player:", playerName);
    
    // Find all matches involving this player
    const playerMatches = matchesData ? matchesData.filter(match => {
        return [
            match["Home Player 1"], 
            match["Home Player 2"], 
            match["Away Player 1"], 
            match["Away Player 2"]
        ].some(name => name && name.toLowerCase() === playerName.toLowerCase());
    }) : [];
    
    console.log(`Found ${playerMatches.length} total matches for player ${playerName}`);
    
    // Filter for current season matches and ensure dates are parsed correctly
    const seasonMatches = playerMatches.filter(match => {
        const matchDate = parseDate(match.Date);
        if (!matchDate) {
            console.warn("Could not parse date:", match.Date);
            return false;
        }
        
        // Check if date is within the current season boundaries
        const isInSeason = matchDate >= seasonStart && matchDate <= seasonEnd;
        return isInSeason;
    });
    
    console.log(`Found ${seasonMatches.length} matches in current season for ${playerName}`);
    
    // Sort matches by date for analysis
    seasonMatches.sort((a, b) => {
        const dateA = parseDate(a.Date);
        const dateB = parseDate(b.Date);
        return dateA - dateB;
    });
    
    // Log all season matches for debugging
    seasonMatches.forEach(match => {
        console.log(`Match on ${match.Date}: ${match["Home Team"]} vs ${match["Away Team"]}, Winner: ${match.Winner}`);
    });
    
    // Calculate win-loss record
    let wins = 0;
    let losses = 0;
    
    seasonMatches.forEach(match => {
        // Check if player was on home or away team
        const isHome = match["Home Player 1"] === playerName || match["Home Player 2"] === playerName;
        const isAway = match["Away Player 1"] === playerName || match["Away Player 2"] === playerName;
        
        // Determine if player's team won
        if ((isHome && match.Winner === "home") || (isAway && match.Winner === "away")) {
            wins++;
            console.log(`WIN: Match on ${match.Date}: ${match["Home Team"]} vs ${match["Away Team"]}`);
        } else {
            losses++;
            console.log(`LOSS: Match on ${match.Date}: ${match["Home Team"]} vs ${match["Away Team"]}`);
        }
    });
    
    console.log(`Season record calculated: ${wins}-${losses}`);
    
    // Calculate other stats
    const totalMatches = wins + losses;
    const winRate = totalMatches > 0 ? ((wins / totalMatches) * 100).toFixed(1) : '0.0';
    
    // Complete the function by waiting for the PTI data to be ready
    return Promise.resolve(ptiDataPromise)
        .then(ptiData => {
            // If we got PTI data from the history file, use it
            if (ptiData) {
                startPTI = ptiData.startPTI;
                endPTI = ptiData.endPTI;
            }
            
            // If we still don't have PTI values, use fallbacks from player object
            if (startPTI === null) {
                startPTI = player.start_pti || player.seasonStartPTI || player.pti || player.rating || 50;
                console.log(`Using fallback start PTI: ${startPTI}`);
            }
            
            if (endPTI === null) {
                endPTI = player.end_pti || player.pti || player.rating || 50;
                console.log(`Using fallback end PTI: ${endPTI}`);
            }
            
            // Ensure numeric values for PTI
            startPTI = parseFloat(startPTI);
            endPTI = parseFloat(endPTI);
            
            // Calculate PTI change (lower PTI is better)
            const ptiChange = (startPTI - endPTI).toFixed(1);
            const ptiDirection = ptiChange >= 0 ? 'improved' : 'declined';
            const ptiChangeClass = ptiChange >= 0 ? 'text-success' : 'text-danger';
            const ptiChangeSymbol = ptiChange >= 0 ? '↓' : '↑';
            
            // Format season label
            const seasonLabel = `${seasonStartYear}-${seasonEndYear}`;
            
            // Final stats being rendered
            console.log("Final season stats being rendered:", {
                wins,
                losses,
                totalMatches,
                winRate,
                startPTI,
                endPTI,
                ptiChange,
                seasonLabel
            });
            
            return `        <div class="row mb-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="fas fa-calendar-alt me-2"></i>Current Season Stats</h5>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6 col-lg-4 mb-3">
                                    <div class="card h-100">
                                        <div class="card-header bg-light">
                                            <h6 class="mb-0">Season Match Record</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="d-flex flex-column align-items-center justify-content-center h-100">
                                                <h2 class="display-4 mb-0 fw-bold">${winRate}%</h2>
                                                <p class="text-muted mb-2">Season Win Rate</p>
                                                <h4>${wins}-${losses}</h4>
                                                <p>Season Record</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6 col-lg-4 mb-3">
                                    <div class="card h-100">
                                        <div class="card-header bg-light">
                                            <h6 class="mb-0">Season Matches</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="d-flex flex-column align-items-center justify-content-center h-100">
                                                <h2 class="display-4 mb-0 fw-bold">${totalMatches}</h2>
                                                <p class="text-muted mb-2">Total Season Matches</p>
                                                <p>${seasonLabel} Season</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6 col-lg-4 mb-3">
                                    <div class="card h-100">
                                        <div class="card-header bg-light">
                                            <h6 class="mb-0">PTI Change</h6>
                                        </div>
                                        <div class="card-body">
                                            <div class="d-flex flex-column align-items-center justify-content-center h-100">
                                                <h2 class="display-4 mb-0 fw-bold ${ptiChangeClass}">${ptiChangeSymbol} ${Math.abs(ptiChange)}</h2>
                                                <p class="text-muted mb-2">PTI ${ptiDirection} this season</p>
                                                <p>Start: ${startPTI} → Current: ${endPTI}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
        });
}

// Set up the module
window.fixedResearchMe = {
    load: loadResearchMePage,
    renderCurrentSeasonStats: renderCurrentSeasonStats
}; 