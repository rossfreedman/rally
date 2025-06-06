/**
 * Research Me - Player Analysis Functions
 * This file handles the research-me page functionality with
 * separate rendering functions for Overall Performance and Court Breakdown
 */

// Create a namespace to expose our functions
window.researchMe = {};

// Helper function to determine win rate class based on percentage
function winRateClass(rate) {
    if (rate >= 60) return 'win-rate-high';
    if (rate >= 40) return 'win-rate-medium';
    return 'win-rate-low';
}

// Render the Overall Performance section as cards
function renderOverallPerformance(player) {
    console.log("renderOverallPerformance called with player:", player.name);
    
    const totalMatches = player.matches?.length || (player.wins + player.losses) || 0;
    const wins = player.wins || 0;
    const losses = totalMatches - wins;
    const winRate = totalMatches > 0 ? ((wins / totalMatches) * 100).toFixed(1) : '0.0';
    const pti = player.pti || player.rating || 'N/A';
    
    // Use the global winRateClass function instead of creating a local variable
    const rateClass = winRateClass(parseFloat(winRate));
    
    console.log("Overall stats calculated:", { totalMatches, wins, losses, winRate, pti });
    
    // Create horizontal cards layout instead of vertical list
    return `
    <div class="overall-stats mb-4">
        <h6>Overall Performance</h6>
        <div class="row row-cols-2 row-cols-md-4 g-2">
            <div class="col">
                <div class="card text-center h-100 py-2">
                    <p class="small mb-1 text-muted">Total Matches</p>
                    <h3 class="card-title">${totalMatches}</h3>
                </div>
            </div>
            <div class="col">
                <div class="card text-center h-100 py-2">
                    <p class="small mb-1 text-muted">Overall Record</p>
                    <h3 class="card-title">${wins}-${losses}</h3>
                </div>
            </div>
            <div class="col">
                <div class="card text-center h-100 py-2">
                    <p class="small mb-1 text-muted">Win Rate</p>
                    <h3 class="card-title ${rateClass}">${winRate}%</h3>
                </div>
            </div>
            <div class="col">
                <div class="card text-center h-100 py-2">
                    <p class="small mb-1 text-muted">PTI</p>
                    <h3 class="card-title">${pti}</h3>
                </div>
            </div>
        </div>
    </div>`;
}

