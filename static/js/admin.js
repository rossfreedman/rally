// Global variables to store data
let users = [];
let clubs = [];
let series = [];

// Initialize the admin dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin dashboard initializing...');
    
    // Initialize tab handling
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs and content
            tabs.forEach(t => t.classList.remove('tab-active'));
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.add('hidden');
            });
            
            // Add active class to clicked tab and show content
            this.classList.add('tab-active');
            const contentId = `${this.getAttribute('data-tab')}-content`;
            document.getElementById(contentId).classList.remove('hidden');
            
            // Refresh data for the active tab
            const tabId = this.getAttribute('data-tab');
            if (tabId === 'users') loadUsers();
            else if (tabId === 'clubs') loadClubs();
            else if (tabId === 'series') loadSeries();
        });
    });

    // Initialize sidebar menu handling
    const menuItems = document.querySelectorAll('.menu a');
    menuItems.forEach(item => {
        item.addEventListener('click', function() {
            menuItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            
            // Trigger click on corresponding tab
            const tabId = this.getAttribute('data-tab');
            document.querySelector(`.tab[data-tab="${tabId}"]`).click();
        });
    });

    // Load initial data
    loadUsers();
    loadClubs();
    loadSeries();
});

// Modal handling functions
function showModal(modalId) {
    document.getElementById(modalId).showModal();
}

function closeModal(modalId) {
    document.getElementById(modalId).close();
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
                    Failed to load users: ${error.message}
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
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${user.first_name} ${user.last_name}</td>
            <td>${user.email}</td>
            <td>${user.club_name || ''}</td>
            <td>${user.series_name || ''}</td>
            <td>${user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</td>
            <td>
                <div class="flex gap-2">
                    <button class="btn btn-sm btn-primary" onclick="showEditUserModal('${user.email}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-info" onclick="viewUserActivity('${user.email}')">
                        <i class="fas fa-history"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function showEditUserModal(email) {
    const user = users.find(u => u.email === email);
    if (!user) return;

    document.getElementById('editUserId').value = user.id;
    document.getElementById('editFirstName').value = user.first_name;
    document.getElementById('editLastName').value = user.last_name;
    document.getElementById('editEmail').value = user.email;

    // Populate club dropdown
    const clubSelect = document.getElementById('editClub');
    clubSelect.innerHTML = clubs.map(club => 
        `<option value="${club.id}" ${club.name === user.club_name ? 'selected' : ''}>${club.name}</option>`
    ).join('');

    // Populate series dropdown
    const seriesSelect = document.getElementById('editSeries');
    seriesSelect.innerHTML = series.map(s => 
        `<option value="${s.id}" ${s.name === user.series_name ? 'selected' : ''}>${s.name}</option>`
    ).join('');

    showModal('editUserModal');
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
        const response = await fetch(`/api/admin/user-activity/${encodeURIComponent(email)}`, {
            credentials: 'include'  // Include cookies for authentication
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        // TODO: Implement activity view modal
        console.log('User activity:', data);
    } catch (error) {
        console.error('Error loading user activity:', error);
        alert('Failed to load user activity');
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
        document.getElementById('clubsTableBody').innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-error">
                    Failed to load clubs: ${error.message}
                </td>
            </tr>
        `;
    }
}

function renderClubs() {
    const tbody = document.getElementById('clubsTableBody');
    tbody.innerHTML = '';
    
    clubs.forEach(club => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${club.id}</td>
            <td>${club.name}</td>
            <td>
                <div class="flex gap-2">
                    <button class="btn btn-sm btn-primary" onclick="showEditClubModal(${club.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-error" onclick="deleteClub(${club.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
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
        const response = await fetch('/api/admin/save-club', {
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
            credentials: 'include'  // Include cookies for authentication
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
        document.getElementById('seriesTableBody').innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-error">
                    Failed to load series: ${error.message}
                </td>
            </tr>
        `;
    }
}

function renderSeries() {
    const tbody = document.getElementById('seriesTableBody');
    tbody.innerHTML = '';
    
    series.forEach(s => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${s.id}</td>
            <td>${s.name}</td>
            <td>
                <div class="flex gap-2">
                    <button class="btn btn-sm btn-primary" onclick="showEditSeriesModal(${s.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-error" onclick="deleteSeries(${s.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
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
        const response = await fetch('/api/admin/save-series', {
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
        "First Name,Last Name,Email,Club,Series,Last Login\n" +
        users.map(user => [
            user.first_name,
            user.last_name,
            user.email,
            user.club_name,
            user.series_name,
            user.last_login ? new Date(user.last_login).toLocaleString() : 'Never'
        ].join(",")).join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "users.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
} 