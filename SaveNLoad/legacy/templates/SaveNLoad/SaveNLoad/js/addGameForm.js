/**
 * Add Game Form Collapse Handler.
 * Handles chevron rotation and highlight effect on collapse toggle.
 *
 * Args:
 *     None
 *
 * Returns:
 *     None
 */
(function() {
    'use strict';
    
    /**
     * Initialize collapse handlers for the Add Game form.
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    document.addEventListener('DOMContentLoaded', function() {
        const collapseElement = document.getElementById('addGameFormCollapse');
        const chevron = document.getElementById('addGameChevron');
        const headerButton = document.querySelector('[data-bs-target="#addGameFormCollapse"]');
        
        if (collapseElement && chevron && headerButton) {
            /**
             * Rotate chevron and highlight header when the collapse opens.
             *
             * Args:
             *     None
             *
             * Returns:
             *     None
             */
            collapseElement.addEventListener('show.bs.collapse', function() {
                chevron.style.transform = 'rotate(90deg)';
                // Add highlight effect
                headerButton.classList.add('active');
            });
            
            /**
             * Reset chevron and header style when the collapse closes.
             *
             * Args:
             *     None
             *
             * Returns:
             *     None
             */
            collapseElement.addEventListener('hide.bs.collapse', function() {
                chevron.style.transform = 'rotate(0deg)';
                // Remove highlight effect
                headerButton.classList.remove('active');
            });
        }
    });
})();

