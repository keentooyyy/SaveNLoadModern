/**
 * Worker Required Page Connection Checker
 * Auto-checks for client worker connection and redirects when connected
 */
(function() {
    'use strict';
    
    // API endpoint is injected from Django template
    const API_ENDPOINT = window.WORKER_CHECK_URL;
    const CHECK_INTERVAL = 5000; // Check every 5 seconds
    
    function createStatusAlert(message, alertClass, iconClass) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert ${alertClass}`;
        
        const icon = document.createElement('i');
        icon.className = `${iconClass} me-2`;
        
        const text = document.createTextNode(message);
        
        alertDiv.appendChild(icon);
        alertDiv.appendChild(text);
        
        return alertDiv;
    }
    
    function checkConnection() {
        fetch(API_ENDPOINT)
            .then(response => response.json())
            .then(data => {
                const statusDiv = document.getElementById('connectionStatus');
                if (!statusDiv) return;
                
                // Clear previous status
                statusDiv.textContent = '';
                
                if (data.connected) {
                    const alert = createStatusAlert(
                        'Client worker connected! Redirecting...',
                        'alert-success',
                        'fas fa-check-circle'
                    );
                    statusDiv.appendChild(alert);
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    const alert = createStatusAlert(
                        'Waiting for worker connection...',
                        'alert-warning',
                        'fas fa-clock'
                    );
                    statusDiv.appendChild(alert);
                }
            })
            .catch(error => {
                console.error('Error checking connection:', error);
                const statusDiv = document.getElementById('connectionStatus');
                if (statusDiv) {
                    statusDiv.textContent = '';
                    const alert = createStatusAlert(
                        'Error checking connection',
                        'alert-danger',
                        'fas fa-exclamation-triangle'
                    );
                    statusDiv.appendChild(alert);
                }
            });
    }
    
    // Start checking when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            checkConnection(); // Initial check
            setInterval(checkConnection, CHECK_INTERVAL);
        });
    } else {
        checkConnection(); // Initial check
        setInterval(checkConnection, CHECK_INTERVAL);
    }
})();

