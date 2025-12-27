document.addEventListener('DOMContentLoaded', function () {
    'use strict';

    const logoutLink = document.getElementById('sidebarLogoutLink');
    if (logoutLink) {
        logoutLink.addEventListener('click', function (e) {
            const clientId = localStorage.getItem('savenload_client_id');
            if (clientId) {
                e.preventDefault();
                const url = new URL(this.href, window.location.origin);
                url.searchParams.set('client_id', clientId);
                window.location.href = url.toString();
            }
        });
    }
});
