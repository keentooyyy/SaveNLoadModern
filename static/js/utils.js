/**
 * Utility functions for SaveNLoad Modern
 * Shared utilities used across multiple JavaScript files
 */

/**
 * Get CSS variable value from :root
 * @param {string} name - CSS variable name (with or without -- prefix)
 * @returns {string} The CSS variable value
 */
function getCSSVariable(name) {
    // Ensure the name starts with --
    const varName = name.startsWith('--') ? name : `--${name}`;
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
}

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

    // Return next z-index (increment by 20 for proper stacking with backdrop gap)
    return maxZIndex + 20;
}

/**
 * Apply modal stacking (z-index + backdrop) for modal-on-modal scenarios
 * @param {HTMLElement} modalElement - The modal root element
 * @param {object} options - Optional settings
 * @param {number} options.zIndex - Explicit z-index override
 * @returns {{zIndex: number|null}} Applied z-index
 */
function applyModalStacking(modalElement, options = {}) {
    if (!modalElement) {
        return { zIndex: null };
    }

    const fallbackZIndex = 1050;
    const nextZIndex = typeof options.zIndex === 'number'
        ? options.zIndex
        : (typeof getNextModalZIndex === 'function' ? getNextModalZIndex() : fallbackZIndex);
    modalElement.style.zIndex = nextZIndex;

    let ownedBackdrop = null;

    const handleShown = () => {
        let backdrop = document.querySelector('.modal-backdrop:last-of-type');
        if (!backdrop) {
            ownedBackdrop = document.createElement('div');
            ownedBackdrop.className = 'modal-backdrop fade show';
            document.body.appendChild(ownedBackdrop);
            backdrop = ownedBackdrop;
        }
        backdrop.style.zIndex = (nextZIndex - 10).toString();
    };

    const handleHidden = () => {
        if (ownedBackdrop && ownedBackdrop.parentNode) {
            ownedBackdrop.remove();
        }
    };

    modalElement.addEventListener('shown.bs.modal', handleShown, { once: true });
    modalElement.addEventListener('hidden.bs.modal', handleHidden, { once: true });

    return { zIndex: nextZIndex };
}

/**
 * Create modal HTML structure for custom confirm dialog
 * Uses safe DOM manipulation (no innerHTML)
 * @returns {HTMLElement} The created modal element
 */
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

/**
 * Get or create confirm modal
 * @returns {HTMLElement} The modal element
 */
function getConfirmModal() {
    let modal = document.getElementById('customConfirmModal');
    if (!modal) {
        modal = createConfirmModal();
    }
    return modal;
}

/**
 * Custom confirm dialog
 * Replaces browser confirm() with styled modal matching app design
 * Uses safe DOM manipulation (no innerHTML)
 * @param {string} message - The message to display
 * @returns {Promise<boolean>} - Promise that resolves to true if confirmed, false if cancelled
 */