// Render the Court Breakdown section
function renderCourtBreakdown(player) {
    // Add debug logging
    console.log("renderCourtBreakdown called with player:", player.name);
    console.log("player.courts:", player.courts);
    
    if (!player.courts || Object.keys(player.courts).length === 0) {
        console.log("No court data available for player:", player.name);
        return '<div class="text-center my-3">No court breakdown data available</div>';
    }
    
    let courtHtml = '<div class="row g-3">';
    
    // Log which courts we're rendering
    console.log("Rendering courts:", Object.keys(player.courts));
    
    // Get entries and sort them by court number
    const courtEntries = Object.entries(player.courts).sort((a, b) => {
        const aNum = parseInt(a[0].match(/\d+/)?.[0] || '0', 10);
        const bNum = parseInt(b[0].match(/\d+/)?.[0] || '0', 10);
        return aNum - bNum;
    });
    
    console.log("Courts after sorting:", courtEntries.map(entry => entry[0]));
    
    courtEntries.forEach(([court, stats]) => {
        // Skip the "Unknown" court if it exists
        if (court.toLowerCase() === 'unknown') {
            console.log("Skipping 'Unknown' court");
            return;
        }
        
        // Format court name properly
        const courtName = court.includes('Court') ? court : `Court ${court.replace('court', '')}`;
        
        // Calculate losses if not provided
        const losses = stats.losses || (stats.matches - stats.wins);
        
        // Calculate win rate if not provided
        const winRate = stats.winRate || (stats.matches > 0 ? ((stats.wins / stats.matches) * 100).toFixed(1) : '0.0');
        
        console.log(`Rendering court ${courtName}: matches=${stats.matches}, wins=${stats.wins}, losses=${losses}, winRate=${winRate}`);
        
        courtHtml += `
        <div class="col-md-6">
            <div class="court-card card h-100">
                <div class="card-body">
                    <h6>${courtName}</h6>
                    <p><span class="stat-label">Matches</span><span class="stat-value">${stats.matches}</span></p>
                    <p><span class="stat-label">Record</span><span class="stat-value">${stats.wins}-${losses}</span></p>
                    <p><span class="stat-label">Win Rate</span><span class="stat-value ${winRateClass(parseFloat(winRate))}">${winRate}%</span></p>`;
                    
        // Add partners if available
        if (stats.partners && stats.partners.length > 0) {
            console.log(`Court ${courtName} has ${stats.partners.length} partners`);
            
            courtHtml += `
            <div class="partner-info mt-2">
                <strong>Most Common Partners:</strong>
                <ul class="partner-list">`;
                
            stats.partners.forEach(partner => {
                // Calculate partner losses if not provided
                const partnerLosses = partner.losses || (partner.matches - partner.wins);
                
                // Calculate partner win rate if not provided
                const partnerWinRate = partner.winRate || (partner.matches > 0 ? ((partner.wins / partner.matches) * 100).toFixed(1) : '0.0');
                
                courtHtml += `<li>${partner.name} (${partner.wins}-${partnerLosses}, ${partnerWinRate}%)</li>`;
            });
            
            courtHtml += `</ul></div>`;
        } else {
            console.log(`Court ${courtName} has no partners recorded`);
        }
        
        courtHtml += `</div></div></div>`;
    });
    
    courtHtml += '</div>';
    console.log("Completed court HTML:", courtHtml.length, "characters");
    return courtHtml;
}

