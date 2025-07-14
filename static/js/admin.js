// Global variables to store data
let users = [];
let clubs = [];
let series = [];
let userToDelete = null;

// Utility function to format timestamps properly
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';
    
    // Create a Date object from the timestamp
    // Since we're now storing in UTC, we need to parse it as UTC
    const date = new Date(timestamp);
    
    // Format using the user's local timezone
    return date.toLocaleString();
}

// Helper function to escape HTML to prevent XSS attacks
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize the admin dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin dashboard initializing...');
    
    // Load initial data
    Promise.all([loadUsers(), loadClubs(), loadSeries()]).then(() => {
        console.log('All data loaded');
    });

    // Handle hash-based navigation
    function handleHashChange() {
        const hash = window.location.hash.slice(1) || 'users';
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.add('hidden');
        });
        const activeContent = document.getElementById(`${hash}-content`);
        if (activeContent) {
            activeContent.classList.remove('hidden');
        }
    }

    // Listen for hash changes
    window.addEventListener('hashchange', handleHashChange);
    
    // Initial hash handling
    handleHashChange();
});

// Modal handling functions
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.showModal();
    } else {
        console.error(`Modal with id ${modalId} not found`);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.close();
    } else {
        console.error(`Modal with id ${modalId} not found`);
    }
}

