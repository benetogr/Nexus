console.log('Script loading...'); // Add at very top of file

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    
    // Update Sync button functionality
    document.getElementById('syncButton').addEventListener('click', function() {
        if (!confirm('Are you sure you want to sync with LDAP now?')) {
            return;
        }
        
        const button = this;
        button.disabled = true;
        button.textContent = 'Syncing...';
        
        fetch('/sync', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.has_conflicts) {
                    alert(`Sync completed with ${data.conflicts} conflicts that need resolution.`);
                } else {
                    alert('Sync completed successfully');
                }
                location.reload();
            } else {
                alert('Sync failed: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Sync error:', error);
            alert('Sync failed. Check console for details.');
        })
        .finally(() => {
            button.disabled = false;
            button.textContent = 'Sync Now';
        });
    });

    // Enhanced Search functionality (fixed)
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');

    function performSearch() {
        const searchTerm = document.getElementById('searchInput').value;
        const currentUrl = new URL(window.location);
        currentUrl.searchParams.set('search', searchTerm);
        window.location.href = currentUrl.toString();
    }

    // Remove the problematic removeEventListener line
    if (searchButton) {
        searchButton.onclick = performSearch;
    }

    if (searchInput) {
        searchInput.onkeyup = function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        };
    }

    // Search on button click
    if (searchButton) {
        searchButton.addEventListener('click', performSearch);
    }

    // Search on Enter key
    if (searchInput) {
        searchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }

    // LDAP Test functionality
    const testButton = document.querySelector('#testLdapButton');
    const statusElement = document.querySelector('#ldapStatus');
    
    if (testButton && statusElement) {
        testButton.addEventListener('click', function() {
            console.log('Test button clicked');
            statusElement.textContent = 'Testing connection...';
            statusElement.className = 'connection-status testing';
            
            fetch('/test-ldap', getFetchOptions('POST'))
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log('LDAP test response:', data);
                statusElement.textContent = data.message;
                statusElement.className = 'connection-status ' + (data.success ? 'success' : 'error');
            })
            .catch(error => {
                console.error('LDAP test error:', error);
                statusElement.textContent = 'Connection test failed: ' + error.message;
                statusElement.className = 'connection-status error';
            });
        });
    }

    // CUCM Test functionality
    const cucmTestButton = document.getElementById('testCucmButton');
    const cucmTestModal = document.getElementById('cucmTestModal');
    
    console.log('CUCM Test Button:', cucmTestButton);  // Check if button exists
    console.log('CUCM Test Modal:', cucmTestModal);    // Check if modal exists
    
    if (cucmTestButton) {
        console.log('Adding click handler to CUCM test button');
        cucmTestButton.addEventListener('click', function() {
            console.log('CUCM test button clicked');  // Check if click handler fires
            const modal = document.getElementById('cucmTestModal');
            const resultDiv = document.getElementById('cucmTestResult');
            
            console.log('Modal element:', modal);        // Check if modal is found
            console.log('Result div:', resultDiv);       // Check if result div is found
            
            // Show modal with loading message
            modal.style.display = 'block';
            document.body.classList.add('modal-open');
            resultDiv.innerHTML = '<div class="loading">Testing CUCM connection...</div>';
            
            fetch('/test-cucm', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    resultDiv.innerHTML = `
                        <div class="success">
                            <svg viewBox="0 0 24 24" width="48" height="48">
                                <path fill="#28a745" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                            </svg>
                            <p>${data.message}</p>
                        </div>`;
                } else {
                    resultDiv.innerHTML = `
                        <div class="error">
                            <svg viewBox="0 0 24 24" width="48" height="48">
                                <path fill="#dc3545" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/>
                            </svg>
                            <p>${data.message}</p>
                        </div>`;
                }
            })
            .catch(error => {
                resultDiv.innerHTML = `
                    <div class="error">
                        <svg viewBox="0 0 24 24" width="48" height="48">
                            <path fill="#dc3545" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/>
                        </svg>
                        <p>Connection test failed: ${error.message}</p>
                    </div>`;
            });
        });
    } else {
        console.error('CUCM Test Button not found in DOM');
    }

    // Add this function to close the CUCM test modal
    window.closeCucmTestModal = function() {
        document.getElementById('cucmTestModal').style.display = 'none';
        document.body.classList.remove('modal-open');
    };

    // Modal initialization
    // Close modal when clicking outside
    window.onclick = function(event) {
        const editModal = document.getElementById('editModal');
        const historyModal = document.getElementById('historyModal');
        if (event.target == editModal) {
            closeModal();
        } else if (event.target == historyModal) {
            closeHistoryModal();
        }
    };

    // Close button in modal
    const closeBtn = document.getElementsByClassName('close')[0];
    if (closeBtn) {
        closeBtn.onclick = closeModal;
    }

    // Add form submission handler
    const editForm = document.getElementById('editForm');
    if (editForm) {
        editForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const modal = document.getElementById('editModal');
            const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
            
            const formData = new FormData(this);
            const jsonData = {};
            formData.forEach((value, key) => {
                jsonData[key] = value;
            });

            fetch(this.action, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(jsonData)
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    modal.style.display = 'none';
                    document.body.classList.remove('modal-open');
                    window.location.href = '/';
                } else {
                    throw new Error(data.error || 'Unknown error occurred');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error saving changes: ' + error.message);
            });
        });
    }

    // Add MAC address formatting
    const macInput = document.getElementById('mac_address');
    if (macInput) {
        macInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^0-9a-fA-F]/g, '');
            if (value.length > 12) value = value.slice(0, 12);
            
            // Format with colons
            let formatted = '';
            for (let i = 0; i < value.length; i++) {
                if (i > 0 && i % 2 === 0) formatted += ':';
                formatted += value[i];
            }
            
            e.target.value = formatted.toUpperCase();
        });

        macInput.addEventListener('invalid', function(e) {
            e.target.setCustomValidity('Please enter a valid MAC address (e.g., 00:11:22:33:44:55)');
        });

        macInput.addEventListener('input', function(e) {
            e.target.setCustomValidity('');
        });
    }

    // Filters functionality
    const filtersButton = document.getElementById('filtersButton');
    const filtersModal = document.getElementById('filtersModal');
    
    if (filtersButton) {
        filtersButton.addEventListener('click', function() {
            filtersModal.style.display = 'block';
            document.body.classList.add('modal-open');
        });
    }

    // Initialize filters from URL params
    initializeFilters();

    // Load and apply saved filters
    const savedFilters = localStorage.getItem('contactFilters');
    if (savedFilters) {
        const filterState = JSON.parse(savedFilters);
        document.getElementById('filterHasPin').checked = filterState.hasPin;
        document.getElementById('filterHasMac').checked = filterState.hasMac;
        document.getElementById('filterShowRetired').checked = filterState.showRetired;
        document.getElementById('filterPhoneModel').value = filterState.phoneModel;
        document.getElementById('filterDepartment').value = filterState.department; // Add this line
        applyFilters(); // Apply the loaded filters
    }

    // Add event listener for LDAP search button
    const ldapSearchButton = document.getElementById('ldapSearchButton');
    if (ldapSearchButton) {
        ldapSearchButton.addEventListener('click', function() {
            document.getElementById('ldapSearchModal').style.display = 'block';
            document.body.classList.add('modal-open');
        });
    }

    // Update page size selector handler
    const pageSizeSelect = document.getElementById('pageSizeSelect');
    if (pageSizeSelect) {
        pageSizeSelect.addEventListener('change', function() {
            const currentUrl = new URL(window.location);
            
            // Keep all existing parameters
            const params = currentUrl.searchParams;
            
            // Update per_page parameter
            params.set('per_page', this.value);
            // Reset to first page
            params.set('page', '1');
            
            // Force page reload with new URL
            window.location.href = currentUrl.toString();
        });
    }

    // Add export button handler
    const exportButton = document.getElementById('exportButton');
    if (exportButton) {
        exportButton.addEventListener('click', function() {
            window.location.href = '/export-csv';
        });
    }

    // Add new contact button handler
    document.getElementById('newContactButton').addEventListener('click', showNewContactModal);
    
    // Add MAC address formatting for new contact form
    const newMacInput = document.getElementById('new_mac_address');
    if (newMacInput) {
        newMacInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^0-9a-fA-F]/g, '');
            if (value.length > 12) value = value.slice(0, 12);
            
            // Format with colons
            let formatted = '';
            for (let i = 0; i < value.length; i++) {
                if (i > 0 && i % 2 === 0) formatted += ':';
                formatted += value[i];
            }
            
            e.target.value = formatted.toUpperCase();
        });
    }
});