function customConfirm(message) {
    return new Promise((resolve) => {
        const modalElement = getConfirmModal();
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
        newOkBtn.addEventListener('click', function () {
            modal.hide();
            resolve(true);
        });

        // Handle cancel
        newCancelBtn.addEventListener('click', function () {
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
        modalElement.addEventListener('shown.bs.modal', function () {
            const backdrop = document.querySelector('.modal-backdrop:last-of-type');
            if (backdrop) {
                backdrop.style.zIndex = (nextZIndex - 10).toString();
            }
        }, { once: true });

        // Show modal
        modal.show();
    });
}

// Expose to global scope
window.customConfirm = customConfirm;
window.applyModalStacking = applyModalStacking;

// Override native confirm() globally
window.confirm = customConfirm;

/**
 * Show toast notification (XSS-safe)
 * Used across multiple JavaScript files for consistent toast notifications
 * @param {string} message - The message to display
 * @param {string} type - The alert type: 'success', 'error', or 'info' (default)
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    const alertType = type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info';
    toast.className = `alert alert-${alertType} alert-dismissible fade show position-fixed toast-container-custom`;

    // Use textContent for message to prevent XSS
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    toast.appendChild(messageSpan);

    // Create close button safely
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'btn-close';
    closeBtn.setAttribute('data-bs-dismiss', 'alert');
    closeBtn.setAttribute('aria-label', 'Close');
    toast.appendChild(closeBtn);

    document.body.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
}

/**
 * Get CSRF token from form or cookie
 * @param {string} selector - Optional selector for CSRF token input (default: '[name="csrfmiddlewaretoken"]')
 * @returns {string|null} The CSRF token or null if not found
 */
function getCsrfToken(selector = '[name="csrfmiddlewaretoken"]') {
    // Try to get from form input first
    const csrfInput = document.querySelector(selector);
    if (csrfInput && csrfInput.value) {
        return csrfInput.value;
    }

    // Fallback: try to get from cookie
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }

    // If not found, show error and return null
    showToast('Error: CSRF token not found', 'error');
    return null;
}

/**
 * Create fetch headers with CSRF token
 * @param {string} csrfToken - The CSRF token
 * @returns {Object} Headers object for fetch requests
 */
function createFetchHeaders(csrfToken) {
    return {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken
    };
}

/**
 * Set button loading state with spinner
 * @param {HTMLElement} button - The button element
 * @param {boolean} isLoading - Whether to show loading state
 * @param {string} loadingText - Text to show during loading (default: 'Loading...')
 */
function setButtonLoadingState(button, isLoading, loadingText = 'Loading...') {
    if (!button) return;

    if (isLoading) {
        const originalContent = Array.from(button.childNodes);
        button.disabled = true;
        button.textContent = '';
        const spinnerIcon = document.createElement('i');
        spinnerIcon.className = 'fas fa-spinner fa-spin me-1';
        const loadingTextNode = document.createTextNode(loadingText);
        button.appendChild(spinnerIcon);
        button.appendChild(loadingTextNode);
        // Store original content for restoration
        button._originalContent = originalContent;
    } else {
        button.disabled = false;
        button.textContent = '';
        if (button._originalContent) {
            button._originalContent.forEach(node => {
                button.appendChild(node.cloneNode(true));
            });
            button._originalContent = null;
        }
    }
}

/**
 * Set button state (simple version - just text change)
 * @param {HTMLElement} button - The button element
 * @param {boolean} isLoading - Whether to show loading state
 * @param {string} loadingText - Text to show during loading (optional, only needed when isLoading is true)
 */
function setButtonState(button, isLoading, loadingText) {
    if (!button) return;

    if (isLoading) {
        if (!loadingText) {
            console.warn('setButtonState: loadingText is required when isLoading is true');
            return;
        }
        button.disabled = true;
        button._originalText = button.textContent;
        button.textContent = loadingText;
    } else {
        button.disabled = false;
        if (button._originalText) {
            button.textContent = button._originalText;
            button._originalText = null;
        }
    }
}

/**
 * Show error message in error element
 * @param {HTMLElement} errorElement - The error display element
 * @param {string} message - The error message
 */
function showError(errorElement, message) {
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('d-none');
        errorElement.classList.add('d-block');
    }
}

/**
 * Show validation error for a specific field (input + error div)
 * @param {string} fieldName - Input element id
 * @param {string} message - Error message
 * @param {object} options - Optional settings
 * @param {string} options.errorSuffix - Error element id suffix (default: '-error')
 * @param {HTMLElement} options.container - Optional container scope
 */
function showFieldError(fieldName, message, options = {}) {
    const errorSuffix = options.errorSuffix || '-error';
    const container = options.container || document;
    const input = container.querySelector(`#${fieldName}`);
    const errorDiv = container.querySelector(`#${fieldName}${errorSuffix}`);

    if (input && errorDiv) {
        input.classList.add('is-invalid');
        input.classList.add('border-danger');
        showError(errorDiv, message);
    }
}

/**
 * Clear validation error for a specific field (input + error div)
 * @param {string} fieldName - Input element id
 * @param {object} options - Optional settings
 * @param {string} options.errorSuffix - Error element id suffix (default: '-error')
 * @param {HTMLElement} options.container - Optional container scope
 */
function clearFieldError(fieldName, options = {}) {
    const errorSuffix = options.errorSuffix || '-error';
    const container = options.container || document;
    const input = container.querySelector(`#${fieldName}`);
    const errorDiv = container.querySelector(`#${fieldName}${errorSuffix}`);

    if (input) {
        input.classList.remove('is-invalid');
        input.classList.remove('border-danger');
    }
    if (errorDiv) {
        clearError(errorDiv);
    }
}

