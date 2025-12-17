/**
 * Custom Confirm Dialog
 * Replaces browser confirm() with styled modal matching app design
 * Uses safe DOM manipulation (no innerHTML)
 */
(function() {
    'use strict';

    // Helper function to get the next z-index for modal stacking
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

    // Create modal HTML structure using safe DOM manipulation
    function createConfirmModal() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'customConfirmModal';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-labelledby', 'customConfirmModalLabel');
        modal.setAttribute('aria-hidden', 'true');
        
        const dialog = document.createElement('div');
        dialog.className = 'modal-dialog modal-dialog-centered';
        
        const content = document.createElement('div');
        content.className = 'modal-content bg-primary border-secondary';
        
        // Header
        const header = document.createElement('div');
        header.className = 'modal-header border-secondary';
        
        const title = document.createElement('h5');
        title.className = 'modal-title text-white';
        title.id = 'customConfirmModalLabel';
        title.textContent = 'Confirm';
        
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close btn-close-white';
        closeBtn.setAttribute('data-bs-dismiss', 'modal');
        closeBtn.setAttribute('aria-label', 'Close');
        
        header.appendChild(title);
        header.appendChild(closeBtn);
        
        // Body
        const body = document.createElement('div');
        body.className = 'modal-body';
        
        const message = document.createElement('p');
        message.className = 'text-white mb-0';
        message.id = 'customConfirmMessage';
        
        body.appendChild(message);
        
        // Footer
        const footer = document.createElement('div');
        footer.className = 'modal-footer border-secondary';
        
        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn btn-secondary text-white';
        cancelBtn.id = 'customConfirmCancelBtn';
        cancelBtn.setAttribute('data-bs-dismiss', 'modal');
        cancelBtn.textContent = 'Cancel';
        
        const okBtn = document.createElement('button');
        okBtn.type = 'button';
        okBtn.className = 'btn btn-danger text-white';
        okBtn.id = 'customConfirmOkBtn';
        okBtn.textContent = 'Confirm';
        
        footer.appendChild(cancelBtn);
        footer.appendChild(okBtn);
        
        // Assemble structure
        content.appendChild(header);
        content.appendChild(body);
        content.appendChild(footer);
        dialog.appendChild(content);
        modal.appendChild(dialog);
        
        document.body.appendChild(modal);
        return modal;
    }

    // Get or create modal
    function getModal() {
        let modal = document.getElementById('customConfirmModal');
        if (!modal) {
            modal = createConfirmModal();
        }
        return modal;
    }

    /**
     * Custom confirm dialog
     * @param {string} message - The message to display
     * @returns {Promise<boolean>} - Promise that resolves to true if confirmed, false if cancelled
     */
    window.customConfirm = function(message) {
        return new Promise((resolve) => {
            const modalElement = getModal();
            const modal = window.bootstrap ? window.bootstrap.Modal.getOrCreateInstance(modalElement) : null;
            
            if (!modal) {
                // Fallback to native confirm if Bootstrap is not available
                const result = window.confirm(message);
                resolve(result);
                return;
            }

            // Set message
            const messageEl = document.getElementById('customConfirmMessage');
            if (messageEl) {
                messageEl.textContent = message;
            }

            // Remove previous event listeners by cloning buttons
            const okBtn = document.getElementById('customConfirmOkBtn');
            const cancelBtn = document.getElementById('customConfirmCancelBtn');
            
            // Create new buttons to remove old listeners
            const newOkBtn = okBtn.cloneNode(true);
            const newCancelBtn = cancelBtn.cloneNode(true);
            okBtn.parentNode.replaceChild(newOkBtn, okBtn);
            cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);

            // Handle confirm
            newOkBtn.addEventListener('click', function() {
                modal.hide();
                resolve(true);
            });

            // Handle cancel
            newCancelBtn.addEventListener('click', function() {
                modal.hide();
                resolve(false);
            });

            // Handle backdrop click or ESC key
            modalElement.addEventListener('hidden.bs.modal', function handler() {
                modalElement.removeEventListener('hidden.bs.modal', handler);
                resolve(false);
            }, { once: true });

            // Get next z-index for proper stacking (ensure it's on top)
            const nextZIndex = getNextModalZIndex();
            modalElement.style.zIndex = nextZIndex;

            // Set backdrop z-index after modal is shown (Bootstrap creates backdrop dynamically)
            modalElement.addEventListener('shown.bs.modal', function() {
                const backdrop = document.querySelector('.modal-backdrop:last-of-type');
                if (backdrop) {
                    backdrop.style.zIndex = (nextZIndex - 10).toString();
                }
            }, { once: true });

            // Show modal
            modal.show();
        });
    };

    // Override native confirm() globally
    window.confirm = window.customConfirm;
})();

