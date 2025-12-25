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
        const headers = window.createFetchHeaders
            ? window.createFetchHeaders(window.getCsrfToken ? window.getCsrfToken() : null)
            : { 'X-Requested-With': 'XMLHttpRequest' };

        fetch(API_ENDPOINT, { headers: headers })
            .then(response => response.json())
            .then(data => {
                if (!data.connected) {
                    // Worker disconnected - reload page (decorator will show worker required page)
                    console.warn('Client worker disconnected. Reloading...');
                    window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error checking worker connection:', error);
                // On error, assume disconnected and reload (decorator will handle it)
                window.location.reload();
            });
    }

    // Start checking when page loads
    function startWorkerCheck() {
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

