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

    function updateBannerPreview(bannerUrl) {
        clearElement(bannerPreview);
        if (!bannerUrl) return;

        const img = document.createElement('img');
        img.src = bannerUrl;
        img.alt = 'Banner preview';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'contain';
        img.className = 'img-thumbnail';

        img.onerror = () => {
            clearElement(bannerPreview);
            const p = document.createElement('p');
            p.className = 'text-muted small';
            p.appendChild(document.createTextNode('Invalid image URL'));
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
            p.className = 'text-muted';
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

    async function searchGames(query) {
        try {
            const response = await fetch(`${searchUrl}?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            displaySearchResults(data.games);
        } catch (error) {
            console.error('Search error:', error);
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

    // Wire up events
    if (bannerInput) {
        bannerInput.addEventListener('input', handleBannerInput);
    }

    // Expose a couple of helpers for inline handlers
    window.clearForm = clearForm;
    window.toggleSearch = toggleSearch;
    window.triggerSearch = triggerSearch;
});