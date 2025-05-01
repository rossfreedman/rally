// Populate series dropdown when page loads
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Loading series...');  // Debug log
    
    // Get series from server
    try {
        const response = await fetch('/get-series');
        const data = await response.json();
        
        if (data.error) {
            console.error('Server error:', data.error);
            return;
        }
        
        // Populate series dropdown
        const seriesSelect = document.getElementById('series-select');
        data.series.forEach(series => {
            const option = document.createElement('option');
            option.value = series;
            option.textContent = series;  // Use exact series name from CSV
            seriesSelect.appendChild(option);
        });
        
        console.log('Series loaded:', data.series);  // Debug log
    } catch (error) {
        console.error('Error loading series:', error);
    }
});

document.getElementById('lineup-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const selectedPlayers = Array.from(document.querySelectorAll('.player-checkbox:checked'))
        .map(checkbox => checkbox.value);
    
    const series = document.getElementById('series-select').value;
    const matchType = document.getElementById('match-type').value;
    
    // Show loading state
    document.querySelector('.submit-btn').disabled = true;
    document.querySelector('.submit-btn').textContent = 'Generating...';
    
    try {
        const response = await fetch('/generate-lineup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                players: selectedPlayers,
                series: series,
                matchType: matchType
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Display the raw response in a text box
        resultsDiv.innerHTML = `
            <textarea class="form-control" rows="10" readonly>${data.suggestion}</textarea>
        `;
        
    } catch (error) {
        console.error('Error:', error);
        alert('Error generating lineup. Please try again.');
    } finally {
        // Reset button state
        document.querySelector('.submit-btn').disabled = false;
        document.querySelector('.submit-btn').textContent = 'Generate Lineup';
    }
}); 