// Manage Accounts - Admin feature to manage user accounts
(function() {
    'use strict';

    // Pagination state
    let currentPage = 1;
    const defaultPageSize = 25;
    let paginationInfo = null;

    // Load users on page load
    document.addEventListener('DOMContentLoaded', function() {
        // Remove loadUsers() from here - only load when accordion opens
        
        // Setup accordion chevron rotation and highlight
        const collapseElement = document.getElementById('manageAccountsCollapse');
        const headerButton = document.querySelector('[data-bs-target="#manageAccountsCollapse"]');
        
        if (collapseElement) {
            // Check if accordion is already open on page load
            const isAlreadyOpen = collapseElement.classList.contains('show');
            
            // Load users if accordion is already open, otherwise wait for show event
            if (isAlreadyOpen) {
                loadUsers(1);
            }
            
            collapseElement.addEventListener('show.bs.collapse', function() {
                const chevron = document.getElementById('manageAccountsChevron');
                if (chevron) {
                    chevron.style.transform = 'rotate(90deg)';
                }
                if (headerButton) {
                    headerButton.classList.add('active');
                }
                loadUsers(1);
            });
            
            collapseElement.addEventListener('hide.bs.collapse', function() {
                const chevron = document.getElementById('manageAccountsChevron');
                if (chevron) {
                    chevron.style.transform = 'rotate(0deg)';
                }
                if (headerButton) {
                    headerButton.classList.remove('active');
                }
            });
        }
        
        // Setup search button
        const searchBtn = document.getElementById('userSearchBtn');
        if (searchBtn) {
            searchBtn.addEventListener('click', function() {
                currentPage = 1; // Reset to first page on search
                loadUsers(1);
            });
        }
        
        // Setup search input enter key
        const searchInput = document.getElementById('userSearchInput');
        if (searchInput) {
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    currentPage = 1; // Reset to first page on search
                    loadUsers(1);
                }
            });
        }
    });

    function loadUsers(page) {
        const usersContainer = document.getElementById('usersList');
        if (!usersContainer) return;
        
        const url = window.LIST_USERS_URL;
        if (!url) {
            clearContainer(usersContainer);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'text-danger';
            errorDiv.textContent = 'Users URL not configured';
            usersContainer.appendChild(errorDiv);
            return;
        }
        
        // Update current page
        if (page) {
            currentPage = page;
        }
        
        const searchInput = document.getElementById('userSearchInput');
        const searchQuery = searchInput ? searchInput.value.trim() : '';
        
        // Build URL with pagination and search parameters
        const params = new URLSearchParams();
        params.append('page', currentPage);
        params.append('page_size', defaultPageSize);
        if (searchQuery) {
            params.append('q', searchQuery);
        }
        const urlWithQuery = `${url}?${params.toString()}`;
        
        // Show loading
        clearContainer(usersContainer);
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
        usersContainer.appendChild(loadingDiv);
        
        fetch(urlWithQuery, {
            method: 'GET',
            headers: {
                'X-CSRFToken': window.getCsrfToken() || '',
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                paginationInfo = data.pagination || null;
                displayUsers(data.users || []);
            } else {
                clearContainer(usersContainer);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'text-danger';
                errorDiv.textContent = 'Error: ' + (data.error || 'Failed to load users');
                usersContainer.appendChild(errorDiv);
            }
        })
        .catch(error => {
            console.error('Error loading users:', error);
            clearContainer(usersContainer);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'text-danger';
            errorDiv.textContent = 'Error loading users: ' + error.message;
            usersContainer.appendChild(errorDiv);
        });
    }
    
    function clearContainer(container) {
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
    }

    function displayUsers(users) {
        const usersContainer = document.getElementById('usersList');
        if (!usersContainer) return;
        
        clearContainer(usersContainer);
        
        if (users.length === 0) {
            const noUsersDiv = document.createElement('div');
            noUsersDiv.className = 'text-center py-3 text-white-50';
            noUsersDiv.textContent = 'No users found.';
            usersContainer.appendChild(noUsersDiv);
            return;
        }
        
        // Create responsive table wrapper
        const tableWrapper = document.createElement('div');
        tableWrapper.className = 'table-responsive';
        
        // Create table matching the template style
        const table = document.createElement('table');
        table.className = 'table align-middle users-table';
        table.style.width = '100%';
        table.style.backgroundColor = 'transparent !important';
        table.setAttribute('style', 'width: 100%; background-color: transparent !important;');
        
        // Table header with dark theme styling
        const thead = document.createElement('thead');
        thead.className = 'users-table-header';
        thead.setAttribute('style', 'background-color: var(--sidebar-bg) !important;');
        const headerRow = document.createElement('tr');
        headerRow.setAttribute('style', 'background-color: var(--sidebar-bg) !important;');
        
        const headers = ['USERNAME', 'EMAIL', 'ROLE', 'ACTIONS'];
        headers.forEach(headerText => {
            const th = document.createElement('th');
            th.className = 'text-white-50 fw-bold';
            th.style.textTransform = 'uppercase';
            th.style.fontSize = '0.75rem';
            th.style.letterSpacing = '0.5px';
            th.style.padding = '1rem';
            th.style.borderBottom = '1px solid var(--white-opacity-10)';
            th.style.borderTop = 'none';
            th.style.backgroundColor = 'var(--sidebar-bg) !important';
            th.textContent = headerText;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Table body
        const tbody = document.createElement('tbody');
        users.forEach((user, index) => {
            const row = document.createElement('tr');
            row.style.borderBottom = '1px solid var(--white-opacity-10)';
            
            // Username
            const usernameCell = document.createElement('td');
            usernameCell.className = 'text-white';
            usernameCell.style.padding = '0.75rem';
            usernameCell.textContent = user.username;
            row.appendChild(usernameCell);
            
            // Email
            const emailCell = document.createElement('td');
            emailCell.className = 'text-white-50';
            emailCell.style.padding = '0.75rem';
            emailCell.textContent = user.email;
            row.appendChild(emailCell);
            
            // Role
            const roleCell = document.createElement('td');
            roleCell.style.padding = '0.75rem';
            const roleBadge = document.createElement('span');
            roleBadge.className = user.role === 'admin' ? 'badge bg-danger' : 'badge bg-secondary';
            roleBadge.textContent = user.role === 'admin' ? 'Admin' : 'User';
            roleCell.appendChild(roleBadge);
            row.appendChild(roleCell);
            
            // Actions
            const actionsCell = document.createElement('td');
            actionsCell.style.padding = '1rem';
            actionsCell.style.backgroundColor = 'transparent';
            const resetBtn = document.createElement('button');
            resetBtn.type = 'button';
            resetBtn.className = 'btn btn-sm btn-secondary text-white';
            
            // Safe DOM manipulation instead of innerHTML
            const resetIcon = document.createElement('i');
            resetIcon.className = 'fas fa-key me-1';
            resetBtn.appendChild(resetIcon);
            resetBtn.appendChild(document.createTextNode('Reset Password'));
            
            resetBtn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                resetUserPassword(user.id, user.username);
            };
            actionsCell.appendChild(resetBtn);
            row.appendChild(actionsCell);
            
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        
        tableWrapper.appendChild(table);
        usersContainer.appendChild(tableWrapper);
        
        // Add pagination controls - always show when paginationInfo exists
        if (paginationInfo) {
            const paginationDiv = createPaginationControls(paginationInfo);
            usersContainer.appendChild(paginationDiv);
        }
    }
    
    // Create pagination controls
    function createPaginationControls(pagination) {
        const paginationDiv = document.createElement('div');
        paginationDiv.className = 'd-flex justify-content-between align-items-center mt-3 pt-3';
        
        // Left side: Page info
        const infoDiv = document.createElement('div');
        infoDiv.className = 'text-white-50';
        infoDiv.style.fontSize = '0.875rem';
        const start = (pagination.page - 1) * pagination.page_size + 1;
        const end = Math.min(start + pagination.page_size - 1, pagination.total_count);
        infoDiv.textContent = `Showing ${start}-${end} of ${pagination.total_count} user(s)`;
        paginationDiv.appendChild(infoDiv);
        
        // Right side: Pagination buttons
        const navDiv = document.createElement('nav');
        const ul = document.createElement('ul');
        ul.className = 'pagination mb-0';
        
        // Previous button
        const prevLi = document.createElement('li');
        prevLi.className = `page-item ${!pagination.has_previous ? 'disabled' : ''}`;
        const prevBtn = document.createElement('button');
        prevBtn.type = 'button';
        prevBtn.className = 'page-link text-white bg-primary border-secondary';
        prevBtn.style.cursor = pagination.has_previous ? 'pointer' : 'not-allowed';
        // Add icon instead of text
        const prevIcon = document.createElement('i');
        prevIcon.className = 'fas fa-chevron-left';
        prevBtn.appendChild(prevIcon);
        prevBtn.setAttribute('aria-label', 'Previous page');
        if (pagination.has_previous) {
            prevBtn.onclick = () => loadUsers(pagination.page - 1);
        }
        prevLi.appendChild(prevBtn);
        ul.appendChild(prevLi);
        
        // Page numbers (show max 5 pages around current)
        const maxVisiblePages = 5;
        let startPage = Math.max(1, pagination.page - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(pagination.total_pages, startPage + maxVisiblePages - 1);
        
        // Adjust if we're near the end
        if (endPage - startPage < maxVisiblePages - 1) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }
        
        // First page if not visible
        if (startPage > 1) {
            const firstLi = document.createElement('li');
            firstLi.className = 'page-item';
            const firstBtn = document.createElement('button');
            firstBtn.type = 'button';
            firstBtn.className = 'page-link text-white bg-primary border-secondary';
            firstBtn.textContent = '1';
            firstBtn.onclick = () => loadUsers(1);
            firstLi.appendChild(firstBtn);
            ul.appendChild(firstLi);
            
            if (startPage > 2) {
                const ellipsisLi = document.createElement('li');
                ellipsisLi.className = 'page-item disabled';
                const ellipsisSpan = document.createElement('span');
                ellipsisSpan.className = 'page-link text-white-50 bg-primary border-secondary';
                ellipsisSpan.textContent = '...';
                ellipsisLi.appendChild(ellipsisSpan);
                ul.appendChild(ellipsisLi);
            }
        }
        
        // Page number buttons
        for (let i = startPage; i <= endPage; i++) {
            const pageLi = document.createElement('li');
            pageLi.className = `page-item ${i === pagination.page ? 'active' : ''}`;
            const pageBtn = document.createElement('button');
            pageBtn.type = 'button';
            pageBtn.className = 'page-link text-white bg-primary border-secondary';
            if (i === pagination.page) {
                pageBtn.style.backgroundColor = 'var(--color-primary)';
                pageBtn.style.borderColor = 'var(--color-primary)';
            }
            pageBtn.textContent = i.toString();
            pageBtn.onclick = () => loadUsers(i);
            pageLi.appendChild(pageBtn);
            ul.appendChild(pageLi);
        }
        
        // Last page if not visible
        if (endPage < pagination.total_pages) {
            if (endPage < pagination.total_pages - 1) {
                const ellipsisLi = document.createElement('li');
                ellipsisLi.className = 'page-item disabled';
                const ellipsisSpan = document.createElement('span');
                ellipsisSpan.className = 'page-link text-white-50 bg-primary border-secondary';
                ellipsisSpan.textContent = '...';
                ellipsisLi.appendChild(ellipsisSpan);
                ul.appendChild(ellipsisLi);
            }
            
            const lastLi = document.createElement('li');
            lastLi.className = 'page-item';
            const lastBtn = document.createElement('button');
            lastBtn.type = 'button';
            lastBtn.className = 'page-link text-white bg-primary border-secondary';
            lastBtn.textContent = pagination.total_pages.toString();
            lastBtn.onclick = () => loadUsers(pagination.total_pages);
            lastLi.appendChild(lastBtn);
            ul.appendChild(lastLi);
        }
        
        // Next button
        const nextLi = document.createElement('li');
        nextLi.className = `page-item ${!pagination.has_next ? 'disabled' : ''}`;
        const nextBtn = document.createElement('button');
        nextBtn.type = 'button';
        nextBtn.className = 'page-link text-white bg-primary border-secondary';
        nextBtn.style.cursor = pagination.has_next ? 'pointer' : 'not-allowed';
        // Add icon instead of text
        const nextIcon = document.createElement('i');
        nextIcon.className = 'fas fa-chevron-right';
        nextBtn.appendChild(nextIcon);
        nextBtn.setAttribute('aria-label', 'Next page');
        if (pagination.has_next) {
            nextBtn.onclick = () => loadUsers(pagination.page + 1);
        }
        nextLi.appendChild(nextBtn);
        ul.appendChild(nextLi);
        
        navDiv.appendChild(ul);
        paginationDiv.appendChild(navDiv);
        
        return paginationDiv;
    }

    async function resetUserPassword(userId, username) {
        const confirmed = await window.customConfirm(
            `Are you sure you want to reset the password for user "${username}"? `
        );
        
        if (!confirmed) {
            return;
        }
        
        const url = window.RESET_USER_PASSWORD_URL_PATTERN.replace('0', userId);
        if (!url) {
            window.showToast('Reset password URL not configured', 'error');
            return;
        }
        
        window.showToast('Resetting password...', 'info');
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.getCsrfToken() || '',
                },
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Get the password from response
                const password = data.password;
                const resetUsername = data.user?.username || username;
                
                // Show password in modal with highlighting
                if (password) {
                    // Use customConfirm and then modify the message to highlight password
                    const confirmPromise = window.customConfirm(
                        `Password reset successfully for user "${resetUsername}".\n\nNew Password: ${password}`
                    );
                    
                    // After a short delay, modify the message to highlight the password
                    setTimeout(() => {
                        const messageEl = document.getElementById('customConfirmMessage');
                        if (messageEl) {
                            const text = messageEl.textContent;
                            // Replace the password text with bold highlighted version
                            const parts = text.split(password);
                            if (parts.length === 2) {
                                messageEl.innerHTML = ''; // Clear first, but we'll rebuild safely
                                
                                // Safely create text nodes
                                const part1 = document.createTextNode(parts[0]);
                                const passwordSpan = document.createElement('span');
                                passwordSpan.className = 'fw-bold text-white';
                                passwordSpan.style.color = 'var(--color-primary)';
                                passwordSpan.style.fontSize = '1.1rem';
                                passwordSpan.textContent = password; // Safe - uses textContent
                                
                                const part2 = document.createTextNode(parts[1]);
                                
                                messageEl.appendChild(part1);
                                messageEl.appendChild(passwordSpan);
                                messageEl.appendChild(part2);
                            }
                        }
                    }, 100);
                    
                    await confirmPromise;
                } else {
                    // If no password in response, still show success
                    await window.customConfirm(
                        `Password reset successfully for user "${resetUsername}".\n\n` +
                        `The password has been reset to the default value.`
                    );
                }
                
                // Only refresh after modal is closed
                window.showToast(data.message || 'Password reset successfully', 'success');
                loadUsers(currentPage); // Reload current page instead of page 1
            } else {
                window.showToast(data.error || 'Failed to reset password', 'error');
            }
        } catch (error) {
            console.error('Error resetting password:', error);
            window.showToast('Error resetting password: ' + error.message, 'error');
        }
    }
})();