// Add this helper function at the start of the file
function getFetchOptions(method = 'GET', body = null) {
    const options = {
        method: method,
        headers: {
            'Accept': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    };
    
    if (body) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(body);
    }
    
    return options;
}

// Make functions globally accessible
window.deleteContact = function(contactId) {
    if (confirm('Are you sure you want to delete this contact?')) {
        fetch(`/contact/${contactId}/delete`, getFetchOptions('POST'))
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            }
        });
    }
};

window.editContact = function(contactId) {
    const modal = document.getElementById('editModal');
    const form = document.getElementById('editForm');
    
    // Prevent background scroll
    document.body.classList.add('modal-open');
    
    fetch(`/contact/${contactId}`, getFetchOptions())
    .then(response => response.json())
    .then(contact => {
        // Populate all fields
        document.getElementById('first_name').value = contact.first_name || '';
        document.getElementById('last_name').value = contact.last_name || '';
        document.getElementById('email').value = contact.email || '';
        document.getElementById('phone').value = contact.phone || '';
        document.getElementById('phone_model').value = contact.phone_model || '';
        document.getElementById('mac_address').value = contact.mac_address || '';
        document.getElementById('pin').value = contact.pin || '';
        document.getElementById('notes').value = contact.notes || '';
        document.getElementById('department').value = contact.department || '';
        document.getElementById('title').value = contact.title || '';
        
        form.action = `/contact/${contactId}/update`;
        modal.style.display = 'block';
    })
    .catch(error => {
        console.error('Error loading contact:', error);
        alert('Error loading contact details');
        document.body.classList.remove('modal-open');
    });
};

window.restoreContact = function(contactId) {
    fetch(`/contact/${contactId}/restore`, getFetchOptions('POST'))
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
};

window.closeModal = function() {
    document.getElementById('editModal').style.display = 'none';
    document.body.classList.remove('modal-open');
};

window.closeFiltersModal = function() {
    document.getElementById('filtersModal').style.display = 'none';
    document.body.classList.remove('modal-open');
};

