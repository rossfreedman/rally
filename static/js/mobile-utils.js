/**
 * Mobile utilities for Rally
 * 
 * This file contains functions and utilities specific to mobile devices
 */

// Fix for iOS 100vh issue
function setVhVariable() {
  let vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
}

// Initialize viewport height calculation on page load
document.addEventListener('DOMContentLoaded', function() {
  // Set on initial load
  setVhVariable();
  
  // Update on resize and orientation change
  window.addEventListener('resize', setVhVariable);
  window.addEventListener('orientationchange', setVhVariable);
  
  // Handle sidebar toggle on mobile
  document.body.addEventListener('click', function(e) {
    // If clicking outside the sidebar when it's open, close it
    if (document.body.classList.contains('sidebar-open')) {
      // Check if click was not inside the sidebar
      const sidebar = document.querySelector('.sidebar');
      if (sidebar && !sidebar.contains(e.target) && !e.target.classList.contains('sidebar-toggler')) {
        document.body.classList.remove('sidebar-open');
      }
    }
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