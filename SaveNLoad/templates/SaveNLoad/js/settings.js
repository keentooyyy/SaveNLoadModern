document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('search_input');
    const modalElement = document.getElementById('gameSearchModal');
    const searchResults = document.getElementById('modal_search_results');
    const nameInput = document.getElementById('name');
    const bannerInput = document.getElementById('banner');
    const saveFileLocationInput = document.getElementById('save_file_location');
    const bannerPreview = document.getElementById('banner_preview');
    const searchUrl = searchInput ? searchInput.dataset.searchUrl : '';

    let searchTimeout = null;
    let bootstrapModal = null;
    let loadingOverlay = null;

    /**
     * Show full-page loading overlay with spinner
     * Creates a semi-transparent overlay that covers the entire page
     * Matches the page's dark theme with primary blue accent color
     */
    function showLoadingOverlay() {
        // Remove existing overlay if present
        if (loadingOverlay && loadingOverlay.parentNode) {
            loadingOverlay.remove();
        }

        // Create overlay container with dark theme background
        loadingOverlay = document.createElement('div');
        loadingOverlay.id = 'search_loading_overlay';
        loadingOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(28, 34, 47, 0.85);
            z-index: 9998;
            display: flex;
            justify-content: center;
            align-items: center;
        `;

        // Create spinner container
        const spinnerContainer = document.createElement('div');
        spinnerContainer.style.cssText = `
            text-align: center;
            color: white;
        `;

        // Create spinner with primary blue color
        const spinner = document.createElement('div');
        spinner.className = 'spinner-border';
        spinner.style.cssText = `
            width: 3rem;
            height: 3rem;
            border-width: 0.25em;
            border-color: #5a8dee;
            border-right-color: transparent;
        `;
        spinner.setAttribute('role', 'status');

        const spinnerText = document.createElement('span');
        spinnerText.className = 'visually-hidden';
        spinnerText.textContent = 'Loading...';
        spinner.appendChild(spinnerText);

        // Create loading text
        const loadingText = document.createElement('p');
        loadingText.className = 'text-white mt-3 mb-0';
        loadingText.style.cssText = 'font-size: 1.1rem; font-weight: 500;';
        loadingText.textContent = 'Searching for games...';

        spinnerContainer.appendChild(spinner);
        spinnerContainer.appendChild(loadingText);
        loadingOverlay.appendChild(spinnerContainer);

        // Add to body
        document.body.appendChild(loadingOverlay);
    }

    /**
     * Hide and remove the loading overlay
     */
    function hideLoadingOverlay() {
        if (loadingOverlay && loadingOverlay.parentNode) {
            loadingOverlay.remove();
            loadingOverlay = null;
        }
    }

    function clearElement(element) {
        if (!element) return;
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    }

    function showModal() {
        if (!modalElement || !window.bootstrap) return;
        if (!bootstrapModal) {
            bootstrapModal = window.bootstrap.Modal.getOrCreateInstance(modalElement);
        }
        bootstrapModal.show();
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
            p.className = 'text-white-50 small';
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

        img.onerror = () => {
            clearElement(bannerPreview);
            const p = document.createElement('p');
            p.className = 'text-white-50 small';
            p.appendChild(document.createTextNode('Failed to load image'));
            bannerPreview.appendChild(p);
        };

        bannerPreview.appendChild(img);
    }

    function populateForm(id, name, saveFileLocation, bannerUrl) {
        if (nameInput) nameInput.value = name;
        if (saveFileLocationInput) saveFileLocationInput.value = saveFileLocation;
        if (bannerInput) bannerInput.value = bannerUrl;

        updateBannerPreview(bannerUrl);

        const card = document.querySelector('.card');
        if (card && card.scrollIntoView) {
            card.scrollIntoView({ behavior: 'smooth' });
        }
    }

    function displaySearchResults(games) {
        // Clear previous results safely
        clearElement(searchResults);

        if (!games || games.length === 0) {
            const p = document.createElement('p');
            p.className = 'text-white-50 text-center py-3';
            p.appendChild(document.createTextNode('No games found.'));
            searchResults.appendChild(p);
            showModal();
            return;
        }

        const listGroup = document.createElement('div');
        listGroup.className = 'list-group';

        games.forEach(game => {
            const gameId = String(game.id ?? '');
            const gameName = game.name ?? '';
            const saveLocation = game.save_file_location ?? '';
            const bannerUrl = game.banner ?? '';

            const link = document.createElement('a');
            link.href = '#';
            link.className = 'list-group-item list-group-item-action bg-primary text-white border-secondary';

            // Store raw values in data attributes (not HTML-escaped)
            link.dataset.gameId = gameId;
            link.dataset.gameName = gameName;
            link.dataset.saveLocation = saveLocation;
            link.dataset.bannerUrl = bannerUrl;

            // Add hover effect
            link.style.transition = 'background-color 0.2s ease';
            link.addEventListener('mouseenter', function() {
                this.style.backgroundColor = 'rgba(90, 141, 238, 0.2)';
            });
            link.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });

            const row = document.createElement('div');
            row.className = 'd-flex align-items-center';

            if (bannerUrl && isValidImageUrl(bannerUrl)) {
                const img = document.createElement('img');
                img.src = bannerUrl;
                img.alt = gameName;
                img.className = 'me-3 rounded';
                img.style.width = '50px';
                img.style.height = '50px';
                img.style.objectFit = 'cover';
                img.referrerPolicy = 'no-referrer';
                row.appendChild(img);
            }

            const textWrapper = document.createElement('div');

            const titleEl = document.createElement('h6');
            titleEl.className = 'mb-1 text-white';
            titleEl.appendChild(document.createTextNode(gameName));

            const saveEl = document.createElement('small');
            saveEl.className = 'text-white-50';
            saveEl.appendChild(document.createTextNode(saveLocation));

            textWrapper.appendChild(titleEl);
            textWrapper.appendChild(saveEl);
            row.appendChild(textWrapper);
            link.appendChild(row);
            listGroup.appendChild(link);

            // Click handler – uses dataset values (not HTML)
            link.addEventListener('click', function (e) {
                e.preventDefault();
                populateForm(
                    this.dataset.gameId || '',
                    this.dataset.gameName || '',
                    this.dataset.saveLocation || '',
                    this.dataset.bannerUrl || ''
                );

                if (bootstrapModal) {
                    bootstrapModal.hide();
                }
            });
        });

        searchResults.appendChild(listGroup);
        showModal();
    }

    /**
     * Search for games using the configured search URL
     * Shows a loading overlay during the search request
     * @param {string} query - The search query string
     */
    async function searchGames(query) {
        if (!searchUrl) {
            console.error('Search URL not configured');
            showToast('Search functionality not configured', 'error');
            return;
        }
        
        // Show loading overlay
        showLoadingOverlay();
        
        try {
            const response = await fetch(`${searchUrl}?q=${encodeURIComponent(query)}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                console.error('Search error from server:', data.error);
                showToast('Failed to search games: ' + data.error, 'error');
                displaySearchResults([]);
            } else {
                displaySearchResults(data.games || []);
            }
        } catch (error) {
            console.error('Search error:', error);
            showToast('Error searching games. Please check console for details.', 'error');
            displaySearchResults([]);
        } finally {
            // Always hide loading overlay when search completes
            hideLoadingOverlay();
        }
    }

    function handleSearchInput() {
        clearTimeout(searchTimeout);
        const query = searchInput.value.trim();

        if (query.length < 2) {
            clearElement(searchResults);
            return;
        }

        searchTimeout = setTimeout(() => {
            searchGames(query);
        }, 300);
    }

    function triggerSearch() {
        if (!searchInput) return;
        const query = searchInput.value.trim();
        if (query.length < 2) {
            return;
        }
        clearTimeout(searchTimeout);
        searchGames(query);
    }

    function handleBannerInput() {
        const bannerUrl = bannerInput.value.trim();
        updateBannerPreview(bannerUrl);
    }

    function clearForm() {
        if (nameInput) nameInput.value = '';
        if (bannerInput) bannerInput.value = '';
        if (saveFileLocationInput) saveFileLocationInput.value = '';
        clearElement(bannerPreview);
        if (searchInput) {
            searchInput.value = '';
        }
        clearElement(searchResults);
    }

    function toggleSearch() {
        const searchSection = document.getElementById('search_section');
        const toggleBtn = document.getElementById('toggle_search_btn');
        if (!searchSection || !toggleBtn) return;

        const isHidden = searchSection.style.display === 'none' || !searchSection.style.display;

        if (isHidden) {
            searchSection.style.display = 'block';
            toggleBtn.textContent = 'Hide Search';
        } else {
            searchSection.style.display = 'none';
            toggleBtn.textContent = 'Search Game';
            clearElement(searchResults);
            if (searchInput) searchInput.value = '';
        }
    }

    // Show toast notification (XSS-safe)
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        
        // Use textContent for message to prevent XSS
        const messageSpan = document.createElement('span');
        messageSpan.textContent = message;
        toast.appendChild(messageSpan);
        
        // Create close button safely
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

    // Handle form submission via AJAX
    const addGameForm = document.getElementById('addGameForm');
    const saveGameBtn = document.getElementById('saveGameBtn');
    
    if (addGameForm && saveGameBtn) {
        addGameForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const csrfInput = document.querySelector('#addGameForm input[name="csrfmiddlewaretoken"]') ||
                document.querySelector('[name="csrfmiddlewaretoken"]');
            const csrfToken = csrfInput ? csrfInput.value : null;
            if (!csrfToken) {
                showToast('Error: CSRF token not found', 'error');
                return;
            }
            
            const name = document.getElementById('name')?.value.trim();
            const saveFileLocation = document.getElementById('save_file_location')?.value.trim();
            const banner = document.getElementById('banner')?.value.trim();
            
            if (!name || !saveFileLocation) {
                showToast('Game name and save file location are required.', 'error');
                return;
            }
            
            // Disable button and show loading state
            const originalContent = Array.from(saveGameBtn.childNodes);
            saveGameBtn.disabled = true;
            // Clear and set loading state safely
            saveGameBtn.textContent = '';
            const spinnerIcon = document.createElement('i');
            spinnerIcon.className = 'fas fa-spinner fa-spin me-1';
            const loadingText = document.createTextNode('Saving...');
            saveGameBtn.appendChild(spinnerIcon);
            saveGameBtn.appendChild(loadingText);
            
            try {
                const response = await fetch(window.CREATE_GAME_URL, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        name: name,
                        save_file_location: saveFileLocation,
                        banner: banner || ''
                    })
                });
                
                // Check if response is JSON
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    // Server returned HTML (likely an error page)
                    const text = await response.text();
                    console.error('Server returned non-JSON response:', text.substring(0, 200));
                    showToast(`Server error (${response.status}): Please check the console for details.`, 'error');
                    return;
                }
                
                const data = await response.json();
                
                if (!response.ok) {
                    // HTTP error status
                    showToast(data.error || `Failed to create game (${response.status})`, 'error');
                    return;
                }
                
                if (data.success) {
                    showToast(data.message || 'Game created successfully!', 'success');
                    // Clear form after successful creation
                    clearForm();
                    // Reload page after a short delay to show the new game
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showToast(data.error || 'Failed to create game', 'error');
                }
            } catch (error) {
                console.error('Error creating game:', error);
                if (error instanceof SyntaxError && error.message.includes('JSON')) {
                    showToast('Server returned invalid response. Please check the console.', 'error');
                } else {
                    showToast('Error: Failed to create game. Please try again.', 'error');
                }
            } finally {
                // Restore button safely
                saveGameBtn.disabled = false;
                saveGameBtn.textContent = '';
                originalContent.forEach(node => {
                    saveGameBtn.appendChild(node.cloneNode(true));
                });
            }
        });
    }

    // Wire up events
    if (bannerInput) {
        bannerInput.addEventListener('input', handleBannerInput);
    }
    
    // Wire up search input event listener (Enter key only)
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                triggerSearch();
            }
        });
    }

    // Expose a couple of helpers for inline handlers
    window.clearForm = clearForm;
    window.toggleSearch = toggleSearch;
    window.triggerSearch = triggerSearch;
});