window.applyFilters = function() {
    const hasPin = document.getElementById('filterHasPin').checked;
    const hasMac = document.getElementById('filterHasMac').checked;
    const showRetired = document.getElementById('filterShowRetired').checked;
    const showStudent = document.getElementById('filterShowStudent').checked;
    const phoneModel = document.getElementById('filterPhoneModel').value;
    const department = document.getElementById('filterDepartment').value;

    // Create filter state object with only active filters
    const filterState = {};
    if (hasPin) filterState.hasPin = true;
    if (hasMac) filterState.hasMac = true;
    if (showRetired) filterState.showRetired = true;
    if (showStudent) filterState.showStudent = true;
    if (phoneModel) filterState.phoneModel = phoneModel;
    if (department) filterState.department = department;

    // Save filters to localStorage
    if (Object.keys(filterState).length > 0) {
        localStorage.setItem('contactFilters', JSON.stringify(filterState));
    } else {
        localStorage.removeItem('contactFilters');
    }

    // Create URL without causing a page reload
    const url = new URL(window.location);
    if (Object.keys(filterState).length > 0) {
        url.searchParams.set('filters', JSON.stringify(filterState));
    } else {
        url.searchParams.delete('filters');
    }

    // Preserve search term if exists
    const searchTerm = document.getElementById('searchInput').value;
    if (searchTerm) {
        url.searchParams.set('search', searchTerm);
    }

    // Update URL without page reload
    window.history.pushState({}, '', url.toString());

    // Close the filters modal
    closeFiltersModal();

    // Fetch and update content without page reload
    fetch(url.toString())
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Check if there are any contacts in the current page
            const newTableRows = doc.querySelectorAll('.contacts-table tbody tr');
            const currentPage = parseInt(url.searchParams.get('page')) || 1;
            
            if (newTableRows.length === 0 && currentPage > 1) {
                // If current page is empty and it's not the first page,
                // redirect to first page
                url.searchParams.set('page', '1');
                window.location.href = url.toString();
                return;
            }
            
            // Rest of existing content update code
            const currentTable = document.querySelector('.contacts-table');
            const newTable = doc.querySelector('.contacts-table');
            if (currentTable && newTable) {
                currentTable.innerHTML = newTable.innerHTML;
            }

            // Update pagination if it exists
            const currentPagination = document.querySelector('.pagination');
            const newPagination = doc.querySelector('.pagination');
            if (currentPagination && newPagination) {
                currentPagination.innerHTML = newPagination.innerHTML;
            }

            // Update active filters display
            const filterDisplay = document.getElementById('activeFilters');
            if (filterDisplay) {
                const activeFilters = [];
                if (hasPin) activeFilters.push('Has PIN');
                if (hasMac) activeFilters.push('Has MAC');
                if (showRetired) activeFilters.push('Including Retired');
                if (showStudent) activeFilters.push('Including Students');
                if (phoneModel) activeFilters.push(`Model: ${phoneModel}`);
                if (department) activeFilters.push(`Dept: ${department}`);
                
                if (activeFilters.length > 0) {
                    document.getElementById('activeFiltersText').textContent = 
                        `Active Filters: ${activeFilters.join(', ')}`;
                    filterDisplay.style.display = 'block';
                } else {
                    filterDisplay.style.display = 'none';
                }
            }
        });
};

window.clearFilters = function() {
    // Clear URL parameters except page
    const url = new URL(window.location);
    url.searchParams.delete('filters');
    url.searchParams.delete('search');
    
    // Reset to first page
    url.searchParams.set('page', '1');
    
    // Clear localStorage
    localStorage.removeItem('contactFilters');
    
    // Redirect to cleaned URL
    window.location.href = url.toString();
};

function initializeFilters() {
    const urlParams = new URLSearchParams(window.location.search);
    const filterParams = urlParams.get('filters');
    
    if (filterParams) {
        try {
            const filterState = JSON.parse(filterParams);
            // Set filter controls to match URL state
            document.getElementById('filterHasPin').checked = filterState.hasPin || false;
            document.getElementById('filterHasMac').checked = filterState.hasMac || false;
            document.getElementById('filterShowRetired').checked = filterState.showRetired || false;
            document.getElementById('filterShowStudent').checked = filterState.showStudent || false;
            document.getElementById('filterPhoneModel').value = filterState.phoneModel || '';
            document.getElementById('filterDepartment').value = filterState.department || '';
            
            // Update active filters display
            const activeFilters = [];
            if (filterState.hasPin) activeFilters.push('Has PIN');
            if (filterState.hasMac) activeFilters.push('Has MAC');
            if (filterState.showRetired) activeFilters.push('Including Retired');
            if (filterState.showStudent) activeFilters.push('Including Students');
            if (filterState.phoneModel) activeFilters.push(`Model: ${filterState.phoneModel}`);
            if (filterState.department) activeFilters.push(`Dept: ${filterState.department}`);
            
            const filterDisplay = document.getElementById('activeFilters');
            if (activeFilters.length > 0) {
                document.getElementById('activeFiltersText').textContent = 
                    `Active Filters: ${activeFilters.join(', ')}`;
                filterDisplay.style.display = 'block';
            }
        } catch (e) {
            console.error('Error parsing filters:', e);
        }
    }
}

window.showHistory = function(contactId) {
    const modal = document.getElementById('historyModal');
    
    // Prevent background scroll
    document.body.classList.add('modal-open');
    
    fetch(`/contact/${contactId}/history`, getFetchOptions())
    .then(response => response.json())
    .then(data => {
        document.getElementById('historyTitle').textContent = `History for ${data.contact_name}`;
        const tbody = document.getElementById('historyTableBody');
        tbody.innerHTML = '';
        
        // Sort history by date in descending order
        const sortedHistory = data.history.sort((a, b) => 
            new Date(b.changed_at) - new Date(a.changed_at)
        );
        
        sortedHistory.forEach(item => {
            const row = document.createElement('tr');
            const date = new Date(item.changed_at);
            row.innerHTML = `
                <td title="${date.toLocaleString()}">${date.toLocaleDateString()}</td>
                <td>${item.field_name}</td>
                <td title="${item.old_value || '-'}">${item.old_value || '-'}</td>
                <td title="${item.new_value || '-'}">${item.new_value || '-'}</td>
            `;
            tbody.appendChild(row);
        });
        
        modal.style.display = 'block';
    })
    .catch(error => {
        console.error('Error loading history:', error);
        alert('Error loading contact history');
        document.body.classList.remove('modal-open');
    });
};

