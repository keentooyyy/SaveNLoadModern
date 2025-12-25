// Operation Queue Management
(function() {
    'use strict';

    // Uses shared utility functions from utils.js

    // Load stats on page load
    document.addEventListener('DOMContentLoaded', function() {
        loadStats();
        
        // Setup accordion chevron rotation and highlight
        const collapseElement = document.getElementById('operationQueueCollapse');
        const headerButton = document.querySelector('[data-bs-target="#operationQueueCollapse"]');
        
        if (collapseElement) {
            collapseElement.addEventListener('show.bs.collapse', function() {
                const chevron = document.getElementById('operationQueueChevron');
                if (chevron) {
                    chevron.style.transform = 'rotate(90deg)';
                }
                // Add highlight effect
                if (headerButton) {
                    headerButton.classList.add('active');
                }
            });
            
            collapseElement.addEventListener('hide.bs.collapse', function() {
                const chevron = document.getElementById('operationQueueChevron');
                if (chevron) {
                    chevron.style.transform = 'rotate(0deg)';
                }
                // Remove highlight effect
                if (headerButton) {
                    headerButton.classList.remove('active');
                }
            });
        }
        
        // Setup clear button
        const clearBtn = document.getElementById('clearOperationsBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', async function() {
                const confirmed = await customConfirm('Are you sure you want to clear all operations? This cannot be undone!');
                if (confirmed) {
                    performCleanup('all', clearBtn);
                }
            });
        }
    });

    function loadStats() {
        const statsContainer = document.getElementById('operationQueueStats');
        if (!statsContainer) return;
        
        const url = window.OPERATION_QUEUE_STATS_URL;
        if (!url) {
            clearContainer(statsContainer);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'text-danger';
            errorDiv.textContent = 'Stats URL not configured';
            statsContainer.appendChild(errorDiv);
            return;
        }
        
        // Show loading
        clearContainer(statsContainer);
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'text-center py-3';
        const spinner = document.createElement('div');
        spinner.className = 'spinner-border text-light';
        spinner.setAttribute('role', 'status');
        const spinnerSpan = document.createElement('span');
        spinnerSpan.className = 'visually-hidden';
        spinnerSpan.textContent = 'Loading...';
        spinner.appendChild(spinnerSpan);
        loadingDiv.appendChild(spinner);
        statsContainer.appendChild(loadingDiv);
        
        fetch(url, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // json_response_success merges data into response, so stats are at top level
                const stats = {
                    total: data.total,
                    by_status: data.by_status,
                    by_type: data.by_type,
                    old_count_30_days: data.old_count_30_days,
                    stuck_count: data.stuck_count
                };
                displayStats(stats);
            } else {
                clearContainer(statsContainer);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'text-danger';
                errorDiv.textContent = 'Error: ' + (data.error || 'Failed to load stats');
                statsContainer.appendChild(errorDiv);
            }
        })
        .catch(error => {
            console.error('Error loading stats:', error);
            clearContainer(statsContainer);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'text-danger';
            errorDiv.textContent = 'Error loading stats: ' + error.message;
            statsContainer.appendChild(errorDiv);
        });
    }
    
    function clearContainer(container) {
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
    }

    function displayStats(stats) {
        const statsContainer = document.getElementById('operationQueueStats');
        if (!statsContainer || !stats) return;
        
        clearContainer(statsContainer);
        
        const total = stats.total || 0;
        const byStatus = stats.by_status || {};
        const oldCount = stats.old_count_30_days || 0;
        const stuckCount = stats.stuck_count || 0;
        
        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = 'mb-3';
        
        // Helper function to create stat row
        function createStatRow(label, value, valueClass = 'text-white') {
            const row = document.createElement('div');
            row.className = 'd-flex justify-content-between align-items-center mb-2';
            
            const labelSpan = document.createElement('span');
            labelSpan.className = 'text-white-50';
            labelSpan.textContent = label;
            
            const valueSpan = document.createElement('span');
            valueSpan.className = valueClass;
            valueSpan.textContent = value;
            
            row.appendChild(labelSpan);
            row.appendChild(valueSpan);
            return row;
        }
        
        wrapperDiv.appendChild(createStatRow('Total Operations:', total, 'text-white fw-bold'));
        wrapperDiv.appendChild(createStatRow('Pending:', byStatus.pending || 0));
        wrapperDiv.appendChild(createStatRow('In Progress:', byStatus.in_progress || 0));
        wrapperDiv.appendChild(createStatRow('Completed:', byStatus.completed || 0));
        wrapperDiv.appendChild(createStatRow('Failed:', byStatus.failed || 0));
        
        if (oldCount > 0 || stuckCount > 0) {
            const hr = document.createElement('hr');
            hr.className = 'border-secondary my-3';
            wrapperDiv.appendChild(hr);
            
            if (oldCount > 0) {
                wrapperDiv.appendChild(createStatRow('Operations 30+ days old:', oldCount, 'text-warning'));
            }
            if (stuckCount > 0) {
                wrapperDiv.appendChild(createStatRow('Stuck operations (1+ hour):', stuckCount, 'text-danger'));
            }
        }
        
        statsContainer.appendChild(wrapperDiv);
    }

    function performCleanup(type, button) {
        // Disable button and show loading
        const originalContent = button.cloneNode(true);
        button.disabled = true;
        
        // Clear button content and add spinner
        clearContainer(button);
        const spinner = document.createElement('span');
        spinner.className = 'spinner-border spinner-border-sm me-2';
        spinner.setAttribute('role', 'status');
        const spinnerSpan = document.createElement('span');
        spinnerSpan.className = 'visually-hidden';
        spinnerSpan.textContent = 'Loading...';
        spinner.appendChild(spinnerSpan);
        button.appendChild(spinner);
        const text = document.createTextNode('Clearing...');
        button.appendChild(text);
        
        const url = window.OPERATION_QUEUE_CLEANUP_URL;
        if (!url) {
            window.showToast('Cleanup URL not configured', 'error');
            button.disabled = false;
            button.replaceWith(originalContent);
            return;
        }
        
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            credentials: 'same-origin',
            body: JSON.stringify({ type: type })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.showToast(data.message || 'Cleanup completed successfully', 'success');
                loadStats(); // Refresh stats
            } else {
                window.showToast(data.error || 'Cleanup failed', 'error');
            }
        })
        .catch(error => {
            console.error('Error performing cleanup:', error);
            window.showToast('Error performing cleanup: ' + error.message, 'error');
        })
        .finally(() => {
            button.disabled = false;
            // Restore original content
            clearContainer(button);
            const icon = document.createElement('i');
            icon.className = 'fas fa-trash me-1';
            button.appendChild(icon);
            button.appendChild(document.createTextNode('Clear All Operations'));
        });
    }

    function getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        // Fallback: try to get from form
        const form = document.querySelector('form');
        if (form) {
            const csrfInput = form.querySelector('input[name="csrfmiddlewaretoken"]');
            if (csrfInput) {
                return csrfInput.value;
            }
        }
        return '';
    }
})();

