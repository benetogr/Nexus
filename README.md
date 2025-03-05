Important!
this file must be updated everytime there is a change in the project

# LDAP Contact Manager with CUCM Integration

A Flask-based web application that synchronizes contacts from LDAP, integrates with Cisco Unified Communications Manager (CUCM), and provides enhanced contact management capabilities with history tracking.

## Features

### LDAP Synchronization
- Automatic daily synchronization with LDAP server (100 contacts limit)
- Manual sync option with notifications
- Contact retention management system
- Anonymous binding support
- Connection testing interface
- Error notifications and logging
- Conflict detection and resolution system

### CUCM Integration
- AXL SOAP API integration with Cisco Unified Communications Manager
- Phone search and lookup functionality
- MAC address validation and registration status
- Authorization code (FAC) retrieval
- Phone registration status monitoring
- Secure credential storage

### Contact Management
- Store LDAP contacts with additional custom fields:
  - Phone Model
  - MAC Address (with CUCM integration)
  - PIN (with email notification and CUCM sync)
  - Department (from ou)
  - Title (from eduPersonAffiliation)
  - Notes
- Contact soft deletion and restoration
- History tracking for all changes
- Retired contacts filter
- Student contacts filter (hidden by default)
- Dropdown actions menu with confirmations
- PIN delivery via email
- Real-time notifications system

### CSV Import/Export
- Export all contacts to CSV
- Import MAC addresses and PINs from CSV
- CSV import preview with validation
- Selective updates (MAC/PIN can be optional)
- Import history tracking
- Format validation for MAC addresses
- Detailed import preview modal
- Help documentation for import format

### Email Features
- SMTP server configuration
- Customizable email templates
- PIN delivery system
- Template preview in settings
- Email history tracking

### Search & Filtering
- Global text search across all fields
- Advanced filtering options:
  - Has PIN filter
  - Has MAC Address filter
  - Phone Model filter
  - Department filter
  - Show/Hide retired contacts
  - Show/Hide student contacts
- Persistent filters across page navigation
- Active filters display
- Historical search results

### Notification System
- Real-time notification display
- Unread status tracking
- Notification categories:
  - LDAP Sync results
  - Error notifications
  - System updates
  - Test notifications (debug)
- Mark all as read functionality
- Clear all notifications option
- Time-ago formatting
- Notification badge with unread count

### Security Features
- CSRF Protection
- Input validation
- Secure credential storage
- Error handling and logging

## Technical Requirements

- Python 3.8+
- SQLite (included with Python)
- LDAP Server
- SMTP Server (for PIN emails)
- CUCM Server with AXL API access
- Required Python packages:
  - Flask
  - ldap3
  - Flask-SQLAlchemy
  - python-dotenv
  - APScheduler
  - zeep (for SOAP API)
  - requests
  - Flask-WTF (for CSRF)

## Project Structure

1. `app.py` - Main application with Flask routes
2. `config.py` - Configuration and settings management
3. `models.py` - Database models (Contact, History, Settings, Notification)
4. `ldap_sync.py` - LDAP synchronization with conflict handling
5. `cucm_service.py` - CUCM integration using zeep for SOAP
6. `schema/` - Contains WSDL and XSD files for CUCM AXL API
7. `templates/` - HTML templates for the web interface
8. `static/` - Static assets (CSS, JavaScript)

## Project Completion Status

### Overall Progress: 95%

#### Feature Completion
1. Contact Display & Management (100%)
   - ✅ Basic contact listing
   - ✅ Enhanced table view
   - ✅ Contact editing
   - ✅ Deletion/Restore
   - ✅ Custom fields
   - ✅ Pagination
   - ✅ CUCM integration
   - ✅ Student filtering
   - ✅ Actions dropdown menu
   - ✅ Confirmation dialogs

2. LDAP Integration (100%)
   - ✅ Basic LDAP connection
   - ✅ Anonymous binding
   - ✅ Connection testing
   - ✅ Error handling
   - ✅ Logging
   - ✅ 100-contact limit
   - ✅ Search functionality
   - ✅ Conflict detection & resolution

3. CUCM Integration (100%)
   - ✅ AXL API connection
   - ✅ Phone search
   - ✅ Registration status
   - ✅ PIN/FAC retrieval
   - ✅ Connection testing
   - ✅ Error handling

4. Search & Filtering (100%)
   - ✅ Global search
   - ✅ Advanced filters
   - ✅ Persistent filters
   - ✅ Filter indicators
   - ✅ Department filtering
   - ✅ Student/Retired filtering
   - ✅ Export functionality
   - ✅ Historical search results

5. User Interface (95%)
   - ✅ Responsive design
   - ✅ Modal dialogs
   - ✅ Status indicators
   - ✅ Filter management
   - ✅ Dropdown menus
   - ✅ Total contacts counter
   - ❌ Theme customization

6. History & Logging (90%)
   - ✅ Change tracking
   - ✅ History display
   - ✅ Email history
   - ❌ Audit reports

7. Settings & Configuration (90%)
   - ✅ Basic settings management
   - ✅ LDAP configuration
   - ✅ CUCM configuration
   - ✅ Email settings
   - ✅ PIN notification system
   - ❌ Backup configuration

8. Email System (90%)
   - ✅ SMTP configuration
   - ✅ Template management
   - ✅ PIN delivery
   - ❌ Batch operations

9. Security & Performance (90%)
   - ✅ Input validation
   - ✅ SQL injection prevention
   - ✅ XSS protection
   - ✅ CSRF protection
   - ❌ Rate limiting

## Initial Setup

1. Clone the repository
2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install requirements:
```bash
pip install -r requirements.txt
```

4. Initialize database:
```bash
python app.py --init-db
```

5. Configure settings through the web interface:
   - LDAP connection details
   - CUCM connection details
   - SMTP server settings
   - Email templates

6. Run the application:
```bash
python app.py
```

## CUCM Integration Setup

1. Ensure you have admin access to your CUCM server
2. Create an application user with AXL API permissions
3. Configure the CUCM settings in the application:
   - Host: Your CUCM server hostname or IP
   - Username: AXL API user
   - Password: AXL API password
   - Version: Your CUCM version (e.g., 14.0.1)
   - Verify SSL: Set to False for development or self-signed certificates

4. Test connection through the settings interface

## License

MIT License - See LICENSE file for details


