/**
 * Mobile utilities for Rally
 * 
 * This file contains functions and utilities specific to mobile devices
 */

// Mobile utilities for Rally
console.log('[DEBUG] mobile-utils.js loaded on: ' + new Date().toISOString());

// Function to check if mobile view is active
function checkMobileView() {
  const isMobile = window.innerWidth <= 991.98;
  console.log('[DEBUG] Mobile view active: ' + isMobile + ' (width: ' + window.innerWidth + 'px)');
  
  // Add a visual indicator to the page
  const body = document.body;
  if (isMobile) {
    body.setAttribute('data-mobile-view', 'active');
    console.log('[DEBUG] Mobile CSS should be applied');
  } else {
    body.setAttribute('data-mobile-view', 'inactive');
    console.log('[DEBUG] Desktop CSS should be applied');
  }
}

// Fix for iOS 100vh issue by setting CSS var --vh
function setVhVariable() {
  // First we get the viewport height and we multiply it by 1% to get a value for a vh unit
  const vh = window.innerHeight * 0.01;
  // Then we set the value in the --vh custom property to the root of the document
  document.documentElement.style.setProperty('--vh', `${vh}px`);
}

// Function to toggle sidebar visibility
function toggleSidebar() {
  document.body.classList.toggle('sidebar-open');
  
  // Update overlay visibility
  const overlay = document.getElementById('sidebar-overlay');
  if (overlay) {
    if (document.body.classList.contains('sidebar-open')) {
      overlay.style.display = 'block';
      setTimeout(() => overlay.style.opacity = '1', 10);
    } else {
      overlay.style.opacity = '0';
      setTimeout(() => overlay.style.display = 'none', 300);
    }
  }
}

// Function to close sidebar
function closeSidebar() {
  document.body.classList.remove('sidebar-open');
  
  // Update overlay visibility
  const overlay = document.getElementById('sidebar-overlay');
  if (overlay) {
    overlay.style.opacity = '0';
    setTimeout(() => overlay.style.display = 'none', 300);
  }
}

// Initialize viewport height calculation on page load
document.addEventListener('DOMContentLoaded', function() {
  console.log('[DEBUG] DOMContentLoaded event fired in mobile-utils.js');
  
  // Set on initial load
  setVhVariable();
  
  // Check mobile view
  checkMobileView();
  
  // Update on resize and orientation change
  window.addEventListener('resize', function() {
    setVhVariable();
    checkMobileView();
  });
  window.addEventListener('orientationchange', function() {
    setVhVariable();
    checkMobileView();
  });
  
  // Handle sidebar toggle on mobile
  document.body.addEventListener('click', function(e) {
    // If clicking outside the sidebar when it's open, close it
    if (document.body.classList.contains('sidebar-open')) {
      // Check if click was not inside the sidebar and not the toggle button
      const sidebar = document.querySelector('.sidebar');
      const toggler = document.getElementById('sidebar-toggler');
      if (sidebar && !sidebar.contains(e.target) && 
          toggler && !toggler.contains(e.target)) {
        closeSidebar();
      }
    }
  });
  
  // Attach click handlers to sidebar toggle buttons
  const sidebarToggler = document.getElementById('sidebar-toggler');
  if (sidebarToggler) {
    sidebarToggler.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      toggleSidebar();
    });
  }
  
  const sidebarOverlay = document.getElementById('sidebar-overlay');
  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', function() {
      closeSidebar();
    });
  }
  
  // Close sidebar when a nav item is clicked
  const sidebarNavItems = document.querySelectorAll('.sidebar .nav-item');
  sidebarNavItems.forEach(item => {
    item.addEventListener('click', function() {
      if (window.innerWidth < 992) { // Only on mobile
        closeSidebar();
      }
    });
  });
  
  // Improve scrolling behavior on iOS
  document.querySelectorAll('.scrollable-area').forEach(function(element) {
    element.addEventListener('touchstart', function() {
      const top = element.scrollTop;
      const totalScroll = element.scrollHeight;
      const currentScroll = top + element.offsetHeight;
      
      // If we're at the top, allow overscroll behavior
      if(top === 0) {
        element.scrollTop = 1;
      }
      // If we're at the bottom, allow overscroll behavior
      else if(currentScroll === totalScroll) {
        element.scrollTop = top - 1;
      }
    });
  });
}); 