// Users Management
async function loadUsers() {
    console.log('Loading users...');
    try {
        const response = await fetch('/api/admin/users', {
            credentials: 'include'
        });
        console.log('Users API response status:', response.status);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error || 'Unknown error'}`);
        }
        
        const data = await response.json();
        console.log('Users data received:', data);
        users = data;
        renderUsers();
    } catch (error) {
        console.error('Error loading users:', error);
        document.getElementById('usersTableBody').innerHTML = `
            <tr>
                <td colspan="6" class="text-center text-error">
                    Failed to load users: ${escapeHtml(error.message)}
                </td>
            </tr>
        `;
    }
}

function renderUsers() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) {
        console.error('Users table body element not found');
        return;
    }
    
    console.log('Rendering users table with', users.length, 'users');
    tbody.innerHTML = '';
    
    users.forEach(user => {
        // Format most recent activity if available
        const mostRecentActivity = user.most_recent_activity ? formatTimestamp(user.most_recent_activity) : 'Unknown';
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${escapeHtml(user.first_name)} ${escapeHtml(user.last_name)}</td>
            <td>${escapeHtml(user.email)}</td>
            <td>${escapeHtml(user.club_name) || '-'}</td>
            <td>${escapeHtml(user.series_name) || '-'}</td>
            <td>${user.last_login ? escapeHtml(formatTimestamp(user.last_login)) : 'Never'}</td>
            <td>${mostRecentActivity}</td>
            <td class="space-x-2">
                <button class="btn btn-sm" onclick="editUser('${escapeHtml(user.id)}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm" onclick="viewUserActivity('${escapeHtml(user.email)}')">
                    <i class="fas fa-history"></i>
                </button>
                <button class="btn btn-sm bg-red-600 hover:bg-red-700 text-white" onclick="showDeleteUserModal('${escapeHtml(user.email)}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });

    // Also update the mobile view
    const mobileView = document.getElementById('usersMobileView');
    if (mobileView) {
        mobileView.innerHTML = users.map(user => {
            const mostRecentActivity = user.most_recent_activity ? formatTimestamp(user.most_recent_activity) : 'Unknown';
            
            return `
            <div class="card bg-white shadow-sm p-4">
                <div class="flex justify-between items-start mb-2">
                    <div>
                        <h3 class="font-bold">${escapeHtml(user.first_name)} ${escapeHtml(user.last_name)}</h3>
                        <p class="text-sm text-gray-600">${escapeHtml(user.email)}</p>
                    </div>
                    <div class="flex gap-2">
                        <button class="btn btn-sm bg-black hover:bg-gray-800 text-yellow-400" onclick="editUser('${escapeHtml(user.id)}')">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm bg-black hover:bg-gray-800 text-yellow-400" onclick="viewUserActivity('${escapeHtml(user.email)}')">
                            <i class="fas fa-history"></i>
                        </button>
                        <button class="btn btn-sm bg-red-600 hover:bg-red-700 text-white" onclick="showDeleteUserModal('${escapeHtml(user.email)}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="text-sm">
                    <p><span class="font-semibold">Club:</span> ${escapeHtml(user.club_name) || 'None'}</p>
                    <p><span class="font-semibold">Series:</span> ${escapeHtml(user.series_name) || 'None'}</p>
                    <p><span class="font-semibold">Last Login:</span> ${user.last_login ? escapeHtml(formatTimestamp(user.last_login)) : 'Never'}</p>
                    <p><span class="font-semibold">Most Recent Activity:</span> ${mostRecentActivity}</p>
                </div>
            </div>
        `}).join('');
    }
}

function editUser(userId) {
    console.log('Opening edit modal for user ID:', userId);
    const user = users.find(u => u.id === userId || u.id === parseInt(userId));
    if (!user) {
        console.error('User not found:', userId);
        return;
    }

    console.log('Found user:', user);
    console.log('Available clubs:', clubs);
    console.log('Available series:', series);

    document.getElementById('editUserId').value = user.id;
    document.getElementById('editFirstName').value = user.first_name;
    document.getElementById('editLastName').value = user.last_name;
    document.getElementById('editEmail').value = user.email;

    // Populate club dropdown
    const clubSelect = document.getElementById('editClub');
    clubSelect.innerHTML = '<option value="">Select Club</option>' + 
        clubs.map(club => 
            `<option value="${club.id}" ${club.id === user.club_id ? 'selected' : ''}>${club.name}</option>`
        ).join('');

    // Populate series dropdown
    const seriesSelect = document.getElementById('editSeries');
    seriesSelect.innerHTML = '<option value="">Select Series</option>' + 
        series.map(s => 
            `<option value="${s.id}" ${s.id === user.series_id ? 'selected' : ''}>${s.name}</option>`
        ).join('');

    showModal('editUserModal');
}

// For backward compatibility
function showEditUserModal(email) {
    console.log('Opening edit modal for user email:', email);
    const user = users.find(u => u.email === email);
    if (user) {
        editUser(user.id);
    } else {
        console.error('User not found:', email);
    }
}

async function saveUserChanges() {
    const userData = {
        id: document.getElementById('editUserId').value,
        email: document.getElementById('editEmail').value,
        first_name: document.getElementById('editFirstName').value,
        last_name: document.getElementById('editLastName').value,
        club_id: document.getElementById('editClub').value,
        series_id: document.getElementById('editSeries').value
    };

    try {
        const response = await fetch('/api/admin/update-user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(userData)
        });

        if (response.ok) {
            closeModal('editUserModal');
            loadUsers();
        } else {
            const error = await response.json();
            alert(error.message || 'Failed to update user');
        }
    } catch (error) {
        console.error('Error updating user:', error);
        alert('Failed to update user');
    }
}

async function viewUserActivity(email) {
    try {
        const response = await fetch(`/api/admin/user-activity/${email}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch user activity');
        }

        // Update user info section
        const userInfo = data.user;
        document.querySelector('.user-name').textContent = `${userInfo.first_name} ${userInfo.last_name}`;
        document.querySelector('.user-email').textContent = userInfo.email;
        document.querySelector('.user-last-login').textContent = userInfo.last_login ? formatTimestamp(userInfo.last_login) : 'Never';

        // Clear existing activity data
        const tableBody = document.getElementById('activityTableBody');
        const mobileView = document.getElementById('activityMobileView');
        tableBody.innerHTML = '';
        mobileView.innerHTML = '';

        // Sort activities by timestamp in descending order (though they should already be sorted)
        const activities = data.activities;

        // Populate desktop table view
        activities.forEach(activity => {
            let detailsDisplay = activity.details || '-';
            if ((activity.page === 'player_detail' || activity.page === 'mobile_player_detail') && activity.details) {
                detailsDisplay = `Visited Player Detail: ${activity.details}`;
            } else if (activity.page === 'mobile_teams_players') {
                detailsDisplay = 'Visited Teams & Players';
            }
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="py-2">${new Date(activity.timestamp).toLocaleString()}</td>
                <td class="py-2">${activity.activity_type || '-'}</td>
                <td class="py-2">${activity.page || '-'}</td>
                <td class="py-2">${activity.action || '-'}</td>
                <td class="py-2">${detailsDisplay}</td>
                <td class="py-2">${activity.ip_address || '-'}</td>
            `;
            tableBody.appendChild(row);
        });

        // Populate mobile view
        activities.forEach(activity => {
            let detailsDisplay = activity.details || '-';
            if ((activity.page === 'player_detail' || activity.page === 'mobile_player_detail') && activity.details) {
                detailsDisplay = `Visited Player Detail: ${activity.details}`;
            } else if (activity.page === 'mobile_teams_players') {
                detailsDisplay = 'Visited Teams & Players';
            }
            const card = document.createElement('div');
            card.className = 'bg-white p-4 rounded-lg shadow-sm border';
            card.innerHTML = `
                <div class="space-y-2">
                    <div class="flex justify-between items-start">
                        <span class="text-sm font-medium">${new Date(activity.timestamp).toLocaleString()}</span>
                        <span class="text-xs bg-gray-100 px-2 py-1 rounded">${activity.activity_type || '-'}</span>
                    </div>
                    <div class="space-y-1">
                        <p class="text-sm"><span class="font-medium">Page:</span> ${activity.page || '-'}</p>
                        <p class="text-sm"><span class="font-medium">Action:</span> ${activity.action || '-'}</p>
                        <p class="text-sm"><span class="font-medium">Details:</span> ${detailsDisplay}</p>
                        <p class="text-sm"><span class="font-medium">IP:</span> ${activity.ip_address || '-'}</p>
                    </div>
                </div>
            `;
            mobileView.appendChild(card);
        });

        // Show the modal
        showModal('activityModal');
    } catch (error) {
        console.error('Error fetching user activity:', error);
        alert('Failed to fetch user activity. Please try again.');
    }
}

function showDeleteUserModal(email) {
    userToDelete = email;
    showModal('deleteUserModal');
}

async function confirmDeleteUser() {
    if (!userToDelete) return;
    
    try {
        const response = await fetch('/api/admin/delete-user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: userToDelete })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete user');
        }
        
        // Remove user from local array
        users = users.filter(user => user.email !== userToDelete);
        
        // Re-render users table
        renderUsers();
        
        // Close modal
        closeModal('deleteUserModal');
        
        // Reset userToDelete
        userToDelete = null;
        
        // Show success message
        alert('User deleted successfully');
        
    } catch (error) {
        console.error('Error deleting user:', error);
        alert('Failed to delete user. Please try again.');
    }
}

// Clubs Management
async function loadClubs() {
    console.log('Loading clubs...');
    try {
        const response = await fetch('/api/admin/clubs', {
            credentials: 'include'
        });
        console.log('Clubs API response status:', response.status);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error || 'Unknown error'}`);
        }
        
        const data = await response.json();
        console.log('Clubs data received:', data);
        clubs = data;
        renderClubs();
    } catch (error) {
        console.error('Error loading clubs:', error);
        const clubsTableBody = document.getElementById('clubsTableBody');
        if (clubsTableBody) {
            clubsTableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-error">
                        Failed to load clubs: ${escapeHtml(error.message)}
                    </td>
                </tr>
            `;
        }
    }
}

function renderClubs() {
    const tbody = document.getElementById('clubsTableBody');
    if (!tbody) {
        console.error('Clubs table body element not found');
        return;
    }
    
    tbody.innerHTML = '';
    
    clubs.forEach(club => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="py-2">${escapeHtml(club.id)}</td>
            <td class="py-2">${escapeHtml(club.name)}</td>
            <td class="py-2 text-right">
                <div class="flex gap-2 justify-end">
                    <button class="btn btn-sm bg-black hover:bg-gray-800 text-yellow-400" onclick="showEditClubModal(${escapeHtml(club.id)})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm bg-black hover:bg-gray-800 text-yellow-400" onclick="deleteClub(${escapeHtml(club.id)})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });

    // Update mobile view
    const mobileView = document.getElementById('clubsMobileView');
    if (mobileView) {
        mobileView.innerHTML = clubs.map(club => `
            <div class="card bg-white shadow-sm p-4">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="font-bold">${escapeHtml(club.name)}</h3>
                        <p class="text-sm text-gray-600">ID: ${escapeHtml(club.id)}</p>
                    </div>
                    <div class="flex gap-2">
                        <button class="btn btn-sm bg-black hover:bg-gray-800 text-yellow-400" onclick="showEditClubModal(${escapeHtml(club.id)})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm bg-black hover:bg-gray-800 text-yellow-400" onclick="deleteClub(${escapeHtml(club.id)})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }
}

function showAddClubModal() {
    document.getElementById('clubId').value = '';
    document.getElementById('clubName').value = '';
    showModal('clubModal');
}

function showEditClubModal(clubId) {
    const club = clubs.find(c => c.id === clubId);
    if (!club) return;

    document.getElementById('clubId').value = club.id;
    document.getElementById('clubName').value = club.name;
    showModal('clubModal');
}

async function saveClub() {
    const clubId = document.getElementById('clubId').value;
    const clubData = {
        id: clubId,
        name: document.getElementById('clubName').value
    };

    try {
        const response = await fetch('/api/admin/update-club', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(clubData)
        });

        if (response.ok) {
            closeModal('clubModal');
            loadClubs();
        } else {
            const error = await response.json();
            alert(error.message || 'Failed to save club');
        }
    } catch (error) {
        console.error('Error saving club:', error);
        alert('Failed to save club');
    }
}

