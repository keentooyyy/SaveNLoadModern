document.addEventListener('DOMContentLoaded', function () {
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
    
    // Sanitize email input
    function sanitizeEmail(email) {
        if (!email) return '';
        
        // Strip whitespace
        email = email.trim();
        
        // Remove HTML tags (XSS prevention)
        const div = document.createElement('div');
        div.textContent = email;
        email = div.textContent || div.innerText || '';
        
        // Limit length (RFC 5321 limit is 254 characters)
        if (email.length > 254) {
            email = email.substring(0, 254);
        }
        
        // Normalize to lowercase
        email = email.toLowerCase();
        
        return email;
    }
    
    // Sanitize password input
    function sanitizePassword(password) {
        if (!password) return '';
        
        // Strip whitespace
        password = password.trim();
        
        // Remove null bytes and other dangerous control characters
        password = password.replace(/\x00/g, '');
        
        // Limit length (prevent extremely long inputs)
        if (password.length > 128) {
            password = password.substring(0, 128);
        }
        
        return password;
    }
    
    // Validate email format
    function validateEmailFormat(email) {
        if (!email) return false;
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    // Initialize account settings
    const accountSettingsForm = document.getElementById('accountSettingsForm');
    const saveAccountSettingsBtn = document.getElementById('saveAccountSettingsBtn');
    const emailInput = document.getElementById('email');
    // Sanitize original email for proper comparison
    const originalEmail = emailInput ? sanitizeEmail(emailInput.value) : '';
    
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
    
    // Handle account settings form
    if (accountSettingsForm) {
        accountSettingsForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            
            const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
            if (!csrfToken) {
                showToast('Error: CSRF token not found', 'error');
                return;
            }
            
            // Sanitize inputs
            const rawEmail = emailInput?.value || '';
            const email = sanitizeEmail(rawEmail);
            const currentPassword = sanitizePassword(document.getElementById('currentPassword')?.value || '');
            const newPassword = sanitizePassword(document.getElementById('newPassword')?.value || '');
            const confirmPassword = sanitizePassword(document.getElementById('confirmPassword')?.value || '');
            
            // Check if email changed (both are already sanitized and lowercased)
            const emailChanged = email && email !== originalEmail;
            
            // Check if password fields are filled
            const passwordFieldsFilled = currentPassword || newPassword || confirmPassword;
            
            // If nothing changed, show message
            if (!emailChanged && !passwordFieldsFilled) {
                showToast('No changes made.', 'info');
                return;
            }
            
            // Validate email if changed
            if (emailChanged) {
                if (!validateEmailFormat(email)) {
                    showToast('Please enter a valid email address.', 'error');
                    return;
                }
                
                // Check email length
                if (email.length > 254) {
                    showToast('Email is too long (maximum 254 characters).', 'error');
                    return;
                }
            }
            
            // Validate password if password fields are filled
            if (passwordFieldsFilled) {
                if (!currentPassword) {
                    showToast('Current password is required to change password.', 'error');
                    return;
                }
                
                if (!newPassword) {
                    showToast('New password is required.', 'error');
                    return;
                }
                
                if (!confirmPassword) {
                    showToast('Please confirm your new password.', 'error');
                    return;
                }
                
                // Check password length
                if (currentPassword.length > 128) {
                    showToast('Password is too long (maximum 128 characters).', 'error');
                    return;
                }
                
                if (newPassword.length > 128) {
                    showToast('Password is too long (maximum 128 characters).', 'error');
                    return;
                }
                
                if (confirmPassword.length > 128) {
                    showToast('Password is too long (maximum 128 characters).', 'error');
                    return;
                }
                
                // Check minimum password length
                if (newPassword.length < 8) {
                    showToast('Password must be at least 8 characters long.', 'error');
                    return;
                }
                
                if (newPassword !== confirmPassword) {
                    showToast('New passwords do not match.', 'error');
                    return;
                }
            }
            
            // Disable button and show loading state
            const originalContent = Array.from(saveAccountSettingsBtn.childNodes);
            saveAccountSettingsBtn.disabled = true;
            // Clear and set loading state safely
            saveAccountSettingsBtn.textContent = '';
            const spinnerIcon = document.createElement('i');
            spinnerIcon.className = 'fas fa-spinner fa-spin me-1';
            const loadingText = document.createTextNode('Saving...');
            saveAccountSettingsBtn.appendChild(spinnerIcon);
            saveAccountSettingsBtn.appendChild(loadingText);
            
            try {
                const requestBody = {};
                
                // Always include email (backend will check if it changed)
                if (email) {
                    requestBody.email = email;
                }
                
                // Only include password fields if they're filled
                if (passwordFieldsFilled) {
                    requestBody.current_password = currentPassword;
                    requestBody.new_password = newPassword;
                    requestBody.confirm_password = confirmPassword;
                }
                
                const response = await fetch(window.UPDATE_ACCOUNT_SETTINGS_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify(requestBody)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showToast(data.message || 'Settings updated successfully!', 'success');
                    // Reset password fields only
                    document.getElementById('currentPassword').value = '';
                    document.getElementById('newPassword').value = '';
                    document.getElementById('confirmPassword').value = '';
                } else {
                    showToast(data.error || data.message || 'Failed to update settings', 'error');
                }
            } catch (error) {
                console.error('Error updating account settings:', error);
                showToast('Error: Failed to update settings. Please try again.', 'error');
            } finally {
                saveAccountSettingsBtn.disabled = false;
                // Restore original content safely
                saveAccountSettingsBtn.textContent = '';
                originalContent.forEach(node => {
                    saveAccountSettingsBtn.appendChild(node.cloneNode(true));
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
            toggleCurrentPassword.classList.toggle('fa-eye');
            toggleCurrentPassword.classList.toggle('fa-eye-slash');
        });
    }
    
    if (toggleNewPassword && newPasswordInput) {
        toggleNewPassword.addEventListener('click', function () {
            const type = newPasswordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            newPasswordInput.setAttribute('type', type);
            toggleNewPassword.classList.toggle('fa-eye');
            toggleNewPassword.classList.toggle('fa-eye-slash');
        });
    }
    
    if (toggleConfirmPassword && confirmPasswordInput) {
        toggleConfirmPassword.addEventListener('click', function () {
            const type = confirmPasswordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            confirmPasswordInput.setAttribute('type', type);
            toggleConfirmPassword.classList.toggle('fa-eye');
            toggleConfirmPassword.classList.toggle('fa-eye-slash');
        });
    }
});
