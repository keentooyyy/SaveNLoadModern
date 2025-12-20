/**
 * Reset Password Form Handler
 */
(function() {
    'use strict';
    
    // Show toast notification (XSS-safe)
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
    
    const resetPasswordForm = document.getElementById('resetPasswordForm');
    const resetPasswordBtn = document.getElementById('resetPasswordBtn');
    
    // Password visibility toggles
    const toggleNewPassword = document.getElementById('toggleNewPassword');
    const toggleConfirmPassword = document.getElementById('toggleConfirmPassword');
    const newPasswordInput = document.getElementById('new_password');
    const confirmPasswordInput = document.getElementById('confirm_password');
    
    if (toggleNewPassword && newPasswordInput) {
        toggleNewPassword.addEventListener('click', function() {
            const type = newPasswordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            newPasswordInput.setAttribute('type', type);
            
            // Toggle icon directly (the toggle element IS the icon)
            if (type === 'password') {
                toggleNewPassword.classList.remove('fa-eye');
                toggleNewPassword.classList.add('fa-eye-slash');
            } else {
                toggleNewPassword.classList.remove('fa-eye-slash');
                toggleNewPassword.classList.add('fa-eye');
            }
        });
    }
    
    if (toggleConfirmPassword && confirmPasswordInput) {
        toggleConfirmPassword.addEventListener('click', function() {
            const type = confirmPasswordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            confirmPasswordInput.setAttribute('type', type);
            
            // Toggle icon directly (the toggle element IS the icon)
            if (type === 'password') {
                toggleConfirmPassword.classList.remove('fa-eye');
                toggleConfirmPassword.classList.add('fa-eye-slash');
            } else {
                toggleConfirmPassword.classList.remove('fa-eye-slash');
                toggleConfirmPassword.classList.add('fa-eye');
            }
        });
    }
    
    if (resetPasswordForm) {
        resetPasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
            if (!csrfToken) {
                showToast('Error: CSRF token not found', 'error');
                return;
            }
            
            const newPassword = document.getElementById('new_password')?.value.trim() || '';
            const confirmPassword = document.getElementById('confirm_password')?.value.trim() || '';
            
            // Get error elements
            const newPasswordError = document.getElementById('new-password-error');
            const confirmPasswordError = document.getElementById('confirm-password-error');
            
            // Clear previous errors
            [newPasswordError, confirmPasswordError].forEach(el => {
                if (el) {
                    el.style.display = 'none';
                    el.textContent = '';
                }
            });
            
            // Validation
            let hasErrors = false;
            
            if (!newPassword) {
                if (newPasswordError) {
                    newPasswordError.textContent = 'New password is required.';
                    newPasswordError.style.display = 'block';
                }
                hasErrors = true;
            } else if (newPassword.length < 8) {
                if (newPasswordError) {
                    newPasswordError.textContent = 'Password must be at least 8 characters long.';
                    newPasswordError.style.display = 'block';
                }
                hasErrors = true;
            }
            
            if (!confirmPassword) {
                if (confirmPasswordError) {
                    confirmPasswordError.textContent = 'Please confirm your password.';
                    confirmPasswordError.style.display = 'block';
                }
                hasErrors = true;
            } else if (newPassword !== confirmPassword) {
                if (confirmPasswordError) {
                    confirmPasswordError.textContent = 'Passwords do not match.';
                    confirmPasswordError.style.display = 'block';
                }
                hasErrors = true;
            }
            
            if (hasErrors) {
                return;
            }
            
            // Disable button and show loading state
            const originalContent = Array.from(resetPasswordBtn.childNodes);
            resetPasswordBtn.disabled = true;
            resetPasswordBtn.textContent = '';
            const spinnerIcon = document.createElement('i');
            spinnerIcon.className = 'fas fa-spinner fa-spin me-1';
            const loadingText = document.createTextNode('Resetting...');
            resetPasswordBtn.appendChild(spinnerIcon);
            resetPasswordBtn.appendChild(loadingText);
            
            try {
                const response = await fetch('{% url "SaveNLoad:reset_password" %}', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        new_password: newPassword,
                        confirm_password: confirmPassword
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showToast(data.message || 'Password reset successfully!', 'success');
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
                        if (data.field_errors.new_password && newPasswordError) {
                            newPasswordError.textContent = data.field_errors.new_password;
                            newPasswordError.style.display = 'block';
                        }
                        if (data.field_errors.confirm_password && confirmPasswordError) {
                            confirmPasswordError.textContent = data.field_errors.confirm_password;
                            confirmPasswordError.style.display = 'block';
                        }
                    } else {
                        showToast(errorMsg, 'error');
                    }
                }
            } catch (error) {
                console.error('Error resetting password:', error);
                showToast('Error: Failed to reset password. Please try again.', 'error');
            } finally {
                resetPasswordBtn.disabled = false;
                resetPasswordBtn.textContent = '';
                originalContent.forEach(node => {
                    resetPasswordBtn.appendChild(node.cloneNode(true));
                });
            }
        });
    }
})();