window.closeHistoryModal = function() {
    document.getElementById('historyModal').style.display = 'none';
    document.body.classList.remove('modal-open');
};

window.closeLdapSearchModal = function() {
    document.getElementById('ldapSearchModal').style.display = 'none';
    document.body.classList.remove('modal-open');
};

window.searchLDAP = function() {
    const searchTerm = document.getElementById('ldapSearchTerm').value;
    const excludeStudents = document.getElementById('ldapExcludeStudents').checked;
    const excludeAlumni = document.getElementById('ldapExcludeAlumni').checked;
    const resultsDiv = document.getElementById('ldapSearchResults');
    const progressContainer = document.getElementById('importProgress');
    
    resultsDiv.innerHTML = '<p>Searching...</p>';
    document.getElementById('importAllButton').style.display = 'none';
    progressContainer.style.display = 'none';

    fetch('/ldap-search', getFetchOptions('POST', { 
        search_term: searchTerm,
        exclude_students: excludeStudents,
        exclude_alumni: excludeAlumni
    }))
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.contacts.length > 0) {
                const html = data.contacts.map(contact => `
                    <div class="ldap-result">
                        <span>${contact.name} (${contact.uid})</span>
                        <button onclick="importContact('${contact.dn}')" class="button import">
                            Import
                        </button>
                    </div>
                `).join('');
                resultsDiv.innerHTML = html;
                // Show Import All button only when there are results
                document.getElementById('importAllButton').style.display = 'inline-block';
                // Store contacts for Import All function
                window.currentSearchResults = data.contacts;
            } else {
                resultsDiv.innerHTML = '<p>No contacts found</p>';
            }
        } else {
            resultsDiv.innerHTML = `<p class="error">${data.error}</p>`;
        }
    })
    .catch(error => {
        resultsDiv.innerHTML = '<p class="error">Search failed</p>';
        console.error('LDAP search error:', error);
    });
};

window.importAllContacts = async function() {
    if (!window.currentSearchResults || !window.currentSearchResults.length) {
        return;
    }

    const importAllButton = document.getElementById('importAllButton');
    const progressBar = document.querySelector('.progress-bar');
    const progressContainer = document.getElementById('importProgress');
    const statusText = document.getElementById('importStatus');
    const total = window.currentSearchResults.length;
    
    importAllButton.disabled = true;
    progressContainer.style.display = 'block';
    statusText.textContent = `0/${total}`;
    progressBar.style.width = '0%';

    try {
        let imported = 0;
        for (const contact of window.currentSearchResults) {
            await fetch('/import-contact', getFetchOptions('POST', { dn: contact.dn }));
            
            imported++;
            const progress = (imported / total) * 100;
            progressBar.style.width = `${progress}%`;
            statusText.textContent = `${imported}/${total}`;
        }
        
        // Short delay to show completion before refresh
        await new Promise(resolve => setTimeout(resolve, 500));
        location.reload();
    } catch (error) {
        alert('Error importing contacts: ' + error);
        importAllButton.disabled = false;
        progressContainer.style.display = 'none';
    }
};

window.importContact = function(dn) {
    fetch('/import-contact', getFetchOptions('POST', { dn: dn }))
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else if (data.conflict) {
            // Enhanced conflict resolution dialog
            const options = [
                'Keep manual data (ignore LDAP)',
                'Use LDAP data (override all manual data)',
                'Update empty fields only (then switch to LDAP contact)'
            ];
            const choice = confirm(`A contact with UID "${data.uid}" already exists.\n\n` +
                                 'Choose:\n' +
                                 'OK - Update empty fields only and convert to LDAP contact\n' +
                                 'Cancel - Choose other options');
            
            if (choice) {
                // User chose to update empty fields
                fetch('/resolve-conflict/' + data.contact_id, getFetchOptions('POST', {
                    action: 'merge_ldap',
                    dn: dn
                }))
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Error resolving conflict: ' + data.error);
                    }
                });
            } else {
                // Ask for other options
                const secondChoice = confirm(
                    `Choose action for UID "${data.uid}":\n\n` +
                    `OK - Use LDAP data (will override all manual data)\n` +
                    `Cancel - Keep manual data (ignore LDAP)`
                );
                if (secondChoice) {
                    // User chose to use LDAP data
                    fetch('/resolve-conflict/' + data.contact_id, getFetchOptions('POST', {
                        action: 'use_ldap',
                        dn: dn
                    }))
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            location.reload();
                        } else {
                            alert('Error resolving conflict: ' + data.error);
                        }
                    });
                } else {
                    // User chose to keep manual data
                    fetch('/resolve-conflict/' + data.contact_id, getFetchOptions('POST', {
                        action: 'keep_manual',
                        dn: dn
                    }))
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            location.reload();
                        } else {
                            alert('Error resolving conflict: ' + data.error);
                        }
                    });
                }
            }
        } else {
            alert('Import failed: ' + data.error);
        }
    });
};

