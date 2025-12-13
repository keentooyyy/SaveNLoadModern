// Password visibility toggle for login and register pages
document.addEventListener('DOMContentLoaded', function() {
    // Helper function to set up password toggle
    function setupPasswordToggle(toggleId, inputId) {
        const toggleIcon = document.getElementById(toggleId);
        const passwordInput = document.getElementById(inputId);
        
        if (toggleIcon && passwordInput) {
            toggleIcon.addEventListener('click', function() {
                const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
                passwordInput.setAttribute('type', type);
                
                // Toggle icon
                if (type === 'password') {
                    toggleIcon.classList.remove('fa-eye');
                    toggleIcon.classList.add('fa-eye-slash');
                } else {
                    toggleIcon.classList.remove('fa-eye-slash');
                    toggleIcon.classList.add('fa-eye');
                }
            });
        }
    }
    
    // Set up toggle for password field (login and register)
    setupPasswordToggle('togglePassword', 'password');
    
    // Set up toggle for repeat password field (register only)
    setupPasswordToggle('toggleRepeatPassword', 'repeatPassword');
});