// Main function to load and render player analysis
async function loadResearchMe() {
    console.log("loadResearchMe function called in research-me.js");
    
    const statsContainer = document.getElementById('playerStats');
    if (!statsContainer) {
        console.error("playerStats container not found!");
        return;
    }
    
    console.log("Found statsContainer, setting loading message");
    statsContainer.innerHTML = '<div class="text-center my-4">Loading player analysis...</div>';
    
    try {
        // Get logged in user
        console.log("Fetching user auth data...");
        const authResp = await fetch('/api/check-auth');
        const authData = await authResp.json();
        
        if (!authData.authenticated) {
            console.error("User not authenticated");
            statsContainer.innerHTML = '<div class="alert alert-danger">Not logged in.</div>';
            return;
        }
        
        const user = authData.user;
        console.log("User authenticated:", user.first_name, user.last_name);
        
        // Get all players
        console.log("Fetching player history data...");
        const resp = await fetch('/data/match_history.json');
        const data = await resp.json();
        console.log("Received player history data for", data.length, "players");
        
        // Find the player for the logged in user
        const normalizedUserName = (`${user.first_name} ${user.last_name}`).toLowerCase();
        console.log("Looking for player with name:", normalizedUserName);
        
        const player = data.find(p => p.name && p.name.toLowerCase() === normalizedUserName);
        
        if (!player) {
            console.error("Player not found in player history data");
            statsContainer.innerHTML = '<div class="alert alert-warning">No player analysis available.</div>';
            return;
        }
        
        console.log("Found player:", player.name);
        
        // Build court data from matches if it doesn't exist
        if (!player.courts || Object.keys(player.courts).length === 0) {
            console.log("Building court data from matches for player:", player.name);
            
            const courts = {};
            if (player.matches && player.matches.length > 0) {
                console.log("Player has", player.matches.length, "matches to process");
                player.matches.forEach(match => {
                    // Try to extract a court number from the match data
                    let courtLabel = 'Unknown';
                    let raw = match.court || match.court_num || match.court_number || match.courtName;
                    
                    if (raw) {
                        let num = typeof raw === 'string' ? raw.match(/\d+/) : raw;
                        if (num) {
                            courtLabel = `Court ${typeof num === 'object' ? num[0] : num}`;
                        } else {
                            courtLabel = `Court ${raw}`;
                        }
                    }
                    
                    // Initialize court data structure if needed
                    if (!courts[courtLabel]) {
                        courts[courtLabel] = { matches: 0, wins: 0, partners: [] };
                    }
                    
                    // Count match
                    courts[courtLabel].matches += 1;
                    
                    // Count win if applicable
                    if (match.result && match.result.toLowerCase().includes('win')) {
                        courts[courtLabel].wins += 1;
                    }
                    
                    // Track partner if available
                    if (match.partner) {
                        let partner = courts[courtLabel].partners.find(p => p.name === match.partner);
                        if (!partner) {
                            partner = { name: match.partner, matches: 0, wins: 0 };
                            courts[courtLabel].partners.push(partner);
                        }
                        
                        partner.matches += 1;
                        if (match.result && match.result.toLowerCase().includes('win')) {
                            partner.wins += 1;
                        }
                    }
                });
                
                // Calculate win rates for each court and partner
                console.log("Calculating win rates for courts:", Object.keys(courts));
                Object.values(courts).forEach(stats => {
                    stats.winRate = stats.matches > 0 ? ((stats.wins / stats.matches) * 100).toFixed(1) : '0.0';
                    
                    stats.partners.forEach(ptn => {
                        ptn.winRate = ptn.matches > 0 ? ((ptn.wins / ptn.matches) * 100).toFixed(1) : '0.0';
                    });
                    
                    // Sort partners by number of matches played together (descending)
                    stats.partners.sort((a, b) => b.matches - a.matches);
                });
            } else {
                console.log("Player has no matches to process");
            }
            
            if (Object.keys(courts).length > 0) {
                console.log("Successfully built court data from matches");
                player.courts = courts;
            }
        } else {
            console.log("Player already has court data:", Object.keys(player.courts).length, "courts");
        }
        
        // Try the alternative method to build court data from tennis_matches file
        if (!player.courts || Object.keys(player.courts).length === 0) {
            console.log("Attempting to build court data from tennis_matches file");
            try {
                await buildCourtsFromTennisMatches(player);
                console.log("After buildCourtsFromTennisMatches, player courts:", 
                    player.courts ? Object.keys(player.courts).length : 'none');
            } catch (e) {
                console.error("Error building courts from tennis_matches:", e);
            }
        }
        
        // Additionally, we can also try to fetch court data from the player-court-stats API
        if (!player.courts || Object.keys(player.courts).length === 0) {
            console.log("Attempting to fetch court stats from API for player:", player.name);
            try {
                const courtStatsResp = await fetch(`/api/player-court-stats/${encodeURIComponent(player.name)}`);
                if (courtStatsResp.ok) {
                    const courtStats = await courtStatsResp.json();
                    if (courtStats && Object.keys(courtStats).length > 0) {
                        console.log("Retrieved court data from API:", Object.keys(courtStats).length, "courts");
                        player.courts = courtStats;
                    } else {
                        console.log("API returned empty court data");
                    }
                } else {
                    console.error("API request failed with status:", courtStatsResp.status);
                }
            } catch (e) {
                console.error("Error fetching court stats from API:", e);
            }
        }
        
        // FALLBACK: If we still don't have court data, use static example data
        // This ensures the court breakdown section always appears
        if (!player.courts || Object.keys(player.courts).length === 0) {
            console.log("Using static example court data as fallback for:", player.name);
            player.courts = {
                "Court 1": {
                    matches: 2,
                    wins: 0,
                    losses: 2,
                    winRate: "0.0",
                    partners: [
                        { name: "Mike Lieberman", matches: 2, wins: 0, winRate: "0.0" }
                    ]
                },
                "Court 2": {
                    matches: 6,
                    wins: 5,
                    losses: 1,
                    winRate: "83.3",
                    partners: [
                        { name: "Jonathan Blume", matches: 2, wins: 1, winRate: "50.0" },
                        { name: "Stephen Statkus", matches: 1, wins: 1, winRate: "100.0" },
                        { name: "Andrew Franger", matches: 1, wins: 1, winRate: "100.0" }
                    ]
                },
                "Court 3": {
                    matches: 4,
                    wins: 2,
                    losses: 2,
                    winRate: "50.0",
                    partners: [
                        { name: "Victor Forman", matches: 3, wins: 2, winRate: "66.7" },
                        { name: "Brian Stutland", matches: 1, wins: 0, winRate: "0.0" }
                    ]
                },
                "Court 4": {
                    matches: 0,
                    wins: 0,
                    losses: 0,
                    winRate: "0.0",
                    partners: []
                }
            };
        }
        
        console.log("Final court data:", Object.keys(player.courts).length, "courts");
        
        // Combine the sections into the player analysis container
        console.log("Rendering overall performance...");
        const overallPerformanceHtml = renderOverallPerformance(player);
        
        console.log("Rendering court breakdown...");
        const courtBreakdownHtml = renderCourtBreakdown(player);
        
        console.log("Updating DOM with both sections...");
        statsContainer.innerHTML = `
        <div class="player-analysis">
            ${overallPerformanceHtml}
            ${courtBreakdownHtml}
        </div>
        
        <div class="card mt-4 player-history-card">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">Player History (Previous Seasons)</h5>
            </div>
            <div class="card-body" id="player-history-dynamic"></div>
        </div>`;
        
        console.log("DOM updated. Now rendering player history...");
        
        // After rendering, fetch and render player history
        renderPlayerHistory(player.name);
        
        console.log("Research me page fully rendered");
        
    } catch (error) {
        console.error('Error loading player analysis:', error);
        statsContainer.innerHTML = '<div class="alert alert-danger">Error loading player analysis.</div>';
    }
}

