// Manage Accounts - Admin feature to manage user accounts
/**
 * Manage accounts module wrapper.
 *
 * Args:
 *     None
 *
 * Returns:
 *     None
 */
(function () {
    'use strict';

    // Pagination state
    let currentPage = 1;
    const defaultPageSize = 25;
    let paginationInfo = null;

    // Load users on page load
    /**
     * Initialize manage accounts UI handlers.
     *
     * Args:
     *     None
     *
     * Returns:
     *     None
     */
    document.addEventListener('DOMContentLoaded', function () {
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

            collapseElement.addEventListener('show.bs.collapse', function () {
                const chevron = document.getElementById('manageAccountsChevron');
                if (chevron) {
                    chevron.style.transform = 'rotate(90deg)';
                }
                if (headerButton) {
                    headerButton.classList.add('active');
                }
                loadUsers(1);
            });

            collapseElement.addEventListener('hide.bs.collapse', function () {
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
            searchBtn.addEventListener('click', function () {
                currentPage = 1; // Reset to first page on search
                loadUsers(1);
            });
        }

        // Setup search input enter key
        const searchInput = document.getElementById('userSearchInput');
        if (searchInput) {
            searchInput.addEventListener('keypress', function (e) {
                if (e.key === 'Enter') {
                    currentPage = 1; // Reset to first page on search
                    loadUsers(1);
                }
            });
        }
    });

    /**
     * Fetch users with pagination and optional search.
     *
     * Args:
     *     page: Page number to load.
     *
     * Returns:
     *     None
     */
    function loadUsers(page) {
        const usersContainer = document.getElementById('usersList');
        if (!usersContainer) return;

        const url = window.LIST_USERS_URL;
        if (!url) {
            if (window.clearElement) window.clearElement(usersContainer);
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
        if (window.clearElement) window.clearElement(usersContainer);
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
            headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : {
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
                    if (window.clearElement) window.clearElement(usersContainer);
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'text-danger';
                    errorDiv.textContent = 'Error: ' + (data.error || 'Failed to load users');
                    usersContainer.appendChild(errorDiv);
                }
            })
            .catch(error => {
                console.error('Error loading users:', error);
                if (window.clearElement) window.clearElement(usersContainer);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'text-danger';
                errorDiv.textContent = 'Error loading users: ' + error.message;
                usersContainer.appendChild(errorDiv);
            });
    }

    // clearContainer removed - using shared clearElement

    /**
     * Render the user list and pagination controls.
     *
     * Args:
     *     users: Array of user objects.
     *
     * Returns:
     *     None
     */
    function displayUsers(users) {
        const usersContainer = document.getElementById('usersList');
        if (!usersContainer) return;

        if (window.clearElement) window.clearElement(usersContainer);

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
            
            // Button container
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'd-flex gap-2';
            
            // Reset Password Button
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
            buttonContainer.appendChild(resetBtn);
            
            // Delete User Button
            const deleteBtn = document.createElement('button');
            deleteBtn.type = 'button';
            deleteBtn.className = 'btn btn-sm btn-danger text-white';
            
            const deleteIcon = document.createElement('i');
            deleteIcon.className = 'fas fa-trash me-1';
            deleteBtn.appendChild(deleteIcon);
            deleteBtn.appendChild(document.createTextNode('Delete'));
            
            deleteBtn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                deleteUser(user.id, user.username);
            };
            buttonContainer.appendChild(deleteBtn);
            
            actionsCell.appendChild(buttonContainer);
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
    /**
     * Build pagination controls for the user list.
     *
     * Args:
     *     pagination: Pagination metadata from the backend.
     *
     * Returns:
     *     Pagination container element.
     */
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

    // Create progress modal for user deletion
    /**
     * Build and show the deletion progress modal.
     *
     * Args:
     *     operationId: Operation identifier.
     *     username: Username being deleted.
     *
     * Returns:
     *     Modal data object used by the polling loop.
     */
    function createUserDeletionProgressModal(operationId, username) {
        const modalId = `progressModal_delete_user_${operationId}`;
        const modalBackdrop = document.createElement('div');
        modalBackdrop.className = 'modal fade';
        modalBackdrop.id = modalId;
        modalBackdrop.setAttribute('data-bs-backdrop', 'static');
        modalBackdrop.setAttribute('data-bs-keyboard', 'false');
        modalBackdrop.setAttribute('tabindex', '-1');
        modalBackdrop.setAttribute('aria-labelledby', `${modalId}Label`);
        modalBackdrop.setAttribute('aria-hidden', 'true');

        const modalDialog = document.createElement('div');
        modalDialog.className = 'modal-dialog modal-dialog-centered';

        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content bg-primary text-white border-0';

        const modalHeader = document.createElement('div');
        modalHeader.className = 'modal-header bg-primary border-secondary';

        const modalTitle = document.createElement('h5');
        modalTitle.className = 'modal-title text-white';
        modalTitle.id = `${modalId}Label`;
        modalTitle.textContent = `Deleting User: ${username}`;

        modalHeader.appendChild(modalTitle);

        const modalBody = document.createElement('div');
        modalBody.className = 'modal-body bg-primary';

        const progressBarWrapper = document.createElement('div');
        progressBarWrapper.className = 'progress mb-3';
        progressBarWrapper.style.height = '30px';
        progressBarWrapper.style.backgroundColor = getCSSVariable('--white-opacity-10') || 'rgba(255, 255, 255, 0.1)';

        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
        progressBar.setAttribute('role', 'progressbar');
        progressBar.style.width = '0%';
        progressBar.style.backgroundColor = getCSSVariable('--color-primary-bootstrap') || '#0d6efd';
        progressBar.setAttribute('aria-valuenow', '0');
        progressBar.setAttribute('aria-valuemin', '0');
        progressBar.setAttribute('aria-valuemax', '100');

        const progressText = document.createElement('div');
        progressText.className = 'text-center mt-3 text-white fs-6 fw-medium';
        progressText.textContent = 'Starting deletion...';

        const progressDetails = document.createElement('div');
        progressDetails.className = 'text-center text-white-50 mt-2 small';
        progressDetails.textContent = 'Cleaning up FTP server and removing user account...';

        progressBarWrapper.appendChild(progressBar);
        modalBody.appendChild(progressBarWrapper);
        modalBody.appendChild(progressText);
        modalBody.appendChild(progressDetails);

        modalContent.appendChild(modalHeader);
        modalContent.appendChild(modalBody);
        modalDialog.appendChild(modalContent);
        modalBackdrop.appendChild(modalDialog);

        document.body.appendChild(modalBackdrop);

        const modal = new bootstrap.Modal(modalBackdrop, {
            backdrop: 'static',
            keyboard: false
        });

        if (window.applyModalStacking) {
            window.applyModalStacking(modalBackdrop);
        }

        modal.show();

        const updateProgress = (progressData) => {
            const percentage = progressData.percentage || 0;
            const current = progressData.current || 0;
            const total = progressData.total || 0;
            const message = progressData.message || '';

            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);

            if (total > 0) {
                progressText.textContent = `${current}/${total} ${message || 'Processing...'}`;
                progressDetails.textContent = `${percentage}% complete`;
            } else if (message) {
                progressText.textContent = message;
            } else {
                progressText.textContent = 'Processing...';
                progressDetails.textContent = 'Please wait...';
            }
        };

        return { modal, modalBackdrop, modalContent, updateProgress, progressBar, progressText, progressDetails };
    }

    // Poll operation status for user deletion
    /**
     * Poll deletion progress and update modal state.
     *
     * Args:
     *     operationId: Operation identifier.
     *     modalData: Modal data returned by createUserDeletionProgressModal.
     *     username: Username being deleted.
     *
     * Returns:
     *     None
     */
    async function pollUserDeletionStatus(operationId, modalData, username) {
        const maxAttempts = 300; // 5 minutes max
        let attempts = 0;
        const pollInterval = 1000; // 1 second
        let consecutive404s = 0; // Track consecutive 404s

        const { modal, modalBackdrop, modalContent, updateProgress, progressBar, progressText, progressDetails } = modalData;

        const checkStatus = async () => {
            try {
                const urlPattern = window.CHECK_OPERATION_STATUS_URL_PATTERN;
                if (!urlPattern) {
                    throw new Error('Operation status URL not configured');
                }
                // Replace the placeholder '0' with the actual operation ID
                // URL pattern is like: /admin/operations/0/status/
                const url = urlPattern.replace('/0/', `/${operationId}/`);
                const response = await fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });

                // Handle 404 - for user deletion, operation may be deleted due to CASCADE
                // If the operation is gone, it likely means the user was deleted successfully
                if (response.status === 404) {
                    // Check if response has success data (backend may return success even for 404)
                    try {
                        const data = await response.json();
                        if (data.success && data.completed) {
                            // Backend returned success for missing operation (user deletion completed)
                            progressBar.classList.remove('progress-bar-animated');
                            progressBar.style.backgroundColor = getCSSVariable('--color-success') || '#198754';
                            progressBar.style.width = '100%';
                            progressBar.setAttribute('aria-valuenow', '100');
                            progressText.textContent = 'User Deleted Successfully!';
                            progressDetails.textContent = `User "${username}" has been permanently deleted`;
                            setTimeout(() => {
                                modal.hide();
                                setTimeout(() => {
                                    modalBackdrop.remove();
                                    // Reload page to refresh everything
                                    window.location.reload();
                                }, 300);
                            }, 1500);
                            return true;
                        }
                    } catch (e) {
                        // Not JSON, treat as real 404
                    }
                    // Real 404 - operation not found, but for user deletion this might mean success
                    // If we get multiple consecutive 404s (operation was deleted due to CASCADE), treat as success
                    consecutive404s++;
                    if (consecutive404s >= 2) {
                        // Operation is gone, which means user was deleted (CASCADE) - treat as success
                        progressBar.classList.remove('progress-bar-animated');
                        progressBar.style.backgroundColor = getCSSVariable('--color-success') || '#198754';
                        progressBar.style.width = '100%';
                        progressBar.setAttribute('aria-valuenow', '100');
                        progressText.textContent = 'User Deleted Successfully!';
                        progressDetails.textContent = `User "${username}" has been permanently deleted`;
                        setTimeout(() => {
                            modal.hide();
                            setTimeout(() => {
                                modalBackdrop.remove();
                                // Reload page to refresh everything
                                window.location.reload();
                            }, 300);
                        }, 1500);
                        return true;
                    }
                    return false;
                }

                if (!response.ok) {
                    throw new Error('Failed to check operation status');
                }

                const data = await response.json();

                // Reset 404 counter on successful response
                consecutive404s = 0;

                if (data.progress) {
                    updateProgress(data.progress);
                }

                if (data.completed) {
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-success') || '#198754';
                    progressBar.style.width = '100%';
                    progressBar.setAttribute('aria-valuenow', '100');
                    progressText.textContent = 'User Deleted Successfully!';
                    progressDetails.textContent = `User "${username}" has been permanently deleted`;
                    setTimeout(() => {
                        modal.hide();
                        setTimeout(() => {
                            modalBackdrop.remove();
                            // Reload page to refresh everything
                            window.location.reload();
                        }, 300);
                    }, 1500);
                    return true;
                } else if (data.failed) {
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-danger') || '#dc3545';
                    progressText.textContent = 'Deletion Failed';
                    progressDetails.textContent = data.message || 'An error occurred during deletion';
                    const modalFooter = document.createElement('div');
                    modalFooter.className = 'modal-footer bg-primary border-secondary';
                    const closeBtn = document.createElement('button');
                    closeBtn.type = 'button';
                    closeBtn.className = 'btn btn-outline-secondary text-white';
                    closeBtn.textContent = 'Close';
                    closeBtn.onclick = () => {
                        modal.hide();
                        modalBackdrop.remove();
                    };
                    modalFooter.appendChild(closeBtn);
                    modalContent.appendChild(modalFooter);
                    return true;
                }

                return false;
            } catch (error) {
                console.error('Error checking operation status:', error);
                return false;
            }
        };

        const completed = await checkStatus();
        if (completed) return;

        const poll = setInterval(async () => {
            attempts++;
            const completed = await checkStatus();

            if (completed || attempts >= maxAttempts) {
                clearInterval(poll);
                if (attempts >= maxAttempts && !completed) {
                    progressBar.classList.remove('progress-bar-animated');
                    progressBar.style.backgroundColor = getCSSVariable('--color-warning') || '#ffc107';
                    progressText.textContent = 'Operation Timed Out';
                    progressDetails.textContent = 'The operation is taking longer than expected. Please check the operation status manually.';
                    const modalFooter = document.createElement('div');
                    modalFooter.className = 'modal-footer bg-primary border-secondary';
                    const closeBtn = document.createElement('button');
                    closeBtn.type = 'button';
                    closeBtn.className = 'btn btn-outline-secondary text-white';
                    closeBtn.textContent = 'Close';
                    closeBtn.onclick = () => {
                        modal.hide();
                        modalBackdrop.remove();
                    };
                    modalFooter.appendChild(closeBtn);
                    modalContent.appendChild(modalFooter);
                }
            }
        }, pollInterval);
    }

    /**
     * Delete a user after confirmation and track progress if queued.
     *
     * Args:
     *     userId: User identifier.
     *     username: Username string.
     *
     * Returns:
     *     None
     */
    async function deleteUser(userId, username) {
        const confirmed = await window.customConfirm(
            `Are you sure you want to DELETE user "${username}"? This will permanently delete the account and all their save data from the server. This action cannot be undone.`
        );

        if (!confirmed) {
            return;
        }

        const url = window.DELETE_USER_URL_PATTERN ? window.DELETE_USER_URL_PATTERN.replace('0', userId) : null;
        if (!url) {
            window.showToast('Delete user URL not configured', 'error');
            return;
        }

        try {
            const response = await fetch(url, {
                method: 'DELETE',
                headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.getCsrfToken() || '',
                },
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (data.success) {
                // Check if operation was queued (has operation_id) or was immediate (no saves)
                if (data.operation_id) {
                    // Show progress modal and poll for status
                    const modalData = createUserDeletionProgressModal(data.operation_id, username);
                    pollUserDeletionStatus(data.operation_id, modalData, username);
                } else {
                    // Immediate deletion (no saves to clean up)
                    window.showToast(`User "${username}" deleted successfully`, 'success');
                    loadUsers(currentPage);
                }
            } else {
                window.showToast(data.error || 'Failed to delete user', 'error');
            }
        } catch (error) {
            console.error('Error deleting user:', error);
            window.showToast('Error deleting user. Please try again.', 'error');
        }
    }

    /**
     * Trigger a password reset for a user after confirmation.
     *
     * Args:
     *     userId: User identifier.
     *     username: Username string.
     *
     * Returns:
     *     None
     */
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
                headers: window.createFetchHeaders ? window.createFetchHeaders(window.getCsrfToken()) : {
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
