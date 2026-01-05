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

const toastrDefaults = {
    closeButton: true,
    debug: false,
    newestOnTop: false,
    progressBar: true,
    positionClass: 'toast-top-right',
    preventDuplicates: false,
    onclick: null,
    showDuration: 300,
    hideDuration: 1000,
    timeOut: 5000,
    extendedTimeOut: 1000,
    showEasing: 'swing',
    hideEasing: 'linear',
    showMethod: 'fadeIn',
    hideMethod: 'fadeOut'
};

function configureToastrOptions(overrides = {}) {
    if (!window.toastr) {
        return;
    }
    window.toastr.options = {
        ...toastrDefaults,
        ...(window.toastr.options || {}),
        ...(overrides || {})
    };
}

configureToastrOptions();

/**
 * Show toast notification (XSS-safe)
 * Used across multiple JavaScript files for consistent toast notifications
 * @param {string} message - The message to display
 * @param {string} type - The toast type: 'success', 'error', 'warning', or 'info' (default)
 * @param {object} options - Optional overrides for toast behavior
 */
function showToast(message, type = 'info', options = {}) {
    if (!window.toastr) {
        console.warn('Toastr is not loaded.');
        return;
    }
    configureToastrOptions(options);
    const normalized = String(type || 'info').toLowerCase();
    const show = typeof window.toastr[normalized] === 'function'
        ? window.toastr[normalized]
        : window.toastr.info;
    show(message);
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

/**
 * Normalize operation IDs from various response shapes.
 * @param {object} data - Response data
 * @returns {string[]} Normalized operation IDs
 */
function normalizeOperationIds(data) {
    if (!data) {
        return [];
    }
    if (Array.isArray(data.operation_ids)) {
        return data.operation_ids;
    }
    if (Array.isArray(data.operationIds)) {
        return data.operationIds;
    }
    if (data.data && Array.isArray(data.data.operation_ids)) {
        return data.data.operation_ids;
    }
    if (typeof data.operation_ids === 'string') {
        return data.operation_ids.split(',').map(id => id.trim()).filter(Boolean);
    }
    if (data.operation_id) {
        return [data.operation_id];
    }
    if (data.data && data.data.operation_id) {
        return [data.data.operation_id];
    }
    return [];
}

/**
 * Poll multiple operations and aggregate progress.
 * @param {string[]} operationIds - Operation IDs to poll
 * @param {object} options - Polling options
 * @param {number} options.maxAttempts - Max poll attempts (default 300)
 * @param {number} options.pollInterval - Poll interval in ms (default 1000)
 * @param {function} options.onProgress - Called with aggregated progress
 * @param {function} options.onComplete - Called when all succeed
 * @param {function} options.onPartial - Called when some succeed
 * @param {function} options.onFail - Called when all fail
 * @param {function} options.onTimeout - Called on timeout
 * @param {function} options.onError - Called on unexpected errors
 * @returns {Promise<{status: string}>} Resolves when finished
 */
function pollMultipleOperationStatus(operationIds, options = {}) {
    if (!Array.isArray(operationIds) || operationIds.length === 0) {
        return Promise.resolve({ status: 'no-ops' });
    }

    const maxAttempts = options.maxAttempts || 300;
    const pollInterval = options.pollInterval || 1000;
    const onProgress = options.onProgress;
    const onComplete = options.onComplete;
    const onPartial = options.onPartial;
    const onFail = options.onFail;
    const onTimeout = options.onTimeout;
    const onError = options.onError;
    const urlPattern = options.checkUrlPattern || window.CHECK_OPERATION_STATUS_URL_PATTERN;

    const totalOperations = operationIds.length;
    const operationStatuses = {};
    operationIds.forEach(id => {
        operationStatuses[id] = { completed: false, success: false };
    });

    let attempts = 0;
    let pollHandle = null;
    let resolved = false;

    const resolveOnce = (resolve, status) => {
        if (resolved) return;
        resolved = true;
        if (pollHandle) {
            clearInterval(pollHandle);
            pollHandle = null;
        }
        resolve({ status });
    };

    const aggregateAndReport = () => {
        const activeOperations = Object.entries(operationStatuses)
            .filter(([id, status]) => !status.completed && status.progress)
            .map(([id, status]) => status.progress);

        let totalCurrent = 0;
        let totalTotal = 0;
        let latestMessage = '';

        activeOperations.forEach(progress => {
            if (progress.current !== undefined && progress.total !== undefined) {
                totalCurrent += progress.current || 0;
                totalTotal += progress.total || 0;
            }
            if (progress.message) {
                latestMessage = progress.message;
            }
        });

        const completedCount = Object.values(operationStatuses).filter(s => s.completed).length;
        const percentage = totalTotal > 0
            ? Math.round((totalCurrent / totalTotal) * 100)
            : Math.round((completedCount / totalOperations) * 100);

        if (typeof onProgress === 'function') {
            onProgress({
                percentage,
                current: totalCurrent,
                total: totalTotal,
                message: latestMessage,
                completedCount,
                totalOperations,
                activeCount: activeOperations.length
            });
        }
    };

    const checkStatus = async () => {
        try {
            const statusPromises = operationIds.map(async (opId) => {
                if (operationStatuses[opId].completed) {
                    return operationStatuses[opId];
                }

                try {
                    const url = urlPattern.replace('/0/', `/${opId}/`);
                    const response = await fetch(url, {
                        headers: { 'X-Requested-With': 'XMLHttpRequest' }
                    });

                    if (response.ok) {
                        const data = await response.json();
                        if (data.completed) {
                            operationStatuses[opId] = {
                                completed: true,
                                success: !data.failed
                            };
                        } else if (data.failed) {
                            operationStatuses[opId] = {
                                completed: true,
                                success: false
                            };
                        } else if (data.progress) {
                            operationStatuses[opId].progress = data.progress;
                        }
                    }
                } catch (error) {
                    console.error(`Error checking operation ${opId} status:`, error);
                }

                return operationStatuses[opId];
            });

            await Promise.all(statusPromises);
            aggregateAndReport();

            const allCompleted = Object.values(operationStatuses).every(status => status.completed);
            if (!allCompleted) {
                return false;
            }

            const allSuccessful = Object.values(operationStatuses).every(status => status.success);
            const someSuccessful = Object.values(operationStatuses).some(status => status.success);

            if (allSuccessful && typeof onComplete === 'function') {
                onComplete();
            } else if (someSuccessful && typeof onPartial === 'function') {
                onPartial();
            } else if (!someSuccessful && typeof onFail === 'function') {
                onFail();
            } else if (typeof onComplete === 'function') {
                onComplete();
            }

            return true;
        } catch (error) {
            console.error('Error checking operation status:', error);
            if (typeof onError === 'function') {
                onError(error);
            }
            return false;
        }
    };

    return new Promise(async (resolve) => {
        const completed = await checkStatus();
        if (completed) {
            resolveOnce(resolve, 'completed');
            return;
        }

        pollHandle = setInterval(async () => {
            attempts++;
            const done = await checkStatus();

            if (done) {
                resolveOnce(resolve, 'completed');
                return;
            }

            if (attempts >= maxAttempts) {
                if (typeof onTimeout === 'function') {
                    onTimeout();
                }
                resolveOnce(resolve, 'timeout');
            }
        }, pollInterval);
    });
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
window.normalizeOperationIds = normalizeOperationIds;
window.pollMultipleOperationStatus = pollMultipleOperationStatus;

