document.addEventListener('DOMContentLoaded', function() {
    // Notification system
    const notificationsButton = document.getElementById('notificationsButton');
    const notificationsModal = document.getElementById('notificationsModal');
    const closeNotificationsBtn = document.getElementById('closeNotificationsBtn');
    const markAllReadBtn = document.getElementById('markAllReadBtn');
    const clearAllBtn = document.getElementById('clearAllBtn');
    const notificationsList = document.getElementById('notificationsList');
    const notificationBadge = document.getElementById('notificationBadge');
    let notifications = [];
    let unreadCount = 0;

    // Load notifications initially if applicable
    if (typeof loadNotifications === 'function') {
        loadNotifications();
    }

    // Set up periodic check for new notifications
    if (typeof loadNotifications === 'function') {
        setInterval(loadNotifications, 30000); // Check every 30 seconds
    }

    // Show notifications modal
    notificationsButton && notificationsButton.addEventListener('click', function() {
        notificationsModal.style.display = 'flex';
    });

    // Close notifications modal
    closeNotificationsBtn && closeNotificationsBtn.addEventListener('click', function() {
        notificationsModal.style.display = 'none';
    });

    // Mark all notifications as read
    markAllReadBtn && markAllReadBtn.addEventListener('click', function() {
        fetch('/notifications/mark-all-read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update UI
                const unreadItems = notificationsList.querySelectorAll('.notification.unread');
                unreadItems.forEach(item => {
                    item.classList.remove('unread');
                });
                updateNotificationBadge(0);
            }
        });
    });

    // Clear all notifications
    clearAllBtn && clearAllBtn.addEventListener('click', function() {
        fetch('/notifications/clear-all', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear notifications list
                notificationsList.innerHTML = '<div class="no-notifications">No notifications</div>';
                updateNotificationBadge(0);
            }
        });
    });

    // Test notification button
    const testNotificationBtn = document.getElementById('testNotificationBtn');
    if (testNotificationBtn) {
        testNotificationBtn.addEventListener('click', function() {
            fetch('/notifications/create-test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    title: 'Test Notification',
                    message: 'This is a test notification created at ' + new Date().toLocaleTimeString()
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadNotifications();
                }
            });
        });
    }
    
    // Test LDAP connection
    const testConnectionBtn = document.getElementById('testConnectionBtn');
    if (testConnectionBtn) {
        testConnectionBtn.addEventListener('click', function() {
            // Show loading state
            testConnectionBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
            
            fetch('/test-ldap', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                const icon = data.success ? 'check' : 'times';
                const color = data.success ? 'green' : 'red';
                
                // Show result as alert
                alert(`LDAP Test: ${data.message}`);
                
                // Reset button
                testConnectionBtn.innerHTML = '<i class="fas fa-plug"></i> Test LDAP';
            })
            .catch(error => {
                alert('Error testing connection: ' + error);
                testConnectionBtn.innerHTML = '<i class="fas fa-plug"></i> Test LDAP';
            });
        });
    }
    
    // Test CUCM connection
    const testCucmBtn = document.getElementById('testCucmBtn');
    if (testCucmBtn) {
        testCucmBtn.addEventListener('click', function() {
            // Show loading state
            testCucmBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
            
            fetch('/test-cucm', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                const icon = data.success ? 'check' : 'times';
                const color = data.success ? 'green' : 'red';
                
                // Show result as alert
                alert(`CUCM Test: ${data.message}`);
                
                // Reset button
                testCucmBtn.innerHTML = '<i class="fas fa-phone"></i> Test CUCM';
            })
            .catch(error => {
                alert('Error testing CUCM connection: ' + error);
                testCucmBtn.innerHTML = '<i class="fas fa-phone"></i> Test CUCM';
            });
        });
    }
    
    // COMPLETELY REMOVE ALL SYNC BUTTON EVENT HANDLERS IN THIS FILE
    // *** DO NOT ADD ANY SYNC BUTTON HANDLERS HERE *** 
    // The sync button is now handled in base.html using the cloneNode technique

    function loadNotifications() {
        fetch('/notifications')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    notifications = data.notifications;
                    renderNotifications();
                    updateNotificationBadge();
                }
            })
            .catch(error => {
                console.error('Error loading notifications:', error);
            });
    }

    function renderNotifications() {
        if (notifications.length === 0) {
            notificationsList.innerHTML = '<div class="no-notifications">No notifications</div>';
            return;
        }

        notificationsList.innerHTML = '';
        unreadCount = 0;

        notifications.forEach(notification => {
            const notificationItem = document.createElement('div');
            notificationItem.className = 'notification';
            if (notification.unread) {
                notificationItem.classList.add('unread');
                unreadCount++;
            }
            
            notificationItem.innerHTML = `
                <div class="notification-title">${notification.title}</div>
                <div class="notification-message">${notification.message}</div>
                <div class="notification-time">${notification.time_ago}</div>
            `;
            
            notificationsList.appendChild(notificationItem);
        });
    }
    
    function updateNotificationBadge(count = null) {
        const badgeCount = count !== null ? count : unreadCount;
        if (badgeCount > 0) {
            notificationBadge.textContent = badgeCount > 99 ? '99+' : badgeCount;
            notificationBadge.style.display = 'flex';
        } else {
            notificationBadge.style.display = 'none';
        }
    }

    // Conflict alert check
    fetch('/conflicts')
        .then(response => {
            if (response.url.endsWith('/conflicts')) {
                // We were redirected to the conflicts page - extract count
                const conflictCount = document.querySelectorAll('.conflict-item').length;
                if (conflictCount > 0) {
                    showConflictAlert(conflictCount);
                }
            }
        })
        .catch(error => {
            console.error('Error checking conflicts:', error);
        });

    function showConflictAlert(count) {
        const conflictAlert = document.getElementById('conflictAlert');
        if (conflictAlert) {
            const countSpan = document.getElementById('conflictCount');
            countSpan.textContent = count;
            conflictAlert.style.display = 'flex';
        }
    }

    // Generic confirmation modal
    const confirmModal = document.getElementById('confirmModal');
    const confirmText = document.getElementById('confirmText');
    const confirmYes = document.getElementById('confirmYes');
    const confirmNo = document.getElementById('confirmNo');
    let confirmCallback = null;

    function showConfirmDialog(title, message, onConfirm) {
        confirmText.textContent = message;
        document.querySelector('#confirmModal h3').textContent = title;
        confirmModal.style.display = 'flex';
        confirmCallback = onConfirm;
    }

    confirmYes && confirmYes.addEventListener('click', function() {
        confirmModal.style.display = 'none';
        if (confirmCallback) {
            confirmCallback();
            confirmCallback = null;
        }
    });

    confirmNo && confirmNo.addEventListener('click', function() {
        confirmModal.style.display = 'none';
        confirmCallback = null;
    });

    // Close modal when clicking outside
    window.onclick = function(event) {
        if (confirmModal && event.target === confirmModal) {
            confirmModal.style.display = 'none';
            confirmCallback = null;
        }
        if (notificationsModal && event.target === notificationsModal) {
            notificationsModal.style.display = 'none';
        }
    };
});
