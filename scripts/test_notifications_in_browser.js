// Test script to run in browser console
// Copy and paste this into the browser console on http://localhost:8080/mobile

console.log("=== Testing Notifications in Browser ===");

// Test 1: Check if elements exist
const container = document.getElementById('notifications-container');
const loading = document.getElementById('notifications-loading');
const empty = document.getElementById('notifications-empty');
const content = document.getElementById('notifications-content');

console.log('Elements check:');
console.log('- notifications-container:', !!container);
console.log('- notifications-loading:', !!loading);  
console.log('- notifications-empty:', !!empty);
console.log('- notifications-content:', !!content);

if (!container) {
    console.error('❌ notifications-container not found! This is why notifications aren\'t loading.');
    console.log('Available elements with "notification" in ID:');
    const notificationElements = document.querySelectorAll('[id*="notification"]');
    notificationElements.forEach(el => console.log(`- ${el.id}:`, el));
} else {
    console.log('✅ Container found, testing API call...');
    
    // Test 2: Direct API call
    fetch('/api/home/notifications')
        .then(response => {
            console.log('API Response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('API Response data:', data);
            
            if (data.error) {
                console.error('❌ API Error:', data.error);
            } else {
                const notifications = data.notifications || [];
                console.log(`✅ Got ${notifications.length} notifications:`);
                
                // Look for pickup game notifications
                const pickupNotifications = notifications.filter(n => 
                    n.id.includes('pickup') || 
                    n.title.toLowerCase().includes('pickup') ||
                    n.message.toLowerCase().includes('pickup')
                );
                
                console.log(`🎾 Found ${pickupNotifications.length} pickup notifications:`);
                pickupNotifications.forEach((notif, i) => {
                    console.log(`  ${i + 1}. ${notif.title}`);
                    console.log(`     ${notif.message}`);
                    console.log(`     Priority: ${notif.priority}`);
                });
                
                if (pickupNotifications.length === 0) {
                    console.log('All notifications:');
                    notifications.forEach((notif, i) => {
                        console.log(`  ${i + 1}. ${notif.title} (${notif.id})`);
                    });
                }
            }
        })
        .catch(error => {
            console.error('❌ Fetch Error:', error);
        });
}

// Test 3: Try to call the initialization function if it exists
if (typeof initializeHomePageNotifications === 'function') {
    console.log('✅ initializeHomePageNotifications function exists, calling it...');
    initializeHomePageNotifications();
} else {
    console.error('❌ initializeHomePageNotifications function not found!');
}
