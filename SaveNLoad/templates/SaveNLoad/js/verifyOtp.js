/**
 * Verify OTP Form Handler
 */
(function() {
    'use strict';
    
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
    
    const verifyOtpForm = document.getElementById('verifyOtpForm');
    const verifyOtpBtn = document.getElementById('verifyOtpBtn');
    const resendOtpBtn = document.getElementById('resendOtpBtn');
    const otpInput = document.getElementById('otp_code');
    
    // Auto-focus OTP input
    if (otpInput) {
        otpInput.focus();
    }
    
    // Only allow numbers in OTP input
    if (otpInput) {
        otpInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });
    }
    
    if (verifyOtpForm) {
        verifyOtpForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
            if (!csrfToken) {
                showToast('Error: CSRF token not found', 'error');
                return;
            }
            
            const otpCode = otpInput?.value.trim() || '';
            const otpError = document.getElementById('otp-error');
            
            // Clear previous errors
            if (otpError) {
                otpError.style.display = 'none';
                otpError.textContent = '';
            }
            
            // Basic validation
            if (!otpCode) {
                if (otpError) {
                    otpError.textContent = 'OTP code is required.';
                    otpError.style.display = 'block';
                }
                return;
            }
            
            if (otpCode.length !== 6) {
                if (otpError) {
                    otpError.textContent = 'OTP code must be 6 digits.';
                    otpError.style.display = 'block';
                }
                return;
            }
            
            // Disable button and show loading state
            const originalContent = Array.from(verifyOtpBtn.childNodes);
            verifyOtpBtn.disabled = true;
            verifyOtpBtn.textContent = '';
            const spinnerIcon = document.createElement('i');
            spinnerIcon.className = 'fas fa-spinner fa-spin me-1';
            const loadingText = document.createTextNode('VERIFYING...');
            verifyOtpBtn.appendChild(spinnerIcon);
            verifyOtpBtn.appendChild(loadingText);
            
            try {
                const response = await fetch('{% url "SaveNLoad:verify_otp" %}', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
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
                        otpError.style.display = 'block';
                    } else {
                        showToast(errorMsg, 'error');
                    }
                }
            } catch (error) {
                console.error('Error verifying OTP:', error);
                showToast('Error: Failed to verify OTP. Please try again.', 'error');
            } finally {
                verifyOtpBtn.disabled = false;
                verifyOtpBtn.textContent = '';
                originalContent.forEach(node => {
                    verifyOtpBtn.appendChild(node.cloneNode(true));
                });
            }
        });
    }
    
    if (resendOtpBtn) {
        resendOtpBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            
            const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
            if (!csrfToken) {
                showToast('Error: CSRF token not found', 'error');
                return;
            }
            
            // Disable button and show loading state
            const originalContent = Array.from(resendOtpBtn.childNodes);
            resendOtpBtn.disabled = true;
            resendOtpBtn.textContent = '';
            const spinnerIcon = document.createElement('i');
            spinnerIcon.className = 'fas fa-spinner fa-spin me-1';
            const loadingText = document.createTextNode('SENDING...');
            resendOtpBtn.appendChild(spinnerIcon);
            resendOtpBtn.appendChild(loadingText);
            
            try {
                const response = await fetch('{% url "SaveNLoad:verify_otp" %}', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        action: 'resend'
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showToast(data.message || 'A new OTP code has been sent to your email address.', 'success');
                    // Clear OTP input
                    if (otpInput) {
                        otpInput.value = '';
                        otpInput.focus();
                    }
                } else {
                    const errorMsg = data.error || data.message || 'Failed to resend OTP. Please try again.';
                    showToast(errorMsg, 'error');
                }
            } catch (error) {
                console.error('Error resending OTP:', error);
                showToast('Error: Failed to resend OTP. Please try again.', 'error');
            } finally {
                resendOtpBtn.disabled = false;
                resendOtpBtn.textContent = '';
                originalContent.forEach(node => {
                    resendOtpBtn.appendChild(node.cloneNode(true));
                });
            }
        });
    }
})();

