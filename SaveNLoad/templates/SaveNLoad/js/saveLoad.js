document.addEventListener('DOMContentLoaded', function () {
    const csrfToken = window.getCsrfToken ? window.getCsrfToken() : null;

    if (!csrfToken) {
        console.error('CSRF token not found');
        return; // getCsrfToken already shows a toast
    }

    function normalizeOperationIds(data) {
        if (!data) {
            return [];
        }
        if (Array.isArray(data.operation_ids)) {
            return data.operation_ids;
        }
        if (Array.isArray(data.operationIds)) {
            return data.operationIds;
        }
        if (data.data && Array.isArray(data.data.operation_ids)) {
            return data.data.operation_ids;
        }
        if (typeof data.operation_ids === 'string') {
            return data.operation_ids.split(',').map(id => id.trim()).filter(Boolean);
        }
        if (data.operation_id) {
            return [data.operation_id];
        }
        if (data.data && data.data.operation_id) {
            return [data.data.operation_id];
        }
        return [];
    }

    // Poll operation status until completion
    async function pollOperationStatus(operationId, btn, originalIcon, originalText) {
        // Handle both single operation ID and array of operation IDs
        const isMultiple = Array.isArray(operationId);
        const operationIds = isMultiple ? operationId : [operationId];
        const totalOperations = operationIds.length;

        const maxAttempts = 300; // 300 attempts = 5 minutes max (1 second intervals)
        let attempts = 0;
        const pollInterval = 1000; // Poll every 1 second

        // Create modal for progress
        const modalId = `progressModal_${isMultiple ? 'multi_' + operationIds.join('_') : operationId}`;
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
        // Determine title based on operation type (save vs load)
        const isLoadOperation = originalText && originalText.includes('Load');
        modalTitle.textContent = isMultiple
            ? (isLoadOperation ? `Loading ${totalOperations} Location(s)...` : `Saving ${totalOperations} Location(s)...`)
            : (isLoadOperation ? 'Loading Game...' : 'Operation in Progress');

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
        progressDetails.textContent = isMultiple ? `Processing ${totalOperations} save location(s). Please wait...` : 'Please wait while the operation completes...';

        progressBarWrapper.appendChild(progressBar);
        modalBody.appendChild(progressBarWrapper);
        modalBody.appendChild(progressText);
        modalBody.appendChild(progressDetails);

        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        modalDialog.appendChild(modalContent);
        modalBackdrop.appendChild(modalDialog);

        // Get next z-index for proper stacking
        // Add modal to body
        document.body.appendChild(modalBackdrop);

        // Show modal using Bootstrap
        const modal = new bootstrap.Modal(modalBackdrop, {
            backdrop: 'static',
            keyboard: false
        });

        // Set backdrop z-index after modal is shown (Bootstrap creates backdrop dynamically)
        if (window.applyModalStacking) {
            window.applyModalStacking(modalBackdrop);
        }

        modal.show();

        // Track completion status for multiple operations
        const operationStatuses = {};
        if (isMultiple) {
            operationIds.forEach(id => {
                operationStatuses[id] = { completed: false, success: false };
            });
        }

        // Flag to prevent multiple completion handlers
        let completionHandled = false;

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
                if (isMultiple) {
                    // Check all operations and aggregate progress
                    const statusPromises = operationIds.map(async (opId) => {
                        if (operationStatuses[opId].completed) {
                            return operationStatuses[opId];
                        }

                        try {
                            const urlPattern = window.CHECK_OPERATION_STATUS_URL_PATTERN;
                            const url = urlPattern.replace('/0/', `/${opId}/`);
                            const response = await fetch(url, {
                                headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : { 'X-Requested-With': 'XMLHttpRequest' }
                            });

                            if (response.ok) {
                                const data = await response.json();
                                if (data.completed) {
                                    operationStatuses[opId] = {
                                        completed: true,
                                        success: !data.failed,
                                        message: data.message || null  // Store error message
                                    };
                                } else if (data.failed) {
                                    operationStatuses[opId] = {
                                        completed: true,
                                        success: false,
                                        message: data.message || null  // Store error message
                                    };
                                } else {
                                    // Store progress data for real-time updates
                                    if (data.progress) {
                                        operationStatuses[opId].progress = data.progress;
                                    }
                                }
                            }
                        } catch (error) {
                            console.error(`Error checking operation ${opId} status:`, error);
                        }

                        return operationStatuses[opId];
                    });

                    await Promise.all(statusPromises);

                    // Aggregate progress from all active operations
                    const activeOperations = Object.entries(operationStatuses)
                        .filter(([id, status]) => !status.completed && status.progress)
                        .map(([id, status]) => status.progress);

                    if (activeOperations.length > 0) {
                        // Calculate aggregated progress
                        let totalCurrent = 0;
                        let totalTotal = 0;
                        let latestMessage = '';

                        activeOperations.forEach(progress => {
                            if (progress.current !== undefined && progress.total !== undefined) {
                                totalCurrent += progress.current || 0;
                                totalTotal += progress.total || 0;
                            }
                            if (progress.message) {
                                latestMessage = progress.message;
                            }
                        });

                        // Update progress bar with aggregated data
                        if (totalTotal > 0) {
                            const percentage = Math.round((totalCurrent / totalTotal) * 100);
                            updateProgress({
                                current: totalCurrent,
                                total: totalTotal,
                                percentage: percentage,
                                message: latestMessage
                            });
                        } else if (latestMessage) {
                            updateProgress({
                                percentage: 0,
                                message: latestMessage
                            });
                        }
                    }

                    // Check if all operations are complete
                    const allCompleted = Object.values(operationStatuses).every(status => status.completed);
                    const allSuccessful = Object.values(operationStatuses).every(status => status.success);
                    const someSuccessful = Object.values(operationStatuses).some(status => status.success);
                    const completedCount = Object.values(operationStatuses).filter(s => s.completed).length;

                    // If no active progress data, show completion count
                    if (activeOperations.length === 0 && !allCompleted) {
                        const overallPercent = Math.round((completedCount / totalOperations) * 100);
                        progressBar.style.width = `${overallPercent}%`;
                        progressBar.setAttribute('aria-valuenow', overallPercent);
                        progressText.textContent = `Processing... (${completedCount}/${totalOperations} completed)`;
                        progressDetails.textContent = `${overallPercent}% complete`;
                    }

                    if (allCompleted && !completionHandled) {
                        completionHandled = true;
                        progressBar.classList.remove('progress-bar-animated');
                        if (allSuccessful) {
                            progressBar.style.backgroundColor = getCSSVariable('--color-success');
                            progressBar.style.width = '100%';
                            progressBar.setAttribute('aria-valuenow', '100');
                            progressText.textContent = 'All Operations Complete!';
                            const isLoadOperation = originalText && originalText.includes('Load');
                            progressDetails.textContent = isLoadOperation
                                ? `Successfully loaded ${totalOperations} location(s)`
                                : 'Game saved successfully!';
                            window.showToast(
                                isLoadOperation
                                    ? `Successfully loaded ${totalOperations} location(s)!`
                                    : 'Game saved successfully!',
                                'success'
                            );
                        } else if (someSuccessful) {
                            progressBar.style.backgroundColor = getCSSVariable('--color-warning');
                            progressText.textContent = 'Partially Complete';
                            progressDetails.textContent = 'Some locations saved successfully';
                            window.showToast('Partially completed. Some locations saved successfully.', 'warning');
                        } else {
                            progressBar.style.backgroundColor = getCSSVariable('--color-danger');
                            progressText.textContent = 'All Operations Failed';

                            // Collect error messages from failed operations
                            const errorMessages = Object.values(operationStatuses)
                                .filter(status => status.completed && !status.success && status.message)
                                .map(status => status.message);

                            // Show specific error message(s) if available, otherwise generic message
                            if (errorMessages.length > 0) {
                                // If all errors are the same, show it once; otherwise show first error
                                const uniqueErrors = [...new Set(errorMessages)];
                                const displayMessage = uniqueErrors.length === 1
                                    ? uniqueErrors[0]
                                    : uniqueErrors[0] + (uniqueErrors.length > 1 ? ` (and ${uniqueErrors.length - 1} more)` : '');
                                progressDetails.textContent = displayMessage;
                                window.showToast(displayMessage, 'error');
                            } else {
                                progressDetails.textContent = 'Save operation failed for all locations';
                                window.showToast('Save operation failed for all locations.', 'error');
                            }
                        }

                        // Close modal after a delay, then refresh page
                        setTimeout(() => {
                            modal.hide();
                            setTimeout(() => {
                                modalBackdrop.remove();
                                // Refresh page to update recent games
                                window.location.reload();
                            }, 300);
                        }, 1500);
                        return true;
                    }

                    return false;
                } else {
                    // Single operation - always use real-time progress
                    const urlPattern = window.CHECK_OPERATION_STATUS_URL_PATTERN;
                    const url = urlPattern.replace('/0/', `/${operationId}/`);
                    const response = await fetch(url, {
                        headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : { 'X-Requested-With': 'XMLHttpRequest' }
                    });

                    if (!response.ok) {
                        throw new Error('Failed to check operation status');
                    }

                    const data = await response.json();

                    // Always update progress bar with real-time data when available
                    if (data.progress) {
                        updateProgress(data.progress);
                    }

                    if (data.completed && !completionHandled) {
                        completionHandled = true;
                        progressBar.classList.remove('progress-bar-animated');
                        progressBar.style.backgroundColor = getCSSVariable('--color-success');
                        progressBar.style.width = '100%';
                        progressBar.setAttribute('aria-valuenow', '100');
                        progressText.textContent = 'Operation Complete!';
                        progressDetails.textContent = 'Successfully completed';
                        const isLoadOperation = originalText && originalText.includes('Load');
                        window.showToast(
                            isLoadOperation ? 'Game loaded successfully!' : 'Game saved successfully!',
                            'success'
                        );
                        // Close modal after a delay, then refresh page
                        setTimeout(() => {
                            modal.hide();
                            setTimeout(() => {
                                modalBackdrop.remove();
                                // Refresh page to update recent games
                                window.location.reload();
                            }, 300);
                        }, 1500);
                        return true;
                    } else if (data.failed) {
                        progressBar.classList.remove('progress-bar-animated');
                        progressBar.style.backgroundColor = getCSSVariable('--color-danger');
                        progressText.textContent = 'Operation Failed';
                        progressDetails.textContent = data.message || 'An error occurred';
                        window.showToast(data.message || 'Save operation failed', 'error');
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
                }
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
                    window.showToast('Operation is taking longer than expected. Please refresh the page.', 'error');
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

    // Poll multiple operation statuses until all complete
    async function pollMultipleOperationStatus(operationIds, btn, originalIcon, originalText, totalPaths) {
        const maxAttempts = 300; // 300 attempts = 5 minutes max (1 second intervals)
        let attempts = 0;
        const pollInterval = 1000; // Poll every 1 second

        // Create modal for progress
        const modalId = `progressModal_multi_${operationIds.join('_')}`;
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
        modalTitle.textContent = `Saving ${totalPaths} Location(s)...`;

        modalHeader.appendChild(modalTitle);

        const modalBody = document.createElement('div');
        modalBody.className = 'modal-body bg-primary';

        const progressBarWrapper = document.createElement('div');
        progressBarWrapper.className = 'progress mb-3';
        progressBarWrapper.style.height = '30px';

        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
        progressBar.setAttribute('role', 'progressbar');
        progressBar.style.width = '0%';
        progressBar.style.backgroundColor = '#28a745';
        progressBar.setAttribute('aria-valuenow', '0');
        progressBar.setAttribute('aria-valuemin', '0');
        progressBar.setAttribute('aria-valuemax', '100');

        const progressText = document.createElement('div');
        progressText.className = 'text-center mt-3 text-white fs-6 fw-medium';
        progressText.textContent = 'Starting...';

        const progressDetails = document.createElement('div');
        progressDetails.className = 'text-center text-white-50 mt-2 small';
        progressDetails.textContent = `Processing ${totalPaths} save location(s). Please wait...`;

        progressBarWrapper.appendChild(progressBar);
        modalBody.appendChild(progressBarWrapper);
        modalBody.appendChild(progressText);
        modalBody.appendChild(progressDetails);

        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        modalDialog.appendChild(modalContent);
        modalBackdrop.appendChild(modalDialog);

        document.body.appendChild(modalBackdrop);

        const modal = new bootstrap.Modal(modalBackdrop, {
            backdrop: 'static',
            keyboard: false
        });
        modal.show();

        // Track completion status for each operation
        const operationStatuses = {};
        operationIds.forEach(id => {
            operationStatuses[id] = { completed: false, success: false };
        });

        const pollStatus = async () => {
            attempts++;

            if (attempts > maxAttempts) {
                modal.hide();
                setTimeout(() => modalBackdrop.remove(), 300);
                window.showToast('Operation timed out. Please check the status manually.', 'error');
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
                return;
            }

            // Poll all operations
            const statusPromises = operationIds.map(async (opId) => {
                if (operationStatuses[opId].completed) {
                    return operationStatuses[opId];
                }

                try {
                    const statusUrl = window.CHECK_OPERATION_STATUS_URL_PATTERN.replace('/0/', `/${opId}/`);
                    const statusResponse = await fetch(statusUrl, {
                        headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : { 'X-Requested-With': 'XMLHttpRequest' }
                    });

                    if (statusResponse.ok) {
                        const statusData = await statusResponse.json();
                        if (statusData.status === 'completed') {
                            operationStatuses[opId] = { completed: true, success: statusData.success || false };
                        } else if (statusData.status === 'failed') {
                            operationStatuses[opId] = { completed: true, success: false };
                        } else if (statusData.progress) {
                            // Update progress if available
                            const progress = statusData.progress;
                            if (progress.current !== undefined && progress.total !== undefined) {
                                const percent = Math.round((progress.current / progress.total) * 100);
                                progressBar.style.width = `${percent}%`;
                                progressBar.setAttribute('aria-valuenow', percent);
                                if (progress.message) {
                                    progressText.textContent = progress.message;
                                }
                            }
                        }
                    }
                } catch (error) {
                    console.error(`Error checking operation ${opId} status:`, error);
                }

                return operationStatuses[opId];
            });

            await Promise.all(statusPromises);

            // Check if all operations are complete
            const allCompleted = Object.values(operationStatuses).every(status => status.completed);
            const allSuccessful = Object.values(operationStatuses).every(status => status.success);
            const someSuccessful = Object.values(operationStatuses).some(status => status.success);

            if (allCompleted) {
                modal.hide();
                setTimeout(() => modalBackdrop.remove(), 300);

                if (allSuccessful) {
                    window.showToast('Game saved successfully!', 'success');
                } else if (someSuccessful) {
                    window.showToast(`Partially completed. Some locations saved successfully.`, 'warning');
                } else {
                    window.showToast('Save operation failed for all locations.', 'error');
                }

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
            } else {
                // Update progress based on completed operations
                const completedCount = Object.values(operationStatuses).filter(s => s.completed).length;
                const overallPercent = Math.round((completedCount / totalPaths) * 100);
                progressBar.style.width = `${overallPercent}%`;
                progressBar.setAttribute('aria-valuenow', overallPercent);
                progressText.textContent = `Processing... (${completedCount}/${totalPaths} completed)`;

                setTimeout(pollStatus, pollInterval);
            }
        };

        // Start polling
        setTimeout(pollStatus, pollInterval);
    }

    // Uses shared utility functions from utils.js

    // Handle Save button clicks
    document.addEventListener('click', async function (e) {
        if (e.target.closest('.save-game-btn')) {
            e.preventDefault();
            e.stopPropagation();

            const btn = e.target.closest('.save-game-btn');
            const gameId = btn.dataset.gameId;

            if (!gameId) {
                window.showToast('Error: Game ID not found', 'error');
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
                // Get save paths from global object
                let gameSavePaths = [];
                if (window.GAME_SAVE_PATHS && window.GAME_SAVE_PATHS[gameId]) {
                    gameSavePaths = window.GAME_SAVE_PATHS[gameId].filter(path => path && path.trim());
                }

                const urlPattern = window.SAVE_GAME_URL_PATTERN;
                const url = urlPattern.replace('/0/', `/${gameId}/`);

                // Always explicitly send local_save_paths in AJAX request
                const payload = {
                    local_save_paths: gameSavePaths
                };

                const response = await fetch(url, {
                    method: 'POST',
                    headers: window.createFetchHeaders ? window.createFetchHeaders(csrfToken) : {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify(payload)
                });

                // Handle 404 - game was deleted
                if (response.status === 404) {
                    window.showToast('Game not found (may have been deleted)', 'error');
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

                // Handle both single operation_id and multiple operation_ids
                if (data.success) {
                    const operationIds = normalizeOperationIds(data);
                    if (operationIds.length > 1) {
                        // Multiple operations (multi-path save) - pass array
                        await pollOperationStatus(operationIds, btn, originalIcon, originalText);
                    } else if (operationIds.length === 1) {
                        // Single operation - existing behavior
                        await pollOperationStatus(operationIds[0], btn, originalIcon, originalText);
                    } else {
                        // Success but no operation ID (shouldn't happen, but handle gracefully)
                        window.showToast(data.message || 'Save operation completed', 'success');
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
                    }
                } else {
                    // Check if it's a "not found" error
                    if (response.status === 404 || (data.error && data.error.includes('not found'))) {
                        window.showToast('Game not found (may have been deleted)', 'error');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    } else {
                        window.showToast(data.error || data.message || 'Failed to save game', 'error');
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
                window.showToast('Error: Failed to save game. Please try again.', 'error');
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
                window.showToast('Error: Game ID not found', 'error');
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
                            headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : { 'X-Requested-With': 'XMLHttpRequest' }
                        });

                        // Handle 404 - game was deleted
                        if (foldersResponse.status === 404) {
                            window.showToast('Game not found (may have been deleted)', 'error');
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
                                window.showToast('Oops! You have no save files to load', 'error');
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
                    window.showToast('Game not found (may have been deleted)', 'error');
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

                // Handle both single operation_id and multiple operation_ids
                if (data.success) {
                    const operationIds = normalizeOperationIds(data);
                    if (operationIds.length > 1) {
                        // Multiple operations (multi-path load) - pass array
                        const originalText = ' Quick Load';
                        await pollOperationStatus(operationIds, btn, originalIcon, originalText);
                    } else if (operationIds.length === 1) {
                        // Single operation - use shared pollOperationStatus function
                        const originalText = ' Quick Load';
                        await pollOperationStatus(operationIds[0], btn, originalIcon, originalText);
                    } else {
                        // Success but no operation ID (shouldn't happen, but handle gracefully)
                        window.showToast(data.message || 'Load operation completed', 'success');
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
                    }
                } else {
                    // Check if it's a "not found" error
                    if (response.status === 404 || (data.error && data.error.includes('not found'))) {
                        window.showToast('Game not found (may have been deleted)', 'error');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    } else if (data.error && (data.error.includes('No save folders') || data.error.includes('save folder'))) {
                        // Check if error is about no save folders
                        window.showToast('Oops! You have no save files to load', 'error');
                    } else {
                        window.showToast(data.error || data.message || 'Failed to load game', 'error');
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
                window.showToast('Error: Failed to load game. Please try again.', 'error');
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
        // Add modal to body
        document.body.appendChild(modalBackdrop);

        // Show modal using Bootstrap
        const modal = new bootstrap.Modal(modalBackdrop, {
            backdrop: 'static',
            keyboard: false
        });

        // Set backdrop z-index after modal is shown (Bootstrap creates backdrop dynamically)
        if (window.applyModalStacking) {
            window.applyModalStacking(modalBackdrop);
        }

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
                    window.showToast('Game loaded successfully!', 'success');
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
                    window.showToast(data.message || 'Load operation failed', 'error');
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
                    window.showToast('Operation is taking longer than expected. Please refresh the page.', 'error');
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

