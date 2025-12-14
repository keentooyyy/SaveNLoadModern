// Expandable card hover functionality
// Configuration: Delay in milliseconds for expand and collapse actions
const HOVER_DELAY_MS = 500; // Change this value to adjust delay (500 = 0.5 seconds)

document.addEventListener('DOMContentLoaded', function() {
    const expandableCards = document.querySelectorAll('.expandable-card');
    const expandTimeouts = new Map();
    const collapseTimeouts = new Map();

    expandableCards.forEach((card, index) => {
        const cardBody = card.querySelector('.card-body');
        const cardImage = card.querySelector('.card-img-left');
        
        // Initialize collapsed state - show only image
        if (cardBody) {
            cardBody.style.maxWidth = '0';
            cardBody.style.width = '0';
            cardBody.style.opacity = '0';
            cardBody.style.visibility = 'hidden';
            cardBody.style.overflow = 'hidden';
            cardBody.style.paddingLeft = '0';
            cardBody.style.paddingRight = '0';
        }
        if (cardImage) {
            cardImage.style.width = '100%';
            cardImage.style.borderRadius = '0.375rem'; // Full border radius when collapsed
        }

        card.addEventListener('mouseenter', function() {
            // Clear any existing collapse timeout
            if (collapseTimeouts.has(index)) {
                clearTimeout(collapseTimeouts.get(index));
                collapseTimeouts.delete(index);
            }

            // Clear any existing expand timeout
            if (expandTimeouts.has(index)) {
                clearTimeout(expandTimeouts.get(index));
            }

            // Set timeout to expand
            const timeout = setTimeout(function() {
                card.style.width = '800px';
                if (cardBody) {
                    cardBody.style.maxWidth = '66.667%';
                    cardBody.style.width = '66.667%';
                    cardBody.style.opacity = '1';
                    cardBody.style.visibility = 'visible';
                    cardBody.style.paddingLeft = '';
                    cardBody.style.paddingRight = '';
                }
                if (cardImage) {
                    cardImage.style.width = '33.333%';
                    cardImage.style.borderRadius = '0.375rem 0 0 0.375rem'; // Only left corners when expanded
                }
                expandTimeouts.delete(index);
            }, HOVER_DELAY_MS);
            
            expandTimeouts.set(index, timeout);
        });

        card.addEventListener('mouseleave', function() {
            // Clear expand timeout if mouse leaves before 0.5s
            if (expandTimeouts.has(index)) {
                clearTimeout(expandTimeouts.get(index));
                expandTimeouts.delete(index);
            }

            // Clear any existing collapse timeout
            if (collapseTimeouts.has(index)) {
                clearTimeout(collapseTimeouts.get(index));
            }

            // Set timeout before collapsing
            const collapseTimeout = setTimeout(function() {
                // Collapse card - hide body completely
                card.style.width = '266px';
                if (cardBody) {
                    cardBody.style.maxWidth = '0';
                    cardBody.style.width = '0';
                    cardBody.style.opacity = '0';
                    cardBody.style.visibility = 'hidden';
                    cardBody.style.paddingLeft = '0';
                    cardBody.style.paddingRight = '0';
                }
                if (cardImage) {
                    cardImage.style.width = '100%';
                    cardImage.style.borderRadius = '0.375rem'; // Full border radius when collapsed
                }
                collapseTimeouts.delete(index);
            }, HOVER_DELAY_MS);

            collapseTimeouts.set(index, collapseTimeout);
        });
    });
});

