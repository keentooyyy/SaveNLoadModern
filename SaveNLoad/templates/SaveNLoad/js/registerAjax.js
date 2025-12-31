document.addEventListener('DOMContentLoaded', function () {
    const registerForm = document.querySelector('form[action*="register"]');

    if (!registerForm) return;

    // Uses shared utility functions from utils.js

    // Clear field errors when user starts typing
    setupFieldErrorClear(['username', 'email', 'password', 'repeatPassword']);

    registerForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const submitButton = registerForm.querySelector('button[type="submit"]');

        // Set button loading state
        setButtonLoadingState(submitButton, true, 'REGISTERING...');

        // Get form data
        const formData = new FormData(registerForm);

        // Get CSRF token
        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            showToast('CSRF token not found. Please refresh the page and try again.', 'error');
            setButtonLoadingState(submitButton, false);
            return;
        }

        // Make AJAX request with CSRF protection
        fetch(registerForm.action, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            credentials: 'same-origin',
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
                    showToast(data.message, 'success');
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

                    // Show general errors
                    if (data.errors && data.errors.length > 0) {
                        showToast(data.errors[0], 'error');
                    } else if (data.message && !data.success) {
                        showToast(data.message, 'error');
                    }

                    setButtonLoadingState(submitButton, false);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                if (error.message && error.message.includes('CSRF')) {
                    showToast('CSRF verification failed. Please refresh the page and try again.', 'error');
                } else {
                    showToast('An error occurred. Please try again.', 'error');
                }
                setButtonLoadingState(submitButton, false);
            });
    });
});

