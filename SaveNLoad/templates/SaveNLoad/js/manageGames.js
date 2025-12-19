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
window.openGameEditModal = function(gameId, hideSavesTab = false) {
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
    if (bannerPreviewRef) {
        clearElement(bannerPreviewRef);
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
            savesTabContainer.style.display = 'none';
        } else {
            savesTabContainer.style.display = '';
        }
    }
    
    // Load game details (don't load save folders if hiding saves tab)
    if (hideSavesTab) {
        if (loadGameRef) {
            loadGameRef(currentDetailUrlRef, true).then(function () {
                modalInstance.show();
            });
        }
    } else {
        if (loadGameRef && loadSaveFoldersRef) {
            Promise.all([
                loadGameRef(currentDetailUrlRef, false),
                loadSaveFoldersRef(gameId)
            ]).then(function () {
                modalInstance.show();
            });
        }
    }
};

function clearElement(element) {
    if (!element) return;
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
}

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

    const csrfInput = document.querySelector('#gameManageForm input[name=\"csrfmiddlewaretoken\"]') ||
        document.querySelector('#gameCsrfForm input[name=\"csrfmiddlewaretoken\"]');
    const csrfToken = csrfInput ? csrfInput.value : null;

    let currentCard = null;
    // Use the refs directly so they stay in sync
    currentDetailUrlRef = null;
    currentDeleteUrlRef = null;

    function isValidImageUrl(url) {
        if (!url || typeof url !== 'string') return false;
        
        // Remove whitespace
        url = url.trim();
        if (!url) return false;
        
        // Block dangerous schemes
        const lowerUrl = url.toLowerCase();
        if (lowerUrl.startsWith('javascript:') || 
            lowerUrl.startsWith('data:') || 
            lowerUrl.startsWith('vbscript:') ||
            lowerUrl.startsWith('file:')) {
            return false;
        }
        
        // Only allow http/https URLs
        try {
            const urlObj = new URL(url);
            if (urlObj.protocol !== 'http:' && urlObj.protocol !== 'https:') {
                return false;
            }
        } catch (e) {
            // Invalid URL format
            return false;
        }
        
        return true;
    }

    function updateBannerPreview(bannerUrl) {
        clearElement(bannerPreview);
        if (!bannerUrl) return;

        // Validate URL before using it
        if (!isValidImageUrl(bannerUrl)) {
            const p = document.createElement('p');
            p.className = 'text-muted small';
            p.appendChild(document.createTextNode('Invalid or unsafe URL'));
            bannerPreview.appendChild(p);
            return;
        }

        const img = document.createElement('img');
        img.src = bannerUrl;
        img.alt = 'Banner preview';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'contain';
        img.className = 'img-thumbnail';
        // Security attributes
        img.loading = 'lazy';
        img.referrerPolicy = 'no-referrer';

        img.onerror = function () {
            clearElement(bannerPreview);
            const p = document.createElement('p');
            p.className = 'text-muted small';
            p.appendChild(document.createTextNode('Failed to load image'));
            bannerPreview.appendChild(p);
        };

        bannerPreview.appendChild(img);
    }

    const loadGame = async function(detailUrl, hideSavesTab = false) {
        try {
            const response = await fetch(detailUrl, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await response.json();
            if (!response.ok) {
                console.error('Failed to load game:', data);
                return;
            }

            idInput.value = data.id || '';
            nameInput.value = data.name || '';
            bannerInput.value = data.banner || '';
            saveFileLocationInput.value = data.save_file_location || '';
            updateBannerPreview(data.banner || '');
            
            // Hide/show saves tab based on flag
            const savesTabContainer = document.getElementById('saves-tab-container');
            if (savesTabContainer) {
                if (hideSavesTab) {
                    savesTabContainer.style.display = 'none';
                } else {
                    savesTabContainer.style.display = '';
                }
            }
        } catch (e) {
            console.error('Error loading game:', e);
        }
    };
    loadGameRef = loadGame; // Store reference

    async function saveGame() {
        if (!currentDetailUrlRef) return;
        if (!csrfToken) {
            console.error('CSRF token not found');
            return;
        }

        const payload = {
            name: nameInput.value.trim(),
            banner: bannerInput.value.trim(),
            save_file_location: saveFileLocationInput.value.trim()
        };

        try {
            const response = await fetch(currentDetailUrlRef, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                console.error('Failed to save game:', data);
                return;
            }

            // Easiest: refresh the page so cards reflect the new data
            window.location.reload();
        } catch (e) {
            console.error('Error saving game:', e);
        }
    }

    async function deleteGame() {
        if (!currentDeleteUrlRef) return;
        if (!csrfToken) {
            console.error('CSRF token not found');
            return;
        }

        const confirmed = await customConfirm('Are you sure you want to delete this game? This cannot be undone.');
        if (!confirmed) {
            return;
        }

        try {
            const response = await fetch(currentDeleteUrlRef, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                }
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                console.error('Failed to delete game:', data);
                return;
            }

            window.location.reload();
        } catch (e) {
            console.error('Error deleting game:', e);
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

    const loadSaveFolders = async function(gameId) {
        const container = document.getElementById('savesListContainer');
        if (!container) return;

        clearElement(container);
        container.appendChild(createLoadingState());

        try {
            const urlPattern = window.LIST_SAVE_FOLDERS_URL_PATTERN;
            const url = urlPattern.replace('/0/', `/${gameId}/`);
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                clearElement(container);
                container.appendChild(createErrorMessage(data.error || 'Failed to load saves'));
                return;
            }

            if (!data.save_folders || data.save_folders.length === 0) {
                clearElement(container);
                container.appendChild(createErrorMessage('No saves available'));
                return;
            }

            // Add backup and delete buttons at the top
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'mb-3 d-flex justify-content-between align-items-center gap-2';
            
            // Open folder button on the left
            const openFolderButton = document.createElement('button');
            openFolderButton.className = 'btn btn-info text-white';
            openFolderButton.type = 'button';
            const folderIcon = document.createElement('i');
            folderIcon.className = 'fas fa-folder-open me-2';
            openFolderButton.appendChild(folderIcon);
            openFolderButton.appendChild(document.createTextNode('Open Save Location'));
            openFolderButton.addEventListener('click', function() {
                openSaveLocation(gameId);
            });
            buttonContainer.appendChild(openFolderButton);
            
            // Right side button container
            const rightButtonContainer = document.createElement('div');
            rightButtonContainer.className = 'd-flex gap-2';
            
            const backupButton = document.createElement('button');
            backupButton.className = 'btn btn-secondary text-white';
            backupButton.type = 'button';
            const backupIcon = document.createElement('i');
            backupIcon.className = 'fas fa-download me-2';
            backupButton.appendChild(backupIcon);
            backupButton.appendChild(document.createTextNode('Backup All Saves'));
            backupButton.addEventListener('click', function() {
                backupAllSaves(gameId);
            });
            buttonContainer.appendChild(backupButton);
            
            const deleteButton = document.createElement('button');
            deleteButton.className = 'btn btn-danger text-white';
            deleteButton.type = 'button';
            const deleteIcon = document.createElement('i');
            deleteIcon.className = 'fas fa-trash me-2';
            deleteButton.appendChild(deleteIcon);
            deleteButton.appendChild(document.createTextNode('Delete All Saves'));
            deleteButton.addEventListener('click', function() {
                deleteAllSaves(gameId);
            });
            rightButtonContainer.appendChild(backupButton);
            rightButtonContainer.appendChild(deleteButton);
            buttonContainer.appendChild(rightButtonContainer);

            const listGroup = document.createElement('div');
            listGroup.className = 'list-group';

            data.save_folders.forEach(folder => {
                const link = document.createElement('a');
                link.href = '#';
                link.className = 'list-group-item list-group-item-action bg-primary text-white border-secondary';
                link.style.transition = 'background-color 0.2s ease';
                link.dataset.folderNumber = folder.folder_number;

                link.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = 'rgba(90, 141, 238, 0.2)';
                });
                link.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = '';
                });

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
                loadBtn.addEventListener('click', function(e) {
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
                deleteBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    deleteSaveFolder(gameId, folder.folder_number);
                });
                
                buttonGroup.appendChild(loadBtn);
                buttonGroup.appendChild(deleteBtn);

                row.appendChild(leftDiv);
                row.appendChild(buttonGroup);
                link.appendChild(row);
                listGroup.appendChild(link);
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
        progressBarWrapper.className = 'progress';
        progressBarWrapper.style.height = '30px';
        progressBarWrapper.style.marginBottom = '15px';
        progressBarWrapper.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
        
        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
        progressBar.setAttribute('role', 'progressbar');
        progressBar.style.width = '0%';
        progressBar.style.backgroundColor = '#0d6efd';
        progressBar.setAttribute('aria-valuenow', '0');
        progressBar.setAttribute('aria-valuemin', '0');
        progressBar.setAttribute('aria-valuemax', '100');
        
        const progressText = document.createElement('div');
        progressText.className = 'text-center mt-3';
        progressText.style.fontSize = '0.9rem';
        progressText.style.fontWeight = '500';
        progressText.style.color = '#ffffff';
        progressText.textContent = 'Starting...';
        
        const progressDetails = document.createElement('div');
        progressDetails.className = 'text-center text-white-50 mt-2';
        progressDetails.style.fontSize = '0.85rem';
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
                    progressBar.style.backgroundColor = '#198754';
                    progressBar.style.width = '100%';
                    progressBar.setAttribute('aria-valuenow', '100');
                    progressText.textContent = 'Operation Complete!';
                    progressDetails.textContent = 'Successfully completed';
                    setTimeout(() => {
                        modal.hide();
                        modalBackdrop.remove();
                    }, 1500);
                    if (onComplete) onComplete();
                    return true;
                } else if (data.failed) {
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = '#dc3545';
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
                    progressBar.style.backgroundColor = '#ffc107';
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
                    modalFooter.appendChild(closeBtn);
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

        // Show toast notification
        function showToast(message, type = 'info') {
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

            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 5000);
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

            console.log('Delete response:', data); // Debug

            if (data.success && data.operation_id) {
                // Show progress modal and poll for status
                const modalData = createProgressModal(data.operation_id, 'Deleting Save Folder', 'delete');
                pollOperationStatus(
                    data.operation_id,
                    modalData,
                    () => {
                        showToast('Save folder deleted successfully!', 'success');
                        loadSaveFolders(gameId);
                    },
                    () => {
                        showToast('Failed to delete save folder', 'error');
                    }
                );
            } else if (data.success) {
                showToast(data.message || 'Save folder deleted successfully!', 'success');
                loadSaveFolders(gameId);
            } else {
                showToast(data.error || 'Failed to delete save folder', 'error');
            }
        } catch (error) {
            console.error('Error deleting save folder:', error);
            showToast('Error: Failed to delete save folder. Please try again.', 'error');
        }
    }

    async function loadSelectedSave(gameId, saveFolderNumber) {
        const csrfInput = document.querySelector('#gameCsrfForm input[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfInput ? csrfInput.value : null;

        if (!csrfToken) {
            console.error('CSRF token not found');
            return;
        }

        // Show toast notification
        function showToast(message, type = 'info') {
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

            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 5000);
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

            console.log('Load response:', data); // Debug

            if (data.success && data.operation_id) {
                // Show progress modal and poll for status
                const modalData = createProgressModal(data.operation_id, 'Loading Game', 'load');
                pollOperationStatus(
                    data.operation_id,
                    modalData,
                    () => {
                        showToast('Game loaded successfully!', 'success');
                    },
                    () => {
                        showToast('Failed to load game', 'error');
                    }
                );
            } else if (data.success) {
                showToast(data.message || 'Game loaded successfully!', 'success');
            } else {
                showToast(data.error || data.message || 'Failed to load game', 'error');
            }
        } catch (error) {
            console.error('Error loading game:', error);
            showToast('Error: Failed to load game. Please try again.', 'error');
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

        // Reset form state (only if form exists - users don't have edit form)
        if (form) {
            form.reset();
        }
        if (bannerPreview) {
            clearElement(bannerPreview);
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
                savesTabContainer.style.display = '';
            }
            Promise.all([
                loadGame(currentDetailUrlRef, false),
                loadSaveFolders(gameId)
            ]).then(function () {
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
            updateBannerPreview(bannerInput.value.trim());
        });
    }

    // Handle tab switching to update active states
    const editTab = document.getElementById('edit-tab');
    const savesTab = document.getElementById('saves-tab');
    
    if (editTab && savesTab) {
        editTab.addEventListener('shown.bs.tab', function () {
            editTab.classList.add('active', 'text-white');
            editTab.classList.remove('text-white-50');
            savesTab.classList.remove('active', 'text-white');
            savesTab.classList.add('text-white-50');
        });
        
        savesTab.addEventListener('shown.bs.tab', function () {
            savesTab.classList.add('active', 'text-white');
            savesTab.classList.remove('text-white-50');
            editTab.classList.remove('active', 'text-white');
            editTab.classList.add('text-white-50');
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
        
        // Show toast notification helper
        function showToast(message, type = 'info') {
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
            
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 5000);
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
                showToast(data.error || 'Failed to open save location', 'error');
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
                        showToast('Operation timed out. Please check if the folder exists.', 'error');
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
                            showToast('Error checking operation status', 'error');
                            return false;
                        }
                        
                        const statusData = await statusResponse.json();
                        
                        // Check if operation is completed or failed
                        if (statusData.success && statusData.data) {
                            if (statusData.data.completed === true) {
                                stopPolling();
                                showToast('Folder opened successfully', 'success');
                                return false; // Stop polling
                            } else if (statusData.data.failed === true) {
                                stopPolling();
                                // Check if it's a "does not exist" error
                                const errorMsg = statusData.data.message || 'Failed to open folder';
                                if (errorMsg.includes('does not exist') || errorMsg.includes('not found') || errorMsg.includes('not a directory')) {
                                    showToast('The folder or directory does not exist', 'error');
                                } else {
                                    showToast(errorMsg, 'error');
                                }
                                return false; // Stop polling
                            }
                            // If still in progress (pending or in_progress), continue polling
                            return true; // Continue polling
                        } else {
                            // Invalid response structure, stop polling to avoid infinite loop
                            stopPolling();
                            showToast('Error: Invalid response from server', 'error');
                            return false;
                        }
                    } catch (error) {
                        console.error('Error polling operation status:', error);
                        stopPolling();
                        showToast('Error checking operation status', 'error');
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
                showToast('Open folder operation queued', 'info');
            }
            
        } catch (error) {
            console.error('Error opening save location:', error);
            showToast('Error: Failed to open save location. Please try again.', 'error');
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
                function showToast(message, type = 'info') {
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

                    setTimeout(() => {
                        if (toast.parentNode) {
                            toast.remove();
                        }
                    }, 5000);
                }
                showToast(data.error || 'Failed to create backup', 'error');
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
                        function showToast(message, type = 'info') {
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

                            setTimeout(() => {
                                if (toast.parentNode) {
                                    toast.remove();
                                }
                            }, 5000);
                        }
                        showToast('Backup failed', 'error');
                    }
                );
            } else {
                // Fallback: no operation ID, show toast
                function showToast(message, type = 'info') {
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

                    setTimeout(() => {
                        if (toast.parentNode) {
                            toast.remove();
                        }
                    }, 5000);
                }
                showToast(data.message || 'Backup operation queued', 'info');
            }
            
        } catch (error) {
            console.error('Error creating backup:', error);
            function showToast(message, type = 'info') {
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

                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.remove();
                    }
                }, 5000);
            }
            showToast('Error: Failed to create backup. Please try again.', 'error');
        }
    }
    
    // Helper function to check backup result and show download info
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
                    function showToast(message, type = 'info') {
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

                        setTimeout(() => {
                            if (toast.parentNode) {
                                toast.remove();
                            }
                        }, 5000);
                    }
                    showToast(`Backup complete! Saved to: ${data.result_data.zip_path}`, 'success');
                }
            }
        } catch (error) {
            console.error('Error checking backup result:', error);
        }
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
                // Show toast notification
                function showToast(message, type = 'info') {
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

                    setTimeout(() => {
                        if (toast.parentNode) {
                            toast.remove();
                        }
                    }, 5000);
                }
                showToast(data.error || 'Failed to delete all saves', 'error');
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
                function showToast(message, type = 'info') {
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

                    setTimeout(() => {
                        if (toast.parentNode) {
                            toast.remove();
                        }
                    }, 5000);
                }
                showToast(data.message || 'All saves deleted successfully!', 'success');
                loadSaveFolders(gameId);
            }
            
        } catch (error) {
            console.error('Error deleting all saves:', error);
            function showToast(message, type = 'info') {
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

                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.remove();
                    }
                }, 5000);
            }
            showToast('Error: Failed to delete all saves. Please try again.', 'error');
        }
    }
    
    // Helper function to check if all delete operations are complete
    async function checkAllOperationsComplete(operationIds, gameId) {
        if (!operationIds || operationIds.length === 0) {
            loadSaveFolders(gameId);
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
        
        // If all are complete, refresh the UI
        if (allComplete) {
            // Small delay to ensure backend has processed all deletions
            setTimeout(() => {
                loadSaveFolders(gameId);
            }, 500);
        } else {
            // Not all complete yet, check again in a bit
            setTimeout(() => {
                checkAllOperationsComplete(operationIds, gameId);
            }, 2000);
        }
    }
});


