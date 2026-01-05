// Horizontal scroll with mouse wheel and arrow buttons
/**
 * Initialize horizontal scrolling behavior and button states.
 *
 * Args:
 *     None
 *
 * Returns:
 *     None
 */
document.addEventListener('DOMContentLoaded', function() {
    const scrollContainer = document.getElementById('cardsScrollContainer');
    if (!scrollContainer) return;

    const scrollLeftBtn = document.querySelector('.scroll-left');
    const scrollRightBtn = document.querySelector('.scroll-right');

    // Mouse wheel horizontal scrolling - convert vertical scroll to horizontal
    /**
     * Convert vertical wheel input into horizontal scrolling.
     *
     * Args:
     *     e: Wheel event.
     *
     * Returns:
     *     None
     */
    scrollContainer.addEventListener('wheel', function(e) {
        // Check if user is scrolling vertically (most common case)
        if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
            e.preventDefault();
            scrollContainer.scrollLeft += e.deltaY;
        } else if (e.deltaX !== 0) {
            // If already scrolling horizontally, allow it
            e.preventDefault();
            scrollContainer.scrollLeft += e.deltaX;
        }
    }, { passive: false });

    // Arrow button navigation
    if (scrollLeftBtn) {
        scrollLeftBtn.addEventListener('click', function() {
            scrollContainer.scrollBy({
                left: -scrollContainer.offsetWidth * 0.8,
                behavior: 'smooth'
            });
        });
    }

    if (scrollRightBtn) {
        scrollRightBtn.addEventListener('click', function() {
            scrollContainer.scrollBy({
                left: scrollContainer.offsetWidth * 0.8,
                behavior: 'smooth'
            });
        });
    }

    // Update arrow button visibility based on scroll position
    /**
     * Update arrow button state based on current scroll position.
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    function updateArrowButtons() {
        const { scrollLeft, scrollWidth, clientWidth } = scrollContainer;
        const isAtStart = scrollLeft <= 0;
        const isAtEnd = scrollLeft >= scrollWidth - clientWidth - 1;

        if (scrollLeftBtn) {
            scrollLeftBtn.style.opacity = isAtStart ? '0.5' : '1';
            scrollLeftBtn.disabled = isAtStart;
            // Opacity needs to be set via style for smooth transitions
        }
        if (scrollRightBtn) {
            scrollRightBtn.style.opacity = isAtEnd ? '0.5' : '1';
            scrollRightBtn.disabled = isAtEnd;
            // Opacity needs to be set via style for smooth transitions
        }
    }

    // Initial check and on scroll
    updateArrowButtons();
    scrollContainer.addEventListener('scroll', updateArrowButtons);
    
    // Also check on resize
    window.addEventListener('resize', updateArrowButtons);
});

