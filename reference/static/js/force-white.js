// FORCE TEXT WHITE
document.addEventListener('DOMContentLoaded', function() {
  const style = document.createElement('style');
  style.textContent = ".sidebar, .sidebar *, .nav-item, .nav-section-header { color: white !important; -webkit-text-fill-color: white !important; }";
  document.head.appendChild(style);
  
  // Check for gray text
  setTimeout(function() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
      sidebar.querySelectorAll('*').forEach(el => {
        if (el.tagName !== 'IMG') {
          el.style.setProperty('color', 'white', 'important');
        }
      });
    }
  }, 300);
}); 