document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.querySelector('form[action*="register"]');
    
    if (!registerForm) return;
    
    // Create message container if it doesn't exist
    let alertContainer = document.getElementById('alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alert-container';
        alertContainer.className = 'mb-3';
        const form = registerForm;
        form.parentNode.insertBefore(alertContainer, form);
    }
    
    function clearFieldErrors() {
        // Clear all field errors
        const errorElements = document.querySelectorAll('.invalid-feedback');
        const inputs = document.querySelectorAll('.is-invalid');
        errorElements.forEach(el => {
            el.textContent = '';
            el.style.display = 'none';
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
            errorDiv.style.display = 'none';
        }
    }
    
    function showFieldError(fieldName, message) {
        const input = document.getElementById(fieldName);
        const errorDiv = document.getElementById(fieldName + '-error');
        
        if (input && errorDiv) {
            input.classList.add('is-invalid');
            input.classList.add('border-danger');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
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
    
    // Clear field errors when user starts typing
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const repeatPasswordInput = document.getElementById('repeatPassword');
    
    if (usernameInput) {
        usernameInput.addEventListener('input', function() {
            clearFieldError('username');
        });
    }
    
    if (emailInput) {
        emailInput.addEventListener('input', function() {
            clearFieldError('email');
        });
    }
    
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            clearFieldError('password');
        });
    }
    
    if (repeatPasswordInput) {
        repeatPasswordInput.addEventListener('input', function() {
            clearFieldError('repeatPassword');
        });
    }
    
    registerForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const submitButton = registerForm.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        
        // Disable submit button
        submitButton.disabled = true;
        submitButton.textContent = 'REGISTERING...';
        
        // Get form data (includes CSRF token from hidden input)
        const formData = new FormData(registerForm);
        
        // Get CSRF token from hidden input (created by {% csrf_token %})
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!csrfInput || !csrfInput.value) {
            showAlert('CSRF token not found. Please refresh the page and try again.', 'danger');
            submitButton.disabled = false;
            submitButton.textContent = originalText;
            return;
        }
        
        // Make AJAX request with CSRF protection
        fetch(registerForm.action, {
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
                    }, 1500);
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
                
                submitButton.disabled = false;
                submitButton.textContent = originalText;
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
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        });
    });
});

