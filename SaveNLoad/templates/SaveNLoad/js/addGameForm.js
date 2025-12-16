/**
 * Add Game Form Collapse Handler
 * Handles chevron rotation and highlight effect on collapse toggle
 */
(function() {
    'use strict';
    
    document.addEventListener('DOMContentLoaded', function() {
        const collapseElement = document.getElementById('addGameFormCollapse');
        const chevron = document.getElementById('addGameChevron');
        const headerButton = document.querySelector('[data-bs-target="#addGameFormCollapse"]');
        
        if (collapseElement && chevron && headerButton) {
            collapseElement.addEventListener('show.bs.collapse', function() {
                chevron.classList.remove('fa-chevron-right');
                chevron.classList.add('fa-chevron-down');
                // Add highlight effect
                headerButton.classList.add('active');
            });
            
            collapseElement.addEventListener('hide.bs.collapse', function() {
                chevron.classList.remove('fa-chevron-down');
                chevron.classList.add('fa-chevron-right');
                // Remove highlight effect
                headerButton.classList.remove('active');
            });
        }
    });
})();

