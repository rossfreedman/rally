// Rally - Responsive Test Script
// This script will run basic tests to ensure responsive functionality works

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== Running Responsive Design Tests ===');
    
    // Test 1: Check viewport meta tag
    testViewportMetaTag();
    
    // Test 2: Check responsive CSS file is loaded
    testResponsiveCssLoaded();
    
    // Test 3: Check sidebar behavior
    testSidebarBehavior();
    
    // Log device info
    logDeviceInfo();
});

// Test viewport meta tag
function testViewportMetaTag() {
    const viewport = document.querySelector('meta[name="viewport"]');
    if (viewport) {
        console.log('✅ Viewport meta tag exists');
        console.log('   Content: ' + viewport.getAttribute('content'));
    } else {
        console.error('❌ Viewport meta tag missing');
    }
}

// Test responsive CSS loaded
function testResponsiveCssLoaded() {
    const responsiveCss = document.querySelector('link[href="/static/css/responsive.css"]');
    if (responsiveCss) {
        console.log('✅ Responsive CSS file is loaded');
    } else {
        console.error('❌ Responsive CSS file is not loaded');
    }
}

// Test sidebar behavior
function testSidebarBehavior() {
    const sidebar = document.querySelector('.sidebar');
    if (!sidebar) {
        console.error('❌ Sidebar element not found');
        return;
    }
    
    console.log('✅ Sidebar element exists');
    
    // Check if sidebar is properly positioned based on screen size
    const screenWidth = window.innerWidth;
    const sidebarStyle = window.getComputedStyle(sidebar);
    
    if (screenWidth < 768) {
        // On mobile, sidebar should be off-screen
        if (sidebarStyle.left === '-100%' || parseFloat(sidebarStyle.left) < 0) {
            console.log('✅ Sidebar correctly positioned for mobile (hidden)');
        } else {
            console.warn('⚠️ Sidebar may not be correctly positioned for mobile');
            console.log('   Current position: ' + sidebarStyle.left);
        }
    } else {
        // On desktop, sidebar should be visible
        if (sidebarStyle.left === '0px' || parseFloat(sidebarStyle.left) === 0) {
            console.log('✅ Sidebar correctly positioned for desktop (visible)');
        } else {
            console.warn('⚠️ Sidebar may not be correctly positioned for desktop');
            console.log('   Current position: ' + sidebarStyle.left);
        }
    }
}

// Log device information
function logDeviceInfo() {
    console.log('=== Device Information ===');
    console.log('Screen Width: ' + window.innerWidth + 'px');
    console.log('Screen Height: ' + window.innerHeight + 'px');
    console.log('User Agent: ' + navigator.userAgent);
    console.log('Device Pixel Ratio: ' + window.devicePixelRatio);
    
    // Check if this is likely a mobile device
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768;
    console.log('Detected as Mobile: ' + (isMobile ? 'Yes' : 'No'));
} 