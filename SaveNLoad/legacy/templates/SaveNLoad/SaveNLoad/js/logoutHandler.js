/**
 * Wire up logout link behavior once the DOM is ready.
 *
 * Args:
 *     None
 *
 * Returns:
 *     None
 */
document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    const logoutLink = document.getElementById('sidebarLogoutLink');
    if (logoutLink) {
        /**
         * Append client_id to logout URL and clear cached client data.
         *
         * Args:
         *     e: Click event.
         *
         * Returns:
         *     None
         */
        logoutLink.addEventListener('click', function (e) {
            const clientId = localStorage.getItem('savenload_client_id');
            if (clientId) {
                e.preventDefault();
                const url = new URL(this.href, window.location.origin);
                url.searchParams.set('client_id', clientId);
                // Clear localStorage to prevent stale data
                localStorage.removeItem('savenload_client_id');
                window.location.href = url.toString();
            } else {
                // Even if no client_id, clear any stale data
                localStorage.removeItem('savenload_client_id');
            }
        });
    }
});
