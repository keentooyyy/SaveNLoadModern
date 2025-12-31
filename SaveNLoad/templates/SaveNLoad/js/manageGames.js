// Store references for openGameEditModal function
let modalInstance = null;
let currentDetailUrlRef = null;
let currentDeleteUrlRef = null;
let formRef = null;
let bannerPreviewRef = null;
let loadGameRef = null;
let loadSaveFoldersRef = null;

// Expose function to open modal programmatically
// This function is available immediately, but will only work after DOMContentLoaded
window.openGameEditModal = function (gameId, hideSavesTab = false) {
    if (!modalInstance) {
        console.error('Modal not initialized yet. Please wait for page to load.');
        return;
    }

    // Construct detail URL using Django URL pattern
    if (window.GAME_DETAIL_URL_PATTERN) {
        currentDetailUrlRef = window.GAME_DETAIL_URL_PATTERN.replace('0', gameId);
    } else {
        console.error('GAME_DETAIL_URL_PATTERN not defined');
        return;
    }
    if (window.GAME_DELETE_URL_PATTERN) {
        currentDeleteUrlRef = window.GAME_DELETE_URL_PATTERN.replace('0', gameId);
    }

    // Reset form state
    if (formRef) {
        formRef.reset();
    }
    // Clear save locations using manager
    manageSaveLocationManager.populateLocations('');
    // Clear banner preview
    const bannerPreviewEl = document.getElementById('manage_banner_preview');
    if (bannerPreviewEl) {
        clearElement(bannerPreviewEl);
    }

    // Update modal title
    const modalTitle = document.getElementById('gameManageModalLabel');
    if (modalTitle) {
        modalTitle.textContent = 'Edit Game';
    }

    // Hide/show saves tab
    const savesTabContainer = document.getElementById('saves-tab-container');
    if (savesTabContainer) {
        if (hideSavesTab) {
            savesTabContainer.classList.add('d-none');
        } else {
            savesTabContainer.classList.remove('d-none');
        }
    }

    // Load game details (don't load save folders if hiding saves tab)
    if (hideSavesTab) {
        if (loadGameRef) {
            loadGameRef(currentDetailUrlRef, true).then(function () {
                // Ensure buttons are visible when only edit tab is available
                const editTabButtons = document.getElementById('edit-tab-buttons');
                const saveGameBtn = document.getElementById('saveGameBtn');
                if (editTabButtons) editTabButtons.classList.remove('d-none');
                if (saveGameBtn) saveGameBtn.classList.remove('d-none');
                modalInstance.show();
            });
        }
    } else {
        if (loadGameRef && loadSaveFoldersRef) {
            Promise.all([
                loadGameRef(currentDetailUrlRef, false),
                loadSaveFoldersRef(gameId)
            ]).then(function () {
                // Ensure buttons are shown/hidden based on initial active tab
                const editPane = document.getElementById('edit-pane');
                const savesPane = document.getElementById('saves-pane');
                const editTabButtons = document.getElementById('edit-tab-buttons');
                const saveGameBtn = document.getElementById('saveGameBtn');

                if (editPane && savesPane && editTabButtons && saveGameBtn) {
                    if (editPane.classList.contains('active') && editPane.classList.contains('show')) {
                        editTabButtons.classList.remove('d-none');
                        saveGameBtn.classList.remove('d-none');
                    } else if (savesPane.classList.contains('active') && savesPane.classList.contains('show')) {
                        editTabButtons.classList.add('d-none');
                        saveGameBtn.classList.add('d-none');
                    }
                }
                modalInstance.show();
            });
        }
    }
};