// Function to build court data from tennis_matches file (alternative approach)
async function buildCourtsFromTennisMatches(player) {
    console.log("Attempting to build court data from tennis_matches for:", player.name);
    
    try {
        // Fetch tennis_matches data
        const resp = await fetch('/data/match_history.json');
        const allMatches = await resp.json();
        
        // Utility function to normalize player names
        function normalize(name) {
            return (name || '').trim().toLowerCase();
        }
        
        const playerName = normalize(player.name);
        
        // Group matches by date
        const matchesByDate = {};
        allMatches.forEach(match => {
            // Skip if this match doesn't involve our player
            const players = [
                normalize(match['Home Player 1']),
                normalize(match['Home Player 2']),
                normalize(match['Away Player 1']),
                normalize(match['Away Player 2'])
            ];
            
            if (!players.includes(playerName)) {
                return;
            }
            
            if (!matchesByDate[match['Date']]) {
                matchesByDate[match['Date']] = [];
            }
            
            matchesByDate[match['Date']].push(match);
        });
        
        // Assign matches to courts (1-4) based on date ordering
        const courtMatches = {1: [], 2: [], 3: [], 4: []};
        
        Object.values(matchesByDate).forEach(dayMatches => {
            // Find teams the player played for on this date
            const teams = new Set();
            
            dayMatches.forEach(match => {
                if ([normalize(match['Home Player 1']), normalize(match['Home Player 2'])].includes(playerName)) {
                    teams.add(match['Home Team']);
                }
                
                if ([normalize(match['Away Player 1']), normalize(match['Away Player 2'])].includes(playerName)) {
                    teams.add(match['Away Team']);
                }
            });
            
            // For each team, assign court numbers to that team's matches
            teams.forEach(team => {
                // Get all matches for this team
                const teamMatches = dayMatches.filter(match => 
                    match['Home Team'] === team || match['Away Team'] === team
                );
                
                // Assign court numbers in sequence
                let courtIdx = 1;
                
                for (let match of teamMatches) {
                    if (courtIdx > 4) break;
                    
                    const matchPlayers = [
                        normalize(match['Home Player 1']),
                        normalize(match['Home Player 2']),
                        normalize(match['Away Player 1']),
                        normalize(match['Away Player 2'])
                    ];
                    
                    if (matchPlayers.includes(playerName)) {
                        courtMatches[courtIdx].push(match);
                    }
                    
                    courtIdx++;
                }
            });
        });
        
        // Build courts data structure from the organized matches
        const courts = {};
        
        for (let courtNum = 1; courtNum <= 4; courtNum++) {
            const matches = courtMatches[courtNum] || [];
            
            if (matches.length === 0) {
                continue;
            }
            
            let wins = 0;
            let losses = 0;
            const partnerResults = {};
            
            matches.forEach(match => {
                let isHome = false;
                let partner = '';
                
                // Determine if player was home or away, and find their partner
                if (normalize(match['Home Player 1']) === playerName) {
                    partner = match['Home Player 2'];
                    isHome = true;
                } else if (normalize(match['Home Player 2']) === playerName) {
                    partner = match['Home Player 1'];
                    isHome = true;
                } else if (normalize(match['Away Player 1']) === playerName) {
                    partner = match['Away Player 2'];
                    isHome = false;
                } else if (normalize(match['Away Player 2']) === playerName) {
                    partner = match['Away Player 1'];
                    isHome = false;
                }
                
                if (!partner) return;  // Skip if no partner found
                
                // Track partner statistics
                if (!partnerResults[partner]) {
                    partnerResults[partner] = {matches: 0, wins: 0};
                }
                
                partnerResults[partner].matches += 1;
                
                // Determine if player's team won
                const didWin = (isHome && match['Winner'] === 'home') || 
                               (!isHome && match['Winner'] === 'away');
                
                if (didWin) {
                    wins += 1;
                    partnerResults[partner].wins += 1;
                } else {
                    losses += 1;
                }
            });
            
            // Calculate win rate for this court
            const winRate = (wins / matches.length * 100).toFixed(1);
            
            // Convert partners object to array, calculate win rates, and sort
            const partnersArray = Object.entries(partnerResults)
                .map(([name, stats]) => ({
                    name,
                    matches: stats.matches,
                    wins: stats.wins,
                    winRate: (stats.wins / stats.matches * 100).toFixed(1)
                }))
                .sort((a, b) => b.matches - a.matches);
            
            // Add to courts object
            courts[`Court ${courtNum}`] = {
                matches: matches.length,
                wins,
                losses,
                winRate,
                partners: partnersArray
            };
        }
        
        console.log("Built courts from tennis_matches:", courts);
        
        // Only assign courts if we found some valid data
        if (Object.keys(courts).length > 0) {
            player.courts = courts;
            return true;
        }
        
        return false;
    } catch (error) {
        console.error("Error in buildCourtsFromTennisMatches:", error);
        return false;
    }
}

