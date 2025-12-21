document.addEventListener('DOMContentLoaded', function () {
    const csrfInput = document.querySelector('#gameCsrfForm input[name="csrfmiddlewaretoken"]');
    const csrfToken = csrfInput ? csrfInput.value : null;

    if (!csrfToken) {
        console.error('CSRF token not found');
        return;
    }

    // Poll operation status until completion
    async function pollOperationStatus(operationId, btn, originalIcon, originalText) {
        const maxAttempts = 300; // 300 attempts = 5 minutes max (1 second intervals)
        let attempts = 0;
        const pollInterval = 1000; // Poll every 1 second
        
        // Create modal for progress
        const modalId = `progressModal_${operationId}`;
        const modalBackdrop = document.createElement('div');
        modalBackdrop.className = 'modal fade';
        modalBackdrop.id = modalId;
        modalBackdrop.setAttribute('data-bs-backdrop', 'static');
        modalBackdrop.setAttribute('data-bs-keyboard', 'false');
        modalBackdrop.setAttribute('tabindex', '-1');
        modalBackdrop.setAttribute('aria-labelledby', `${modalId}Label`);
        modalBackdrop.setAttribute('aria-hidden', 'true');
        
        const modalDialog = document.createElement('div');
        modalDialog.className = 'modal-dialog modal-dialog-centered';
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content bg-primary text-white border-0';
        
        const modalHeader = document.createElement('div');
        modalHeader.className = 'modal-header bg-primary border-secondary';
        
        const modalTitle = document.createElement('h5');
        modalTitle.className = 'modal-title text-white';
        modalTitle.id = `${modalId}Label`;
        modalTitle.textContent = 'Operation in Progress';
        
        modalHeader.appendChild(modalTitle);
        
        const modalBody = document.createElement('div');
        modalBody.className = 'modal-body bg-primary';
        
        const progressBarWrapper = document.createElement('div');
        progressBarWrapper.className = 'progress mb-3';
        progressBarWrapper.style.height = '30px';
        progressBarWrapper.style.backgroundColor = getCSSVariable('--white-opacity-10');
        
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
        progressBar.setAttribute('role', 'progressbar');
        progressBar.style.width = '0%';
        progressBar.style.backgroundColor = getCSSVariable('--color-primary-bootstrap');
        progressBar.setAttribute('aria-valuenow', '0');
        progressBar.setAttribute('aria-valuemin', '0');
        progressBar.setAttribute('aria-valuemax', '100');
        
        const progressText = document.createElement('div');
        progressText.className = 'text-center mt-3 text-white fs-6 fw-medium';
        progressText.textContent = 'Starting...';
        
        const progressDetails = document.createElement('div');
        progressDetails.className = 'text-center text-white-50 mt-2 small';
        progressDetails.textContent = 'Please wait while the operation completes...';
        
        progressBarWrapper.appendChild(progressBar);
        modalBody.appendChild(progressBarWrapper);
        modalBody.appendChild(progressText);
        modalBody.appendChild(progressDetails);
        
        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        modalDialog.appendChild(modalContent);
        modalBackdrop.appendChild(modalDialog);
        
        // Get next z-index for proper stacking
        const nextZIndex = getNextModalZIndex();
        modalBackdrop.style.zIndex = nextZIndex;
        
        // Add modal to body
        document.body.appendChild(modalBackdrop);
        
        // Show modal using Bootstrap
        const modal = new bootstrap.Modal(modalBackdrop, {
            backdrop: 'static',
            keyboard: false
        });
        
        // Set backdrop z-index after modal is shown (Bootstrap creates backdrop dynamically)
        modal._element.addEventListener('shown.bs.modal', function() {
            const backdrop = document.querySelector('.modal-backdrop:last-of-type');
            if (backdrop) {
                backdrop.style.zIndex = (nextZIndex - 10).toString();
            }
        }, { once: true });
        
        modal.show();
        
        const updateProgress = (progressData) => {
            const percentage = progressData.percentage || 0;
            const current = progressData.current || 0;
            const total = progressData.total || 0;
            const message = progressData.message || '';
            
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
            
            if (total > 0) {
                progressText.textContent = `${current}/${total} ${message || 'Processing...'}`;
                progressDetails.textContent = `${percentage}% complete`;
            } else if (message) {
                progressText.textContent = message;
                progressDetails.textContent = 'Processing...';
            } else {
                progressText.textContent = 'Processing...';
                progressDetails.textContent = 'Please wait...';
            }
        };
        
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
                
                // Update progress bar
                if (data.progress) {
                    updateProgress(data.progress);
                }
                
                if (data.completed) {
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-success');
                    progressBar.style.width = '100%';
                    progressBar.setAttribute('aria-valuenow', '100');
                    progressText.textContent = 'Operation Complete!';
                    progressDetails.textContent = 'Successfully completed';
                    showToast('Game saved successfully!', 'success');
                    // Close modal after a delay
                    setTimeout(() => {
                        modal.hide();
                        modalBackdrop.remove();
                    }, 1500);
                    // Refresh page after a short delay to update recent games
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                    return true;
                } else if (data.failed) {
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-danger');
                    progressText.textContent = 'Operation Failed';
                    progressDetails.textContent = data.message || 'An error occurred';
                    showToast(data.message || 'Save operation failed', 'error');
                    // Add close button on failure
                    const modalFooter = document.createElement('div');
                    modalFooter.className = 'modal-footer bg-primary border-secondary';
                    const closeBtn = document.createElement('button');
                    closeBtn.type = 'button';
                    closeBtn.className = 'btn btn-outline-secondary text-white';
                    closeBtn.textContent = 'Close';
                    closeBtn.onclick = () => {
                        modal.hide();
                        modalBackdrop.remove();
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
                    };
                    modalFooter.appendChild(closeBtn);
                    modalContent.appendChild(modalFooter);
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
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-warning');
                    progressText.textContent = 'Operation Timed Out';
                    progressDetails.textContent = 'The operation is taking longer than expected. Please check the operation status manually.';
                    showToast('Operation is taking longer than expected. Please refresh the page.', 'error');
                    // Add close button on timeout
                    const modalFooter = document.createElement('div');
                    modalFooter.className = 'modal-footer bg-primary border-secondary';
                    const closeBtn = document.createElement('button');
                    closeBtn.type = 'button';
                    closeBtn.className = 'btn btn-outline-secondary text-white';
                    closeBtn.textContent = 'Close';
                    closeBtn.onclick = () => {
                        modal.hide();
                        modalBackdrop.remove();
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
                    };
                    modalFooter.appendChild(closeBtn);
                    modalContent.appendChild(modalFooter);
                }
            }
        }, pollInterval);
    }

    // Show toast notification
    function showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        const alertType = type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info';
        toast.className = `alert alert-${alertType} alert-dismissible fade show position-fixed toast-container-custom`;
        
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

                // Handle 404 - game was deleted
                if (response.status === 404) {
                    showToast('Game not found (may have been deleted)', 'error');
                    // Restore button
                    btn.disabled = false;
                    while (btn.firstChild) {
                        btn.removeChild(btn.firstChild);
                    }
                    if (originalIcon) {
                        const iconClone = originalIcon.cloneNode(true);
                        btn.appendChild(iconClone);
                    }
                    btn.appendChild(document.createTextNode(' Save'));
                    // Reload page to refresh game list
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                    return;
                }

                const data = await response.json();

                if (data.success && data.operation_id) {
                    // Poll for operation completion
                    await pollOperationStatus(data.operation_id, btn, originalIcon, originalText);
                } else {
                    // Check if it's a "not found" error
                    if (response.status === 404 || (data.error && data.error.includes('not found'))) {
                        showToast('Game not found (may have been deleted)', 'error');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    } else {
                        showToast(data.error || data.message || 'Failed to save game', 'error');
                    }
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
                // First check if there are any save folders for this game (if URL pattern is available)
                const listFoldersUrlPattern = window.LIST_SAVE_FOLDERS_URL_PATTERN;
                if (listFoldersUrlPattern) {
                    try {
                        const listFoldersUrl = listFoldersUrlPattern.replace('/0/', `/${gameId}/`);
                        const foldersResponse = await fetch(listFoldersUrl, {
                            headers: { 'X-Requested-With': 'XMLHttpRequest' }
                        });
                        
                        // Handle 404 - game was deleted
                        if (foldersResponse.status === 404) {
                            showToast('Game not found (may have been deleted)', 'error');
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
                            // Reload page to refresh game list
                            setTimeout(() => {
                                window.location.reload();
                            }, 1500);
                            return;
                        }
                        
                        if (foldersResponse.ok) {
                            const foldersData = await foldersResponse.json();
                            if (!foldersData.success || !foldersData.save_folders || foldersData.save_folders.length === 0) {
                                // No save folders found - show friendly message
                                showToast('Oops! You have no save files to load', 'error');
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
                                return;
                            }
                        }
                    } catch (e) {
                        // If check fails, continue with load attempt - backend will handle it
                    }
                }
                
                // Proceed with load if save folders exist
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

                // Handle 404 - game was deleted
                if (response.status === 404) {
                    showToast('Game not found (may have been deleted)', 'error');
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
                    // Reload page to refresh game list
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                    return;
                }

                const data = await response.json();

                if (data.success && data.operation_id) {
                    // Poll for operation completion
                    await pollLoadOperationStatus(data.operation_id, btn, originalIcon);
                } else {
                    // Check if it's a "not found" error
                    if (response.status === 404 || (data.error && data.error.includes('not found'))) {
                        showToast('Game not found (may have been deleted)', 'error');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    } else if (data.error && (data.error.includes('No save folders') || data.error.includes('save folder'))) {
                        // Check if error is about no save folders
                        showToast('Oops! You have no save files to load', 'error');
                    } else {
                        showToast(data.error || data.message || 'Failed to load game', 'error');
                    }
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
        const maxAttempts = 300; // 300 attempts = 5 minutes max (1 second intervals)
        let attempts = 0;
        const pollInterval = 1000; // Poll every 1 second
        
        // Create modal for progress
        const modalId = `progressModal_${operationId}`;
        const modalBackdrop = document.createElement('div');
        modalBackdrop.className = 'modal fade';
        modalBackdrop.id = modalId;
        modalBackdrop.setAttribute('data-bs-backdrop', 'static');
        modalBackdrop.setAttribute('data-bs-keyboard', 'false');
        modalBackdrop.setAttribute('tabindex', '-1');
        modalBackdrop.setAttribute('aria-labelledby', `${modalId}Label`);
        modalBackdrop.setAttribute('aria-hidden', 'true');
        
        const modalDialog = document.createElement('div');
        modalDialog.className = 'modal-dialog modal-dialog-centered';
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content bg-primary text-white border-0';
        
        const modalHeader = document.createElement('div');
        modalHeader.className = 'modal-header bg-primary border-secondary';
        
        const modalTitle = document.createElement('h5');
        modalTitle.className = 'modal-title text-white';
        modalTitle.id = `${modalId}Label`;
        modalTitle.textContent = 'Loading Game';
        
        modalHeader.appendChild(modalTitle);
        
        const modalBody = document.createElement('div');
        modalBody.className = 'modal-body bg-primary';
        
        const progressBarWrapper = document.createElement('div');
        progressBarWrapper.className = 'progress mb-3';
        progressBarWrapper.style.height = '30px';
        progressBarWrapper.style.backgroundColor = getCSSVariable('--white-opacity-10');
        
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
        progressBar.setAttribute('role', 'progressbar');
        progressBar.style.width = '0%';
        progressBar.style.backgroundColor = getCSSVariable('--color-primary-bootstrap');
        progressBar.setAttribute('aria-valuenow', '0');
        progressBar.setAttribute('aria-valuemin', '0');
        progressBar.setAttribute('aria-valuemax', '100');
        
        const progressText = document.createElement('div');
        progressText.className = 'text-center mt-3 text-white fs-6 fw-medium';
        progressText.textContent = 'Starting...';
        
        const progressDetails = document.createElement('div');
        progressDetails.className = 'text-center text-white-50 mt-2 small';
        progressDetails.textContent = 'Please wait while the game loads...';
        
        progressBarWrapper.appendChild(progressBar);
        modalBody.appendChild(progressBarWrapper);
        modalBody.appendChild(progressText);
        modalBody.appendChild(progressDetails);
        
        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        modalDialog.appendChild(modalContent);
        modalBackdrop.appendChild(modalDialog);
        
        // Get next z-index for proper stacking
        const nextZIndex = getNextModalZIndex();
        modalBackdrop.style.zIndex = nextZIndex;
        
        // Add modal to body
        document.body.appendChild(modalBackdrop);
        
        // Show modal using Bootstrap
        const modal = new bootstrap.Modal(modalBackdrop, {
            backdrop: 'static',
            keyboard: false
        });
        
        // Set backdrop z-index after modal is shown (Bootstrap creates backdrop dynamically)
        modal._element.addEventListener('shown.bs.modal', function() {
            const backdrop = document.querySelector('.modal-backdrop:last-of-type');
            if (backdrop) {
                backdrop.style.zIndex = (nextZIndex - 10).toString();
            }
        }, { once: true });
        
        modal.show();
        
        const updateProgress = (progressData) => {
            const percentage = progressData.percentage || 0;
            const current = progressData.current || 0;
            const total = progressData.total || 0;
            const message = progressData.message || '';
            
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
            
            if (total > 0) {
                progressText.textContent = `${current}/${total} ${message || 'Processing...'}`;
                progressDetails.textContent = `${percentage}% complete`;
            } else if (message) {
                progressText.textContent = message;
                progressDetails.textContent = 'Processing...';
            } else {
                progressText.textContent = 'Processing...';
                progressDetails.textContent = 'Please wait...';
            }
        };
        
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
                
                // Update progress bar
                if (data.progress) {
                    updateProgress(data.progress);
                }
                
                if (data.completed) {
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-success');
                    progressBar.style.width = '100%';
                    progressBar.setAttribute('aria-valuenow', '100');
                    progressText.textContent = 'Operation Complete!';
                    progressDetails.textContent = 'Successfully completed';
                    showToast('Game loaded successfully!', 'success');
                    // Close modal after a delay
                    setTimeout(() => {
                        modal.hide();
                        modalBackdrop.remove();
                    }, 1500);
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
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-danger');
                    progressText.textContent = 'Operation Failed';
                    progressDetails.textContent = data.message || 'An error occurred';
                    showToast(data.message || 'Load operation failed', 'error');
                    // Add close button on failure
                    const modalFooter = document.createElement('div');
                    modalFooter.className = 'modal-footer bg-primary border-secondary';
                    const closeBtn = document.createElement('button');
                    closeBtn.type = 'button';
                    closeBtn.className = 'btn btn-outline-secondary text-white';
                    closeBtn.textContent = 'Close';
                    closeBtn.onclick = () => {
                        modal.hide();
                        modalBackdrop.remove();
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
                    };
                    modalFooter.appendChild(closeBtn);
                    modalContent.appendChild(modalFooter);
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
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-warning');
                    progressText.textContent = 'Operation Timed Out';
                    progressDetails.textContent = 'The operation is taking longer than expected. Please check the operation status manually.';
                    showToast('Operation is taking longer than expected. Please refresh the page.', 'error');
                    // Add close button on timeout
                    const modalFooter = document.createElement('div');
                    modalFooter.className = 'modal-footer bg-primary border-secondary';
                    const closeBtn = document.createElement('button');
                    closeBtn.type = 'button';
                    closeBtn.className = 'btn btn-outline-secondary text-white';
                    closeBtn.textContent = 'Close';
                    closeBtn.onclick = () => {
                        modal.hide();
                        modalBackdrop.remove();
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
                    };
                    modalFooter.appendChild(closeBtn);
                    modalContent.appendChild(modalFooter);
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