async function deleteClub(clubId) {
    if (!confirm('Are you sure you want to delete this club?')) return;

    try {
        const response = await fetch(`/api/admin/delete-club/${clubId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (response.ok) {
            loadClubs();
        } else {
            const error = await response.json();
            alert(error.message || 'Failed to delete club');
        }
    } catch (error) {
        console.error('Error deleting club:', error);
        alert('Failed to delete club');
    }
}

// Series Management
async function loadSeries() {
    console.log('Loading series...');
    try {
        const response = await fetch('/api/admin/series', {
            credentials: 'include'
        });
        console.log('Series API response status:', response.status);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.error || 'Unknown error'}`);
        }
        
        const data = await response.json();
        console.log('Series data received:', data);
        series = data;
        renderSeries();
    } catch (error) {
        console.error('Error loading series:', error);
        const seriesTableBody = document.getElementById('seriesTableBody');
        if (seriesTableBody) {
            seriesTableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-error">
                        Failed to load series: ${escapeHtml(error.message)}
                    </td>
                </tr>
            `;
        }
    }
}

function renderSeries() {
    const tbody = document.getElementById('seriesTableBody');
    if (!tbody) {
        console.error('Series table body element not found');
        return;
    }
    
    tbody.innerHTML = '';
    
    series.forEach(s => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="py-2">${escapeHtml(s.id)}</td>
            <td class="py-2">${escapeHtml(s.name)}</td>
            <td class="py-2 text-right">
                <div class="flex gap-2 justify-end">
                    <button class="btn btn-sm bg-black hover:bg-gray-800 text-yellow-400" onclick="showEditSeriesModal(${escapeHtml(s.id)})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm bg-black hover:bg-gray-800 text-yellow-400" onclick="deleteSeries(${escapeHtml(s.id)})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });

    // Update mobile view
    const mobileView = document.getElementById('seriesMobileView');
    if (mobileView) {
        mobileView.innerHTML = series.map(s => `
            <div class="card bg-white shadow-sm p-4">
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="font-bold">${escapeHtml(s.name)}</h3>
                        <p class="text-sm text-gray-600">ID: ${escapeHtml(s.id)}</p>
                    </div>
                    <div class="flex gap-2">
                        <button class="btn btn-sm bg-black hover:bg-gray-800 text-yellow-400" onclick="showEditSeriesModal(${escapeHtml(s.id)})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm bg-black hover:bg-gray-800 text-yellow-400" onclick="deleteSeries(${escapeHtml(s.id)})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }
}

function showAddSeriesModal() {
    document.getElementById('seriesId').value = '';
    document.getElementById('seriesName').value = '';
    showModal('seriesModal');
}

function showEditSeriesModal(seriesId) {
    const s = series.find(s => s.id === seriesId);
    if (!s) return;

    document.getElementById('seriesId').value = s.id;
    document.getElementById('seriesName').value = s.name;
    showModal('seriesModal');
}

async function saveSeries() {
    const seriesId = document.getElementById('seriesId').value;
    const seriesData = {
        id: seriesId,
        name: document.getElementById('seriesName').value
    };

    try {
        const response = await fetch('/api/admin/update-series', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(seriesData)
        });

        if (response.ok) {
            closeModal('seriesModal');
            loadSeries();
        } else {
            const error = await response.json();
            alert(error.message || 'Failed to save series');
        }
    } catch (error) {
        console.error('Error saving series:', error);
        alert('Failed to save series');
    }
}

