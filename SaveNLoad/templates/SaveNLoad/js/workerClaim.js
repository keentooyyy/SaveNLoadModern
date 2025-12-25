document.addEventListener('DOMContentLoaded', function () {
    const claimBtns = document.querySelectorAll('.claim-btn');

    // Get config from data attributes
    const configDiv = document.getElementById('worker-config');
    const claimUrl = configDiv ? configDiv.dataset.claimUrl : null;

    // Get worker count from json_script
    const workerCountScript = document.getElementById('worker-count');
    const workerCount = workerCountScript ? JSON.parse(workerCountScript.textContent) : 0;

    // Auto-refresh logic if no workers found
    if (workerCount === 0) {
        setTimeout(() => {
            location.reload();
        }, 5000);
    }

    // Get CSRF token using utility
    const csrfToken = getCsrfToken();

    claimBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            if (!claimUrl) {
                console.error('Claim URL not found');
                return;
            }

            const clientId = this.dataset.clientId;

            // Use shared utility for button state (handles spinner)
            setButtonLoadingState(this, true, 'Connecting...');

            fetch(claimUrl, {
                method: 'POST',
                headers: createFetchHeaders(csrfToken),
                body: JSON.stringify({
                    client_id: clientId
                })
            })
                .then(response => {
                    // Check for CSRF error (403 status)
                    if (response.status === 403) {
                        return response.json().then(data => {
                            throw new Error('CSRF verification failed');
                        }).catch(() => {
                            throw new Error('CSRF verification failed');
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        // Success! Reload to proceed to dashboard
                        window.location.reload();
                    } else {
                        // Use shared toast utility
                        showToast('Error: ' + (data.error || 'Failed to claim worker'), 'error');
                        setButtonLoadingState(this, false);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (error.message && error.message.includes('CSRF')) {
                        showToast('CSRF verification failed. Please refresh the page and try again.', 'error');
                    } else {
                        showToast('An error occurred. Please try again.', 'error');
                    }
                    setButtonLoadingState(this, false);
                });
        });
    });
});
