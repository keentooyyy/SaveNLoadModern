/**
 * Reset Password Form Handler
 * Uses shared utility functions from utils.js
 */
(function() {
    'use strict';
    
    const resetPasswordForm = document.getElementById('resetPasswordForm');
    const resetPasswordBtn = document.getElementById('resetPasswordBtn');
    
    // Password visibility toggles - using shared utility function
    window.setupPasswordToggle(document.getElementById('toggleNewPassword'), document.getElementById('new_password'));
    window.setupPasswordToggle(document.getElementById('toggleConfirmPassword'), document.getElementById('confirm_password'));
    
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const csrfToken = window.getCsrfToken();
            if (!csrfToken) {
                return;
            }
            
            const newPassword = document.getElementById('new_password')?.value.trim() || '';
            const confirmPassword = document.getElementById('confirm_password')?.value.trim() || '';
            
            // Get error elements
            const newPasswordError = document.getElementById('new-password-error');
            const confirmPasswordError = document.getElementById('confirm-password-error');
            
            // Clear previous errors
            window.clearError(newPasswordError);
            window.clearError(confirmPasswordError);
            
            // Validation
            let hasErrors = false;
            
            if (!newPassword) {
                window.showError(newPasswordError, 'New password is required.');
                hasErrors = true;
            } else if (newPassword.length < 8) {
                window.showError(newPasswordError, 'Password must be at least 8 characters long.');
                hasErrors = true;
            }
            
            if (!confirmPassword) {
                window.showError(confirmPasswordError, 'Please confirm your password.');
                hasErrors = true;
            } else if (newPassword !== confirmPassword) {
                window.showError(confirmPasswordError, 'Passwords do not match.');
                hasErrors = true;
            }
            
            if (hasErrors) {
                return;
            }
            
            // Set button loading state
            window.setButtonLoadingState(resetPasswordBtn, true, 'Resetting...');
            
            try {
                const response = await fetch('{% url "SaveNLoad:reset_password" %}', {
                    method: 'POST',
                    headers: window.createFetchHeaders(csrfToken),
                    body: JSON.stringify({
                        new_password: newPassword,
                        confirm_password: confirmPassword
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    window.showToast(data.message || 'Password reset successfully!', 'success');
                    // Check if redirect is provided
                    if (data.redirect_url) {
                        setTimeout(() => {
                            window.location.href = data.redirect_url;
                        }, 1500);
                    } else {
                        setTimeout(() => {
                            window.location.href = '{% url "SaveNLoad:login" %}';
                        }, 1500);
                    }
                } else {
                    const errorMsg = data.error || data.message || 'Failed to reset password. Please try again.';
                    
                    // Try to show field-specific errors
                    if (data.field_errors) {
                        if (data.field_errors.new_password) {
                            window.showError(newPasswordError, data.field_errors.new_password);
                        }
                        if (data.field_errors.confirm_password) {
                            window.showError(confirmPasswordError, data.field_errors.confirm_password);
                        }
                    } else {
                        window.showToast(errorMsg, 'error');
                    }
                }
            } catch (error) {
                console.error('Error resetting password:', error);
                window.showToast('Error: Failed to reset password. Please try again.', 'error');
            } finally {
                window.setButtonLoadingState(resetPasswordBtn, false);
            }
        });
    }
})();

