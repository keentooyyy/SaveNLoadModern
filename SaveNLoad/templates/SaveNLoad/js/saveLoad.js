document.addEventListener('DOMContentLoaded', function () {
    const csrfInput = document.querySelector('#gameCsrfForm input[name="csrfmiddlewaretoken"]');
    const csrfToken = csrfInput ? csrfInput.value : null;

    if (!csrfToken) {
        console.error('CSRF token not found');
        return;
    }

    // Show toast notification
    function showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.body.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 5000);
    }

    // Handle Save button clicks
    document.addEventListener('click', async function (e) {
        if (e.target.closest('.save-game-btn')) {
            e.preventDefault();
            e.stopPropagation();
            
            const btn = e.target.closest('.save-game-btn');
            const gameId = btn.dataset.gameId;
            
            if (!gameId) {
                showToast('Error: Game ID not found', 'error');
                return;
            }

            // Disable button and show loading state
            const originalHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Saving...';

            try {
                const response = await fetch(`/admin/games/${gameId}/save/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({}) // Empty body - uses game's save_file_location
                });

                const data = await response.json();

                if (data.success) {
                    showToast(data.message || 'Game saved successfully!', 'success');
                } else {
                    showToast(data.error || data.message || 'Failed to save game', 'error');
                }
            } catch (error) {
                console.error('Error saving game:', error);
                showToast('Error: Failed to save game. Please try again.', 'error');
            } finally {
                // Restore button
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }

        // Handle Load button clicks
        if (e.target.closest('.load-game-btn')) {
            e.preventDefault();
            e.stopPropagation();
            
            const btn = e.target.closest('.load-game-btn');
            const gameId = btn.dataset.gameId;
            
            if (!gameId) {
                showToast('Error: Game ID not found', 'error');
                return;
            }

            // Disable button and show loading state
            const originalHtml = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Loading...';

            try {
                const response = await fetch(`/admin/games/${gameId}/load/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({}) // Empty body - uses game's save_file_location
                });

                const data = await response.json();

                if (data.success) {
                    showToast(data.message || 'Game loaded successfully!', 'success');
                } else {
                    showToast(data.error || data.message || 'Failed to load game', 'error');
                }
            } catch (error) {
                console.error('Error loading game:', error);
                showToast('Error: Failed to load game. Please try again.', 'error');
            } finally {
                // Restore button
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }
    });

    // Prevent card click when clicking save/load buttons
    document.addEventListener('click', function (e) {
        if (e.target.closest('.save-game-btn') || e.target.closest('.load-game-btn')) {
            const card = e.target.closest('.game-card');
            if (card) {
                e.stopPropagation();
            }
        }
    });
});

