document.addEventListener('DOMContentLoaded', function () {
    const claimBtns = document.querySelectorAll('.claim-btn');

    // URLs and config from global window object (injected in template)
    const claimUrl = window.CLAIM_WORKER_URL;
    const pollUrl = window.UNPAIRED_WORKERS_POLL_URL;
    const workerCount = window.WORKER_COUNT || 0;

    // Smart polling to keep list up to date
    if (pollUrl) {
        // Collect current worker IDs from DOM
        const getCurrentWorkerIds = () => {
            const ids = new Set();
            document.querySelectorAll('.claim-btn').forEach(btn => {
                ids.add(btn.dataset.clientId);
            });
            return ids;
        };

        setInterval(() => {
            fetch(pollUrl)
                .then(r => r.json())
                .then(data => {
                    const workers = data.workers || [];
                    const currentIds = getCurrentWorkerIds();

                    // Check if list changed
                    let changed = false;

                    // Check for new workers
                    if (workers.length !== currentIds.size) {
                        changed = true;
                    } else {
                        // Check if content matches
                        for (const w of workers) {
                            if (!currentIds.has(w.client_id)) {
                                changed = true;
                                break;
                            }
                        }
                    }

                    if (changed) {
                        // List changed (new worker appeared or existing one went offline)
                        // Reload to update UI
                        location.reload();
                    }
                })
                .catch(e => console.error('Polling error:', e));
        }, 3000); // Check every 3 seconds
    } else if (workerCount === 0) {
        // Fallback if no poll URL
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

        // Auto-click if it's the only worker
        if (claimBtns.length === 1) {
            showToast('Auto-connecting to worker...', 'info');
            btn.click();
        }
    });
});

