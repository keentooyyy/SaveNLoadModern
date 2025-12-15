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

        img.onerror = function () {
            clearElement(bannerPreview);
            const p = document.createElement('p');
            p.className = 'text-muted small';
            p.appendChild(document.createTextNode('Invalid image URL'));
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

    // Click handler on available games grid
    section.addEventListener('click', function (e) {
        const card = e.target.closest('.game-card[data-game-id]');
        if (!card) return;

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

        loadGame(currentDetailUrl).then(function () {
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
});


