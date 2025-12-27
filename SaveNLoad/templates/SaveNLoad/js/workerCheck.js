/**
 * Worker Connection Checker
 * Periodically checks if client worker is connected and redirects if not
 */
(function () {
    'use strict';

    const CHECK_INTERVAL = 5000; // Check every 5 second
    // API endpoint is injected from Django template
    const API_ENDPOINT = window.WORKER_CHECK_URL;

    let checkInterval = null;

    function checkWorkerConnection() {
        // Validate API endpoint is defined
        if (!API_ENDPOINT || API_ENDPOINT === 'undefined') {
            console.error('WORKER_CHECK_URL is not defined. Skipping worker check.');
            return;
        }

        const headers = window.createFetchHeaders
            ? window.createFetchHeaders(window.getCsrfToken ? window.getCsrfToken() : null)
            : { 'X-Requested-With': 'XMLHttpRequest' };

        fetch(API_ENDPOINT, { headers: headers })
            .then(response => response.json())
            .then(data => {
                if (!data.connected) {
                    // Worker disconnected - clear localStorage and reload page (decorator will show worker required page)
                    console.warn('Client worker disconnected. Clearing localStorage and reloading...');
                    localStorage.removeItem('savenload_client_id');
                    window.location.reload();
                } else if (data.client_id) {
                    // Store client_id for logout handling
                    localStorage.setItem('savenload_client_id', data.client_id);
                }
            })
            .catch(error => {
                console.error('Error checking worker connection:', error);
                // On error, clear localStorage and reload (decorator will handle it)
                localStorage.removeItem('savenload_client_id');
                window.location.reload();
            });
    }

    // Start checking when page loads
    function startWorkerCheck() {
        // Validate API endpoint before starting checks
        if (!API_ENDPOINT || API_ENDPOINT === 'undefined') {
            console.error('WORKER_CHECK_URL is not defined. Worker check disabled.');
            return;
        }

        // Initial check
        checkWorkerConnection();

        // Set up periodic checks
        checkInterval = setInterval(checkWorkerConnection, CHECK_INTERVAL);
    }

    // Stop checking when page unloads
    function stopWorkerCheck() {
        if (checkInterval) {
            clearInterval(checkInterval);
            checkInterval = null;
        }
    }

    // Start checking when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startWorkerCheck);
    } else {
        startWorkerCheck();
    }

    // Stop checking when page unloads
    window.addEventListener('beforeunload', stopWorkerCheck);

    // Also check on visibility change (when user switches tabs)
    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible') {
            // Page became visible - check immediately
            checkWorkerConnection();
        }
    });
})();

