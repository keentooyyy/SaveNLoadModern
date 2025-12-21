document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('gameSearchInput');
    const sortSelect = document.getElementById('gameSortSelect');
    const gamesContainer = document.getElementById('availableGamesContainer');
    const isUserView = typeof window.IS_USER_VIEW !== 'undefined' && window.IS_USER_VIEW;
    
    // Get the search URL based on user type
    let searchUrl;
    if (isUserView) {
        if (!window.USER_SEARCH_GAMES_URL) {
            console.error('USER_SEARCH_GAMES_URL not defined');
            return;
        }
        searchUrl = window.USER_SEARCH_GAMES_URL;
    } else {
        if (!window.ADMIN_SEARCH_GAMES_URL) {
            console.error('ADMIN_SEARCH_GAMES_URL not defined');
            return;
        }
        searchUrl = window.ADMIN_SEARCH_GAMES_URL;
    }
    
    let searchTimeout = null;
    let isLoading = false;
    
    /**
     * Perform AJAX search and sort
     */
    function performSearch() {
        if (isLoading) return;
        
        const searchQuery = searchInput ? searchInput.value.trim() : '';
        const sortBy = sortSelect ? sortSelect.value : 'name_asc';
        
        // Build URL with query parameters
        const url = new URL(searchUrl, window.location.origin);
        if (searchQuery) {
            url.searchParams.set('q', searchQuery);
        }
        url.searchParams.set('sort', sortBy);
        
        isLoading = true;
        showLoadingState();
        
        fetch(url.toString(), {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
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
     * Render games in the container
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
        
        // Render each game
        games.forEach(game => {
            const gameCol = document.createElement('div');
            gameCol.className = 'col-12 col-sm-6 col-md-4 col-lg-3 col-xl-2 col-xxl-2 game-item';
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
     * Create game card element safely
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
     * Show loading state
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
     * Show error message
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
        reloadBtn.addEventListener('click', function() {
            location.reload();
        });
        
        centerDiv.appendChild(errorText);
        centerDiv.appendChild(reloadBtn);
        col.appendChild(centerDiv);
        gamesContainer.appendChild(col);
    }
    
    /**
     * Set search query and trigger search
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
     * Scroll to available games section
     */
    function scrollToAvailableGames() {
        const availableGamesSection = document.getElementById('availableGamesSection');
        if (availableGamesSection) {
            availableGamesSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    
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
    document.addEventListener('click', function(e) {
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