/**
 * Clear all field errors in a container
 * @param {HTMLElement} container - Optional container scope
 */
function clearFieldErrors(container = document) {
    const errorElements = container.querySelectorAll('.invalid-feedback');
    const inputs = container.querySelectorAll('.is-invalid');
    errorElements.forEach(el => clearError(el));
    inputs.forEach(input => {
        input.classList.remove('is-invalid');
        input.classList.remove('border-danger');
    });
}

/**
 * Attach input listeners to clear field errors
 * @param {string[]} fieldNames - Array of input ids
 * @param {object} options - Optional settings
 * @param {string} options.errorSuffix - Error element id suffix (default: '-error')
 * @param {HTMLElement} options.container - Optional container scope
 */
function setupFieldErrorClear(fieldNames, options = {}) {
    const names = Array.isArray(fieldNames) ? fieldNames : [fieldNames];
    const container = options.container || document;
    names.forEach(name => {
        const input = container.querySelector(`#${name}`);
        if (input) {
            input.addEventListener('input', function () {
                clearFieldError(name, options);
            });
        }
    });
}

/**
 * Clear error message from error element
 * @param {HTMLElement} errorElement - The error display element
 */
function clearError(errorElement) {
    if (errorElement) {
        errorElement.classList.add('d-none');
        errorElement.classList.remove('d-block');
        errorElement.textContent = '';
    }
}

/**
 * Setup password visibility toggle
 * @param {HTMLElement|string} toggleBtn - The toggle button element or its ID
 * @param {HTMLElement|string} passwordInput - The password input element or its ID
 */
function setupPasswordToggle(toggleBtn, passwordInput) {
    // Support both element ID (string) and element object
    const toggle = typeof toggleBtn === 'string' ? document.getElementById(toggleBtn) : toggleBtn;
    const input = typeof passwordInput === 'string' ? document.getElementById(passwordInput) : passwordInput;

    if (!toggle || !input) return;

    toggle.addEventListener('click', function () {
        const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
        input.setAttribute('type', type);

        // Toggle icon classes
        if (type === 'password') {
            toggle.classList.remove('fa-eye');
            toggle.classList.add('fa-eye-slash');
        } else {
            toggle.classList.remove('fa-eye-slash');
            toggle.classList.add('fa-eye');
        }
    });
}

/**
 * Clear all children from an element
 * @param {HTMLElement} element - The element to clear
 */
function clearElement(element) {
    if (!element) return;
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
}

/**
 * Sanitize email input (trim, strip tags, normalize, length limit)
 * @param {string} email - Raw email input
 * @returns {string} Sanitized email
 */
function sanitizeEmailInput(email) {
    if (!email) return '';

    let cleaned = email.trim();
    const div = document.createElement('div');
    div.textContent = cleaned;
    cleaned = div.textContent || div.innerText || '';

    if (cleaned.length > 254) {
        cleaned = cleaned.substring(0, 254);
    }

    return cleaned.toLowerCase();
}

/**
 * Sanitize password input (trim, remove null bytes, length limit)
 * @param {string} password - Raw password input
 * @returns {string} Sanitized password
 */
function sanitizePasswordInput(password) {
    if (!password) return '';

    let cleaned = password.trim();
    cleaned = cleaned.replace(/\x00/g, '');

    if (cleaned.length > 128) {
        cleaned = cleaned.substring(0, 128);
    }

    return cleaned;
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if valid
 */
function validateEmailFormat(email) {
    if (!email) return false;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}


// Expose all utility functions to global scope
window.showToast = showToast;
window.getCsrfToken = getCsrfToken;
window.createFetchHeaders = createFetchHeaders;
window.setButtonLoadingState = setButtonLoadingState;
window.setButtonState = setButtonState;
window.showError = showError;
window.clearError = clearError;
window.showFieldError = showFieldError;
window.clearFieldError = clearFieldError;
window.clearFieldErrors = clearFieldErrors;
window.setupFieldErrorClear = setupFieldErrorClear;
window.setupPasswordToggle = setupPasswordToggle;
window.clearElement = clearElement;
window.getNextModalZIndex = getNextModalZIndex;
window.sanitizeEmailInput = sanitizeEmailInput;
window.sanitizePasswordInput = sanitizePasswordInput;
window.validateEmailFormat = validateEmailFormat;