// Add to window functions
window.sendPinEmail = function(contactId) {
    if (confirm('Send PIN number via email?')) {
        fetch(`/contact/${contactId}/send-pin`, getFetchOptions('POST'))
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('PIN sent successfully');
            } else {
                alert('Error sending PIN: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error sending PIN');
        });
    }
};

// New Contact Modal Functions
function showNewContactModal() {
    document.getElementById('newContactModal').style.display = 'block';
    document.body.classList.add('modal-open');
}

function closeNewContactModal() {
    document.getElementById('newContactModal').style.display = 'none';
    document.body.classList.remove('modal-open');
    document.getElementById('newContactForm').reset();
}

function createNewContact(event) {
    event.preventDefault();
    const form = document.getElementById('newContactForm');
    const formData = new FormData(form);
    const data = {};
    
    // Convert FormData to a plain object
    formData.forEach((value, key) => {
        data[key] = value;
    });
    
    fetch('/contact/create', getFetchOptions('POST', data))
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            closeNewContactModal();
            location.reload();
        } else {
            alert('Error creating contact: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error creating contact: ' + error.message);
    });
    
    return false;
}

function addCSRFToken(headers = {}) {
    return {
        ...headers,
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
    };
}

window.permanentlyDeleteContact = function(contactId) {
    if (confirm('This action cannot be undone! Are you sure you want to permanently delete this contact?')) {
        fetch(`/contact/${contactId}/permanent-delete`, getFetchOptions('POST'))
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error permanently deleting contact');
        });
    }
};

function showPhoneDetails(mac) {
    const modal = document.getElementById('phoneDetailsModal');
    const content = document.getElementById('phoneDetailsContent');
    const title = document.getElementById('phoneDetailsTitle');
    
    // Format MAC address for display
    const formattedMac = mac.replace(/:/g, '').toUpperCase().replace(/(.{2})/g, '$1:').slice(0, -1);
    
    // Set title and loading state
    title.textContent = `Phone Details: ${formattedMac}`;
    content.innerHTML = '<div class="loading">Loading phone details...</div>';
    modal.style.display = 'block';
    document.body.classList.add('modal-open');
    
    // Fetch phone details from CUCM
    fetch(`/api/phones/${mac}/details`, {
        headers: { 'Accept': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            content.innerHTML = `<div class="error">
                <p class="error-title">Error retrieving phone details</p>
                <p class="error-message">${data.error}</p>
                <p class="help-text">This may occur if the phone doesn't exist in CUCM or if there are connectivity issues.</p>
            </div>`;
            return;
        }
        
        // Check if we have meaningful data or just placeholders
        const hasData = data.name !== 'Unknown' || 
                      data.description || 
                      data.model || 
                      data.product || 
                      data.class || 
                      data.protocol;
        
        // Format the phone details
        if (hasData) {
            let html = `<div class="phone-detail-item">
                <h3>${data.name || formattedMac}</h3>
                <p class="status ${data.status === 'Registered' ? 'registered' : 'not-registered'}">
                    Status: ${data.status || 'Unknown'}
                </p>
                <table class="details-table">
                    <tr>
                        <th>Description:</th>
                        <td>${data.description || 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Model:</th>
                        <td>${data.model || 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Product:</th>
                        <td>${data.product || 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Class:</th>
                        <td>${data.class || 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Protocol:</th>
                        <td>${data.protocol || 'N/A'}</td>
                    </tr>
                </table>
            </div>`;
            content.innerHTML = html;
        } else {
            // No meaningful data found
            content.innerHTML = `<div class="no-data">
                <p class="no-data-title">No detailed information available</p>
                <p>The phone with MAC address ${formattedMac} exists in CUCM but has limited information.</p>
                <p class="status not-registered">Status: ${data.status || 'Not Registered'}</p>
                <p class="help-text">This phone may not be currently registered or may need to be reconfigured in CUCM.</p>
            </div>`;
        }
    })
    .catch(error => {
        content.innerHTML = `<div class="error">
            <p class="error-title">Connection Error</p>
            <p class="error-message">Error fetching phone details: ${error.message}</p>
            <p class="help-text">Please check your CUCM connection settings and try again.</p>
        </div>`;
    });
}

function closePhoneDetailsModal() {
    document.getElementById('phoneDetailsModal').style.display = 'none';
    document.body.classList.remove('modal-open');
}

function testCUCMConnection() {
    fetch('/test-cucm', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        showModal(
            'CUCM Connection Test',
            data.success ? 
                `<div class="alert alert-success">${data.message}</div>` :
                `<div class="alert alert-danger">${data.message}</div>`
        );
    })
    .catch(error => {
        showModal(
            'CUCM Connection Test',
            `<div class="alert alert-danger">Connection test failed: ${error}</div>`
        );
    });
}

window.fetchAuthCode = function(contactId) {
    if (!confirm('Fetch authorization code from CUCM?')) {
        return;
    }

    fetch(`/api/contact/${contactId}/fetch-auth-code`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            // Update the PIN field in the table if it exists
            const pinCell = document.querySelector(`#contact-${contactId} .pin-field`);
            if (pinCell) {
                pinCell.textContent = data.pin;
            }
            alert('Authorization code fetched successfully');
            // Optionally reload the page
            // location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to fetch authorization code');
    });
};

