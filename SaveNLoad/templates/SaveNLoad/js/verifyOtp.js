/**
 * Verify OTP Form Handler
 * Uses shared utility functions from utils.js
 */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    // Clear input and focus - local helper function
    function clearAndFocusInput() {
        if (otpInput) {
            otpInput.value = '';
            otpInput.focus();
        }
    }

    // Show loading indicator in the input field
    function showLoadingState(isLoading) {
        const otpInput = document.getElementById('otp_code');
        if (!otpInput) return;

        if (isLoading) {
            otpInput.disabled = true;
            otpInput.style.opacity = '0.6';
            otpInput.style.cursor = 'not-allowed';
            // Add loading text as placeholder
            const originalPlaceholder = otpInput.placeholder;
            otpInput.setAttribute('data-original-placeholder', originalPlaceholder);
            otpInput.placeholder = 'Verifying...';
        } else {
            otpInput.disabled = false;
            otpInput.style.opacity = '1';
            otpInput.style.cursor = 'text';
            // Restore original placeholder
            const originalPlaceholder = otpInput.getAttribute('data-original-placeholder');
            if (originalPlaceholder) {
                otpInput.placeholder = originalPlaceholder;
            }
        }
    }

    const verifyOtpForm = document.getElementById('verifyOtpForm');
    const resendOtpBtn = document.getElementById('resendOtpBtn');
    const otpInput = document.getElementById('otp_code');
    let isSubmitting = false; // Prevent multiple submissions

    // Auto-focus OTP input
    if (otpInput) {
        otpInput.focus();
    }

    // Function to check OTP length and handle auto-submit
    function checkOtpLength() {
        const otpCode = otpInput?.value.trim() || '';

        // Only auto-submit if we have 6 digits and not already submitting
        if (otpCode.length === 6 && !isSubmitting) {
            // Auto-submit the form after a short delay for better UX
            setTimeout(() => {
                if (verifyOtpForm && otpInput.value.length === 6 && !isSubmitting) {
                    verifyOtpForm.dispatchEvent(new Event('submit'));
                }
            }, 300);
        }
    }

    // Only allow numbers in OTP input
    if (otpInput) {
        otpInput.addEventListener('input', function (e) {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
            // Check if all 6 digits are entered
            checkOtpLength();
        });

        // Also check on paste events
        otpInput.addEventListener('paste', function (e) {
            setTimeout(() => {
                e.target.value = e.target.value.replace(/[^0-9]/g, '');
                checkOtpLength();
            }, 10);
        });
    }

    if (verifyOtpForm) {
        verifyOtpForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            // Prevent multiple submissions
            if (isSubmitting) {
                return;
            }

            const csrfToken = window.getCsrfToken();
            if (!csrfToken) {
                return;
            }

            const otpCode = otpInput?.value.trim() || '';
            const otpError = document.getElementById('otp-error');

            // Clear previous errors
            if (otpError) {
                otpError.classList.add('d-none');
                otpError.classList.remove('d-block');
                otpError.textContent = '';
            }

            // Basic validation
            if (!otpCode) {
                if (otpError) {
                    otpError.textContent = 'OTP code is required.';
                    otpError.classList.remove('d-none');
                    otpError.classList.add('d-block');
                }
                return;
            }

            if (otpCode.length !== 6) {
                if (otpError) {
                    otpError.textContent = 'OTP code must be 6 digits.';
                    otpError.classList.remove('d-none');
                    otpError.classList.add('d-block');
                }
                return;
            }

            // Set submitting state and show loading
            isSubmitting = true;
            showLoadingState(true);

            try {
                const response = await fetch('{% url "SaveNLoad:verify_otp" %}', {
                    method: 'POST',
                    headers: window.createFetchHeaders(csrfToken),
                    body: JSON.stringify({
                        action: 'verify',
                        otp_code: otpCode
                    })
                });

                const data = await response.json();

                if (data.success) {
                    // Redirect to reset password page
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    } else {
                        window.location.href = '{% url "SaveNLoad:reset_password" %}';
                    }
                } else {
                    const errorMsg = data.error || data.message || 'Invalid OTP code. Please try again.';
                    if (otpError) {
                        otpError.textContent = errorMsg;
                        otpError.classList.remove('d-none');
                        otpError.classList.add('d-block');
                    } else {
                        window.showToast(errorMsg, 'error');
                    }
                    // Clear input on error so user can try again
                    clearAndFocusInput();
                }
            } catch (error) {
                console.error('Error verifying OTP:', error);
                window.showToast('Error: Failed to verify OTP. Please try again.', 'error');
                // Clear input on error so user can try again
                clearAndFocusInput();
            } finally {
                isSubmitting = false;
                showLoadingState(false);
            }
        });
    }

    if (resendOtpBtn) {
        resendOtpBtn.addEventListener('click', async function (e) {
            e.preventDefault();

            const csrfToken = window.getCsrfToken();
            if (!csrfToken) {
                return;
            }

            // Disable button and show loading state
            window.setButtonLoadingState(resendOtpBtn, true, 'SENDING...');

            try {
                const response = await fetch('{% url "SaveNLoad:verify_otp" %}', {
                    method: 'POST',
                    headers: window.createFetchHeaders(csrfToken),
                    body: JSON.stringify({
                        action: 'resend'
                    })
                });

                const data = await response.json();

                if (data.success) {
                    window.showToast(data.message || 'A new code has been sent to your email address.', 'success');
                    // Clear OTP input
                    clearAndFocusInput();
                } else {
                    const errorMsg = data.error || data.message || 'Failed to resend OTP. Please try again.';
                    window.showToast(errorMsg, 'error');
                }
            } catch (error) {
                console.error('Error resending OTP:', error);
                window.showToast('Error: Failed to resend OTP. Please try again.', 'error');
            } finally {
                window.setButtonLoadingState(resendOtpBtn, false);
            }
        });
    }
});
