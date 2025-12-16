document.addEventListener('DOMContentLoaded', function () {
    // Show toast notification (XSS-safe)
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        
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
    
    // Initialize account settings
    const changePasswordForm = document.getElementById('changePasswordForm');
    const changePasswordBtn = document.getElementById('changePasswordBtn');
    
    // Handle accordion chevron rotation
    const accountSettingsHeader = document.querySelector('.account-settings-header');
    const accountSettingsChevron = document.getElementById('accountSettingsChevron');
    const accountSettingsCollapse = document.getElementById('accountSettingsCollapse');
    
    if (accountSettingsCollapse) {
        accountSettingsCollapse.addEventListener('show.bs.collapse', function () {
            if (accountSettingsHeader) accountSettingsHeader.classList.add('active');
            if (accountSettingsChevron) {
                accountSettingsChevron.style.transform = 'rotate(90deg)';
            }
        });
        
        accountSettingsCollapse.addEventListener('hide.bs.collapse', function () {
            if (accountSettingsHeader) accountSettingsHeader.classList.remove('active');
            if (accountSettingsChevron) {
                accountSettingsChevron.style.transform = 'rotate(0deg)';
            }
        });
    }
    
    // Handle change password form
    if (changePasswordForm) {
        changePasswordForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            
            const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
            if (!csrfToken) {
                showToast('Error: CSRF token not found', 'error');
                return;
            }
            
            const currentPassword = document.getElementById('currentPassword')?.value.trim();
            const newPassword = document.getElementById('newPassword')?.value.trim();
            const confirmPassword = document.getElementById('confirmPassword')?.value.trim();
            
            if (!currentPassword || !newPassword || !confirmPassword) {
                showToast('Please fill in all password fields.', 'error');
                return;
            }
            
            if (newPassword !== confirmPassword) {
                showToast('New passwords do not match.', 'error');
                return;
            }
            
            // Disable button and show loading state
            const originalContent = Array.from(changePasswordBtn.childNodes);
            changePasswordBtn.disabled = true;
            // Clear and set loading state safely
            changePasswordBtn.textContent = '';
            const spinnerIcon = document.createElement('i');
            spinnerIcon.className = 'fas fa-spinner fa-spin me-1';
            const loadingText = document.createTextNode('Changing...');
            changePasswordBtn.appendChild(spinnerIcon);
            changePasswordBtn.appendChild(loadingText);
            
            try {
                const response = await fetch(window.CHANGE_PASSWORD_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        current_password: currentPassword,
                        new_password: newPassword,
                        confirm_password: confirmPassword
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showToast(data.message || 'Password changed successfully!', 'success');
                    changePasswordForm.reset();
                } else {
                    showToast(data.error || data.message || 'Failed to change password', 'error');
                }
            } catch (error) {
                console.error('Error changing password:', error);
                showToast('Error: Failed to change password. Please try again.', 'error');
            } finally {
                changePasswordBtn.disabled = false;
                // Restore original content safely
                changePasswordBtn.textContent = '';
                originalContent.forEach(node => {
                    changePasswordBtn.appendChild(node.cloneNode(true));
                });
            }
        });
    }
    
    // Password visibility toggles
    const toggleCurrentPassword = document.getElementById('toggleCurrentPassword');
    const toggleNewPassword = document.getElementById('toggleNewPassword');
    const toggleConfirmPassword = document.getElementById('toggleConfirmPassword');
    const currentPasswordInput = document.getElementById('currentPassword');
    const newPasswordInput = document.getElementById('newPassword');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    
    if (toggleCurrentPassword && currentPasswordInput) {
        toggleCurrentPassword.addEventListener('click', function () {
            const type = currentPasswordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            currentPasswordInput.setAttribute('type', type);
            const icon = toggleCurrentPassword.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-eye');
                icon.classList.toggle('fa-eye-slash');
            }
        });
    }
    
    if (toggleNewPassword && newPasswordInput) {
        toggleNewPassword.addEventListener('click', function () {
            const type = newPasswordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            newPasswordInput.setAttribute('type', type);
            const icon = toggleNewPassword.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-eye');
                icon.classList.toggle('fa-eye-slash');
            }
        });
    }
    
    if (toggleConfirmPassword && confirmPasswordInput) {
        toggleConfirmPassword.addEventListener('click', function () {
            const type = confirmPasswordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            confirmPasswordInput.setAttribute('type', type);
            const icon = toggleConfirmPassword.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-eye');
                icon.classList.toggle('fa-eye-slash');
            }
        });
    }
});
