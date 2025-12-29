document.addEventListener('DOMContentLoaded', function () {
    const claimBtns = document.querySelectorAll('.claim-btn');

    // URLs and config from global window object (injected in template)
    const claimUrl = window.CLAIM_WORKER_URL;
    const pollUrl = window.UNPAIRED_WORKERS_POLL_URL;
    const workerCount = window.WORKER_COUNT || 0;

    // Smart polling to keep list up to date - detects claim status changes too!
    if (pollUrl) {
        // Build map of current worker states from DOM
        const getCurrentWorkerStates = () => {
            const states = new Map();
            document.querySelectorAll('.list-group-item').forEach(item => {
                const btn = item.querySelector('.claim-btn');
                const clientId = btn ? btn.dataset.clientId : null;
                if (clientId) {
                    // Check if worker is claimed (no button = claimed)
                    const isClaimed = !btn || item.querySelector('.text-muted');
                    states.set(clientId, {
                        claimed: isClaimed,
                        linkedUser: item.textContent.includes('Claimed by:') ? 
                            item.textContent.match(/Claimed by: ([^\n]+)/)?.[1]?.trim() : null
                    });
                }
            });
            return states;
        };

        setInterval(() => {
            fetch(pollUrl)
                .then(r => r.json())
                .then(data => {
                    const workers = data.workers || [];
                    const currentStates = getCurrentWorkerStates();
                    const currentIds = new Set(currentStates.keys());

                    // Check if list changed (new/removed workers)
                    const newWorkerIds = new Set(workers.map(w => w.client_id));
                    let listChanged = workers.length !== currentIds.size;
                    
                    if (!listChanged) {
                        // Check if any worker IDs don't match
                        for (const w of workers) {
                            if (!currentIds.has(w.client_id)) {
                                listChanged = true;
                                break;
                            }
                        }
                    }

                    // Check if claim status changed for existing workers
                    let statusChanged = false;
                    if (!listChanged) {
                        for (const w of workers) {
                            const currentState = currentStates.get(w.client_id);
                            if (currentState) {
                                // Check if claim status changed
                                if (currentState.claimed !== w.claimed) {
                                    statusChanged = true;
                                    break;
                                }
                                // Check if linked user changed
                                if (w.claimed && currentState.linkedUser !== w.linked_user) {
                                    statusChanged = true;
                                    break;
                                }
                            }
                        }
                    }

                    if (listChanged || statusChanged) {
                        // List or status changed - reload to update UI
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
            setButtonLoadingState(this, true, 'CONNECTING...');

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
            claimBtns[0].click();
        }
    });
});

