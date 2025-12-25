document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    
    if (!loginForm) {
        console.error('Login form not found!');
        return;
    }
    
    // Safe wrapper for setButtonState with fallback
    // Ensures the function exists before calling it
    function safeSetButtonState(button, isLoading, loadingText) {
        if (typeof window.setButtonState === 'function') {
            window.setButtonState(button, isLoading, loadingText);
        } else {
            // Fallback: simple button state management
            if (!button) return;
            if (isLoading) {
                button.disabled = true;
                if (loadingText) {
                    button._originalText = button.textContent;
                    button.textContent = loadingText;
                }
            } else {
                button.disabled = false;
                if (button._originalText) {
                    button.textContent = button._originalText;
                    button._originalText = null;
                }
            }
        }
    }
    
    // Get or create message container
    let alertContainer = document.getElementById('alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alert-container';
        alertContainer.className = 'mb-3';
        loginForm.parentNode.insertBefore(alertContainer, loginForm);
    }
    
    function clearFieldErrors() {
        // Clear all field errors
        const errorElements = document.querySelectorAll('.invalid-feedback');
        const inputs = document.querySelectorAll('.is-invalid');
        errorElements.forEach(el => {
            el.textContent = '';
            el.classList.add('d-none');
            el.classList.remove('d-block');
        });
        inputs.forEach(input => {
            input.classList.remove('is-invalid');
            input.classList.remove('border-danger');
        });
    }
    
    function clearFieldError(fieldName) {
        const input = document.getElementById(fieldName);
        const errorDiv = document.getElementById(fieldName + '-error');
        
        if (input && errorDiv) {
            input.classList.remove('is-invalid');
            input.classList.remove('border-danger');
            errorDiv.textContent = '';
            errorDiv.classList.add('d-none');
            errorDiv.classList.remove('d-block');
        }
    }
    
    function showFieldError(fieldName, message) {
        const input = document.getElementById(fieldName);
        const errorDiv = document.getElementById(fieldName + '-error');
        
        if (input && errorDiv) {
            input.classList.add('is-invalid');
            input.classList.add('border-danger');
            errorDiv.textContent = message;
            errorDiv.classList.remove('d-none');
            errorDiv.classList.add('d-block');
        }
    }
    
    function showAlert(message, type = 'danger', errors = []) {
        // Remove existing alerts
        const existingAlerts = alertContainer.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());
        
        // Create new alert
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        
        // Create message container
        const messageContainer = document.createElement('div');
        
        // Add main message
        const messageText = document.createTextNode(message);
        messageContainer.appendChild(messageText);
        
        // Add errors if any (each on a new line)
        if (errors && errors.length > 0) {
            errors.forEach((error, index) => {
                if (index > 0) {
                    messageContainer.appendChild(document.createElement('br'));
                }
                const errorText = document.createTextNode(error);
                messageContainer.appendChild(errorText);
            });
        }
        
        // Create close button
        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'btn-close';
        closeButton.setAttribute('data-bs-dismiss', 'alert');
        closeButton.setAttribute('aria-label', 'Close');
        
        // Append elements
        alertDiv.appendChild(messageContainer);
        alertDiv.appendChild(closeButton);
        alertContainer.appendChild(alertDiv);
        
        // Scroll to top of form
        alertContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    // Uses shared utility functions from utils.js
    
    // Clear field errors when user starts typing
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    
    if (usernameInput) {
        usernameInput.addEventListener('input', function() {
            clearFieldError('username');
        });
    }
    
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            clearFieldError('password');
        });
    }
    
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const submitButton = loginForm.querySelector('button[type="submit"]');
        
        // Set button loading state
        safeSetButtonState(submitButton, true, 'LOGGING IN...');
        
        // Get form data (includes CSRF token from hidden input)
        const formData = new FormData(loginForm);
        
        // Get CSRF token from hidden input (created by {% csrf_token %})
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfInput || !csrfInput.value) {
            showAlert('CSRF token not found. Please refresh the page and try again.', 'danger');
            safeSetButtonState(submitButton, false);
            return;
        }
        
        // Make AJAX request with CSRF protection
        fetch(loginForm.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfInput.value
            },
            credentials: 'same-origin',  // Important for CSRF cookie
            body: formData
        })
        .then(response => {
            // Check for CSRF error (403 status)
            if (response.status === 403) {
                return response.json().then(data => {
                    throw new Error('CSRF verification failed');
                }).catch(() => {
                    throw new Error('CSRF verification failed');
                });
            }
            // Check for server-side redirect header
            const redirectUrl = response.headers.get('X-Redirect-URL');
            return response.json().then(data => ({ data, redirectUrl }));
        })
        .then(({ data, redirectUrl }) => {
            if (data.success) {
                clearFieldErrors();
                showAlert(data.message, 'success');
                // Follow server-side redirect
                if (redirectUrl) {
                    setTimeout(() => {
                        window.location.href = redirectUrl;
                    }, 1000);
                }
            } else {
                // Clear previous field errors
                clearFieldErrors();
                
                // Show field-specific errors
                if (data.field_errors) {
                    Object.keys(data.field_errors).forEach(fieldName => {
                        showFieldError(fieldName, data.field_errors[fieldName]);
                    });
                }
                
                // Only show general alert if there are general errors (not field errors)
                if (data.errors && data.errors.length > 0) {
                    showAlert(data.errors[0], 'danger', data.errors);
                }
                
                safeSetButtonState(submitButton, false);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            // Check for CSRF errors
            if (error.message && error.message.includes('CSRF')) {
                showAlert('CSRF verification failed. Please refresh the page and try again.', 'danger');
            } else {
                showAlert('An error occurred. Please try again.', 'danger');
            }
            safeSetButtonState(submitButton, false);
        });
    });
});

