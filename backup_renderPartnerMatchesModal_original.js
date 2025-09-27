// BACKUP: Original renderPartnerMatchesModal function from analyze_me.html
// Created: $(date)
// Purpose: Backup before adding new format below existing scores

function renderPartnerMatchesModal(matches, partnerName, courtName) {
    const modalContent = document.getElementById('matchesModalContent');
    
    let html = `
        <div class="mb-4 p-4 bg-blue-50 rounded-lg">
            <h3 class="text-base font-semibold text-gray-900 mb-2">${partnerName} on ${courtName}</h3>
        </div>
    `;
    
    // Group matches by date and team matchup
    const groupedMatches = groupMatchesByTeamMatchup(matches);
    
    groupedMatches.forEach(group => {
        // Calculate team result (W or L)
        const playerMatches = group.matches.filter(match => match.player_was_home !== null);
        const wins = playerMatches.filter(match => match.player_won).length;
        const losses = playerMatches.filter(match => !match.player_won).length;
        const teamResult = wins > losses ? 'W' : 'L';
        const resultClass = teamResult === 'W' ? 'text-green-600' : 'text-red-600';
        
        html += `
            <div class="mb-6 border border-gray-200 rounded-lg overflow-hidden">
                <!-- Team Match Header -->
                <div class="bg-gray-50 px-4 py-3 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <span class="text-xs font-medium text-gray-900">${group.date}</span>
                            <span class="text-xs text-gray-600">${group.home_team} (H) vs ${group.away_team} (A)</span>
                        </div>
                        <span class="text-base font-bold ${resultClass}">${teamResult}</span>
                    </div>
                </div>
                
                <!-- Individual Matches -->
                <div class="divide-y divide-gray-100">
        `;
        
        // Sort matches by court number (handle both string and number formats)
        group.matches.sort((a, b) => {
            const aNum = typeof a.court_number === 'string' ? parseInt(a.court_number.replace(/\D/g, '')) : a.court_number;
            const bNum = typeof b.court_number === 'string' ? parseInt(b.court_number.replace(/\D/g, '')) : b.court_number;
            return aNum - bNum;
        });
        
        group.matches.forEach(match => {
            const resultClass = match.player_won ? 'text-green-600' : 'text-red-600';
            const matchResult = match.player_won ? 'WIN' : 'LOSS';
            
            // Handle court number display
            const courtDisplay = typeof match.court_number === 'string' && match.court_number.startsWith('Court') 
                ? match.court_number 
                : `Court ${match.court_number}`;
            
            html += `
                <div class="px-4 py-3 bg-gray-50">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-medium text-gray-900">${courtDisplay}</span>
                            <span class="text-xs text-gray-700">${match.partner_name}</span>
                        </div>
                        <span class="text-xs font-bold ${resultClass}">${matchResult}</span>
                    </div>
                    
                    <div class="flex items-center justify-between">
                        <div class="text-xs text-gray-600">
                            vs ${match.opponent1_name}${match.opponent2_name && match.opponent2_name !== 'Unknown' ? ` & ${match.opponent2_name}` : ''}
                        </div>
                        <div class="text-xs font-medium text-gray-900">${match.scores}</div>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    modalContent.innerHTML = html;
}
