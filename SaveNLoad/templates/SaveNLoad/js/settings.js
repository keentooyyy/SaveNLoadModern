class GameSettings {
    constructor() {
        this.searchTimeout = null;
        this.searchInput = document.getElementById('search_input');
        // Results are rendered into the RAWG search modal
        this.modalElement = document.getElementById('gameSearchModal');
        this.searchResults = document.getElementById('modal_search_results');
        this.nameInput = document.getElementById('name');
        this.bannerInput = document.getElementById('banner');
        this.saveFileLocationInput = document.getElementById('save_file_location');
        this.gameIdInput = document.getElementById('game_id');
        this.bannerPreview = document.getElementById('banner_preview');
        this.searchUrl = this.searchInput ? this.searchInput.dataset.searchUrl : '';
        
        this.init();
    }

    init() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => this.handleSearchInput());
        }
        
        if (this.bannerInput) {
            this.bannerInput.addEventListener('input', () => this.handleBannerInput());
        }
    }

    handleSearchInput() {
        clearTimeout(this.searchTimeout);
        const query = this.searchInput.value.trim();
        
        if (query.length < 2) {
            this.clearElement(this.searchResults);
            return;
        }

        this.searchTimeout = setTimeout(() => {
            this.searchGames(query);
        }, 300);
    }

    async searchGames(query) {
        try {
            const response = await fetch(`${this.searchUrl}?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            this.displaySearchResults(data.games);
        } catch (error) {
            console.error('Search error:', error);
        }
    }

    displaySearchResults(games) {
        // Clear previous results safely
        this.clearElement(this.searchResults);

        if (!games || games.length === 0) {
            const p = document.createElement('p');
            p.className = 'text-muted';
            p.appendChild(document.createTextNode('No games found.'));
            this.searchResults.appendChild(p);

            // Still show the modal so the user sees the message
            this.showModal();
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
            link.className = 'list-group-item list-group-item-action';

            // Store raw values in data attributes (not HTML-escaped)
            link.dataset.gameId = gameId;
            link.dataset.gameName = gameName;
            link.dataset.saveLocation = saveLocation;
            link.dataset.bannerUrl = bannerUrl;

            const row = document.createElement('div');
            row.className = 'd-flex align-items-center';

            if (bannerUrl) {
                const img = document.createElement('img');
                img.src = bannerUrl;
                img.alt = gameName;
                img.className = 'me-3';
                img.style.width = '50px';
                img.style.height = '50px';
                img.style.objectFit = 'cover';
                row.appendChild(img);
            }

            const textWrapper = document.createElement('div');

            const titleEl = document.createElement('h6');
            titleEl.className = 'mb-0';
            titleEl.appendChild(document.createTextNode(gameName));

            const saveEl = document.createElement('small');
            saveEl.className = 'text-muted';
            saveEl.appendChild(document.createTextNode(saveLocation));

            textWrapper.appendChild(titleEl);
            textWrapper.appendChild(saveEl);
            row.appendChild(textWrapper);
            link.appendChild(row);
            listGroup.appendChild(link);

            // Click handler – uses dataset values (not HTML)
            link.addEventListener('click', (e) => {
                e.preventDefault();
                this.populateForm(
                    link.dataset.gameId || '',
                    link.dataset.gameName || '',
                    link.dataset.saveLocation || '',
                    link.dataset.bannerUrl || ''
                );

                // Close modal after selection
                if (this.bootstrapModal) {
                    this.bootstrapModal.hide();
                }
            });
        });

        this.searchResults.appendChild(listGroup);
        this.showModal();
    }

    populateForm(id, name, saveFileLocation, bannerUrl) {
        this.gameIdInput.value = id;
        this.nameInput.value = name;
        this.saveFileLocationInput.value = saveFileLocation;
        this.bannerInput.value = bannerUrl;
        
        this.updateBannerPreview(bannerUrl);
        
        // Scroll to top of form
        document.querySelector('.card')?.scrollIntoView({ behavior: 'smooth' });
    }

    handleBannerInput() {
        const bannerUrl = this.bannerInput.value.trim();
        this.updateBannerPreview(bannerUrl);
    }

    updateBannerPreview(bannerUrl) {
        this.clearElement(this.bannerPreview);

        if (!bannerUrl) {
            return;
        }

        const img = document.createElement('img');
        img.src = bannerUrl;
        img.alt = 'Banner preview';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'contain';
        img.className = 'img-thumbnail';

        img.onerror = () => {
            this.clearElement(this.bannerPreview);
            const p = document.createElement('p');
            p.className = 'text-muted small';
            p.appendChild(document.createTextNode('Invalid image URL'));
            this.bannerPreview.appendChild(p);
        };

        this.bannerPreview.appendChild(img);
    }

    clearForm() {
        this.gameIdInput.value = '';
        this.nameInput.value = '';
        this.bannerInput.value = '';
        this.saveFileLocationInput.value = '';
        this.clearElement(this.bannerPreview);
        if (this.searchInput) {
            this.searchInput.value = '';
        }
        this.clearElement(this.searchResults);
    }

    clearElement(element) {
        if (!element) return;
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    }

    showModal() {
        if (!this.modalElement || !window.bootstrap) {
            return;
        }

        if (!this.bootstrapModal) {
            this.bootstrapModal = window.bootstrap.Modal.getOrCreateInstance(this.modalElement);
        }
        this.bootstrapModal.show();
    }
}

// Toggle search section visibility
function toggleSearch() {
    const searchSection = document.getElementById('search_section');
    const toggleBtn = document.getElementById('toggle_search_btn');
    
    if (searchSection.style.display === 'none') {
        searchSection.style.display = 'block';
        toggleBtn.textContent = 'Hide Search';
    } else {
        searchSection.style.display = 'none';
        toggleBtn.textContent = 'Search Game';
        // Clear search results when hiding
        const searchResults = document.getElementById('modal_search_results');
        const searchInput = document.getElementById('search_input');
        if (searchResults && window.gameSettings) {
            window.gameSettings.clearElement(searchResults);
        }
        if (searchInput) searchInput.value = '';
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.gameSettings = new GameSettings();
    
    // Make clearForm available globally for the button onclick
    window.clearForm = () => {
        window.gameSettings.clearForm();
    };
    
    // Make toggleSearch available globally for the button onclick
    window.toggleSearch = toggleSearch;
});