// General utility functions
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// Contact management functions
function editContact(contactId) {
    // Fetch contact details
    fetch(`/contact/${contactId}`, {
        headers: { 'Accept': 'application/json' }
    })
    .then(response => response.json())
    .then(contact => {
        // Populate form with contact data
        const form = document.getElementById('editForm');
        form.action = `/contact/${contactId}/update`;
        document.getElementById('first_name').value = contact.first_name || '';
        document.getElementById('last_name').value = contact.last_name || '';
        document.getElementById('email').value = contact.email || '';
        document.getElementById('phone').value = contact.phone || '';
        document.getElementById('phone_model').value = contact.phone_model || '';
        document.getElementById('mac_address').value = contact.mac_address || '';
        document.getElementById('pin').value = contact.pin || '';
        document.getElementById('notes').value = contact.notes || '';
        document.getElementById('department').value = contact.department || '';
        document.getElementById('title').value = contact.title || '';
        
        // Show modal
        const modal = document.getElementById('editModal');
        modal.style.display = 'block';
        document.body.classList.add('modal-open');
    });
}

function closeModal() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none';
    });
    document.body.classList.remove('modal-open');
}

function deleteContact(contactId) {
    if (confirm('Are you sure you want to delete this contact?')) {
        fetch(`/contact/${contactId}/delete`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error deleting contact: ' + data.error);
            }
        });
    }
}

function permanentlyDeleteContact(contactId) {
    if (confirm('WARNING: This will permanently delete the contact and all history. This cannot be undone. Continue?')) {
        fetch(`/contact/${contactId}/permanent-delete`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error deleting contact: ' + data.error);
            }
        });
    }
}

function restoreContact(contactId) {
    if (confirm('Restore this contact?')) {
        fetch(`/contact/${contactId}/restore`, {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('Error restoring contact: ' + data.error);
            }
        });
    }
}

