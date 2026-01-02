/**
 * Forgot Password Form Handler
 * Uses shared utility functions from utils.js
 */
/**
 * Initialize Forgot Password form behavior.
 *
 * Args:
 *     None
 *
 * Returns:
 *     None
 */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    const forgotPasswordForm = document.getElementById('forgotPasswordForm');
    const sendOtpBtn = document.getElementById('sendOtpBtn');

    if (forgotPasswordForm) {
        /**
         * Submit the email to request an OTP.
         *
         * Args:
         *     e: Submit event.
         *
         * Returns:
         *     None
         */
        forgotPasswordForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const emailInput = document.getElementById('email');
            const emailError = document.getElementById('email-error');
            const email = sanitizeEmailInput(emailInput.value);
            const csrfToken = getCsrfToken();

            // Clear previous errors
            clearError(emailError);

            // Basic validation
            if (!email) {
                showError(emailError, 'Email is required.');
                return;
            }

            // Basic email format validation
            if (!validateEmailFormat(email)) {
                showError(emailError, 'Please enter a valid email address.');
                return;
            }

            // Set button loading state
            setButtonLoadingState(sendOtpBtn, true, 'SENDING...');

            try {
                const response = await fetch('{% url "SaveNLoad:forgot_password" %}', {
                    method: 'POST',
                    headers: createFetchHeaders(csrfToken),
                    body: JSON.stringify({
                        email: email
                    })
                });

                const data = await response.json();

                if (data.success) {
                    // Email was sent successfully - redirect to verify OTP page
                    showToast(data.message || 'OTP code has been sent to your email address. Please check your inbox.', 'success');
                    // Small delay before redirect to show toast
                    setTimeout(() => {
                        window.location.href = '{% url "SaveNLoad:verify_otp" %}';
                    }, 1000);
                } else {
                    // Show error message
                    const errorMsg = data.error || data.message || 'Failed to send OTP. Please try again.';
                    showError(emailError, errorMsg);
                    if (!emailError) showToast(errorMsg, 'error');
                }
            } catch (error) {
                console.error('Error sending OTP:', error);
                showToast('Error: Failed to send OTP. Please try again.', 'error');
            } finally {
                setButtonLoadingState(sendOtpBtn, false);
            }
        });
    }
});
