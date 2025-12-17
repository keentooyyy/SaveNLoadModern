/**
 * Modal Utilities
 * Shared functions for modal management across the application
 */

/**
 * Get the next z-index for modal stacking
 * Ensures new modals always appear on top of existing ones
 * @returns {number} The next z-index value to use
 */
function getNextModalZIndex() {
    // Bootstrap default: modal = 1050, backdrop = 1040
    let maxZIndex = 1050;
    
    // Find all existing modals and backdrops
    const existingModals = document.querySelectorAll('.modal.show, .modal[style*="z-index"]');
    const existingBackdrops = document.querySelectorAll('.modal-backdrop');
    
    // Check modal z-indexes
    existingModals.forEach(modal => {
        const zIndex = parseInt(window.getComputedStyle(modal).zIndex) || 0;
        if (zIndex > maxZIndex) {
            maxZIndex = zIndex;
        }
    });
    
    // Check backdrop z-indexes
    existingBackdrops.forEach(backdrop => {
        const zIndex = parseInt(window.getComputedStyle(backdrop).zIndex) || 0;
        if (zIndex > maxZIndex) {
            maxZIndex = zIndex;
        }
    });
    
    // Return next z-index (increment by 10 for proper stacking)
    return maxZIndex + 10;
}