function showHistory(contactId) {
    fetch(`/contact/${contactId}/history`, {
        headers: { 'Accept': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        const modal = document.getElementById('historyModal');
        const title = document.getElementById('historyTitle');
        const tbody = document.getElementById('historyTableBody');
        
        title.textContent = `History for ${data.contact_name}`;
        tbody.innerHTML = '';
        
        data.history.forEach(item => {
            const tr = document.createElement('tr');
            
            const dateCell = document.createElement('td');
            const date = new Date(item.changed_at);
            dateCell.textContent = date.toLocaleString();
            tr.appendChild(dateCell);
            
            const fieldCell = document.createElement('td');
            fieldCell.textContent = item.field_name;
            tr.appendChild(fieldCell);
            
            const oldCell = document.createElement('td');
            oldCell.textContent = item.old_value || '';
            tr.appendChild(oldCell);
            
            const newCell = document.createElement('td');
            newCell.textContent = item.new_value || '';
            tr.appendChild(newCell);
            
            tbody.appendChild(tr);
        });
        
        modal.style.display = 'block';
        document.body.classList.add('modal-open');
    });
}

function closeHistoryModal() {
    document.getElementById('historyModal').style.display = 'none';
    document.body.classList.remove('modal-open');
}

// Phone details modal functionality
function showPhoneDetails(mac) {
    const modal = document.getElementById('phoneDetailsModal');
    const content = document.getElementById('phoneDetailsContent');
    const title = document.getElementById('phoneDetailsTitle');
    
    // Format MAC address for display
    const formattedMac = mac.replace(/:/g, '').toUpperCase().replace(/(.{2})/g, '$1:').slice(0, -1);
    
    // Set title and loading state
    title.textContent = `Phone Details: ${formattedMac}`;
    content.innerHTML = '<div class="loading">Loading phone details...</div>';
    modal.style.display = 'block';
    document.body.classList.add('modal-open');
    
    // Fetch phone details from CUCM
    fetch(`/api/phones/${mac}/details`, {
        headers: { 'Accept': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            content.innerHTML = `<div class="error">
                <p class="error-title">Error retrieving phone details</p>
                <p class="error-message">${data.error}</p>
                <p class="help-text">This may occur if the phone doesn't exist in CUCM or if there are connectivity issues.</p>
            </div>`;
            return;
        }
        
        // Check if we have meaningful data or just placeholders
        const hasData = data.name !== 'Unknown' || 
                      data.description || 
                      data.model || 
                      data.product || 
                      data.class || 
                      data.protocol;
        
        // Format the phone details
        if (hasData) {
            let html = `<div class="phone-detail-item">
                <h3>${data.name || formattedMac}</h3>
                <p class="status ${data.status === 'Registered' ? 'registered' : 'not-registered'}">
                    Status: ${data.status || 'Unknown'}
                </p>
                <table class="details-table">
                    <tr>
                        <th>Description:</th>
                        <td>${data.description || 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Model:</th>
                        <td>${data.model || 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Product:</th>
                        <td>${data.product || 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Class:</th>
                        <td>${data.class || 'N/A'}</td>
                    </tr>
                    <tr>
                        <th>Protocol:</th>
                        <td>${data.protocol || 'N/A'}</td>
                    </tr>
                </table>
            </div>`;
            content.innerHTML = html;
        } else {
            // No meaningful data found
            content.innerHTML = `<div class="no-data">
                <p class="no-data-title">No detailed information available</p>
                <p>The phone with MAC address ${formattedMac} exists in CUCM but has limited information.</p>
                <p class="status not-registered">Status: ${data.status || 'Not Registered'}</p>
                <p class="help-text">This phone may not be currently registered or may need to be reconfigured in CUCM.</p>
            </div>`;
        }
    })
    .catch(error => {
        content.innerHTML = `<div class="error">
            <p class="error-title">Connection Error</p>
            <p class="error-message">Error fetching phone details: ${error.message}</p>
            <p class="help-text">Please check your CUCM connection settings and try again.</p>
        </div>`;
    });
}

function closePhoneDetailsModal() {
    document.getElementById('phoneDetailsModal').style.display = 'none';
    document.body.classList.remove('modal-open');
}

// Document ready handler
document.addEventListener('DOMContentLoaded', function() {
    // Setup close buttons for all modals
    document.querySelectorAll('.modal .close').forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal');
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
        });
    });
    
    // Setup edit form submission
    const editForm = document.getElementById('editForm');
    if (editForm) {
        editForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const contactId = this.action.split('/').pop();
            const data = {
                first_name: document.getElementById('first_name').value,
                last_name: document.getElementById('last_name').value,
                email: document.getElementById('email').value,
                phone: document.getElementById('phone').value,
                phone_model: document.getElementById('phone_model').value,
                mac_address: document.getElementById('mac_address').value,
                pin: document.getElementById('pin').value,
                notes: document.getElementById('notes').value,
                department: document.getElementById('department').value,
                title: document.getElementById('title').value
            };
            
            fetch(`/contact/${contactId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    closeModal();
                    location.reload();
                } else {
                    alert('Error updating contact: ' + result.error);
                }
            });
        });
    }
    
    // Setup search functionality
    const searchInput = document.getElementById('searchInput');
    const searchButton = document.getElementById('searchButton');
    
    if (searchInput && searchButton) {
        searchButton.addEventListener('click', function() {
            const searchTerm = searchInput.value.trim();
            const url = new URL(window.location);
            if (searchTerm) {
                url.searchParams.set('search', searchTerm);
            } else {
                url.searchParams.delete('search');
            }
            url.searchParams.set('page', '1'); // Reset to first page
            window.location.href = url.toString();
        });
        
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchButton.click();
            }
        });
    }
    
    // Setup page size selector
    const pageSizeSelect = document.getElementById('pageSizeSelect');
    if (pageSizeSelect) {
        pageSizeSelect.addEventListener('change', function() {
            const url = new URL(window.location);
            url.searchParams.set('per_page', this.value);
            url.searchParams.set('page', '1'); // Reset to first page
            window.location.href = url.toString();
        });
    }
    
    // Setup filters button
    const filtersButton = document.getElementById('filtersButton');
    if (filtersButton) {
        filtersButton.addEventListener('click', function() {
            const modal = document.getElementById('filtersModal');
            modal.style.display = 'block';
            document.body.classList.add('modal-open');
        });
    }
    
    // Setup LDAP search button
    const ldapSearchButton = document.getElementById('ldapSearchButton');
    if (ldapSearchButton) {
        ldapSearchButton.addEventListener('click', function() {
            const modal = document.getElementById('ldapSearchModal');
            modal.style.display = 'block';
            document.body.classList.add('modal-open');
        });
    }
    
    // Setup sync button
    const syncButton = document.getElementById('syncButton');
    if (syncButton) {
        syncButton.addEventListener('click', function() {
            if (confirm('Start LDAP synchronization now?')) {
                syncButton.disabled = true;
                syncButton.textContent = 'Syncing...';
                
                fetch('/sync', {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                    }
                })
                .then(response => response.json())
                .then(data => {
                    syncButton.disabled = false;
                    syncButton.textContent = 'Sync Now';
                    
                    if (data.success) {
                        alert(data.message);
                        if (data.has_conflicts) {
                            if (confirm('Conflicts detected. Go to settings to resolve them?')) {
                                window.location.href = '/settings/data_management';
                            }
                        } else {
                            location.reload();
                        }
                    } else {
                        alert('Sync failed: ' + data.error);
                    }
                })
                .catch(error => {
                    syncButton.disabled = false;
                    syncButton.textContent = 'Sync Now';
                    alert('Error during sync: ' + error.message);
                });
            }
        });
    }
    
    // Setup new contact button
    const newContactButton = document.getElementById('newContactButton');
    if (newContactButton) {
        newContactButton.addEventListener('click', function() {
            const modal = document.getElementById('newContactModal');
            modal.style.display = 'block';
            document.body.classList.add('modal-open');
        });
    }
    
    // Load LDAP search
    window.searchLDAP = function() {
        const searchTerm = document.getElementById('ldapSearchTerm').value.trim();
        const excludeStudents = document.getElementById('ldapExcludeStudents').checked;
        const excludeAlumni = document.getElementById('ldapExcludeAlumni').checked;
        
        if (!searchTerm) {
            alert('Please enter a search term');
            return;
        }
        
        const resultsDiv = document.getElementById('ldapSearchResults');
        resultsDiv.innerHTML = '<div class="loading">Searching LDAP directory...</div>';
        
        fetch('/ldap-search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({
                search_term: searchTerm,
                exclude_students: excludeStudents,
                exclude_alumni: excludeAlumni
            })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                resultsDiv.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                return;
            }
            
            if (data.contacts.length === 0) {
                resultsDiv.innerHTML = '<div class="no-results">No matching contacts found in LDAP</div>';
                return;
            }
            
            // Show import all button if multiple contacts
            const importAllButton = document.getElementById('importAllButton');
            if (importAllButton && data.contacts.length > 1) {
                importAllButton.style.display = 'inline-block';
            }
            
            // Display results
            let html = '<div class="ldap-results-list">';
            data.contacts.forEach(contact => {
                html += `
                    <div class="ldap-contact-item">
                        <div class="ldap-contact-details">
                            <h4>${contact.name || 'Unknown'}</h4>
                            <p>UID: ${contact.uid || 'N/A'}</p>
                            <p>Email: ${contact.email || 'N/A'}</p>
                            <p>DN: ${contact.dn || 'N/A'}</p>
                        </div>
                        <div class="ldap-contact-actions">
                            <button onclick="importContact('${contact.dn}')" class="button import">Import</button>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            resultsDiv.innerHTML = html;
        })
        .catch(error => {
            resultsDiv.innerHTML = `<div class="error">Error searching LDAP: ${error.message}</div>`;
        });
    };
    
    // Import contact function
    window.importContact = function(dn) {
        if (!confirm('Import this contact from LDAP?')) {
            return;
        }
        
        fetch('/import-contact', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify({ dn: dn })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Contact imported successfully!');
                closeLdapSearchModal();
                location.reload();
            } else if (data.conflict) {
                if (confirm(`A contact with UID ${data.uid} already exists. View the existing contact?`)) {
                    window.location.href = `/contact/${data.contact_id}`;
                }
            } else {
                alert('Error importing contact: ' + data.error);
            }
        })
        .catch(error => {
            alert('Error importing contact: ' + error.message);
        });
    };
    
    // Import all contacts function
    window.importAllContacts = function() {
        if (!confirm('Import all contacts in search results?')) {
            return;
        }
        
        const items = document.querySelectorAll('.ldap-contact-item');
        const total = items.length;
        let current = 0;
        let success = 0;
        let conflicts = 0;
        let errors = 0;
        
        // Show progress bar
        const progressBar = document.getElementById('importProgress');
        const progressStatus = document.getElementById('importStatus');
        if (progressBar) {
            progressBar.style.display = 'block';
            progressBar.querySelector('.progress-bar').style.width = '0%';
            progressStatus.textContent = `0/${total}`;
        }
        
        // Process import sequentially
        function processNext() {
            if (current >= total) {
                // All done
                alert(`Import complete. Success: ${success}, Conflicts: ${conflicts}, Errors: ${errors}`);
                progressBar.style.display = 'none';
                closeLdapSearchModal();
                location.reload();
                return;
            }
            
            const item = items[current];
            const dn = item.querySelector('.ldap-contact-details p:nth-child(3)').textContent.replace('DN: ', '');
            
            fetch('/import-contact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify({ dn: dn })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    success++;
                } else if (data.conflict) {
                    conflicts++;
                } else {
                    errors++;
                }
                
                current++;
                // Update progress
                if (progressBar) {
                    const percent = (current / total) * 100;
                    progressBar.querySelector('.progress-bar').style.width = `${percent}%`;
                    progressStatus.textContent = `${current}/${total}`;
                }
                
                // Process next
                processNext();
            })
            .catch(error => {
                console.error('Import error:', error);
                errors++;
                current++;
                processNext();
            });
        }
        
        // Start processing
        processNext();
    };
    
    // Close LDAP search modal
    window.closeLdapSearchModal = function() {
        document.getElementById('ldapSearchModal').style.display = 'none';
        document.body.classList.remove('modal-open');
    };
    
    // Close filters modal 
    window.closeFiltersModal = function() {
        document.getElementById('filtersModal').style.display = 'none';
        document.body.classList.remove('modal-open');
    };
    
    // Create new contact form handler
    window.createNewContact = function(event) {
        event.preventDefault();
        
        const form = document.getElementById('newContactForm');
        const formData = new FormData(form);
        const data = {
            first_name: formData.get('first_name'),
            last_name: formData.get('last_name'),
            uid: formData.get('uid'),
            email: formData.get('email'),
            phone: formData.get('phone'),
            department: formData.get('department'),
            title: formData.get('title'),
            phone_model: formData.get('phone_model'),
            mac_address: formData.get('mac_address'),
            pin: formData.get('pin'),
            notes: formData.get('notes')
        };
        
        fetch('/contact/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                alert('Contact created successfully!');
                closeNewContactModal();
                location.reload();
            } else {
                alert('Error creating contact: ' + result.error);
            }
        })
        .catch(error => {
            alert('Error creating contact: ' + error.message);
        });
        
        return false;
    };
    
    // Close new contact modal
    window.closeNewContactModal = function() {
        document.getElementById('newContactModal').style.display = 'none';
        document.body.classList.remove('modal-open');
    };
    
    // Test CUCM connection in settings
    const testCucmButton = document.getElementById('testCucmButton');
    if (testCucmButton) {
        testCucmButton.addEventListener('click', function() {
            const modal = document.getElementById('cucmTestModal');
            const result = document.getElementById('cucmTestResult');
            
            modal.style.display = 'block';
            document.body.classList.add('modal-open');
            result.innerHTML = 'Testing CUCM connection...';
            
            fetch('/test-cucm', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    result.innerHTML = `<div class="success-message">
                        <svg viewBox="0 0 24 24" width="24" height="24">
                            <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                        <p>${data.message}</p>
                    </div>`;
                } else {
                    result.innerHTML = `<div class="error-message">
                        <svg viewBox="0 0 24 24" width="24" height="24">
                            <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                        </svg>
                        <p>${data.message}</p>
                    </div>`;
                }
            })
            .catch(error => {
                result.innerHTML = `<div class="error-message">
                    <svg viewBox="0 0 24 24" width="24" height="24">
                        <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                    </svg>
                    <p>Connection error: ${error.message}</p>
                </div>`;
            });
        });
    }
    
    // Close CUCM test modal
    window.closeCucmTestModal = function() {
        document.getElementById('cucmTestModal').style.display = 'none';
        document.body.classList.remove('modal-open');
    };
});
