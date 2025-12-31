/**
 * Settings Page Handler
 * Uses shared utilities from utils.js and gameFormUtils.js
 */

document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('search_input');
    const modalElement = document.getElementById('gameSearchModal');
    const searchResults = document.getElementById('modal_search_results');
    const nameInput = document.getElementById('name');
    const bannerInput = document.getElementById('banner');
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
        loadingOverlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
        loadingOverlay.style.cssText = `
            background-color: ${getCSSVariable('--overlay-bg')};
            z-index: 9998;
        `;

        // Create spinner container
        const spinnerContainer = document.createElement('div');
        spinnerContainer.className = 'text-center text-white';

        // Create spinner with primary blue color
        const spinner = document.createElement('div');
        spinner.className = 'spinner-border';
        spinner.style.cssText = `
            width: 3rem;
            height: 3rem;
            border-width: 0.25em;
            border-color: ${getCSSVariable('--color-primary')};
            border-right-color: transparent;
        `;
        spinner.setAttribute('role', 'status');

        const spinnerText = document.createElement('span');
        spinnerText.className = 'visually-hidden';
        spinnerText.textContent = 'Loading...';
        spinner.appendChild(spinnerText);

        // Create loading text
        const loadingText = document.createElement('p');
        loadingText.className = 'text-white mt-3 mb-0 fs-6 fw-medium';
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

    // Initialize save location manager
    const saveLocationManager = new SaveLocationManager('save_locations_container');

    // Wrapper functions for backward compatibility with inline handlers
    function addSaveLocation() {
        saveLocationManager.addLocation();
    }

    function removeSaveLocation(btn) {
        saveLocationManager.removeLocation(btn);
    }

    function updateRemoveButtons() {
        saveLocationManager.updateRemoveButtons();
    }

    function getAllSaveLocations() {
        return saveLocationManager.getAllLocations();
    }

    function createDefaultSaveLocationRow() {
        return saveLocationManager.createRow();
    }

    /**
     * Show the search results modal and sync the modal search input with the main search input
     */
    function showModal() {
        if (!modalElement || !window.bootstrap) return;
        if (!bootstrapModal) {
            bootstrapModal = window.bootstrap.Modal.getOrCreateInstance(modalElement);
        }

        // Sync modal search input with main search input
        const modalSearchInput = document.getElementById('modal_search_input');
        if (modalSearchInput && searchInput) {
            modalSearchInput.value = searchInput.value.trim();
        }

        bootstrapModal.show();
    }

    // Update populateForm to use manager
    function populateForm(id, name, saveFileLocation, bannerUrl) {
        if (nameInput) nameInput.value = name;

        // Use manager to populate save locations
        saveLocationManager.populateLocations(saveFileLocation || '');

        if (bannerInput) bannerInput.value = bannerUrl;

        // Use shared updateBannerPreview function
        updateBannerPreview(bannerPreview, bannerUrl);

        const card = document.querySelector('.card');
        if (card && card.scrollIntoView) {
            card.scrollIntoView({ behavior: 'smooth' });
        }
    }

    /**
     * Display search results in a clean list format matching the app's dark theme
     * Shows game image, title, and save location in a minimalist design
     */
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

        // Create container for the list
        const listContainer = document.createElement('div');
        listContainer.className = 'p-0 m-0';

        games.forEach(game => {
            const gameId = String(game.id ?? '');
            const gameName = game.name ?? '';
            // Handle both old format (string) and new format (array)
            let saveLocation = '';
            if (game.save_file_locations && Array.isArray(game.save_file_locations)) {
                saveLocation = game.save_file_locations.join('\n');
            } else if (game.save_file_location) {
                // Fallback for old format
                saveLocation = game.save_file_location;
            }
            const bannerUrl = game.banner ?? '';
            const year = game.year ?? '';
            const company = game.company ?? '';

            // Create list item container
            const listItem = document.createElement('div');
            listItem.className = 'search-list-item';

            // Store raw values in data attributes (not HTML-escaped)
            listItem.dataset.gameId = gameId;
            listItem.dataset.gameName = gameName;
            listItem.dataset.saveLocation = saveLocation;
            listItem.dataset.bannerUrl = bannerUrl;

            // Hover effect is handled by CSS class .search-list-item:hover

            // Create image container
            if (bannerUrl && isValidImageUrl(bannerUrl)) {
                const imgContainer = document.createElement('div');
                imgContainer.className = 'search-img-container';

                const img = document.createElement('img');
                img.src = bannerUrl;
                img.alt = gameName;
                img.className = 'w-100 h-100 object-fit-cover';
                img.referrerPolicy = 'no-referrer';
                imgContainer.appendChild(img);
                listItem.appendChild(imgContainer);
            } else {
                // Placeholder for games without images
                const placeholder = document.createElement('div');
                placeholder.className = 'search-img-container d-flex align-items-center justify-content-center';
                const icon = document.createElement('i');
                icon.className = 'fas fa-gamepad text-white-50 fs-4';
                placeholder.appendChild(icon);
                listItem.appendChild(placeholder);
            }

            // Create text content container
            const textContainer = document.createElement('div');
            textContainer.className = 'search-text-container';

            // Primary title with year: "Game Name (Year)" in white
            const titleEl = document.createElement('div');
            titleEl.className = 'search-title';

            // Format title with year: "Game Name (Year)" or just "Game Name" if no year
            let titleText = gameName;
            if (year) {
                titleText = `${gameName} (${year})`;
            }
            titleEl.appendChild(document.createTextNode(titleText));

            // Secondary info: Company name in lighter grey
            const companyEl = document.createElement('div');
            companyEl.className = 'search-subtitle';
            companyEl.appendChild(document.createTextNode(company || ''));

            textContainer.appendChild(titleEl);
            textContainer.appendChild(companyEl);
            listItem.appendChild(textContainer);

            // Click handler – uses dataset values (not HTML)
            listItem.addEventListener('click', function (e) {
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

            listContainer.appendChild(listItem);
        });

        searchResults.appendChild(listContainer);
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
                window.showToast('Failed to search games: ' + data.error, 'error');
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

    /**
     * Trigger search from the modal search input
     * Syncs the main search input and performs the search
     */
    function triggerModalSearch() {
        const modalSearchInput = document.getElementById('modal_search_input');
        if (!modalSearchInput) return;

        const query = modalSearchInput.value.trim();
        if (query.length < 2) {
            return;
        }

        // Sync with main search input
        if (searchInput) {
            searchInput.value = query;
        }

        // Perform search
        clearTimeout(searchTimeout);
        searchGames(query);
    }

    function handleBannerInput() {
        const bannerUrl = bannerInput.value.trim();
        updateBannerPreview(bannerPreview, bannerUrl);
    }

    function clearForm() {
        if (nameInput) nameInput.value = '';
        if (bannerInput) bannerInput.value = '';

        // Use manager to reset save locations
        saveLocationManager.populateLocations('');

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

        const isHidden = searchSection.classList.contains('d-none');

        if (isHidden) {
            searchSection.classList.remove('d-none');
            toggleBtn.textContent = 'Hide Search';
        } else {
            searchSection.classList.add('d-none');
            toggleBtn.textContent = 'Search Game';
            clearElement(searchResults);
            if (searchInput) searchInput.value = '';
        }
    }

    // Uses shared utility functions from utils.js

    // Handle form submission via AJAX
    const addGameForm = document.getElementById('addGameForm');
    const saveGameBtn = document.getElementById('saveGameBtn');

    if (addGameForm && saveGameBtn) {
        addGameForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const csrfToken = window.getCsrfToken('#addGameForm input[name="csrfmiddlewaretoken"]');
            if (!csrfToken) {
                return;
            }

            const name = document.getElementById('name')?.value.trim();
            const saveLocations = saveLocationManager.getAllLocations();
            const banner = document.getElementById('banner')?.value.trim();

            const duplicateLocations = saveLocationManager.getDuplicateLocations();
            if (duplicateLocations.length > 0) {
                window.showToast('Duplicate save file locations are not allowed.', 'error');
                return;
            }

            if (!name || saveLocations.length === 0) {
                window.showToast('Game name and at least one save file location are required.', 'error');
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
                    headers: window.createFetchHeaders(csrfToken),
                    body: JSON.stringify({
                        name: name,
                        save_file_locations: saveLocations,
                        banner: banner || ''
                    })
                });

                // Check if response is JSON
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    // Server returned HTML (likely an error page)
                    const text = await response.text();
                    console.error('Server returned non-JSON response:', text.substring(0, 200));
                    window.showToast(`Server error (${response.status}): Please check the console for details.`, 'error');
                    return;
                }

                const data = await response.json();

                if (!response.ok) {
                    // HTTP error status
                    window.showToast(data.error || `Failed to create game (${response.status})`, 'error');
                    return;
                }

                if (data.success) {
                    window.showToast(data.message || 'Game created successfully!', 'success');
                    // Clear form after successful creation
                    clearForm();
                    // Reload page after a short delay to show the new game
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    window.showToast(data.error || 'Failed to create game', 'error');
                }
            } catch (error) {
                console.error('Error creating game:', error);
                if (error instanceof SyntaxError && error.message.includes('JSON')) {
                    window.showToast('Server returned invalid response. Please check the console.', 'error');
                } else {
                    window.showToast('Error: Failed to create game. Please try again.', 'error');
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
        searchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                triggerSearch();
            }
        });
    }

    // Wire up modal search input event listeners
    const modalSearchInput = document.getElementById('modal_search_input');
    if (modalSearchInput) {
        // Enter key to search
        modalSearchInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                triggerModalSearch();
            }
        });
    }

    // Expose a couple of helpers for inline handlers
    window.clearForm = clearForm;
    window.toggleSearch = toggleSearch;
    window.triggerSearch = triggerSearch;
    window.triggerModalSearch = triggerModalSearch;
    window.addSaveLocation = addSaveLocation;
    window.removeSaveLocation = removeSaveLocation;
});
