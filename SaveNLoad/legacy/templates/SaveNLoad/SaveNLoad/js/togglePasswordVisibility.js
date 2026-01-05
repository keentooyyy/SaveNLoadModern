// Password visibility toggle for login and register pages
/**
 * Initialize password visibility toggles after DOM is ready.
 *
 * Args:
 *     None
 *
 * Returns:
 *     None
 */
document.addEventListener('DOMContentLoaded', function () {
    // Uses shared setupPasswordToggle from utils.js.

    // Set up toggle for password field (login and register)
    setupPasswordToggle('togglePassword', 'password');

    // Set up toggle for repeat password field (register only)
    setupPasswordToggle('toggleRepeatPassword', 'repeatPassword');
});

