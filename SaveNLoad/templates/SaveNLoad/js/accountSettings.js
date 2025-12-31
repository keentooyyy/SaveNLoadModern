/**
 * Account Settings Handler
 * Uses shared utility functions from utils.js
 */
document.addEventListener('DOMContentLoaded', function () {

    // Initialize account settings
    const accountSettingsForm = document.getElementById('accountSettingsForm');
    const saveAccountSettingsBtn = document.getElementById('saveAccountSettingsBtn');
    const emailInput = document.getElementById('email');
    // Sanitize original email for proper comparison
    const originalEmail = emailInput ? sanitizeEmailInput(emailInput.value) : '';

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

            const csrfToken = window.getCsrfToken();
            if (!csrfToken) {
                return;
            }

            // Sanitize inputs
            const rawEmail = emailInput?.value || '';
            const email = sanitizeEmailInput(rawEmail);
            const currentPassword = sanitizePasswordInput(document.getElementById('currentPassword')?.value || '');
            const newPassword = sanitizePasswordInput(document.getElementById('newPassword')?.value || '');
            const confirmPassword = sanitizePasswordInput(document.getElementById('confirmPassword')?.value || '');

            // Check if email changed (both are already sanitized and lowercased)
            const emailChanged = email && email !== originalEmail;

            // Check if password fields are filled
            const passwordFieldsFilled = currentPassword || newPassword || confirmPassword;

            // If nothing changed, show message
            if (!emailChanged && !passwordFieldsFilled) {
                window.showToast('No changes made.', 'info');
                return;
            }

            // Validate email if changed
            if (emailChanged) {
                if (!validateEmailFormat(email)) {
                    window.showToast('Please enter a valid email address.', 'error');
                    return;
                }

                // Check email length
                if (email.length > 254) {
                    window.showToast('Email is too long (maximum 254 characters).', 'error');
                    return;
                }
            }

            // Validate password if password fields are filled
            if (passwordFieldsFilled) {
                if (!currentPassword) {
                    window.showToast('Current password is required to change password.', 'error');
                    return;
                }

                if (!newPassword) {
                    window.showToast('New password is required.', 'error');
                    return;
                }

                if (!confirmPassword) {
                    window.showToast('Please confirm your new password.', 'error');
                    return;
                }

                // Check password length
                if (currentPassword.length > 128) {
                    window.showToast('Password is too long (maximum 128 characters).', 'error');
                    return;
                }

                if (newPassword.length > 128) {
                    window.showToast('Password is too long (maximum 128 characters).', 'error');
                    return;
                }

                if (confirmPassword.length > 128) {
                    window.showToast('Password is too long (maximum 128 characters).', 'error');
                    return;
                }

                // Check minimum password length
                if (newPassword.length < 8) {
                    window.showToast('Password must be at least 8 characters long.', 'error');
                    return;
                }

                if (newPassword !== confirmPassword) {
                    window.showToast('New passwords do not match.', 'error');
                    return;
                }
            }

            // Set button loading state
            window.setButtonLoadingState(saveAccountSettingsBtn, true, 'SAVING...');

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
                    headers: window.createFetchHeaders(csrfToken),
                    body: JSON.stringify(requestBody)
                });

                const data = await response.json();

                if (data.success) {
                    window.showToast(data.message || 'Settings updated successfully!', 'success');
                    // Reset password fields only
                    document.getElementById('currentPassword').value = '';
                    document.getElementById('newPassword').value = '';
                    document.getElementById('confirmPassword').value = '';
                } else {
                    window.showToast(data.error || data.message || 'Failed to update settings', 'error');
                }
            } catch (error) {
                console.error('Error updating account settings:', error);
                window.showToast('Error: Failed to update settings. Please try again.', 'error');
            } finally {
                window.setButtonLoadingState(saveAccountSettingsBtn, false);
            }
        });
    }

    // Toggle password visibility handled by shared utils
    setupPasswordToggle('toggleCurrentPassword', 'currentPassword');
    setupPasswordToggle('toggleNewPassword', 'newPassword');
    setupPasswordToggle('toggleConfirmPassword', 'confirmPassword');
});
