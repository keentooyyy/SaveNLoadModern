/**
 * Forgot Password Form Handler
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
    
    const forgotPasswordForm = document.getElementById('forgotPasswordForm');
    const sendOtpBtn = document.getElementById('sendOtpBtn');
    
    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
            if (!csrfToken) {
                showToast('Error: CSRF token not found', 'error');
                return;
            }
            
            const emailInput = document.getElementById('email');
            const email = emailInput?.value.trim() || '';
            const emailError = document.getElementById('email-error');
            
            // Clear previous errors
            if (emailError) {
                emailError.classList.add('d-none');
                emailError.classList.remove('d-block');
                emailError.textContent = '';
            }
            
            // Basic validation
            if (!email) {
                if (emailError) {
                    emailError.textContent = 'Email is required.';
                    emailError.classList.remove('d-none');
                    emailError.classList.add('d-block');
                }
                return;
            }
            
            // Basic email format validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                if (emailError) {
                    emailError.textContent = 'Please enter a valid email address.';
                    emailError.classList.remove('d-none');
                    emailError.classList.add('d-block');
                }
                return;
            }
            
            // Disable button and show loading state
            const originalContent = Array.from(sendOtpBtn.childNodes);
            sendOtpBtn.disabled = true;
            sendOtpBtn.textContent = '';
            const spinnerIcon = document.createElement('i');
            spinnerIcon.className = 'fas fa-spinner fa-spin me-1';
            const loadingText = document.createTextNode('SENDING...');
            sendOtpBtn.appendChild(spinnerIcon);
            sendOtpBtn.appendChild(loadingText);
            
            try {
                const response = await fetch('{% url "SaveNLoad:forgot_password" %}', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
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
                    if (emailError) {
                        emailError.textContent = errorMsg;
                        emailError.classList.remove('d-none');
                        emailError.classList.add('d-block');
                    } else {
                        showToast(errorMsg, 'error');
                    }
                }
            } catch (error) {
                console.error('Error sending OTP:', error);
                showToast('Error: Failed to send OTP. Please try again.', 'error');
            } finally {
                sendOtpBtn.disabled = false;
                sendOtpBtn.textContent = '';
                originalContent.forEach(node => {
                    sendOtpBtn.appendChild(node.cloneNode(true));
                });
            }
        });
    }
})();

