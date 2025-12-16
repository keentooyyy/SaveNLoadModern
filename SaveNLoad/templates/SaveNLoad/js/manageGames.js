document.addEventListener('DOMContentLoaded', function () {
    const section = document.getElementById('availableGamesSection');
    const modalElement = document.getElementById('gameManageModal');

    if (!section || !modalElement || !window.bootstrap) {
        return;
    }

    const modal = window.bootstrap.Modal.getOrCreateInstance(modalElement);

    const form = document.getElementById('gameManageForm');
    const idInput = document.getElementById('manage_game_id');
    const nameInput = document.getElementById('name');
    const bannerInput = document.getElementById('banner');
    const saveFileLocationInput = document.getElementById('save_file_location');
    const bannerPreview = document.getElementById('banner_preview');

    const csrfInput = document.querySelector('#gameCsrfForm input[name=\"csrfmiddlewaretoken\"]') ||
        document.querySelector('#gameManageForm input[name=\"csrfmiddlewaretoken\"]');
    const csrfToken = csrfInput ? csrfInput.value : null;

    let currentCard = null;
    let currentDetailUrl = null;
    let currentDeleteUrl = null;

    function clearElement(element) {
        if (!element) return;
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    }

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

    async function loadGame(detailUrl) {
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
        } catch (e) {
            console.error('Error loading game:', e);
        }
    }

    async function saveGame() {
        if (!currentDetailUrl) return;
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
            const response = await fetch(currentDetailUrl, {
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
        if (!currentDeleteUrl) return;
        if (!csrfToken) {
            console.error('CSRF token not found');
            return;
        }

        if (!confirm('Are you sure you want to delete this game? This cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch(currentDeleteUrl, {
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

    async function loadSaveFolders(gameId) {
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
            container.appendChild(listGroup);
        } catch (error) {
            console.error('Error loading save folders:', error);
            clearElement(container);
            container.appendChild(createErrorMessage('Error loading saves'));
        }
    }

    async function deleteSaveFolder(gameId, saveFolderNumber) {
        const csrfInput = document.querySelector('#gameCsrfForm input[name="csrfmiddlewaretoken"]') ||
            document.querySelector('#gameManageForm input[name="csrfmiddlewaretoken"]');
        const csrfToken = csrfInput ? csrfInput.value : null;

        if (!csrfToken) {
            console.error('CSRF token not found');
            return;
        }

        if (!confirm(`Are you sure you want to delete Save ${saveFolderNumber}? This action cannot be undone.`)) {
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

            if (data.success) {
                showToast(data.message || 'Save folder deleted successfully!', 'success');
                // Reload the saves list
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

            if (data.success) {
                showToast(data.message || 'Game loaded successfully!', 'success');
                modal.hide();
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
        currentDetailUrl = card.dataset.gameDetailUrl || '';
        currentDeleteUrl = card.dataset.gameDeleteUrl || '';

        if (!currentDetailUrl) {
            console.error('No detail URL on card');
            return;
        }

        // Reset form state
        form.reset();
        clearElement(bannerPreview);

        // Load game details and save folders
        Promise.all([
            loadGame(currentDetailUrl),
            loadSaveFolders(gameId)
        ]).then(function () {
            modal.show();
        });
    });

    // Wire buttons
    const saveBtn = document.getElementById('saveGameBtn');
    const deleteBtn = document.getElementById('deleteGameBtn');

    if (saveBtn) {
        saveBtn.addEventListener('click', function () {
            saveGame();
        });
    }

    if (deleteBtn) {
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
});