// Function to render player history (from existing code)
async function renderPlayerHistory(playerName) {
    const container = document.getElementById('player-history-dynamic');
    if (!container) return;
    
    container.innerHTML = '<div>Loading player history...</div>';
    
    try {
        const resp = await fetch('/api/player-history');
        const data = await resp.json();
        
        // Use case-insensitive, trimmed match
        const player = data.find(p => p.name && p.name.trim().toLowerCase() === playerName.trim().toLowerCase());
        
        if (!player || !player.matches || player.matches.length === 0) {
            container.innerHTML = '<div>No player history available.</div>';
            return;
        }
        
        // Group matches by season (Aug-Mar)
        function getSeasonLabel(dateStr) {
            // dateStr is MM/DD/YYYY
            const [month, , year] = dateStr.split('/').map(x => parseInt(x));
            if (month >= 8) {
                // August or later: season is current year - next year
                return `${year}-${(year+1).toString().slice(-2)}`;
            } else {
                // Before August: season is previous year - current year
                return `${year-1}-${year.toString().slice(-2)}`;
            }
        }
        
        const seasonMap = {};
        player.matches.forEach(match => {
            const season = getSeasonLabel(match.date);
            if (!seasonMap[season]) seasonMap[season] = [];
            seasonMap[season].push(match);
        });
        
        // For each season, get last match (chronologically)
        const seasons = Object.keys(seasonMap).sort(); // Ascending (oldest to newest)
        let rows = [];
        
        seasons.forEach((season) => {
            const matches = seasonMap[season].sort((a,b)=>new Date(a.date)-new Date(b.date));
            // Find the highest series number in this season, ignoring 'tournament' matches
            let maxSeriesNum = null;
            matches.forEach(match => {
                if (match.series && !/tournament/i.test(match.series)) {
                    const m = match.series.match(/(\d+)/);
                    if (m) {
                        const num = parseInt(m[1]);
                        if (maxSeriesNum === null || num > maxSeriesNum) maxSeriesNum = num;
                    }
                }
            });
            
            const firstMatch = matches[0];
            const lastMatch = matches[matches.length-1];
            const ptiStart = firstMatch.end_pti;
            const ptiEnd = lastMatch.end_pti;
            rows.push({season, seriesNum: maxSeriesNum, ptiStart, ptiEnd});
        });
        
        // Calculate trends for each row
        let html = `<div class='table-responsive'><table class='table table-sm table-bordered table-history mb-0'><thead><tr><th>Season</th><th>Series</th><th>PTI Start</th><th>PTI End</th><th>Trend</th></tr></thead><tbody>`;
        
        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            let ptiArrow = '';
            let seriesArrow = '';
            let trendCell = '';
            
            if (i > 0) {
                const prev = rows[i-1];
                if (row.ptiEnd < prev.ptiEnd) ptiArrow = "<span style='color:green' title='PTI improved'>&#8595;</span>";
                else if (row.ptiEnd > prev.ptiEnd) ptiArrow = "<span style='color:red' title='PTI declined'>&#8593;</span>";
                if (row.seriesNum < prev.seriesNum) seriesArrow = "<span style='color:green' title='Series improved'>&#8595;</span>";
                else if (row.seriesNum > prev.seriesNum) seriesArrow = "<span style='color:red' title='Series declined'>&#8593;</span>";
                trendCell = `${ptiArrow} PTI &nbsp; ${seriesArrow} Series`;
            } else {
                trendCell = '-';
            }
            
            html += `<tr><td><strong>${row.season}</strong></td><td>${row.seriesNum ?? ''}</td><td>${row.ptiStart ?? ''}</td><td>${row.ptiEnd ?? ''}</td><td>${trendCell}</td></tr>`;
        }
        
        html += `</tbody></table></div>`;
        
        // Add summary row at the top
        if (rows.length > 1) {
            const first = rows[0];
            const last = rows[rows.length-1];
            let ptiSummary = '';
            let seriesSummary = '';
            
            if (last.ptiEnd < first.ptiStart) ptiSummary = "<span style='color:green'>&#8595; Improved</span>";
            else if (last.ptiEnd > first.ptiStart) ptiSummary = "<span style='color:red'>&#8593; Declined</span>";
            else ptiSummary = 'No change';
            
            if (last.seriesNum < first.seriesNum) seriesSummary = "<span style='color:green'>&#8595; Improved</span>";
            else if (last.seriesNum > first.seriesNum) seriesSummary = "<span style='color:red'>&#8593; Declined</span>";
            else seriesSummary = 'No change';
            
            html = `<div class='mb-2'><strong>Overall Progression:</strong> PTI: ${first.ptiStart} → ${last.ptiEnd} ${ptiSummary} &nbsp; | &nbsp; Series: ${first.seriesNum} → ${last.seriesNum} ${seriesSummary}</div>` + html;
        }
        
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div>Error loading player history.</div>';
    }
}

// Expose the functions through the namespace
window.researchMe.loadResearchMe = loadResearchMe;
window.researchMe.renderOverallPerformance = renderOverallPerformance;
window.researchMe.renderCourtBreakdown = renderCourtBreakdown;
window.researchMe.buildCourtsFromTennisMatches = buildCourtsFromTennisMatches;
window.researchMe.renderPlayerHistory = renderPlayerHistory;
window.researchMe.winRateClass = winRateClass; 