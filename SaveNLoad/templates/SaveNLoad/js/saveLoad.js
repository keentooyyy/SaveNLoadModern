document.addEventListener('DOMContentLoaded', function () {
    const csrfInput = document.querySelector('#gameCsrfForm input[name="csrfmiddlewaretoken"]');
    const csrfToken = csrfInput ? csrfInput.value : null;

    if (!csrfToken) {
        console.error('CSRF token not found');
        return;
    }

    // Poll operation status until completion
    async function pollOperationStatus(operationId, btn, originalIcon, originalText) {
        const maxAttempts = 60; // 60 attempts = 60 seconds max (1 second intervals)
        let attempts = 0;
        const pollInterval = 1000; // Poll every 1 second
        
        const checkStatus = async () => {
            try {
                const urlPattern = window.CHECK_OPERATION_STATUS_URL_PATTERN;
                const url = urlPattern.replace('/0/', `/${operationId}/`);
                const response = await fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                
                if (!response.ok) {
                    throw new Error('Failed to check operation status');
                }
                
                const data = await response.json();
                
                if (data.completed) {
                    showToast('Game saved successfully!', 'success');
                    // Refresh page after a short delay to update recent games
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                    return true;
                } else if (data.failed) {
                    showToast(data.message || 'Save operation failed', 'error');
                    // Restore button on failure
                    btn.disabled = false;
                    while (btn.firstChild) {
                        btn.removeChild(btn.firstChild);
                    }
                    if (originalIcon) {
                        const iconClone = originalIcon.cloneNode(true);
                        btn.appendChild(iconClone);
                    }
                    btn.appendChild(document.createTextNode(' Save'));
                    return true;
                }
                
                return false;
            } catch (error) {
                console.error('Error checking operation status:', error);
                return false;
            }
        };
        
        // Initial check
        const completed = await checkStatus();
        if (completed) return;
        
        // Poll until completion or max attempts
        const poll = setInterval(async () => {
            attempts++;
            const completed = await checkStatus();
            
            if (completed || attempts >= maxAttempts) {
                clearInterval(poll);
                if (attempts >= maxAttempts && !completed) {
                    showToast('Operation is taking longer than expected. Please refresh the page.', 'error');
                    // Restore button on timeout
                    btn.disabled = false;
                    while (btn.firstChild) {
                        btn.removeChild(btn.firstChild);
                    }
                    if (originalIcon) {
                        const iconClone = originalIcon.cloneNode(true);
                        btn.appendChild(iconClone);
                    }
                    btn.appendChild(document.createTextNode(' Save'));
                }
            }
        }, pollInterval);
    }

    // Show toast notification
    function showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        const alertType = type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info';
        toast.className = `alert alert-${alertType} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        
        const messageText = document.createTextNode(message);
        toast.appendChild(messageText);
        
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close';
        closeBtn.setAttribute('data-bs-dismiss', 'alert');
        closeBtn.setAttribute('aria-label', 'Close');
        toast.appendChild(closeBtn);
        
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
            const originalIcon = btn.querySelector('i');
            const originalText = btn.childNodes[1] ? btn.childNodes[1].textContent.trim() : 'Save';
            btn.disabled = true;
            
            // Clear button content
            while (btn.firstChild) {
                btn.removeChild(btn.firstChild);
            }
            
            const spinner = document.createElement('i');
            spinner.className = 'fas fa-spinner fa-spin me-1';
            btn.appendChild(spinner);
            btn.appendChild(document.createTextNode(' Saving...'));

            try {
                const urlPattern = window.SAVE_GAME_URL_PATTERN;
                const url = urlPattern.replace('/0/', `/${gameId}/`);
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({}) // Empty body - uses game's save_file_location
                });

                const data = await response.json();

                if (data.success && data.operation_id) {
                    // Poll for operation completion
                    await pollOperationStatus(data.operation_id, btn, originalIcon, originalText);
                } else {
                    showToast(data.error || data.message || 'Failed to save game', 'error');
                    // Restore button on error
                    btn.disabled = false;
                    while (btn.firstChild) {
                        btn.removeChild(btn.firstChild);
                    }
                    if (originalIcon) {
                        const iconClone = originalIcon.cloneNode(true);
                        btn.appendChild(iconClone);
                    }
                    btn.appendChild(document.createTextNode(' Save'));
                }
            } catch (error) {
                console.error('Error saving game:', error);
                showToast('Error: Failed to save game. Please try again.', 'error');
                // Restore button on error
                btn.disabled = false;
                while (btn.firstChild) {
                    btn.removeChild(btn.firstChild);
                }
                if (originalIcon) {
                    const iconClone = originalIcon.cloneNode(true);
                    btn.appendChild(iconClone);
                }
                btn.appendChild(document.createTextNode(' Save'));
            }
        }
    });

    // Handle Quick Load button clicks
    document.addEventListener('click', async function (e) {
        if (e.target.closest('.quick-load-btn')) {
            e.preventDefault();
            e.stopPropagation();
            
            const btn = e.target.closest('.quick-load-btn');
            const gameId = btn.dataset.gameId;
            
            if (!gameId) {
                showToast('Error: Game ID not found', 'error');
                return;
            }

            // Disable button and show loading state
            const originalIcon = btn.querySelector('i');
            btn.disabled = true;
            
            // Clear button content
            while (btn.firstChild) {
                btn.removeChild(btn.firstChild);
            }
            
            const spinner = document.createElement('i');
            spinner.className = 'fas fa-spinner fa-spin me-1';
            btn.appendChild(spinner);
            btn.appendChild(document.createTextNode(' Loading...'));

            try {
                const urlPattern = window.LOAD_GAME_URL_PATTERN;
                const url = urlPattern.replace('/0/', `/${gameId}/`);
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({}) // Empty body - uses game's save_file_location and latest save folder
                });

                const data = await response.json();

                if (data.success && data.operation_id) {
                    // Poll for operation completion
                    await pollLoadOperationStatus(data.operation_id, btn, originalIcon);
                } else {
                    showToast(data.error || data.message || 'Failed to load game', 'error');
                    // Restore button on error
                    btn.disabled = false;
                    while (btn.firstChild) {
                        btn.removeChild(btn.firstChild);
                    }
                    if (originalIcon) {
                        const iconClone = originalIcon.cloneNode(true);
                        btn.appendChild(iconClone);
                    }
                    btn.appendChild(document.createTextNode(' Quick Load'));
                }
            } catch (error) {
                console.error('Error loading game:', error);
                showToast('Error: Failed to load game. Please try again.', 'error');
                // Restore button on error
                btn.disabled = false;
                while (btn.firstChild) {
                    btn.removeChild(btn.firstChild);
                }
                if (originalIcon) {
                    const iconClone = originalIcon.cloneNode(true);
                    btn.appendChild(iconClone);
                }
                btn.appendChild(document.createTextNode(' Quick Load'));
            }
        }
    });

    // Poll load operation status until completion
    async function pollLoadOperationStatus(operationId, btn, originalIcon) {
        const maxAttempts = 60; // 60 attempts = 60 seconds max (1 second intervals)
        let attempts = 0;
        const pollInterval = 1000; // Poll every 1 second
        
        const checkStatus = async () => {
            try {
                const urlPattern = window.CHECK_OPERATION_STATUS_URL_PATTERN;
                const url = urlPattern.replace('/0/', `/${operationId}/`);
                const response = await fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                
                if (!response.ok) {
                    throw new Error('Failed to check operation status');
                }
                
                const data = await response.json();
                
                if (data.completed) {
                    showToast('Game loaded successfully!', 'success');
                    // Restore button
                    btn.disabled = false;
                    while (btn.firstChild) {
                        btn.removeChild(btn.firstChild);
                    }
                    if (originalIcon) {
                        const iconClone = originalIcon.cloneNode(true);
                        btn.appendChild(iconClone);
                    }
                    btn.appendChild(document.createTextNode(' Quick Load'));
                    return true;
                } else if (data.failed) {
                    showToast(data.message || 'Load operation failed', 'error');
                    // Restore button on failure
                    btn.disabled = false;
                    while (btn.firstChild) {
                        btn.removeChild(btn.firstChild);
                    }
                    if (originalIcon) {
                        const iconClone = originalIcon.cloneNode(true);
                        btn.appendChild(iconClone);
                    }
                    btn.appendChild(document.createTextNode(' Quick Load'));
                    return true;
                }
                
                return false;
            } catch (error) {
                console.error('Error checking operation status:', error);
                return false;
            }
        };
        
        // Initial check
        const completed = await checkStatus();
        if (completed) return;
        
        // Poll until completion or max attempts
        const poll = setInterval(async () => {
            attempts++;
            const completed = await checkStatus();
            
            if (completed || attempts >= maxAttempts) {
                clearInterval(poll);
                if (attempts >= maxAttempts && !completed) {
                    showToast('Operation is taking longer than expected. Please refresh the page.', 'error');
                    // Restore button on timeout
                    btn.disabled = false;
                    while (btn.firstChild) {
                        btn.removeChild(btn.firstChild);
                    }
                    if (originalIcon) {
                        const iconClone = originalIcon.cloneNode(true);
                        btn.appendChild(iconClone);
                    }
                    btn.appendChild(document.createTextNode(' Quick Load'));
                }
            }
        }, pollInterval);
    }

    // Prevent card click when clicking save or quick load buttons
    document.addEventListener('click', function (e) {
        if (e.target.closest('.save-game-btn') || e.target.closest('.quick-load-btn')) {
            const card = e.target.closest('.game-card');
            if (card) {
                e.stopPropagation();
            }
        }
    });
});