async function deleteSeries(seriesId) {
    if (!confirm('Are you sure you want to delete this series?')) return;

    try {
        const response = await fetch(`/api/admin/delete-series/${seriesId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (response.ok) {
            loadSeries();
        } else {
            const error = await response.json();
            alert(error.message || 'Failed to delete series');
        }
    } catch (error) {
        console.error('Error deleting series:', error);
        alert('Failed to delete series');
    }
}

// Utility Functions
function exportUsers() {
    const csvContent = "data:text/csv;charset=utf-8," + 
        "Name,Email,Club,Series,Last Login,Most Recent Activity\n" +
        users.map(user => {
            const mostRecentActivity = user.most_recent_activity ? formatTimestamp(user.most_recent_activity) : 'Unknown';
            return `"${user.first_name} ${user.last_name}","${user.email}","${user.club_name || ''}","${user.series_name || ''}","${user.last_login ? formatTimestamp(user.last_login) : 'Never'}","${mostRecentActivity}"`;
        }).join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "rally_users.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// AI Optimization Monitoring Functions
async function refreshAIStats() {
    console.log('Refreshing AI statistics...');
    const container = document.getElementById('ai-stats-container');
    
    // Show loading state
    container.innerHTML = `
        <div class="flex justify-center items-center py-8">
            <div class="loading loading-spinner loading-md"></div>
            <span class="ml-2">Loading AI statistics...</span>
        </div>
    `;
    
    try {
        const response = await fetch('/api/ai/stats', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        renderAIStats(data);
    } catch (error) {
        console.error('Error loading AI stats:', error);
        container.innerHTML = `
            <div class="alert alert-error">
                <i class="fas fa-exclamation-triangle"></i>
                <span>Failed to load AI statistics: ${error.message}</span>
            </div>
        `;
    }
}

function renderAIStats(data) {
    const container = document.getElementById('ai-stats-container');
    const stats = data.statistics;
    const config = data.configuration;
    const recommendations = data.recommendations;
    
    // Determine status color
    const statusColor = recommendations.status === 'Excellent' ? 'success' : 
                       recommendations.status === 'Good' ? 'warning' : 'error';
    
    container.innerHTML = `
        <!-- Status Overview -->
        <div class="alert alert-${statusColor} mb-6">
            <i class="fas fa-chart-line"></i>
            <div>
                <h3 class="font-bold">Optimization Level: ${data.optimization_level}</h3>
                <div class="text-sm">${recommendations.message}</div>
            </div>
        </div>
        
        <!-- Statistics Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div class="stat bg-base-200 rounded-lg">
                <div class="stat-figure text-primary">
                    <i class="fas fa-comments text-2xl"></i>
                </div>
                <div class="stat-title">Total Requests</div>
                <div class="stat-value text-primary">${stats.total_requests}</div>
                <div class="stat-desc">Chat interactions</div>
            </div>
            
            <div class="stat bg-base-200 rounded-lg">
                <div class="stat-figure text-secondary">
                    <i class="fas fa-sync-alt text-2xl"></i>
                </div>
                <div class="stat-title">API Polls</div>
                <div class="stat-value text-secondary">${stats.total_polls}</div>
                <div class="stat-desc">${stats.avg_polls_per_request} avg per request</div>
            </div>
            
            <div class="stat bg-base-200 rounded-lg">
                <div class="stat-figure text-accent">
                    <i class="fas fa-memory text-2xl"></i>
                </div>
                <div class="stat-title">Cache Hits</div>
                <div class="stat-value text-accent">${stats.cache_hits}</div>
                <div class="stat-desc">${stats.cache_hit_rate} hit rate</div>
            </div>
            
            <div class="stat bg-base-200 rounded-lg">
                <div class="stat-figure text-success">
                    <i class="fas fa-bolt text-2xl"></i>
                </div>
                <div class="stat-title">Efficiency</div>
                <div class="stat-value text-success">${stats.efficiency_improvement}</div>
                <div class="stat-desc">vs baseline</div>
            </div>
        </div>
        
        <!-- Configuration Details -->
        <div class="collapse collapse-arrow bg-base-200 mb-4">
            <input type="checkbox" /> 
            <div class="collapse-title text-xl font-medium">
                <i class="fas fa-cog mr-2"></i>Configuration Details
            </div>
            <div class="collapse-content"> 
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <h4 class="font-semibold mb-2">Polling Settings</h4>
                        <ul class="text-sm space-y-1">
                            <li><strong>Min Interval:</strong> ${config.min_poll_interval}s</li>
                            <li><strong>Max Interval:</strong> ${config.max_poll_interval}s</li>
                            <li><strong>Backoff Factor:</strong> ${config.exponential_backoff}x</li>
                            <li><strong>Batch Operations:</strong> ${config.batch_operations ? 'Enabled' : 'Disabled'}</li>
                        </ul>
                    </div>
                    <div>
                        <h4 class="font-semibold mb-2">Cache Settings</h4>
                        <ul class="text-sm space-y-1">
                            <li><strong>Assistant Cache:</strong> ${Math.round(config.assistant_cache_duration / 3600)}h</li>
                            <li><strong>Max Context:</strong> ${config.max_context_chars} chars</li>
                            <li><strong>Optimization Saves:</strong> ${stats.optimization_saves}</li>
                            <li><strong>API Calls Saved:</strong> ~${stats.estimated_api_calls_saved}</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Performance Chart Placeholder -->
        <div class="card bg-base-200">
            <div class="card-body">
                <h3 class="card-title">
                    <i class="fas fa-chart-bar mr-2"></i>Performance Summary
                </h3>
                <div class="flex justify-between items-center">
                    <div class="text-sm">
                        <p><strong>Optimization Status:</strong> <span class="badge badge-${statusColor}">${recommendations.status}</span></p>
                        <p><strong>Last Updated:</strong> ${new Date().toLocaleString()}</p>
                    </div>
                    <div class="text-right">
                        <div class="text-2xl font-bold text-${statusColor === 'success' ? 'success' : statusColor === 'warning' ? 'warning' : 'error'}">
                            ${stats.efficiency_improvement}
                        </div>
                        <div class="text-sm opacity-70">Efficiency Gain</div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function resetAIStats() {
    if (!confirm('Are you sure you want to reset AI statistics? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/ai/reset-stats', {
            method: 'POST',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Show success message
        const container = document.getElementById('ai-stats-container');
        container.innerHTML = `
            <div class="alert alert-success mb-4">
                <i class="fas fa-check-circle"></i>
                <span>AI statistics have been reset successfully.</span>
            </div>
        `;
        
        // Refresh stats after a short delay
        setTimeout(refreshAIStats, 1000);
    } catch (error) {
        console.error('Error resetting AI stats:', error);
        const container = document.getElementById('ai-stats-container');
        container.innerHTML = `
            <div class="alert alert-error">
                <i class="fas fa-exclamation-triangle"></i>
                <span>Failed to reset AI statistics: ${error.message}</span>
            </div>
        `;
    }
}

// Load AI stats when the tab is first accessed
document.addEventListener('DOMContentLoaded', function() {
    // Add event listener for tab switching
    document.querySelectorAll('[data-tab="ai-stats"]').forEach(tab => {
        tab.addEventListener('click', function() {
            // Load AI stats when tab is clicked
            setTimeout(refreshAIStats, 100);
        });
    });
}); 