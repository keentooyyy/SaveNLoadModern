/**
 * Forgot Password Form Handler
 */
(function() {
    'use strict';
    
    const forgotPasswordForm = document.getElementById('forgotPasswordForm');
    const sendOtpBtn = document.getElementById('sendOtpBtn');
    
    if (forgotPasswordForm) {
        forgotPasswordForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const csrfToken = document.querySelector('[name="csrfmiddlewaretoken"]')?.value;
            if (!csrfToken) {
                alert('Error: CSRF token not found');
                return;
            }
            
            const emailInput = document.getElementById('email');
            const email = emailInput?.value.trim() || '';
            const emailError = document.getElementById('email-error');
            
            // Clear previous errors
            if (emailError) {
                emailError.style.display = 'none';
                emailError.textContent = '';
            }
            
            // Basic validation
            if (!email) {
                if (emailError) {
                    emailError.textContent = 'Email is required.';
                    emailError.style.display = 'block';
                }
                return;
            }
            
            // Basic email format validation
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(email)) {
                if (emailError) {
                    emailError.textContent = 'Please enter a valid email address.';
                    emailError.style.display = 'block';
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
                    // Redirect to verify OTP page
                    window.location.href = '{% url "SaveNLoad:verify_otp" %}';
                } else {
                    const errorMsg = data.error || data.message || 'Failed to send OTP. Please try again.';
                    if (emailError) {
                        emailError.textContent = errorMsg;
                        emailError.style.display = 'block';
                    } else {
                        alert(errorMsg);
                    }
                }
            } catch (error) {
                console.error('Error sending OTP:', error);
                alert('Error: Failed to send OTP. Please try again.');
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