document.addEventListener('DOMContentLoaded', function () {
    const section = document.getElementById('availableGamesSection');
    const modalElement = document.getElementById('gameManageModal');

    if (!section || !modalElement || !window.bootstrap) {
        return;
    }

    const modal = window.bootstrap.Modal.getOrCreateInstance(modalElement);
    modalInstance = modal; // Store reference

    const form = document.getElementById('gameManageForm');
    formRef = form; // Store reference
    const idInput = document.getElementById('manage_game_id');
    const nameInput = document.getElementById('manage_name');
    const bannerInput = document.getElementById('manage_banner');
    const saveFileLocationInput = document.getElementById('manage_save_file_location');
    const bannerPreview = document.getElementById('manage_banner_preview');
    bannerPreviewRef = bannerPreview; // Store reference

    const csrfToken = window.getCsrfToken ? window.getCsrfToken() : null;

    let currentCard = null;
    // Use the refs directly so they stay in sync
    currentDetailUrlRef = null;
    currentDeleteUrlRef = null;

    // Initialize save location manager for modal
    const manageSaveLocationManager = new SaveLocationManager('manage_save_locations_container');

    // Wrapper functions for inline handlers in template
    window.addManageSaveLocation = function () {
        manageSaveLocationManager.addLocation();
    };

    window.removeManageSaveLocation = function (btn) {
        manageSaveLocationManager.removeLocation(btn);
    };

    // Update loadGame function
    const loadGame = async function (detailUrl, hideSavesTab = false) {
        try {
            const response = await fetch(detailUrl, {
                headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : { 'X-Requested-With': 'XMLHttpRequest' }
            });

            // Handle 404 - game was deleted
            if (response.status === 404) {
                console.warn('Game not found (may have been deleted)');
                // Close modal if open
                if (modalInstance) {
                    modalInstance.hide();
                }
                // Reload page to refresh game list
                window.location.reload();
                return;
            }

            const data = await response.json();
            if (!response.ok) {
                // Handle other errors
                if (response.status === 404 || (data.error && data.error.includes('not found'))) {
                    console.warn('Game not found (may have been deleted)');
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                    window.location.reload();
                    return;
                }
                console.error('Failed to load game:', data);
                return;
            }

            idInput.value = data.id || '';
            nameInput.value = data.name || '';
            // Use banner_url (original URL) for input field, banner (display URL) for preview
            bannerInput.value = data.banner_url || data.banner || '';
            // Use manager to populate save locations
            // Handle both old format (string) and new format (array)
            let saveLocationStr = '';
            if (data.save_file_locations && Array.isArray(data.save_file_locations)) {
                saveLocationStr = data.save_file_locations.join('\n');
            } else if (data.save_file_location) {
                // Fallback for old format
                saveLocationStr = data.save_file_location;
            }
            manageSaveLocationManager.populateLocations(saveLocationStr);
            // Use shared updateBannerPreview function with display URL
            updateBannerPreview('manage_banner_preview', data.banner || data.banner_url || '');

            // Hide/show saves tab based on flag
            const savesTabContainer = document.getElementById('saves-tab-container');
            if (savesTabContainer) {
                if (hideSavesTab) {
                    savesTabContainer.classList.add('d-none');
                } else {
                    savesTabContainer.classList.remove('d-none');
                }
            }
        } catch (e) {
            console.error('Error loading game:', e);
            // If it's a network error and modal is open, close it
            if (modalInstance) {
                modalInstance.hide();
            }
        }
    };
    loadGameRef = loadGame; // Store reference

    async function saveGame() {
        if (!currentDetailUrlRef) return;
        if (!csrfToken) {
            window.showToast('Error: CSRF token not found', 'error');
            return;
        }

        // Get all save locations as array (not string with \n)
        const saveLocations = manageSaveLocationManager.getAllLocations();
        const filteredLocations = saveLocations.filter(loc => loc && loc.trim());

        const duplicateLocations = manageSaveLocationManager.getDuplicateLocations();
        if (duplicateLocations.length > 0) {
            window.showToast('Duplicate save file locations are not allowed.', 'error');
            return;
        }

        if (filteredLocations.length === 0) {
            window.showToast('At least one save file location is required', 'error');
            return;
        }

        // Build payload with array of locations
        const payload = {
            name: nameInput.value.trim(),
            banner: bannerInput.value.trim(),
            save_file_locations: filteredLocations  // Send as array, not string
        };

        try {
            const response = await fetch(currentDetailUrlRef, {
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
                if (modalInstance) {
                    modalInstance.hide();
                }
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
                return;
            }

            const data = await response.json();
            if (!response.ok || !data.success) {
                // Check if it's a "not found" error
                if (response.status === 404 || (data.error && data.error.includes('not found'))) {
                    window.showToast('Game not found (may have been deleted)', 'error');
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                    return;
                }
                window.showToast(data.error || data.message || 'Failed to save game', 'error');
                return;
            }

            // Easiest: refresh the page so cards reflect the new data
            window.location.reload();
        } catch (e) {
            console.error('Error saving game:', e);
            window.showToast('Error: Failed to save game. Please try again.', 'error');
        }
    }

    // Uses shared utility functions from utils.js

    async function deleteGame() {
        if (!currentDeleteUrlRef || !currentDetailUrlRef) return;
        if (!csrfToken) {
            window.showToast('Error: CSRF token not found', 'error');
            return;
        }

        const confirmed = await customConfirm('Are you sure you want to delete this game? This cannot be undone.');
        if (!confirmed) {
            return;
        }

        // Extract game ID from the delete URL
        const gameIdMatch = currentDeleteUrlRef.match(/\/games\/(\d+)\//);
        if (!gameIdMatch) {
            window.showToast('Error: Could not determine game ID', 'error');
            return;
        }
        const gameId = gameIdMatch[1];

        // Close the edit modal first
        if (modalInstance) {
            modalInstance.hide();
        }

        // Show progress modal
        const modalData = createProgressModal(`delete_game_${gameId}`, 'Deleting Game', 'delete');
        const { modal, modalBackdrop, updateProgress, progressBar, progressText, progressDetails } = modalData;

        // Update progress to show initial state
        updateProgress({
            percentage: 10,
            current: 0,
            total: 1,
            message: 'Initiating deletion...'
        });

        try {
            // Make delete request
            const response = await fetch(currentDeleteUrlRef, {
                method: 'POST',
                headers: window.createFetchHeaders ? window.createFetchHeaders(csrfToken) : {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                }
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                const errorMsg = data.error || data.message || 'Failed to delete game';
                modal.hide();
                modalBackdrop.remove();
                window.showToast(errorMsg, 'error');
                return;
            }

            // Update progress
            updateProgress({
                percentage: 30,
                current: 0,
                total: 1,
                message: 'Game deletion queued...'
            });

            // Poll for game deletion completion by checking operation status
            const maxAttempts = 300; // 5 minutes max (1 second intervals)
            let attempts = 0;
            const pollInterval = 1000; // 1 second

            const checkGameDeletionStatus = async () => {
                try {
                    const checkResponse = await fetch(currentDetailUrlRef, {
                        headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : { 'X-Requested-With': 'XMLHttpRequest' }
                    });

                    // If 404, game is deleted (all operations completed)
                    if (checkResponse.status === 404) {
                        return { deleted: true, operations: null };
                    }

                    // If response is ok, check operation status
                    if (checkResponse.ok) {
                        const checkData = await checkResponse.json();
                        const ops = checkData.deletion_operations || {};

                        // If no operations exist and game is not pending deletion, something went wrong
                        if (!checkData.pending_deletion && (!ops.total || ops.total === 0)) {
                            return { deleted: false, operations: null, error: 'No deletion operations found' };
                        }

                        // Return operation status
                        return {
                            deleted: false,
                            operations: {
                                total: ops.total || 0,
                                pending: ops.pending || 0,
                                completed: ops.completed || 0,
                                failed: ops.failed || 0,
                                progress_percentage: ops.progress_percentage || 0,
                            },
                            pending_deletion: checkData.pending_deletion || false
                        };
                    }

                    return { deleted: false, operations: null, error: 'Failed to check status' };
                } catch (error) {
                    console.error('Error checking game deletion status:', error);
                    return { deleted: false, operations: null, error: error.message };
                }
            };

            // Helper function to handle deletion completion
            const handleDeletionComplete = () => {
                updateProgress({
                    percentage: 100,
                    current: 1,
                    total: 1,
                    message: 'Game deleted successfully!'
                });

                progressBar.classList.remove('progress-bar-animated');
                progressBar.style.backgroundColor = getCSSVariable('--color-success');
                progressText.textContent = 'Game Deleted Successfully!';
                progressDetails.textContent = 'The game has been removed from the system';

                setTimeout(() => {
                    modal.hide();
                    modalBackdrop.remove();
                    window.location.reload();
                }, 1500);
            };

            // Initial check before starting polling
            const initialStatus = await checkGameDeletionStatus();
            if (initialStatus.deleted) {
                handleDeletionComplete();
                return;
            }

            // Poll until all operations complete and game is deleted
            const poll = setInterval(async () => {
                attempts++;
                const status = await checkGameDeletionStatus();

                if (status.deleted) {
                    // Game is deleted - all operations completed
                    clearInterval(poll);
                    handleDeletionComplete();
                } else if (status.operations) {
                    const ops = status.operations;

                    // Update progress based on actual operation status
                    if (ops.total > 0) {
                        // Show progress based on completed operations
                        const baseProgress = 30; // Start at 30% after queuing
                        const operationProgress = Math.min(ops.progress_percentage, 100);
                        const overallProgress = baseProgress + Math.floor((operationProgress * 0.7)); // Use 70% of remaining progress

                        updateProgress({
                            percentage: overallProgress,
                            current: ops.completed,
                            total: ops.total,
                            message: ops.pending > 0 ? 'Deleting FTP files...' : 'Finalizing deletion...'
                        });

                        // Update progress text with actual counts
                        if (ops.pending > 0) {
                            progressText.textContent = `${ops.completed}/${ops.total} operations completed`;
                            progressDetails.textContent = `${ops.pending} operation(s) remaining...`;
                        } else if (ops.failed > 0) {
                            // Some operations failed - game will NOT be deleted, but some FTP files may have been deleted
                            clearInterval(poll);
                            progressBar.classList.remove('progress-bar-animated');
                            progressBar.style.backgroundColor = getCSSVariable('--color-danger');
                            progressText.textContent = 'Deletion Cancelled';
                            progressDetails.textContent = `${ops.failed} operation(s) failed. The game will not be deleted. Note: Some FTP files may have been deleted for operations that succeeded.`;
                            setTimeout(() => {
                                modal.hide();
                                modalBackdrop.remove();
                                window.showToast(`Game deletion cancelled. ${ops.failed} FTP cleanup operation(s) failed. The game has been kept in the database.`, 'error');
                            }, 4000);
                            return;
                        } else {
                            // All operations completed, waiting for game deletion
                            updateProgress({
                                percentage: 95,
                                current: ops.total,
                                total: ops.total,
                                message: 'All operations completed, finalizing...'
                            });
                            progressText.textContent = `All ${ops.total} operation(s) completed`;
                            progressDetails.textContent = 'Finalizing game deletion...';
                        }
                    } else if (status.pending_deletion) {
                        // Game marked for deletion but no operations yet (shouldn't happen, but handle it)
                        updateProgress({
                            percentage: 40,
                            current: 0,
                            total: 1,
                            message: 'Processing deletion...'
                        });
                    }
                } else if (status.error) {
                    // Error checking status
                    console.error('Error checking deletion status:', status.error);
                }

                // Timeout check
                if (attempts >= maxAttempts) {
                    clearInterval(poll);
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-warning');
                    progressText.textContent = 'Deletion Taking Longer Than Expected';
                    progressDetails.textContent = 'The game deletion is still processing. The page will reload to show updated status.';

                    setTimeout(() => {
                        modal.hide();
                        modalBackdrop.remove();
                        window.location.reload();
                    }, 2000);
                }
            }, pollInterval);
        } catch (e) {
            console.error('Error deleting game:', e);
            modal.hide();
            modalBackdrop.remove();
            window.showToast('Error: Failed to delete game. Please try again.', 'error');
        }
    }

    function formatDate(dateString) {
        const date = new Date(dateString);
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const month = months[date.getMonth()];
        const day = date.getDate();
        const year = date.getFullYear();
        let hours = date.getHours();
        const minutes = date.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12;
        hours = hours ? hours : 12;
        const minutesStr = minutes < 10 ? '0' + minutes : minutes;
        return `${month}, ${day}, ${year} ${hours}:${minutesStr} ${ampm}`;
    }

    function createLoadingState() {
        const wrapper = document.createElement('div');
        wrapper.className = 'text-center py-4';

        const spinner = document.createElement('div');
        spinner.className = 'spinner-border text-secondary';
        spinner.setAttribute('role', 'status');
        const spinnerSpan = document.createElement('span');
        spinnerSpan.className = 'visually-hidden';
        spinnerSpan.appendChild(document.createTextNode('Loading...'));
        spinner.appendChild(spinnerSpan);

        const text = document.createElement('p');
        text.className = 'text-white-50 mt-2';
        text.appendChild(document.createTextNode('Loading saves...'));

        wrapper.appendChild(spinner);
        wrapper.appendChild(text);
        return wrapper;
    }

    function createErrorMessage(message) {
        const wrapper = document.createElement('div');
        wrapper.className = 'text-center py-4';
        const text = document.createElement('p');
        text.className = 'text-white-50';
        text.appendChild(document.createTextNode(message));
        wrapper.appendChild(text);
        return wrapper;
    }

    const loadSaveFolders = async function (gameId) {
        const container = document.getElementById('savesListContainer');
        if (!container) return;

        clearElement(container);
        container.appendChild(createLoadingState());

        try {
            const urlPattern = window.LIST_SAVE_FOLDERS_URL_PATTERN;
            const url = urlPattern.replace('/0/', `/${gameId}/`);
            const response = await fetch(url, {
                headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : { 'X-Requested-With': 'XMLHttpRequest' }
            });

            // Handle 404 - game was deleted
            if (response.status === 404) {
                console.warn('Game not found (may have been deleted)');
                clearElement(container);
                container.appendChild(createErrorMessage('Game not found'));
                // Close modal if open and reload page after a short delay
                if (modalInstance) {
                    setTimeout(() => {
                        modalInstance.hide();
                        window.location.reload();
                    }, 1500);
                } else {
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                }
                return;
            }

            const data = await response.json();

            if (!response.ok || !data.success) {
                // Check if it's a "not found" error
                if (response.status === 404 || (data.error && (data.error.includes('not found') || data.error.includes('Game not found')))) {
                    console.warn('Game not found (may have been deleted)');
                    clearElement(container);
                    container.appendChild(createErrorMessage('Game not found'));
                    if (modalInstance) {
                        setTimeout(() => {
                            modalInstance.hide();
                            window.location.reload();
                        }, 1500);
                    } else {
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    }
                    return;
                }
                clearElement(container);
                container.appendChild(createErrorMessage(data.error || 'Failed to load saves'));
                return;
            }

            // Always create button container, even if no saves
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'mb-3 d-flex justify-content-between align-items-center gap-2';

            // Open folder button on the left - always show
            const openFolderButton = document.createElement('button');
            openFolderButton.className = 'btn btn-info text-white';
            openFolderButton.type = 'button';
            const folderIcon = document.createElement('i');
            folderIcon.className = 'fas fa-folder-open me-2';
            openFolderButton.appendChild(folderIcon);
            openFolderButton.appendChild(document.createTextNode('Open Save Location'));
            openFolderButton.addEventListener('click', function () {
                openSaveLocation(gameId);
            });
            buttonContainer.appendChild(openFolderButton);

            // Right side button container
            const rightButtonContainer = document.createElement('div');
            rightButtonContainer.className = 'd-flex gap-2';

            // Only show backup/delete buttons if there are saves
            if (data.save_folders && data.save_folders.length > 0) {
                const backupButton = document.createElement('button');
                backupButton.className = 'btn btn-secondary text-white';
                backupButton.type = 'button';
                const backupIcon = document.createElement('i');
                backupIcon.className = 'fas fa-download me-2';
                backupButton.appendChild(backupIcon);
                backupButton.appendChild(document.createTextNode('Backup All Saves'));
                backupButton.addEventListener('click', function () {
                    backupAllSaves(gameId);
                });
                rightButtonContainer.appendChild(backupButton);

                const deleteButton = document.createElement('button');
                deleteButton.className = 'btn btn-danger text-white';
                deleteButton.type = 'button';
                const deleteIcon = document.createElement('i');
                deleteIcon.className = 'fas fa-trash me-2';
                deleteButton.appendChild(deleteIcon);
                deleteButton.appendChild(document.createTextNode('Delete All Saves'));
                deleteButton.addEventListener('click', function () {
                    deleteAllSaves(gameId);
                });
                rightButtonContainer.appendChild(deleteButton);
            }

            buttonContainer.appendChild(rightButtonContainer);

            if (!data.save_folders || data.save_folders.length === 0) {
                clearElement(container);
                container.appendChild(buttonContainer);
                container.appendChild(createErrorMessage('No saves available'));
                return;
            }

            const listGroup = document.createElement('div');
            listGroup.className = 'list-group';

            data.save_folders.forEach(folder => {
                const item = document.createElement('div');
                item.className = 'list-group-item bg-primary text-white border-secondary transition-bg list-group-item-hover';
                item.dataset.folderNumber = folder.folder_number;

                const row = document.createElement('div');
                row.className = 'd-flex justify-content-between align-items-center';

                const leftDiv = document.createElement('div');
                const folderName = document.createElement('h6');
                folderName.className = 'mb-1 text-white';
                folderName.appendChild(document.createTextNode(`Save ${folder.folder_number}`));
                const dateText = document.createElement('small');
                dateText.className = 'text-white-50';
                dateText.appendChild(document.createTextNode(formatDate(folder.created_at)));
                leftDiv.appendChild(folderName);
                leftDiv.appendChild(dateText);

                const buttonGroup = document.createElement('div');
                buttonGroup.className = 'd-flex gap-2';

                const loadBtn = document.createElement('button');
                loadBtn.className = 'btn btn-sm btn-secondary text-white';
                const loadIcon = document.createElement('i');
                loadIcon.className = 'fas fa-download me-1';
                loadBtn.appendChild(loadIcon);
                loadBtn.appendChild(document.createTextNode('Load'));
                loadBtn.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    loadSelectedSave(gameId, folder.folder_number);
                });

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn btn-sm btn-outline-danger text-white';
                const deleteIcon = document.createElement('i');
                deleteIcon.className = 'fas fa-trash me-1';
                deleteBtn.appendChild(deleteIcon);
                deleteBtn.appendChild(document.createTextNode('Delete'));
                deleteBtn.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    deleteSaveFolder(gameId, folder.folder_number);
                });

                buttonGroup.appendChild(loadBtn);
                buttonGroup.appendChild(deleteBtn);

                row.appendChild(leftDiv);
                row.appendChild(buttonGroup);
                item.appendChild(row);
                listGroup.appendChild(item);
            });

            clearElement(container);
            container.appendChild(buttonContainer);
            container.appendChild(listGroup);
        } catch (error) {
            console.error('Error loading save folders:', error);
            clearElement(container);
            container.appendChild(createErrorMessage('Error loading saves'));
        }
    };
    loadSaveFoldersRef = loadSaveFolders; // Store reference

    // Shared function to create progress modal matching app aesthetics
    function createProgressModal(operationId, title, operationType = 'operation') {
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
        modalTitle.textContent = title;

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

        // Add modal to body
        document.body.appendChild(modalBackdrop);

        // Show modal using Bootstrap
        const modal = new bootstrap.Modal(modalBackdrop, {
            backdrop: 'static',
            keyboard: false
        });

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

        return { modal, modalBackdrop, modalContent, updateProgress, progressBar, progressText, progressDetails };
    }

    // Shared function to poll operation status
    async function pollOperationStatus(operationId, modalData, onComplete, onError) {
        const maxAttempts = 300; // 5 minutes max
        let attempts = 0;
        const pollInterval = 1000; // 1 second

        const { modal, modalBackdrop, modalContent, updateProgress, progressBar, progressText, progressDetails } = modalData;

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
                    const handleHidden = () => {
                        modalBackdrop.remove();
                        if (onComplete) onComplete();
                    };
                    modal._element.addEventListener('hidden.bs.modal', handleHidden, { once: true });
                    setTimeout(() => {
                        modal.hide();
                    }, 1500);
                    return true;
                } else if (data.failed) {
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-danger');
                    progressText.textContent = 'Operation Failed';
                    progressDetails.textContent = data.message || 'An error occurred';
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
                        if (onError) onError();
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
                    const modalFooter = document.createElement('div');
                    modalFooter.className = 'modal-footer bg-primary border-secondary';
                    const closeBtn = document.createElement('button');
                    closeBtn.type = 'button';
                    closeBtn.className = 'btn btn-outline-secondary text-white';
                    closeBtn.textContent = 'Close';
                    closeBtn.onclick = () => {
                        modal.hide();
                        modalBackdrop.remove();
                        if (onError) onError();
                    };
                    modalContent.appendChild(modalFooter);
                }
            }
        }, pollInterval);
    }

    async function deleteSaveFolder(gameId, saveFolderNumber) {
        const csrfInput = document.querySelector('#gameCsrfForm input[name="csrfmiddlewaretoken"]') ||
            document.querySelector('#gameManageForm input[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfInput ? csrfInput.value : null;

        if (!csrfToken) {
            console.error('CSRF token not found');
            return;
        }

        const confirmed = await customConfirm(`Are you sure you want to delete Save ${saveFolderNumber}? This action cannot be undone.`);
        if (!confirmed) {
            return;
        }

        try {
            const urlPattern = window.DELETE_SAVE_FOLDER_URL_PATTERN;
            // Replace both placeholders: first game_id, then folder_number
            let url = urlPattern.replace('/0/', `/${gameId}/`);
            url = url.replace('/0/', `/${saveFolderNumber}/`);
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                }
            });

            const data = await response.json();

            if (data.success && data.operation_id) {
                // Show progress modal and poll for status
                const modalData = createProgressModal(data.operation_id, 'Deleting Save Folder', 'delete');
                pollOperationStatus(
                    data.operation_id,
                    modalData,
                    () => {
                        window.showToast('Save folder deleted successfully!', 'success');
                        // Reload page after a short delay
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    },
                    () => {
                        window.showToast('Failed to delete save folder', 'error');
                    }
                );
            } else if (data.success) {
                window.showToast(data.message || 'Save folder deleted successfully!', 'success');
                // Reload page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                window.showToast(data.error || 'Failed to delete save folder', 'error');
            }
        } catch (error) {
            console.error('Error deleting save folder:', error);
            window.showToast('Error: Failed to delete save folder. Please try again.', 'error');
        }
    }

    async function loadSelectedSave(gameId, saveFolderNumber) {
        const csrfInput = document.querySelector('#gameCsrfForm input[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfInput ? csrfInput.value : null;

        if (!csrfToken) {
            console.error('CSRF token not found');
            return;
        }

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
                body: JSON.stringify({
                    save_folder_number: saveFolderNumber
                })
            });

            const data = await response.json();

            if (data.success && data.operation_id) {
                // Show progress modal and poll for status
                const modalData = createProgressModal(data.operation_id, 'Loading Game', 'load');
                pollOperationStatus(
                    data.operation_id,
                    modalData,
                    () => {
                        window.showToast('Game loaded successfully!', 'success');
                    },
                    () => {
                        window.showToast('Failed to load game', 'error');
                    }
                );
            } else if (data.success) {
                window.showToast(data.message || 'Game loaded successfully!', 'success');
            } else {
                window.showToast(data.error || data.message || 'Failed to load game', 'error');
            }
        } catch (error) {
            console.error('Error loading game:', error);
            window.showToast('Error: Failed to load game. Please try again.', 'error');
        }
    }

    // Click handler on available games grid
    section.addEventListener('click', function (e) {
        // Don't open modal if clicking save button
        if (e.target.closest('.save-game-btn')) {
            return;
        }

        const card = e.target.closest('.game-card[data-game-id]');
        if (!card) return;

        // Don't open modal if clicking on buttons
        if (e.target.closest('.save-game-btn') || e.target.closest('.quick-load-btn')) {
            return;
        }

        const gameId = card.dataset.gameId;
        currentCard = card;
        currentDetailUrlRef = card.dataset.gameDetailUrl || '';
        currentDeleteUrlRef = card.dataset.gameDeleteUrl || '';

        const isUserView = window.IS_USER_VIEW || false;

        // For users, we don't need detail URL - they can only view saves
        // For admins, detail URL is required
        if (!isUserView && !currentDetailUrlRef) {
            console.error('No detail URL on card');
            return;
        }

        // Reset form state
        if (form) {
            form.reset();
        }
        // Clear save locations
        manageSaveLocationManager.populateLocations('');
        // Clear banner preview
        const bannerPreviewEl = document.getElementById('manage_banner_preview');
        if (bannerPreviewEl) {
            clearElement(bannerPreviewEl);
        }

        // Get game title from card for modal title
        const cardTitle = card.querySelector('.card-title');
        const gameTitle = cardTitle ? cardTitle.textContent.trim() : 'Game';

        // Update modal title
        const modalTitle = document.getElementById('gameManageModalLabel');
        if (modalTitle) {
            if (isUserView) {
                modalTitle.textContent = gameTitle + ' - Saves';
            } else {
                modalTitle.textContent = 'Edit Game';
            }
        }

        // For users, only load save folders (no edit form, no game details)
        if (isUserView) {
            loadSaveFolders(gameId).then(function () {
                modal.show();
            });
        } else {
            // Load game details and save folders for admin
            // Show saves tab for normal game cards
            const savesTabContainer = document.getElementById('saves-tab-container');
            if (savesTabContainer) {
                savesTabContainer.classList.remove('d-none');
            }
            Promise.all([
                loadGame(currentDetailUrlRef, false),
                loadSaveFolders(gameId)
            ]).then(function () {
                // Ensure buttons are shown/hidden based on initial active tab
                const editPane = document.getElementById('edit-pane');
                const savesPane = document.getElementById('saves-pane');
                const editTabButtons = document.getElementById('edit-tab-buttons');
                const saveGameBtn = document.getElementById('saveGameBtn');

                if (editPane && savesPane && editTabButtons && saveGameBtn) {
                    if (editPane.classList.contains('active') && editPane.classList.contains('show')) {
                        editTabButtons.classList.remove('d-none');
                        saveGameBtn.classList.remove('d-none');
                    } else if (savesPane.classList.contains('active') && savesPane.classList.contains('show')) {
                        editTabButtons.classList.add('d-none');
                        saveGameBtn.classList.add('d-none');
                    }
                }
                modal.show();
            });
        }
    });

    // Wire buttons (only for admin view)
    const isUserView = window.IS_USER_VIEW || false;
    const saveBtn = document.getElementById('saveGameBtn');
    const deleteBtn = document.getElementById('deleteGameBtn');

    if (saveBtn && !isUserView) {
        saveBtn.addEventListener('click', function () {
            saveGame();
        });
    }

    if (deleteBtn && !isUserView) {
        deleteBtn.addEventListener('click', function () {
            deleteGame();
        });
    }

    if (bannerInput) {
        bannerInput.addEventListener('input', function () {
            updateBannerPreview('manage_banner_preview', bannerInput.value.trim());
        });
    }

    // Handle tab switching to update active states and show/hide buttons
    const editTab = document.getElementById('edit-tab');
    const savesTab = document.getElementById('saves-tab');
    const editTabButtons = document.getElementById('edit-tab-buttons');
    const saveGameBtn = document.getElementById('saveGameBtn');

    // Function to show/hide edit buttons based on active tab
    function toggleEditButtons(show) {
        if (editTabButtons) {
            if (show) {
                editTabButtons.classList.remove('d-none');
            } else {
                editTabButtons.classList.add('d-none');
            }
        }
        if (saveGameBtn) {
            if (show) {
                saveGameBtn.classList.remove('d-none');
            } else {
                saveGameBtn.classList.add('d-none');
            }
        }
    }

    if (editTab && savesTab) {
        // Initial state - show buttons if edit tab is active by default
        const editPane = document.getElementById('edit-pane');
        const savesPane = document.getElementById('saves-pane');
        if (editPane && savesPane) {
            // Check which pane is actually shown (Bootstrap uses 'show' class)
            if (editPane.classList.contains('show') && editPane.classList.contains('active')) {
                toggleEditButtons(true);
            } else if (savesPane.classList.contains('show') && savesPane.classList.contains('active')) {
                toggleEditButtons(false);
            } else {
                // Default to showing buttons if edit tab button is active
                if (editTab.classList.contains('active')) {
                    toggleEditButtons(true);
                } else {
                    toggleEditButtons(false);
                }
            }
        }

        editTab.addEventListener('shown.bs.tab', function () {
            editTab.classList.add('active', 'text-white');
            editTab.classList.remove('text-white-50');
            savesTab.classList.remove('active', 'text-white');
            savesTab.classList.add('text-white-50');
            toggleEditButtons(true);
        });

        savesTab.addEventListener('shown.bs.tab', function () {
            savesTab.classList.add('active', 'text-white');
            savesTab.classList.remove('text-white-50');
            editTab.classList.remove('active', 'text-white');
            editTab.classList.add('text-white-50');
            toggleEditButtons(false);
        });
    }

    /**
     * Open save file location for a game
     */
    async function openSaveLocation(gameId) {
        if (!window.OPEN_SAVE_LOCATION_URL_PATTERN) {
            console.error('OPEN_SAVE_LOCATION_URL_PATTERN not defined');
            return;
        }

        // Get CSRF token
        const csrfInput = document.querySelector('#gameCsrfForm input[name="csrfmiddlewaretoken"]') ||
            document.querySelector('#gameManageForm input[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfInput ? csrfInput.value : null;

        if (!csrfToken) {
            console.error('CSRF token not found');
            return;
        }

        const url = window.OPEN_SAVE_LOCATION_URL_PATTERN.replace('0', gameId);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                window.showToast(data.error || 'Failed to open save location', 'error');
                return;
            }

            // If operation ID is returned, poll for status
            if (data.operation_id) {
                const operationId = data.operation_id;

                // Poll for operation status
                const pollInterval = 300; // Poll every 300ms (faster for quick operations)
                const maxAttempts = 100; // Max 30 seconds (100 * 300ms)
                let attempts = 0;
                let pollStatus = null;
                let isPolling = true; // Flag to prevent multiple intervals

                const stopPolling = () => {
                    if (pollStatus) {
                        clearInterval(pollStatus);
                        pollStatus = null;
                    }
                    isPolling = false;
                };

                // Function to check status
                const checkStatus = async () => {
                    if (!isPolling) {
                        return false; // Stop checking if polling was stopped
                    }

                    attempts++;

                    if (attempts > maxAttempts) {
                        stopPolling();
                        window.showToast('Operation timed out. Please check if the folder exists.', 'error');
                        return false;
                    }

                    try {
                        const statusUrl = window.CHECK_OPERATION_STATUS_URL_PATTERN.replace('0', operationId);
                        const statusResponse = await fetch(statusUrl, {
                            headers: {
                                'X-Requested-With': 'XMLHttpRequest',
                                'X-CSRFToken': csrfToken
                            },
                            credentials: 'same-origin'
                        });

                        if (!statusResponse.ok) {
                            stopPolling();
                            window.showToast('Error checking operation status', 'error');
                            return false;
                        }

                        const statusData = await statusResponse.json();

                        // Check if we have a valid response
                        if (!statusData.success) {
                            stopPolling();
                            window.showToast(statusData.error || 'Operation failed', 'error');
                            return false;
                        }

                        // Response structure: fields are at top level (not nested under 'data')
                        // { success: true, status: 'pending', completed: false, failed: false, ... }
                        if (statusData.completed === true) {
                            stopPolling();
                            window.showToast('Folder opened successfully', 'success');
                            return false; // Stop polling
                        } else if (statusData.failed === true) {
                            stopPolling();
                            // Check if it's a "does not exist" error
                            const errorMsg = statusData.message || 'Failed to open folder';
                            if (errorMsg.includes('does not exist') || errorMsg.includes('not found') || errorMsg.includes('not a directory')) {
                                window.showToast('The folder or directory does not exist', 'error');
                            } else {
                                window.showToast(errorMsg, 'error');
                            }
                            return false; // Stop polling
                        }

                        // If still in progress (pending or in_progress), continue polling
                        return true; // Continue polling
                    } catch (error) {
                        console.error('Error polling operation status:', error);
                        stopPolling();
                        window.showToast('Error checking operation status', 'error');
                        return false;
                    }
                };

                // Check immediately first (operation might complete very quickly)
                const immediateCheck = await checkStatus();
                if (!immediateCheck) {
                    // Operation already completed or failed, no need to poll
                    return;
                }

                // If still in progress, start polling interval
                pollStatus = setInterval(async () => {
                    const shouldContinue = await checkStatus();
                    if (!shouldContinue) {
                        // Operation completed or failed, interval will be cleared by checkStatus
                        return;
                    }
                }, pollInterval);
            } else {
                window.showToast('Open folder operation queued', 'info');
            }

        } catch (error) {
            console.error('Error opening save location:', error);
            window.showToast('Error: Failed to open save location. Please try again.', 'error');
        }
    }

    /**
     * Backup all saves for a game
     */
    async function backupAllSaves(gameId) {
        if (!window.BACKUP_ALL_SAVES_URL_PATTERN) {
            console.error('BACKUP_ALL_SAVES_URL_PATTERN not defined');
            return;
        }

        // Get CSRF token
        const csrfInput = document.querySelector('#gameCsrfForm input[name="csrfmiddlewaretoken"]') ||
            document.querySelector('#gameManageForm input[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfInput ? csrfInput.value : null;

        if (!csrfToken) {
            console.error('CSRF token not found');
            return;
        }

        const url = window.BACKUP_ALL_SAVES_URL_PATTERN.replace('0', gameId);

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                window.showToast(data.error || 'Failed to create backup', 'error');
                return;
            }

            // If operation ID is returned, show progress modal and poll
            if (data.operation_id) {
                const operationId = data.operation_id;

                // Show progress modal and poll for status
                const modalData = createProgressModal(operationId, 'Backing Up All Saves', 'backup');
                pollOperationStatus(
                    operationId,
                    modalData,
                    () => {
                        // On completion, check result for zip file path
                        checkBackupResult(operationId);
                    },
                    () => {
                        window.showToast('Backup failed', 'error');
                    }
                );
            } else {
                // Fallback: no operation ID, show toast
                window.showToast(data.message || 'Backup operation queued', 'info');
            }

        } catch (error) {
            console.error('Error creating backup:', error);
            window.showToast('Error: Failed to create backup. Please try again.', 'error');
        }
    }

    // Helper function to check backup result and show modal with folder location
    async function checkBackupResult(operationId) {
        try {
            const urlPattern = window.CHECK_OPERATION_STATUS_URL_PATTERN;
            const url = urlPattern.replace('/0/', `/${operationId}/`);
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.result_data && data.result_data.zip_path) {
                    const zipPath = data.result_data.zip_path;
                    // Show modal using safe DOM manipulation
                    showBackupCompleteModal(zipPath);

                    // Also show toast for quick notification
                    window.showToast('Backup complete!', 'success');
                }
            }
        } catch (error) {
            console.error('Error checking backup result:', error);
        }
    }

    // Show backup complete modal using safe DOM manipulation
    function showBackupCompleteModal(zipPath) {
        // Remove existing modal if present
        const existingModal = document.getElementById('backupCompleteModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal container
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'backupCompleteModal';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-hidden', 'true');

        const dialog = document.createElement('div');
        dialog.className = 'modal-dialog modal-dialog-centered';

        const content = document.createElement('div');
        content.className = 'modal-content bg-primary border-secondary';

        // Header
        const header = document.createElement('div');
        header.className = 'modal-header border-secondary';

        const title = document.createElement('h5');
        title.className = 'modal-title text-white';
        title.id = 'backupCompleteModalLabel';

        title.appendChild(document.createTextNode('Backup Complete!'));

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close btn-close-white';
        closeBtn.setAttribute('data-bs-dismiss', 'modal');
        closeBtn.setAttribute('aria-label', 'Close');

        header.appendChild(title);
        header.appendChild(closeBtn);

        // Body
        const body = document.createElement('div');
        body.className = 'modal-body';

        const message = document.createElement('p');
        message.className = 'text-white mb-3';
        message.textContent = 'Your backup has been saved successfully!';

        const card = document.createElement('div');
        // Match the theme: darker card on primary background
        card.className = 'card bg-dark border-secondary mb-3';

        const cardBody = document.createElement('div');
        cardBody.className = 'card-body py-2';

        const locationLabel = document.createElement('small');
        locationLabel.className = 'text-white-50 d-block mb-1';
        locationLabel.textContent = 'File Location:';

        const codePath = document.createElement('code');
        codePath.className = 'text-info d-block';
        codePath.style.wordBreak = 'break-all';
        codePath.textContent = zipPath;

        cardBody.appendChild(locationLabel);
        cardBody.appendChild(codePath);
        card.appendChild(cardBody);

        body.appendChild(message);
        body.appendChild(card);

        // Footer
        const footer = document.createElement('div');
        footer.className = 'modal-footer border-secondary';

        const closeFooterBtn = document.createElement('button');
        closeFooterBtn.type = 'button';
        closeFooterBtn.className = 'btn btn-secondary text-white';
        closeFooterBtn.setAttribute('data-bs-dismiss', 'modal');
        closeFooterBtn.textContent = 'Close';

        footer.appendChild(closeFooterBtn);

        // Assemble modal
        content.appendChild(header);
        content.appendChild(body);
        content.appendChild(footer);
        dialog.appendChild(content);
        modal.appendChild(dialog);

        document.body.appendChild(modal);

        if (window.applyModalStacking) {
            window.applyModalStacking(modal);
        }

        // Show modal
        const backupModal = new bootstrap.Modal(modal);
        backupModal.show();

        // Clean up on hide
        modal.addEventListener('hidden.bs.modal', function () {
            modal.remove();
        });
    }

    /**
     * Delete all saves for a game
     */
    async function deleteAllSaves(gameId) {
        if (!window.DELETE_ALL_SAVES_URL_PATTERN) {
            console.error('DELETE_ALL_SAVES_URL_PATTERN not defined');
            return;
        }

        // Get CSRF token (same way as deleteSaveFolder)
        const csrfInput = document.querySelector('#gameCsrfForm input[name="csrfmiddlewaretoken"]') ||
            document.querySelector('#gameManageForm input[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfInput ? csrfInput.value : null;

        if (!csrfToken) {
            console.error('CSRF token not found');
            return;
        }

        // Show confirmation dialog
        const confirmed = await customConfirm(
            'Are you sure you want to delete ALL save files for this game? This action cannot be undone!',
            'Delete All Saves',
            'danger'
        );

        if (!confirmed) {
            return;
        }

        const url = window.DELETE_ALL_SAVES_URL_PATTERN.replace('0', gameId);

        try {
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                window.showToast(data.error || 'Failed to delete all saves', 'error');
                return;
            }

            // If operation IDs are returned, show progress modal and poll
            if (data.operation_ids && data.operation_ids.length > 0) {
                // Use the first operation ID for progress tracking
                // All operations will be processed in parallel by the client worker
                const firstOperationId = data.operation_ids[0];
                const totalCount = data.total_count || data.operation_ids.length;

                // Show progress modal and poll for status
                const modalData = createProgressModal(firstOperationId, `Deleting All Saves (${totalCount} folder${totalCount > 1 ? 's' : ''})`, 'delete');
                pollOperationStatus(
                    firstOperationId,
                    modalData,
                    () => {
                        // Check if all operations are complete
                        checkAllOperationsComplete(data.operation_ids, gameId);
                    },
                    () => {
                        // On error, still check if others completed
                        checkAllOperationsComplete(data.operation_ids, gameId);
                    }
                );
            } else {
                // Fallback: no operation IDs, show toast
                window.showToast(data.message || 'All saves deleted successfully!', 'success');
                loadSaveFolders(gameId);
            }

        } catch (error) {
            console.error('Error deleting all saves:', error);
            window.showToast('Error: Failed to delete all saves. Please try again.', 'error');
        }
    }

    // Helper function to check if all delete operations are complete
    async function checkAllOperationsComplete(operationIds, gameId) {
        if (!operationIds || operationIds.length === 0) {
            // Reload page to refresh everything
            setTimeout(() => {
                window.location.reload();
            }, 500);
            return;
        }

        // Check status of all operations
        const urlPattern = window.CHECK_OPERATION_STATUS_URL_PATTERN;
        const statusChecks = operationIds.map(async (opId) => {
            try {
                const url = urlPattern.replace('/0/', `/${opId}/`);
                const response = await fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });

                if (!response.ok) {
                    return { id: opId, status: 'unknown' };
                }

                const data = await response.json();
                return { id: opId, status: data.status || 'unknown' };
            } catch (error) {
                console.error(`Error checking operation ${opId}:`, error);
                return { id: opId, status: 'unknown' };
            }
        });

        const results = await Promise.all(statusChecks);

        // Check if all operations are complete (completed or failed)
        const allComplete = results.every(result =>
            result.status === 'completed' || result.status === 'failed'
        );

        // If all are complete, reload the page
        if (allComplete) {
            // Small delay to ensure backend has processed all deletions
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            // Not all complete yet, check again in a bit
            setTimeout(() => {
                checkAllOperationsComplete(operationIds, gameId);
            }, 2000);
        }
    }
});


