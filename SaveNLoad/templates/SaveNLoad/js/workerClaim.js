/**
 * Initialize worker claim UI and WebSocket updates.
 *
 * Args:
 *     None
 *
 * Returns:
 *     None
 */
document.addEventListener('DOMContentLoaded', function () {
    // URLs and config from global window object (injected in template)
    const claimUrl = window.CLAIM_WORKER_URL;

    // Get CSRF token using utility
    const csrfToken = getCsrfToken();

    const listContainer = document.getElementById('worker_list_container');
    const listGroup = document.getElementById('worker_list');
    const emptyState = document.getElementById('worker_empty_state');
    const refreshButton = document.getElementById('worker_refresh_button');

    /**
     * Show loading state when there is no worker list yet.
     *
     * Args:
     *     isLoading: True to show the loading state.
     *
     * Returns:
     *     None
     */
    function setLoadingState(isLoading) {
        if (!emptyState || !isLoading) {
            return;
        }
        if (listContainer && !listContainer.classList.contains('d-none')) {
            return;
        }
        emptyState.classList.remove('d-none');
    }

    /**
     * Toggle list vs empty state visibility.
     *
     * Args:
     *     hasWorkers: True when there is at least one worker.
     *
     * Returns:
     *     None
     */
    function setListVisibility(hasWorkers) {
        if (listContainer) {
            listContainer.classList.toggle('d-none', !hasWorkers);
        }
        if (emptyState) {
            emptyState.classList.toggle('d-none', hasWorkers);
        }
        if (refreshButton) {
            refreshButton.classList.toggle('d-none', hasWorkers);
        }
    }

    /**
     * Build a worker list row element.
     *
     * Args:
     *     worker: Worker object from the WS payload.
     *
     * Returns:
     *     DOM element for the worker row.
     */
    function createWorkerRow(worker) {
        const item = document.createElement('div');
        item.className = 'list-group-item bg-dark border-secondary d-flex justify-content-between align-items-center';

        const info = document.createElement('div');
        info.className = 'text-start';

        const title = document.createElement('strong');
        title.className = 'text-white d-block';
        title.textContent = `Worker ID: ${worker.client_id}`;
        info.appendChild(title);

        const badges = document.createElement('div');
        badges.className = 'mt-1';

        const onlineBadge = document.createElement('span');
        onlineBadge.className = 'badge bg-success';
        onlineBadge.textContent = 'Online';
        badges.appendChild(onlineBadge);

        if (worker.claimed) {
            const claimedBadge = document.createElement('span');
            claimedBadge.className = 'badge bg-warning text-dark ms-2';
            claimedBadge.textContent = `Claimed by: ${worker.linked_user || 'Unknown'}`;
            badges.appendChild(claimedBadge);
        } else {
            const unclaimedBadge = document.createElement('span');
            unclaimedBadge.className = 'badge bg-secondary ms-2';
            unclaimedBadge.textContent = 'Unclaimed';
            badges.appendChild(unclaimedBadge);
        }

        info.appendChild(badges);
        item.appendChild(info);

        if (!worker.claimed) {
            const button = document.createElement('button');
            button.className = 'btn btn-primary btn-sm claim-btn';
            button.dataset.clientId = worker.client_id;
            button.textContent = 'Use Worker';
            button.addEventListener('click', () => claimWorker(button));
            item.appendChild(button);
        } else {
            const claimedText = document.createElement('span');
            claimedText.className = 'text-muted';
            claimedText.textContent = 'Already claimed';
            item.appendChild(claimedText);
        }

        return item;
    }

    /**
     * Render the current worker list from WS payload.
     *
     * Args:
     *     workers: Array of worker objects.
     *
     * Returns:
     *     None
     */
    function renderWorkers(workers) {
        if (!listGroup || !Array.isArray(workers)) {
            return;
        }

        if (renderWorkers.hasShownSingleAvailableToast === undefined) {
            renderWorkers.hasShownSingleAvailableToast = false;
        }

        listGroup.innerHTML = '';
        workers.forEach(worker => {
            listGroup.appendChild(createWorkerRow(worker));
        });

        setListVisibility(workers.length > 0);

        const available = workers.filter(worker => !worker.claimed);
        if (available.length === 1 && !renderWorkers.hasShownSingleAvailableToast) {
            showToast('One worker available. Select it to connect.', 'info');
            renderWorkers.hasShownSingleAvailableToast = true;
        } else if (available.length !== 1) {
            renderWorkers.hasShownSingleAvailableToast = false;
        }
    }

    /**
     * Claim a worker via API and reload on success.
     *
     * Args:
     *     button: Button element that triggered the claim.
     *
     * Returns:
     *     None
     */
    function claimWorker(button) {
        if (!claimUrl) {
            console.error('Claim URL not found');
            return;
        }

        const clientId = button.dataset.clientId;
        if (!clientId) {
            return;
        }

        setButtonLoadingState(button, true, 'CONNECTING...');

        fetch(claimUrl, {
            method: 'POST',
            headers: createFetchHeaders(csrfToken),
            body: JSON.stringify({
                client_id: clientId
            })
        })
            .then(response => {
                if (response.status === 403) {
                    return response.json().then(() => {
                        throw new Error('CSRF verification failed');
                    }).catch(() => {
                        throw new Error('CSRF verification failed');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    window.location.reload();
                } else {
                    showToast('Error: ' + (data.error || 'Failed to claim worker'), 'error');
                    setButtonLoadingState(button, false);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                if (error.message && error.message.includes('CSRF')) {
                    showToast('CSRF verification failed. Please refresh the page and try again.', 'error');
                } else {
                    showToast('An error occurred. Please try again.', 'error');
                }
                setButtonLoadingState(button, false);
            });
    }

    /**
     * Build WS URL for UI worker updates.
     *
     * Args:
     *     None
     *
     * Returns:
     *     WebSocket URL string.
     */
    function buildWsUrl() {
        const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        return `${scheme}://${window.location.host}/ws/ui/workers/`;
    }

    /**
     * Connect to the worker list socket with basic reconnect.
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    function connectWorkersSocket() {
        if (!window.WebSocket) {
            if (refreshButton) {
                refreshButton.classList.remove('d-none');
            }
            return;
        }
        const wsUrl = buildWsUrl();
        let socket;
        let reconnectTimer;
        let hasOpened = false;

        /**
         * Establish a WS connection and rebind event handlers.
         *
         * Args:
         *     None
         *
         * Returns:
         *     None
         */
        function connect() {
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
                reconnectTimer = null;
            }

            socket = new WebSocket(wsUrl);

            socket.addEventListener('open', () => {
                hasOpened = true;
                setLoadingState(true);
            });

            socket.addEventListener('message', event => {
                try {
                    const message = JSON.parse(event.data);
                    if (message.type === 'workers_update') {
                        const workers = message.payload ? message.payload.workers : [];
                        renderWorkers(workers);
                    }
                } catch (error) {
                    console.error('WS message error:', error);
                }
            });

            socket.addEventListener('close', () => {
                if (refreshButton) {
                    refreshButton.classList.remove('d-none');
                }
                if (hasOpened) {
                    window.location.reload();
                }
                reconnectTimer = setTimeout(connect, 3000);
            });

            socket.addEventListener('error', error => {
                console.error('WS error:', error);
                socket.close();
            });
        }

        connect();
    }

    connectWorkersSocket();
});

