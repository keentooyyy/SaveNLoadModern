/**
 * Shared utility functions for game form handling
 * Used by both settings.js and manageGames.js
 */

/**
 * Safely clear all children from an element
 *
 * Args:
 *     element: Container element to clear.
 *
 * Returns:
 *     None
 */
function clearElement(element) {
    if (!element) return;
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
}

/**
 * Validate if a URL is safe for image loading
 *
 * Args:
 *     url: URL string to validate.
 *
 * Returns:
 *     True if the URL is safe for image loading.
 */
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

/**
 * Update banner preview image
 *
 * Args:
 *     bannerPreviewElementOrId: Preview container element or its ID.
 *     bannerUrl: Banner URL to display.
 *
 * Returns:
 *     None
 */
function updateBannerPreview(bannerPreviewElementOrId, bannerUrl) {
    // Support both element ID (string) and element object
    let bannerPreviewElement;
    if (typeof bannerPreviewElementOrId === 'string') {
        bannerPreviewElement = document.getElementById(bannerPreviewElementOrId);
    } else {
        bannerPreviewElement = bannerPreviewElementOrId;
    }

    if (!bannerPreviewElement) {
        console.warn('Banner preview element not found');
        return;
    }

    clearElement(bannerPreviewElement);
    if (!bannerUrl) return;

    // Validate URL before using it
    if (!isValidImageUrl(bannerUrl)) {
        const p = document.createElement('p');
        p.className = 'text-white-50 small';
        p.appendChild(document.createTextNode('Invalid or unsafe URL'));
        bannerPreviewElement.appendChild(p);
        return;
    }

    const img = document.createElement('img');
    img.src = bannerUrl;
    img.alt = 'Banner preview';
    img.className = 'img-thumbnail w-100 h-100';
    img.style.objectFit = 'contain';
    // Security attributes
    img.loading = 'lazy';
    img.referrerPolicy = 'no-referrer';

    img.onerror = function () {
        clearElement(bannerPreviewElement);
        const p = document.createElement('p');
        p.className = 'text-white-50 small';
        p.appendChild(document.createTextNode('Failed to load image'));
        bannerPreviewElement.appendChild(p);
    };

    bannerPreviewElement.appendChild(img);
}

/**
 * Save Location Manager - handles multiple save location inputs
 *
 * Args:
 *     containerId: ID of the container element.
 *
 * Returns:
 *     None
 */
class SaveLocationManager {
    /**
     * Create a manager bound to the save location container.
     *
     * Args:
     *     containerId: ID of the container element.
     *
     * Returns:
     *     None
     */
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
    }

    /**
     * Create a default save location row
     *
     * Args:
     *     None
     *
     * Returns:
     *     Row element for a save location.
     */
    createRow() {
        const row = document.createElement('div');
        row.className = 'input-group mb-2 save-location-row';

        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'form-control bg-primary border border-1 border-secondary rounded-1 py-2 text-white save-location-input';
        input.placeholder = 'Enter save file location';
        input.required = true;

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-outline-danger text-white remove-location-btn';
        removeBtn.onclick = () => this.removeLocation(removeBtn);
        removeBtn.style.display = 'none';

        const removeIcon = document.createElement('i');
        removeIcon.className = 'fas fa-times';
        removeBtn.appendChild(removeIcon);

        row.appendChild(input);
        row.appendChild(removeBtn);

        return row;
    }

    /**
     * Add a new save location input field
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    addLocation() {
        if (!this.container) {
            // Refresh container reference
            this.container = document.getElementById(this.containerId);
        }
        if (!this.container) return;

        const newRow = this.createRow();
        this.container.appendChild(newRow);
        this.updateRemoveButtons();
    }

    /**
     * Remove a save location input field
     *
     * Args:
     *     btn: Remove button element that triggered the action.
     *
     * Returns:
     *     None
     */
    removeLocation(btn) {
        const row = btn.closest('.save-location-row');
        if (row && this.container) {
            row.remove();
            this.updateRemoveButtons();
        }
    }

    /**
     * Update visibility of remove buttons (hide if only one location)
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    updateRemoveButtons() {
        if (!this.container) {
            this.container = document.getElementById(this.containerId);
        }
        if (!this.container) return;

        const rows = this.container.querySelectorAll('.save-location-row');
        const removeButtons = this.container.querySelectorAll('.remove-location-btn');

        // Show remove buttons only if there are 2+ locations
        removeButtons.forEach(btn => {
            btn.style.display = rows.length > 1 ? 'block' : 'none';
        });
    }

    /**
     * Get all save locations from the form
     *
     * Args:
     *     None
     *
     * Returns:
     *     Array of save location strings.
     */
    getAllLocations() {
        if (!this.container) {
            this.container = document.getElementById(this.containerId);
        }
        if (!this.container) return [];

        const inputs = this.container.querySelectorAll('.save-location-input');
        const locations = [];
        inputs.forEach(input => {
            const value = input.value.trim();
            if (value) {
                locations.push(value);
            }
        });
        return locations;
    }

    /**
     * Get duplicate save locations (case-insensitive, slash-normalized)
     *
     * Args:
     *     None
     *
     * Returns:
     *     Array of duplicate locations.
     */
    getDuplicateLocations() {
        const locations = this.getAllLocations();
        const seen = new Set();
        const duplicates = new Set();

        locations.forEach(location => {
            const normalized = location.replace(/\\/g, '/').toLowerCase();
            if (seen.has(normalized)) {
                duplicates.add(location);
            } else {
                seen.add(normalized);
            }
        });

        return Array.from(duplicates);
    }

    /**
     * Populate save locations in the form
     *
     * Args:
     *     saveFileLocation: Newline-separated locations.
     *
     * Returns:
     *     None
     */
    populateLocations(saveFileLocation) {
        if (!this.container) {
            this.container = document.getElementById(this.containerId);
        }
        if (!this.container) return;

        // Clear existing rows
        while (this.container.firstChild) {
            this.container.removeChild(this.container.firstChild);
        }

        // Split by newline if multiple locations, otherwise use single location
        const locations = saveFileLocation ? saveFileLocation.split('\n').filter(loc => loc.trim()) : [];
        if (locations.length === 0) {
            // No locations, add one empty row
            const defaultRow = this.createRow();
            this.container.appendChild(defaultRow);
        } else {
            // Add rows for each location
            locations.forEach((location) => {
                const row = this.createRow();
                const input = row.querySelector('.save-location-input');
                if (input) {
                    input.value = location.trim();
                }
                this.container.appendChild(row);
            });
        }
        this.updateRemoveButtons();
    }

    /**
     * Get save locations as newline-separated string
     *
     * Args:
     *     None
     *
     * Returns:
     *     Newline-separated save location string.
     */
    getLocationsAsString() {
        const locations = this.getAllLocations();
        return locations.join('\n');
    }
}
