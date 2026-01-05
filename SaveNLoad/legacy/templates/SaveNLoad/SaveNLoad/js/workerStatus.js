/**
 * Worker availability watcher for dashboard/settings.
 * Redirects to worker-required view when no online worker is available.
 */
/**
 * Initialize worker status WebSocket and redirect logic.
 *
 * Args:
 *     None
 *
 * Returns:
 *     None
 */
document.addEventListener('DOMContentLoaded', function () {
    /**
     * Build WS URL for user worker status updates.
     *
     * Args:
     *     None
     *
     * Returns:
     *     WebSocket URL string.
     */
    function buildWsUrl() {
        const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
        return `${scheme}://${window.location.host}/ws/ui/worker-status/`;
    }

    /**
     * Redirect to the worker-required URL when no worker is connected.
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    function redirectToWorkerRequired() {
        if (window.WORKER_REQUIRED_URL) {
            window.location.href = window.WORKER_REQUIRED_URL;
            return;
        }
        window.location.reload();
    }

    /**
     * Connect to the worker status socket with basic reconnect.
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    function connectWorkerStatusSocket() {
        if (!window.WebSocket) {
            return;
        }

        const wsUrl = buildWsUrl();
        let socket;
        let reconnectTimer;

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

            socket.addEventListener('message', event => {
                try {
                    const message = JSON.parse(event.data);
                    // Server emits "worker_status" with connected boolean.
                    if (message.type === 'worker_status') {
                        const payload = message.payload || {};
                        if (payload.connected === false) {
                            redirectToWorkerRequired();
                        }
                    }
                } catch (error) {
                    console.error('Worker status WS message error:', error);
                }
            });

            socket.addEventListener('close', () => {
                // Keep the socket alive while the page is open.
                reconnectTimer = setTimeout(connect, 3000);
            });

            socket.addEventListener('error', error => {
                console.error('Worker status WS error:', error);
                socket.close();
            });
        }

        connect();
    }

    connectWorkerStatusSocket();
});
