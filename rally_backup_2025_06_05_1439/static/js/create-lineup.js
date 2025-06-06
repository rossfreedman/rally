// Global variables
let selectedPlayers = [];
let currentSeries = '';

// Load players when page loads
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Get user's series from session
        const authResponse = await fetch('/api/check-auth');
        if (!authResponse.ok) {
            throw new Error('Failed to authenticate. Please try logging in again.');
        }
        const authData = await authResponse.json();
        
        if (!authData.authenticated) {
            window.location.href = '/login';
            return;
        }
        
        if (!authData.user || !authData.user.series) {
            throw new Error('No series assigned. Please contact your administrator.');
        }
        
        // Store the user's series
        currentSeries = authData.user.series;
        
        // Load players for the current series
        const response = await fetch(`/api/players?series=${encodeURIComponent(currentSeries)}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to load players (Status: ${response.status})`);
        }
        
        const players = await response.json();
        if (!players || players.length === 0) {
            throw new Error(`No players found for series ${currentSeries}`);
        }
        
        const playerList = document.getElementById('playerList');
        
        playerList.innerHTML = '';
        players.forEach(player => {
            const div = document.createElement('div');
            div.className = 'form-check mb-2';
            div.innerHTML = `
                <input class="form-check-input" type="checkbox" value="${player.name}" id="player-${player.name.replace(/\s+/g, '-')}">
                <label class="form-check-label" for="player-${player.name.replace(/\s+/g, '-')}">
                    ${player.name} (${player.rating})
                </label>
            `;
            playerList.appendChild(div);
        });

        // Set up event listeners
        document.getElementById('generateBtn').addEventListener('click', generateLineup);
    } catch (error) {
        console.error('Error loading players:', error);
        document.getElementById('playerList').innerHTML = `
            <div class="alert alert-danger">
                <strong>Error loading players:</strong><br>
                ${error.message}<br><br>
                <small>If this error persists, please try:
                    <ul>
                        <li>Refreshing the page</li>
                        <li>Logging out and back in</li>
                        <li>Contacting support if the issue continues</li>
                    </ul>
                </small>
            </div>
        `;
    }
});

// Generate lineup function
async function generateLineup() {
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const result = document.getElementById('lineupResult');
    const debug = document.getElementById('debugInfo');
    
    // Get selected players
    selectedPlayers = Array.from(document.querySelectorAll('#playerList input[type="checkbox"]:checked'))
        .map(checkbox => checkbox.value);
    
    if (selectedPlayers.length === 0) {
        error.textContent = 'Please select at least one player';
        error.style.display = 'block';
        return;
    }

    // Show loading state
    loading.style.display = 'block';
    error.style.display = 'none';
    result.innerHTML = '';
    debug.style.display = 'none';

    try {
        console.log('=== LINEUP REQUEST ===');
        console.log('Selected players:', selectedPlayers);
        console.log('Current series:', currentSeries);
        
        const response = await fetch('/api/generate-lineup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                players: selectedPlayers,
                series: currentSeries
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('=== LINEUP RESPONSE ===');
        console.log('Prompt:', data.prompt);
        console.log('Response:', data.suggestion);
        console.log('=== END RESPONSE ===');

        // Display the formatted response
        const lines = data.suggestion.split('\n');
        result.innerHTML = `
            <div class="strategy mb-4">
                <h6>Strategy</h6>
                <p>${lines[0]}</p>
            </div>
            <div class="courts">
                ${lines.slice(1).map(line => `
                    <div class="court-row">
                        <div class="court-players">${line}</div>
                    </div>
                `).join('')}
            </div>
        `;

        // Show debug info
        debug.innerHTML = `
            <h6>Debug Information</h6>
            <pre>Prompt: ${data.prompt}\n\nResponse: ${data.suggestion}</pre>
        `;
        debug.style.display = 'block';

    } catch (error) {
        console.error('Error generating lineup:', error);
        error.textContent = error.message;
        error.style.display = 'block';
    } finally {
        loading.style.display = 'none';
    }
} 