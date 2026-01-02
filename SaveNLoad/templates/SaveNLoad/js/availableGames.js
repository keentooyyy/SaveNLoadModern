/**
 * Initialize available games search, sort, and rendering.
 *
 * Args:
 *     None
 *
 * Returns:
 *     None
 */
document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('gameSearchInput');
    const sortSelect = document.getElementById('gameSortSelect');
    const gamesContainer = document.getElementById('availableGamesContainer');
    const isUserView = typeof window.IS_USER_VIEW !== 'undefined' && window.IS_USER_VIEW;

    // Both admin and user search URLs point to the same backend endpoint
    const searchUrl = window.USER_SEARCH_GAMES_URL || window.ADMIN_SEARCH_GAMES_URL;
    if (!searchUrl) {
        console.error('Search URL not defined');
        return;
    }

    let searchTimeout = null;
    let isLoading = false;

    /**
     * Update browser URL with current filter state (without reloading).
     *
     * Args:
     *     searchQuery: Current search string.
     *     sortBy: Current sort option.
     *
     * Returns:
     *     None
     */
    function updateURLWithFilterState(searchQuery, sortBy) {
        const url = new URL(window.location);
        // Update or remove search query parameter
        if (searchQuery && searchQuery.trim()) {
            url.searchParams.set('q', searchQuery.trim());
        } else {
            url.searchParams.delete('q');
        }
        // Update or remove sort parameter (only if not default)
        if (sortBy && sortBy !== 'name_asc') {
            url.searchParams.set('sort', sortBy);
        } else {
            url.searchParams.delete('sort');
        }
        // Update URL without reloading page
        window.history.replaceState({}, '', url);
    }

    /**
     * Restore filter state from URL parameters on page load.
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    function restoreFilterStateFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const searchQuery = urlParams.get('q') || '';
        const sortBy = urlParams.get('sort') || 'name_asc';

        // Restore search input
        if (searchInput && searchQuery) {
            searchInput.value = searchQuery;
        }

        // Restore sort select
        if (sortSelect && sortBy) {
            sortSelect.value = sortBy;
        }

        // If there's a filter state in URL, trigger search to apply it
        if (searchQuery || (sortBy && sortBy !== 'name_asc')) {
            performSearch();
        }
    }

    /**
     * Perform AJAX search and sort.
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    function performSearch() {
        if (isLoading) return;

        const searchQuery = searchInput ? searchInput.value.trim() : '';
        const sortBy = sortSelect ? sortSelect.value : 'name_asc';

        // Update URL with current filter state (doesn't reload page)
        updateURLWithFilterState(searchQuery, sortBy);

        // Build URL with query parameters for AJAX request
        const url = new URL(searchUrl, window.location.origin);
        if (searchQuery) {
            url.searchParams.set('q', searchQuery);
        }
        url.searchParams.set('sort', sortBy);

        isLoading = true;
        showLoadingState();

        fetch(url.toString(), {
            method: 'GET',
            headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': window.getCsrfToken() || ''
            },
            credentials: 'same-origin'
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                isLoading = false;
                if (data.success) {
                    renderGames(data.games);
                } else {
                    showError(data.error || 'Failed to search games');
                }
            })
            .catch(error => {
                isLoading = false;
                console.error('Error searching games:', error);
                showError('Error searching games. Please try again.');
            });
    }

    /**
     * Render games in the container.
     *
     * Args:
     *     games: Array of game objects.
     *
     * Returns:
     *     None
     */
    function renderGames(games) {
        if (!gamesContainer) return;

        if (games.length === 0) {
            // Clear container safely
            while (gamesContainer.firstChild) {
                gamesContainer.removeChild(gamesContainer.firstChild);
            }

            // Create empty state
            const col = document.createElement('div');
            col.className = 'col-12';

            const centerDiv = document.createElement('div');
            centerDiv.className = 'text-center py-5';

            const p = document.createElement('p');
            p.className = 'text-white-50 mb-2';
            p.textContent = 'No games found';

            centerDiv.appendChild(p);
            col.appendChild(centerDiv);
            gamesContainer.appendChild(col);
            return;
        }

        // Clear container safely
        while (gamesContainer.firstChild) {
            gamesContainer.removeChild(gamesContainer.firstChild);
        }

        // Update global GAME_SAVE_PATHS object
        if (!window.GAME_SAVE_PATHS) {
            window.GAME_SAVE_PATHS = {};
        }
        games.forEach(game => {
            if (game.save_file_locations) {
                window.GAME_SAVE_PATHS[game.id] = game.save_file_locations;
            }
        });

        // Render each game
        games.forEach(game => {
            const gameCol = document.createElement('div');
            gameCol.className = 'col-12 col-sm-6 col-md-4 col-lg-3 col-xxl-2 game-item';
            gameCol.setAttribute('data-game-id', game.id);
            gameCol.setAttribute('data-game-title', game.title.toLowerCase());

            // Build game detail and delete URLs
            let gameDetailUrl = '';
            let gameDeleteUrl = '';

            if (!isUserView) {
                // Admin view - construct URLs using Django URL patterns
                if (window.GAME_DETAIL_URL_PATTERN) {
                    gameDetailUrl = window.GAME_DETAIL_URL_PATTERN.replace('0', game.id);
                }
                if (window.GAME_DELETE_URL_PATTERN) {
                    gameDeleteUrl = window.GAME_DELETE_URL_PATTERN.replace('0', game.id);
                }
            }

            // Create card element safely
            const cardElement = createGameCardElement(game, gameDetailUrl, gameDeleteUrl);
            gameCol.appendChild(cardElement);

            gamesContainer.appendChild(gameCol);
        });

        // Event listeners are handled by document-level delegation in saveLoad.js
        // No need to re-attach them
    }

    /**
     * Create game card element safely.
     *
     * Args:
     *     game: Game object to render.
     *     gameDetailUrl: Optional detail URL string.
     *     gameDeleteUrl: Optional delete URL string.
     *
     * Returns:
     *     DOM element for the game card.
     */
    function createGameCardElement(game, gameDetailUrl, gameDeleteUrl) {
        const card = document.createElement('div');
        card.className = 'card border-0 shadow h-100 game-card';
        card.setAttribute('data-game-id', game.id);
        if (gameDetailUrl) {
            card.setAttribute('data-game-detail-url', gameDetailUrl);
        }
        if (gameDeleteUrl) {
            card.setAttribute('data-game-delete-url', gameDeleteUrl);
        }

        if (game.image) {
            // Card with image
            const imgWrapper = document.createElement('div');
            imgWrapper.className = 'card-img-wrapper position-relative overflow-hidden bg-body';
            imgWrapper.style.height = '320px';

            const img = document.createElement('img');
            img.src = game.image;
            img.className = 'card-img-top w-100 h-100 game-card-img object-fit-cover';
            img.alt = game.title;

            const overlay = document.createElement('div');
            overlay.className = 'position-absolute bottom-0 start-0 end-0 p-3 game-card-overlay';

            const title = document.createElement('h5');
            title.className = 'card-title text-white fw-bold mb-1 fs-6';
            title.textContent = game.title;

            const footer = document.createElement('small');
            footer.className = 'text-white-50 d-flex align-items-center mb-2 small';

            const clockIcon = document.createElement('i');
            clockIcon.className = 'fas fa-clock me-1';
            footer.appendChild(clockIcon);
            footer.appendChild(document.createTextNode(' ' + game.footer));

            const buttonsDiv = document.createElement('div');
            buttonsDiv.className = 'd-flex gap-2 mt-2';

            const saveBtn = document.createElement('button');
            saveBtn.className = 'btn btn-sm btn-success save-game-btn flex-fill';
            saveBtn.setAttribute('data-game-id', game.id);
            saveBtn.setAttribute('title', 'Save Game to server');
            const saveIcon = document.createElement('i');
            saveIcon.className = 'fas fa-upload me-1';
            saveBtn.appendChild(saveIcon);
            saveBtn.appendChild(document.createTextNode(' Save'));

            const loadBtn = document.createElement('button');
            loadBtn.className = 'btn btn-sm btn-primary quick-load-btn flex-fill';
            loadBtn.setAttribute('data-game-id', game.id);
            loadBtn.setAttribute('title', 'Quick Load - Load most recent save');
            const loadIcon = document.createElement('i');
            loadIcon.className = 'fas fa-download me-1';
            loadBtn.appendChild(loadIcon);
            loadBtn.appendChild(document.createTextNode(' Quick Load'));

            buttonsDiv.appendChild(saveBtn);
            buttonsDiv.appendChild(loadBtn);

            overlay.appendChild(title);
            overlay.appendChild(footer);
            overlay.appendChild(buttonsDiv);

            imgWrapper.appendChild(img);
            imgWrapper.appendChild(overlay);
            card.appendChild(imgWrapper);
        } else {
            // Card without image
            const cardBody = document.createElement('div');
            cardBody.className = 'card-body d-flex align-items-center justify-content-center bg-body';
            cardBody.style.minHeight = '320px';

            const centerDiv = document.createElement('div');
            centerDiv.className = 'text-center w-100';

            const title = document.createElement('h5');
            title.className = 'card-title text-white mb-2';
            title.textContent = game.title;

            const footer = document.createElement('p');
            footer.className = 'text-white-50 mb-3 small';
            footer.textContent = game.footer;

            const buttonsDiv = document.createElement('div');
            buttonsDiv.className = 'd-flex gap-2 justify-content-center';

            const saveBtn = document.createElement('button');
            saveBtn.className = 'btn btn-sm btn-success save-game-btn';
            saveBtn.setAttribute('data-game-id', game.id);
            saveBtn.setAttribute('title', 'Save Game to server');
            const saveIcon = document.createElement('i');
            saveIcon.className = 'fas fa-upload me-1';
            saveBtn.appendChild(saveIcon);
            saveBtn.appendChild(document.createTextNode(' Save'));

            const loadBtn = document.createElement('button');
            loadBtn.className = 'btn btn-sm btn-primary quick-load-btn';
            loadBtn.setAttribute('data-game-id', game.id);
            loadBtn.setAttribute('title', 'Quick Load - Load most recent save');
            const loadIcon = document.createElement('i');
            loadIcon.className = 'fas fa-download me-1';
            loadBtn.appendChild(loadIcon);
            loadBtn.appendChild(document.createTextNode(' Quick Load'));

            buttonsDiv.appendChild(saveBtn);
            buttonsDiv.appendChild(loadBtn);

            centerDiv.appendChild(title);
            centerDiv.appendChild(footer);
            centerDiv.appendChild(buttonsDiv);

            cardBody.appendChild(centerDiv);
            card.appendChild(cardBody);
        }

        return card;
    }

    /**
     * Show loading state.
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    function showLoadingState() {
        if (!gamesContainer) return;

        // Clear container safely
        while (gamesContainer.firstChild) {
            gamesContainer.removeChild(gamesContainer.firstChild);
        }

        const col = document.createElement('div');
        col.className = 'col-12';

        const centerDiv = document.createElement('div');
        centerDiv.className = 'text-center py-5';

        const spinner = document.createElement('div');
        spinner.className = 'spinner-border text-primary';
        spinner.setAttribute('role', 'status');

        const spinnerText = document.createElement('span');
        spinnerText.className = 'visually-hidden';
        spinnerText.textContent = 'Loading...';
        spinner.appendChild(spinnerText);

        const loadingText = document.createElement('p');
        loadingText.className = 'text-white-50 mt-3 mb-2';
        loadingText.textContent = 'Searching games...';

        centerDiv.appendChild(spinner);
        centerDiv.appendChild(loadingText);
        col.appendChild(centerDiv);
        gamesContainer.appendChild(col);
    }

    /**
     * Show error message.
     *
     * Args:
     *     message: Error message string.
     *
     * Returns:
     *     None
     */
    function showError(message) {
        if (!gamesContainer) return;

        // Clear container safely
        while (gamesContainer.firstChild) {
            gamesContainer.removeChild(gamesContainer.firstChild);
        }

        const col = document.createElement('div');
        col.className = 'col-12';

        const centerDiv = document.createElement('div');
        centerDiv.className = 'text-center py-5';

        const errorText = document.createElement('p');
        errorText.className = 'text-danger mb-2';
        errorText.textContent = message;

        const reloadBtn = document.createElement('button');
        reloadBtn.className = 'btn btn-primary btn-sm';
        reloadBtn.textContent = 'Reload Page';
        reloadBtn.addEventListener('click', function () {
            location.reload();
        });

        centerDiv.appendChild(errorText);
        centerDiv.appendChild(reloadBtn);
        col.appendChild(centerDiv);
        gamesContainer.appendChild(col);
    }

    /**
     * Set search query and trigger search.
     *
     * Args:
     *     query: Search string to apply.
     *
     * Returns:
     *     None
     */
    function setSearchAndTrigger(query) {
        if (searchInput) {
            searchInput.value = query;
            // Clear any pending timeout
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            // Trigger search immediately
            performSearch();
        }
    }

    /**
     * Scroll to available games section.
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    function scrollToAvailableGames() {
        const availableGamesSection = document.getElementById('availableGamesSection');
        if (availableGamesSection) {
            availableGamesSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    // Restore filter state from URL on page load
    restoreFilterStateFromURL();

    // Event listeners
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            // Debounce search - wait 300ms after user stops typing
            if (searchTimeout) {
                clearTimeout(searchTimeout);
            }
            searchTimeout = setTimeout(performSearch, 300);
        });
    }

    if (sortSelect) {
        sortSelect.addEventListener('change', function () {
            performSearch();
        });
    }

    // Handle clicks on recent game cards
    document.addEventListener('click', function (e) {
        const recentCard = e.target.closest('.recent-game-card');
        if (recentCard) {
            const gameTitle = recentCard.getAttribute('data-game-title');
            if (gameTitle) {
                // Set search and trigger
                setSearchAndTrigger(gameTitle);
                // Scroll to available games section
                scrollToAvailableGames();
            }
        }
    });
});

