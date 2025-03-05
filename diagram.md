# LDAP Contact Manager with CUCM Integration - Process Flow Diagram

This document explains the flow of operations in the LDAP Contact Manager application, describing how each component interacts when various actions are performed.

## Table of Contents
1. [Contact Management Operations](#contact-management-operations)
2. [LDAP Synchronization Flow](#ldap-synchronization-flow)
3. [CUCM Integration Operations](#cucm-integration-operations)
4. [Email Notification System](#email-notification-system)
5. [User Interface Interactions](#user-interface-interactions)
6. [Settings Management](#settings-management)
7. [CSV Import/Export Operations](#csv-importexport-operations)

---

## Contact Management Operations

### Creating a New Contact
1. **UI Interaction**: User fills the "New Contact" form and clicks "Save"
2. **Frontend JavaScript**: 
   - JavaScript captures form data and converts it to JSON
   - Sends POST request to `/contact/create` endpoint
3. **Backend Processing** (`app.py`): 
   - `create_contact()` function receives the data
   - Validates required fields (first name, last name, UID)
   - Creates a new Contact object and adds it to the database
   - Creates a History record for the creation event
   - Creates a notification about the new contact
4. **Response**: Server returns JSON with success status and the new contact ID
5. **UI Update**: JavaScript receives response and updates the UI accordingly

### Updating a Contact
1. **UI Interaction**: User edits contact details and clicks "Save"
2. **Frontend JavaScript**:
   - Captures form data as JSON
   - Sends POST request to `/contact/<id>/update` endpoint
3. **Backend Processing** (`app.py`):
   - `contact_update()` function loads the contact by ID
   - Compares old and new values for each field
   - Creates History records for each changed field
   - Updates the contact in the database
4. **Response**: Returns success status as JSON
5. **UI Update**: Contact details are refreshed in the UI

### Deleting a Contact (Soft Delete)
1. **UI Interaction**: User clicks "Delete" in the actions dropdown
2. **Confirmation**: Dialog asks for confirmation
3. **Frontend JavaScript**:
   - Sends POST request to `/contact/<id>/delete` endpoint
4. **Backend Processing** (`app.py`):
   - `contact_delete()` sets the contact's `is_active` flag to `False`
   - Creates a History record for the deletion
5. **Response**: Returns success status
6. **UI Update**: Contact is removed from the active contacts view

### Restoring a Deleted Contact
1. **UI Interaction**: User clicks "Restore" in the actions dropdown for a deleted contact
2. **Frontend JavaScript**:
   - Sends POST request to `/contact/<id>/restore` endpoint
3. **Backend Processing** (`app.py`):
   - `contact_restore()` sets `is_active` back to `True`
   - Creates a History record for the restoration
4. **Response**: Returns success status
5. **UI Update**: Contact appears in the active contacts view again

### Permanently Deleting a Contact
1. **UI Interaction**: User clicks "Permanently Delete" for a soft-deleted contact
2. **Confirmation**: Dialog asks for confirmation, warning about irreversible action
3. **Frontend JavaScript**:
   - Sends POST request to `/contact/<id>/permanent-delete` endpoint
4. **Backend Processing** (`app.py`):
   - `contact_permanent_delete()` verifies the contact is already soft-deleted
   - Creates a notification about the permanent deletion
   - Deletes all history records for the contact
   - Permanently deletes the contact record
5. **Response**: Returns success status
6. **UI Update**: Contact is completely removed from the system

---

## LDAP Synchronization Flow

### Manual LDAP Sync Initiation
1. **UI Interaction**: User clicks "Sync Now" button
2. **Frontend JavaScript**:
   - Shows loading indicator
   - Sends POST request to `/sync` endpoint
3. **Backend Processing** (`app.py`):
   - `sync()` function creates an LDAPSync instance
   - Calls `sync_contacts()` method on the instance
   - LDAPSync connects to the LDAP server (`connect()` method)
   - Performs search with configured filter
   - Processes each returned entry:
     - Maps LDAP attributes to Contact fields
     - Creates new contacts or updates existing ones
     - Checks for and records UID conflicts
     - Creates history records for changes
   - Creates a notification with sync results
4. **Response**: Returns sync results, including conflicts if any
5. **UI Update**:
   - Shows success message with number of contacts synced
   - If conflicts exist, shows conflict resolution interface

### Scheduled LDAP Sync
1. **Trigger**: APScheduler runs sync job based on configured interval
2. **Backend Processing**:
   - Same procedure as manual sync, but runs in background
   - Creates notification with results regardless of success/failure
3. **UI Notification**: Users see sync result in the notification area when complete

### LDAP Testing
1. **UI Interaction**: User clicks "Test LDAP Connection" in settings
2. **Frontend JavaScript**:
   - Sends POST request to `/test-ldap` endpoint
3. **Backend Processing** (`app.py`):
   - `test_ldap()` function creates an LDAPSync instance
   - Attempts to connect to LDAP server
   - Performs a simple search to verify permissions
4. **Response**: Returns connection success/failure status
5. **UI Update**: Shows success or error message

### LDAP User Search
1. **UI Interaction**: User types search term in LDAP search field
2. **Frontend JavaScript**:
   - Sends POST request to `/ldap-search` with the search term
3. **Backend Processing** (`app.py` & `ldap_sync.py`):
   - `ldap_search()` endpoint receives the request
   - Creates LDAPSync instance
   - Calls `search_user()` method with the search term
   - Method builds search filter with the term (searching across uid, cn, mail fields)
   - Performs LDAP search and collects results
4. **Response**: Returns list of matching LDAP entries
5. **UI Update**: Displays search results in dropdown or modal

![alt text](image-1.png)








### Individual Contact Import
1. **UI Interaction**: User clicks "Import" for a specific LDAP search result
2. **Frontend JavaScript**:
   - Sends POST request to `/import-contact` with the LDAP DN
3. **Backend Processing** (`app.py` & `ldap_sync.py`):
   - `import_contact()` endpoint receives the request
   - Calls `import_single_contact()` method on LDAPSync
   - Method connects to LDAP and searches for the specific entry
   - Processes the entry into a new Contact or updates existing one
   - If UID conflict exists, raises UIDConflict exception
4. **Response**: Returns success status or conflict information
5. **UI Update**: Shows success message or conflict resolution interface

---

## CUCM Integration Operations

### Fetching Authorization Code (PIN)
1. **UI Interaction**: User clicks "Fetch PIN from CUCM" button for a contact
2. **Frontend JavaScript**:
   - Shows loading spinner
   - Sends POST request to `/api/contact/<id>/fetch-auth-code` endpoint
3. **Backend Processing**:
   - `app.py`: `fetch_auth_code()` function receives the contact ID
   - Loads the contact and extracts its UID
   - Creates CUCMService instance
   - Calls `fetchAuthCode()` method with the UID
   - `cucm_service.py`: Initializes SOAP client with credentials from Settings
   - Connects to CUCM using AXL API
   - Makes `listFacInfo` API call to retrieve authorization code
   - Returns the PIN if found
   - Updates contact with new PIN and creates history record
4. **Response**: Returns success status and the PIN
5. **UI Update**: Displays the PIN in the contact form

### Testing CUCM Connection
1. **UI Interaction**: User clicks "Test CUCM Connection" in settings
2. **Frontend JavaScript**:
   - Sends POST request to `/test-cucm` endpoint
3. **Backend Processing** (`app.py` & `cucm_service.py`):
   - `test_cucm()` function creates CUCMService instance
   - Calls `_get_client()` method to initialize connection
   - Tests connection with a small query (listPhone)
4. **Response**: Returns connection status (success/failure with message)
5. **UI Update**: Shows success or error message to user

### Phone Lookup by MAC Address
1. **UI Interaction**: User enters MAC address and clicks lookup button
2. **Frontend JavaScript**:
   - Formats MAC address (adds colons if needed)
   - Sends GET request to `/api/phones/<mac>/details` endpoint
3. **Backend Processing** (`app.py` & `cucm_service.py`):
   - `get_phone_details()` function receives the MAC address
   - Creates CUCMService instance
   - Calls `get_phone_by_mac()` method with formatted MAC
   - Method connects to CUCM using AXL API
   - Makes `getPhone` call to retrieve phone details
   - Processes response into a standardized format
4. **Response**: Returns phone details or error
5. **UI Update**: Displays phone information (model, registration status, etc.)

### Phone Search
1. **UI Interaction**: User types search term in phone search field
2. **Frontend JavaScript**:
   - Sends GET request to `/api/phones/search` with search parameter
3. **Backend Processing** (`app.py` & `cucm_service.py`):
   - `search_phones()` function receives the search term
   - Creates CUCMService instance
   - Calls `search_phones()` method with the search term
   - Method connects to CUCM using AXL API
   - Makes `listPhone` call to search for phones
   - Processes response into list of phone objects
4. **Response**: Returns list of matching phones
5. **UI Update**: Displays search results in dropdown or grid

### Enriching Contacts with CUCM Data
1. **Trigger**: During LDAP sync for each contact
2. **Backend Flow** (`ldap_sync.py`):
   - After contact is created/updated from LDAP
   - `_enrich_with_cucm_data()` method is called
   - Creates CUCMService instance
   - Tries to fetch PIN via `fetchAuthCode()`
   - Tries to find phone via `find_phone_by_owner()`
   - Updates contact with any found data
3. **Result**: Contacts automatically enriched with CUCM data during sync

---

## Email Notification System

### Sending PIN Email
1. **UI Interaction**: User clicks "Email PIN" button for a contact
2. **Frontend JavaScript**:
   - Sends POST request to `/contact/<id>/send-pin` endpoint
3. **Backend Processing** (`app.py` & `email_service.py`):
   - `send_pin_email()` function loads the contact
   - Verifies contact has email and PIN
   - Retrieves SMTP settings from database
   - Creates email with configured template
   - Connects to SMTP server
   - Sends email with PIN information
   - Creates history record of email being sent
4. **Response**: Returns success or failure status
5. **UI Update**: Shows success message or error

### Email Template Preview
1. **UI Interaction**: User clicks "Preview" in email settings
2. **Frontend JavaScript**:
   - Shows modal with rendered template
   - Uses sample data for preview (placeholders replaced)
3. **Template Rendering**:
   - Template text from settings is displayed
   - Placeholders like {first_name}, {pin} are replaced with sample values

### Email Configuration Testing
1. **UI Interaction**: User clicks "Test Configuration" in email settings
2. **Frontend JavaScript**:
   - Collects email settings from form
   - Sends POST request to test endpoint with settings
3. **Backend Processing**:
   - Creates test email connection with provided settings
   - Attempts to connect to SMTP server
   - Sends test email if connection successful
4. **Response**: Returns connection status
5. **UI Update**: Shows success or error message

---

## User Interface Interactions

### Contact Filtering
1. **UI Interaction**: User selects filters (department, has PIN, has MAC, etc.)
2. **Frontend JavaScript**:
   - Updates URL with filter parameters
   - Reloads the page with new parameters
3. **Backend Processing** (`app.py`):
   - `index()` route extracts filter parameters from request
   - Builds database query based on filters
   - Executes query and retrieves matching contacts
4. **UI Update**: Displays filtered contacts and active filter indicators

### Pagination
1. **UI Interaction**: User clicks page number or next/previous
2. **Frontend JavaScript**:
   - Updates URL with page parameter
   - Reloads page with new parameter
3. **Backend Processing** (`app.py`):
   - `index()` route extracts page number from request
   - Uses Flask-SQLAlchemy pagination to get correct page of results
4. **UI Update**: Displays requested page of contacts

### Notification System
1. **Notification Creation**:
   - Various actions create notifications (sync, errors, etc.)
   - Notification objects stored in database
2. **UI Polling**:
   - JavaScript periodically calls `/notifications` endpoint
   - Backend returns recent notifications
   - UI updates notification badge count and list
3. **Notification Actions**:
   - Mark all as read: Sends POST to `/notifications/mark-all-read`
   - Clear all: Sends POST to `/notifications/clear-all`
   - The backend updates database accordingly

### View Mode Toggle (Active/Deleted)
1. **UI Interaction**: User toggles between active and deleted contacts
2. **Frontend JavaScript**:
   - Updates URL parameter for show_deleted
   - Reloads page
3. **Backend Processing**:
   - `index()` route changes filter based on show_deleted parameter
4. **UI Update**: Shows active or deleted contacts accordingly

---

## Settings Management

### Saving Settings
1. **UI Interaction**: User changes settings and clicks "Save"
2. **Frontend JavaScript**:
   - Submits form to `/settings/<category>/save` endpoint
3. **Backend Processing** (`app.py`):
   - `save_settings()` function receives the form data
   - For each setting in the category:
     - Gets value from form
     - Updates setting in database
   - Commits changes
4. **Response**: Redirects back to settings page with success message
5. **UI Update**: Shows success flash message

### Category Navigation
1. **UI Interaction**: User clicks on category tab (LDAP, CUCM, Email, etc.)
2. **Frontend Processing**:
   - Changes URL to include category
   - Page loads with selected category active
3. **Backend Processing**:
   - `settings()` route groups settings by category
   - Renders template with active category highlighted

---

## CSV Import/Export Operations

### Exporting Contacts to CSV
1. **UI Interaction**: User clicks "Export to CSV" button
2. **Frontend JavaScript**:
   - Makes GET request to `/export-csv` endpoint
3. **Backend Processing** (`app.py`):
   - `export_csv()` function queries all active contacts
   - Creates CSV file with headers and contact data
   - Formats CSV with UTF-8-BOM encoding for Excel compatibility
4. **Response**: Returns CSV file as download
5. **UI Result**: Browser downloads the CSV file

### CSV Import Preview
1. **UI Interaction**: User uploads CSV file and clicks "Preview"
2. **Frontend JavaScript**:
   - Reads file contents
   - Sends POST request to `/preview-import` with CSV data
3. **Backend Processing** (`app.py`):
   - `preview_import()` parses CSV data
   - For each row:
     - Formats MAC addresses
     - Finds matching contacts by username
     - Prepares preview data
   - Stores preview data in session
4. **Response**: Returns preview summary and entries
5. **UI Update**: Shows preview modal with changes

### Confirming CSV Import
1. **UI Interaction**: User reviews preview and clicks "Import"
2. **Frontend JavaScript**:
   - Sends POST request to `/confirm-import` endpoint
3. **Backend Processing** (`app.py`):
   - `confirm_import()` retrieves preview data from session
   - For each entry with a matching contact:
     - Updates MAC address and/or PIN if provided
     - Creates history records for changes
   - Commits all changes
4. **Response**: Returns number of updated contacts
5. **UI Update**: Shows success message with update count