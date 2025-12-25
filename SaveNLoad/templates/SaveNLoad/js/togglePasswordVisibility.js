// Password visibility toggle for login and register pages
document.addEventListener('DOMContentLoaded', function () {
    // Helper function to set up password toggle
    // Uses shared setupPasswordToggle from utils.js

    // Set up toggle for password field (login and register)
    setupPasswordToggle('togglePassword', 'password');

    // Set up toggle for repeat password field (register only)
    setupPasswordToggle('toggleRepeatPassword', 'repeatPassword');
});

