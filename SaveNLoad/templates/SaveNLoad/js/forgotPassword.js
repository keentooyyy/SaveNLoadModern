/**
 * Forgot Password Form Handler
 * Uses shared utility functions from utils.js
 */
(function() {
    'use strict';
    
    const forgotPasswordForm = document.getElementById('forgotPasswordForm');
    const sendOtpBtn = document.getElementById('sendOtpBtn');
    
    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const csrfToken = window.getCsrfToken();
            if (!csrfToken) {
                return;
            }
            
            const emailInput = document.getElementById('email');
            const email = emailInput?.value.trim() || '';
            const emailError = document.getElementById('email-error');
            
            // Clear previous errors
            window.clearError(emailError);
            
            // Basic validation
            if (!email) {
                window.showError(emailError, 'Email is required.');
                return;
            }
            
            // Basic email format validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                window.showError(emailError, 'Please enter a valid email address.');
                return;
            }
            
            // Set button loading state
            window.setButtonLoadingState(sendOtpBtn, true, 'SENDING...');
            
            try {
                const response = await fetch('{% url "SaveNLoad:forgot_password" %}', {
                    method: 'POST',
                    headers: window.createFetchHeaders(csrfToken),
                    body: JSON.stringify({
                        email: email
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Email was sent successfully - redirect to verify OTP page
                    window.showToast(data.message || 'OTP code has been sent to your email address. Please check your inbox.', 'success');
                    // Small delay before redirect to show toast
                    setTimeout(() => {
                        window.location.href = '{% url "SaveNLoad:verify_otp" %}';
                    }, 1000);
                } else {
                    // Show error message
                    const errorMsg = data.error || data.message || 'Failed to send OTP. Please try again.';
                    window.showError(emailError, errorMsg) || window.showToast(errorMsg, 'error');
                }
            } catch (error) {
                console.error('Error sending OTP:', error);
                window.showToast('Error: Failed to send OTP. Please try again.', 'error');
            } finally {
                window.setButtonLoadingState(sendOtpBtn, false);
            }
        });
    }
})();

