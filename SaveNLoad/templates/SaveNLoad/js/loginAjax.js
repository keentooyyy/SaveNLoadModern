/**
 * Initialize login form AJAX submission.
 *
 * Args:
 *     None
 *
 * Returns:
 *     None
 */
document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');

    if (!loginForm) {
        console.error('Login form not found!');
        return;
    }

    // Uses shared utility functions from utils.js (showToast, setButtonLoadingState, showError, clearError, getCsrfToken, createFetchHeaders)

    // Clear field errors when user starts typing
    setupFieldErrorClear(['username', 'password']);

    /**
     * Submit login form via AJAX and handle response states.
     *
     * Args:
     *     e: Submit event.
     *
     * Returns:
     *     None
     */
    loginForm.addEventListener('submit', function (e) {
        e.preventDefault();

        const submitButton = loginForm.querySelector('button[type="submit"]');

        // Set button loading state
        setButtonLoadingState(submitButton, true, 'LOGGING IN...');

        // Get form data
        const formData = new FormData(loginForm);

        // Get CSRF token
        const csrfToken = getCsrfToken();
        if (!csrfToken) {
            showToast('CSRF token not found. Please refresh the page and try again.', 'error');
            setButtonLoadingState(submitButton, false);
            return;
        }

        // Make AJAX request with CSRF protection
        fetch(loginForm.action, {
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

                    // Show general error if present
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

