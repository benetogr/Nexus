import sys
import subprocess
import os
import json
from io import StringIO, BytesIO
import csv

# Check if this is a reload by flask debug mode
is_reload = False
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    is_reload = True

def install_requirements():
    """Install required packages from requirements.txt"""
    try:
        # Only run this on the initial startup, not on reloads
        if not is_reload:
            # Redirect output to DEVNULL to suppress normal output
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.PIPE,
                check=True,
                text=True
            )
            # Only print a brief success message
            print("Packages verified successfully!")
            return True
    except subprocess.CalledProcessError as e:
        # If there's an error, then show the error output
        print(f"Error installing packages: {e.stderr}")
        sys.exit(1)

# Check Python version before doing anything else
if sys.version_info < (3, 8):
    print("Python 3.8 or higher is required!")
    sys.exit(1)

# Install requirements before anything else
install_requirements()

# Now we can safely import all modules
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from datetime import datetime, timedelta
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for, current_app, send_file, flash, session
from flask_sqlalchemy import SQLAlchemy
from models import db, Contact, History, Settings, Notification
from config import Config
from ldap_sync import LDAPSync
from apscheduler.schedulers.background import BackgroundScheduler
from flask_wtf.csrf import CSRFProtect, CSRFError
from cucm_service import CUCMService
from mail_service import MailService  # Import our new MailService class

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_settings():
    """Initialize default settings in the database"""
    default_settings = []
    
    # Use the model methods to get default settings
    default_settings.extend(Settings.get_default_ldap_settings())
    default_settings.extend(Settings.get_default_cucm_settings())
    
    # Email settings
    email_settings = [
        ('SMTP_SERVER', '', 'SMTP Server', 'string', 'email'),
        ('SMTP_PORT', '587', 'SMTP Port', 'integer', 'email'),
        ('SMTP_USERNAME', '', 'SMTP Username', 'string', 'email'),
        ('SMTP_PASSWORD', '', 'SMTP Password', 'string', 'email'),
        ('SMTP_USE_TLS', 'True', 'Use TLS', 'boolean', 'email'),
        ('MAIL_FROM', '', 'From Email Address', 'string', 'email'),
    ]
    default_settings.extend(email_settings)
    
    # Data Management settings
    data_settings = [
        ('IMPORT_BATCH_SIZE', '100', 'Import Batch Size', 'integer', 'data_management'),
        ('EXPORT_INCLUDE_HISTORY', 'False', 'Include History in Exports', 'boolean', 'data_management'),
        ('CSV_DELIMITER', ',', 'CSV Delimiter', 'string', 'data_management'),
        ('EXPORT_DATE_FORMAT', '%Y-%m-%d %H:%M', 'Export Date Format', 'string', 'data_management'),
        ('CSV_ENCODING', 'utf-8-sig', 'CSV File Encoding', 'string', 'data_management')
    ]
    default_settings.extend(data_settings)
    
    # Add all settings if they don't exist
    for key, value, description, type_, category in default_settings:
        if not Settings.query.filter_by(key=key).first():
            setting = Settings(
                key=key, value=value,
                description=description,
                type=type_, category=category
            )
            db.session.add(setting)
    db.session.commit()

def init_db():
    """Initialize database and create all tables"""
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        # Initialize settings
        init_settings()
        print("Database initialized successfully")

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        # Create tables first
        db.create_all()
        
        # Initialize settings if needed
        if Settings.query.count() == 0:
            init_settings()
        
        # Now create Config instance after settings are initialized
        config = Config()
        
        # Initialize scheduler for automatic LDAP sync
        scheduler = BackgroundScheduler()
        sync_interval = config.SYNC_INTERVAL  # Use config instance
        
        # Don't automatically start LDAP sync if settings are incomplete
        try:
            ldap_sync = LDAPSync(config)
            scheduler.add_job(
                func=ldap_sync.sync_contacts,
                trigger="interval", 
                hours=int(sync_interval)
            )
            scheduler.start()
        except ValueError as e:
            print(f"Warning: LDAP synchronization not enabled - {str(e)}")
            print("You can configure LDAP settings in the web interface.")
        except Exception as e:
            print(f"Error initializing LDAP sync: {str(e)}")
    
    return app

# Configure CSRF protection properly
app = create_app()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
csrf = CSRFProtect()
csrf.init_app(app)

# Add CSRF error handler
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return jsonify({
        'success': False,
        'error': 'CSRF token validation failed',
        'details': str(e)
    }), 400

app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Add this line

# Add CSRF token
csrf = CSRFProtect(app)

@app.context_processor
def inject_contacts_count():
    """Inject both LDAP and active contacts count into all templates"""
    try:
        ldap_total = Contact.query.filter(Contact.ldap_dn.isnot(None)).count()
        active_total = Contact.query.filter_by(is_active=True).count()
        return {
            'ldap_contacts': ldap_total,
            'active_contacts': active_total
        }
    except Exception as e:
        print(f"Error getting contact counts: {e}")  # Add error logging
        return {
            'ldap_contacts': 0,
            'active_contacts': 0
        }

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    show_deleted = request.args.get('show_deleted', '0') == '1'
    show_retired = request.args.get('show_retired', '0') == '1'
    search_term = request.args.get('search', '').strip()
    per_page = request.args.get('per_page', 10, type=int)
    
    # Limit per_page to valid values
    per_page = min(max(per_page, 10), 100)  # Between 10 and 100

    # Get ALL unique values from database, regardless of other filters
    phone_models = db.session.query(Contact.phone_model)\
        .filter(Contact.phone_model.isnot(None), Contact.phone_model != '')\
        .group_by(Contact.phone_model)\
        .order_by(Contact.phone_model)\
        .all()

    departments = db.session.query(Contact.department)\
        .filter(Contact.department.isnot(None), Contact.department != '')\
        .group_by(Contact.department)\
        .order_by(Contact.department)\
        .all()

    # Start with base query for current contacts
    query = Contact.query

    # Start with base query for historical matches
    history_contacts = []

    # Apply deletion filter
    query = query.filter_by(is_active=(not show_deleted))

    # Process filters from URL
    filters = {}
    try:
        filters_param = request.args.get('filters')
        if filters_param:
            filters = json.loads(filters_param)
            
            # Only apply filters that are explicitly set to True
            if filters.get('hasPin', False):
                query = query.filter(Contact.pin.isnot(None), Contact.pin != '')
            if filters.get('hasMac', False):
                query = query.filter(Contact.mac_address.isnot(None), Contact.mac_address != '')
            if filters.get('phoneModel'):
                query = query.filter(Contact.phone_model == filters['phoneModel'])
            if filters.get('department'):
                query = query.filter(Contact.department == filters['department'])
            if filters.get('showRetired', False):
                show_retired = True
    except json.JSONDecodeError:
        filters = {}

    # Apply student filter - hide students by default unless explicitly shown
    if not filters.get('showStudent', False):
        query = query.filter(Contact.title != 'student')

    # Apply retired filter unless explicitly shown
    if not (show_retired or filters.get('showRetired', False)):
        query = query.filter(Contact.title != 'retired')

    # Apply search if provided
    if search_term:
        search = f"%{search_term}%"

        # First, get contacts that match the search term in their current values
        query = query.filter(db.or_(
            Contact.first_name.ilike(search),
            Contact.last_name.ilike(search),
            Contact.email.ilike(search),
            Contact.phone.ilike(search),
            Contact.uid.ilike(search),
            Contact.department.ilike(search),
            Contact.title.ilike(search),
            Contact.phone_model.ilike(search),
            Contact.mac_address.ilike(search),
            Contact.pin.ilike(search),
            Contact.notes.ilike(search)
        ))

        # Then, get contacts that have the search term in their history
        history_matches = db.session.query(Contact).distinct()\
            .join(History)\
            .filter(
                db.or_(
                    History.old_value.ilike(search),
                    History.new_value.ilike(search)
                )
            ).all()

        # Remove contacts that are already in the current results
        current_ids = {c.id for c in query.all()}
        history_contacts = [c for c in history_matches if c.id not in current_ids]

    # Execute pagination for current contacts
    total = query.count()
    max_page = ((total - 1) // per_page) + 1 if total > 0 else 1
    
    # Adjust page number if it's out of range
    if page > max_page:
        return redirect(url_for('index', 
                              page=1,
                              per_page=per_page,
                              filters=request.args.get('filters'),
                              search=search_term,
                              show_deleted=show_deleted))
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('contacts.html',
                         contacts=pagination.items,
                         history_contacts=history_contacts,
                         pagination=pagination,
                         show_deleted=show_deleted,
                         show_retired=show_retired,
                         current_filters=filters,
                         phone_models=[m[0] for m in phone_models],
                         departments=[d[0] for d in departments],
                         search_term=search_term,
                         per_page=per_page)

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get application settings"""
    try:
        settings = Settings.query.all()
        return jsonify({
            'success': True,
            'settings': [{'key': s.key, 'value': s.value} for s in settings]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/phones/search', methods=['GET'])
def search_phones():
    """Search phones endpoint"""
    try:
        search = request.args.get('search', '')
        logger.info(f"Searching for phones with pattern: {search}")
        
        cucm = CUCMService()
        results = cucm.search_phones(search)
        return jsonify({'phones': results})
        
    except Exception as e:
        logger.error(f"Error searching phones: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/phones/<mac>/details', methods=['GET'])
def get_phone_details(mac):
    """Get phone details endpoint"""
    try:
        logger.info(f"Getting details for phone MAC: {mac}")
        
        # Create a CUCMService instance instead of using undefined cucm_service
        cucm_service = CUCMService()
        details = cucm_service.get_phone_by_mac(mac)
        
        if details:
            return jsonify(details)
        return jsonify({'error': 'Phone not found'}), 404
        
    except Exception as e:
        logger.error(f"Error getting phone details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/sync', methods=['POST'])
def sync():
    try:
        app.logger.info("Manual sync initiated")
        ldap_sync = LDAPSync()
        initial_count = Contact.query.count()
        
        conflicts = ldap_sync.sync_contacts()
        
        final_count = Contact.query.count()
        new_contacts = final_count - initial_count
        
        if conflicts:
            return jsonify({
                'success': True,
                'has_conflicts': True,
                'conflicts': len(conflicts),
                'message': f'Sync completed with {len(conflicts)} UID conflicts that need resolution'
            })
            
        if new_contacts > 0:
            notification = Notification(
                title="LDAP Sync Complete",
                message=f"Successfully synchronized contacts. {new_contacts} new contacts added."
            )
            db.session.add(notification)
            db.session.commit()
        
        app.logger.info("Manual sync completed successfully")
        return jsonify({
            'success': True,
            'message': 'Synchronization completed successfully'
        })
    except Exception as e:
        error_msg = str(e)
        app.logger.error(f"Manual sync failed: {error_msg}")
        
        # Add error notification
        notification = Notification(
            title="Sync Error",
            message=f"LDAP synchronization failed: {error_msg}"
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'success': False,
            'error': error_msg
        })

@app.route('/settings', methods=['GET'])
@app.route('/settings/<category>', methods=['GET'])
def settings(category=None):
    # Ensure default settings exist in database
    default_settings = []
    
    # Collect all default settings
    for setting_group in [
        Settings.get_default_ldap_settings(),
        Settings.get_default_cucm_settings(),
        # Add other default settings here
    ]:
        default_settings.extend(setting_group)
    
    # Check each default setting and add if missing
    for key, value, description, type_name, category_name in default_settings:
        if not Settings.query.filter_by(key=key).first():
            new_setting = Settings(
                key=key,
                value=value,
                description=description,
                type=type_name,
                category=category_name
            )
            db.session.add(new_setting)
    
    # Commit any added settings
    db.session.commit()
    
    settings = Settings.query.all()
    settings_by_category = {}
    for setting in settings:
        if setting.category not in settings_by_category:
            settings_by_category[setting.category] = []
        settings_by_category[setting.category].append(setting)
    
    # If no category is selected, show the first one
    if not category and settings_by_category:
        category = next(iter(settings_by_category))
    
    return render_template('settings.html', 
                         settings_by_category=settings_by_category,
                         active_category=category)

@app.route('/settings/<category>/save', methods=['POST'])
def save_settings(category):
    try:
        form_data = request.form.to_dict()
        settings = Settings.query.filter_by(category=category).all()
        
        for setting in settings:
            if setting.type == 'boolean':
                setting.value = str(setting.key in form_data)
            else:
                setting.value = form_data.get(setting.key, '')
        
        db.session.commit()
        flash(f'{category.title()} settings saved successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving {category} settings: {str(e)}', 'error')
    
    return redirect(url_for('settings', category=category))

@app.route('/restart-required')
def restart_required():
    return "Database configuration saved. Please restart the application to apply changes."

@app.route('/test-ldap', methods=['POST'])
def test_ldap():
    print("Testing LDAP connection...")
    try:
        # Get data from request if it's a POST with JSON data
        data = request.get_json()
        
        # Create LDAP sync instance, handling both cases:
        # 1. With provided parameters
        # 2. Using default settings from config
        if data:
            # Explicitly pass all available parameters
            ldap_sync = LDAPSync(
                server=data.get('server'),
                port=data.get('port'),
                bind_dn=data.get('bind_dn'),
                bind_password=data.get('bind_password'),
                base_dn=data.get('base_dn'),
                use_ssl=data.get('use_ssl', False),
                allow_anonymous=data.get('allow_anonymous', False)
            )
        else:
            # Use default settings from config
            ldap_sync = LDAPSync()
            
        # Try a simple search to verify connection works
        conn = ldap_sync.connect()
        
        result = conn.search(
            search_base=ldap_sync.base_dn,
            search_filter='(objectClass=*)',
            search_scope='BASE'
        )
        
        conn.unbind()
        return jsonify({
            'success': True, 
            'message': 'LDAP connection successful' + (' (anonymous binding)' if ldap_sync.use_anonymous else '')
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'LDAP connection failed: {str(e)}'
        })

@app.route('/contact/<int:contact_id>')
def contact_detail(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'id': contact.id,
            'uid': contact.uid,
            'first_name': contact.first_name,
            'last_name': contact.last_name,
            'email': contact.email,
            'phone': contact.phone,
            'phone_model': contact.phone_model,
            'mac_address': contact.mac_address,
            'pin': contact.pin,
            'notes': contact.notes,
            'department': contact.department,
            'title': contact.title,
        })
    return render_template('contacts.html', contact=contact)

@app.route('/contact/<int:contact_id>/update', methods=['POST'])
def contact_update(contact_id):
    try:
        contact = Contact.query.get_or_404(contact_id)
        
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Track changes for history
        changes = []
        # Update all fields
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'phone_model',
            'mac_address', 'pin', 'notes', 'department', 'title'
        ]
        
        for field in fields:
            new_value = data.get(field, '')
            old_value = getattr(contact, field) or ''
            if new_value != old_value:
                changes.append(History(
                    contact_id=contact.id,
                    field_name=field.replace('_', ' ').title(),
                    old_value=old_value,
                    new_value=new_value
                ))
                setattr(contact, field, new_value)
        
        # Add all history records
        if changes:
            for change in changes:
                db.session.add(change)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating contact: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/contact/<int:contact_id>/delete', methods=['POST'])
def contact_delete(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    contact.is_active = False
    
    # Add deletion to history
    history = History(
        contact_id=contact.id,
        field_name='Status',
        old_value='Active',
        new_value='Deleted'
    )
    db.session.add(history)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/contact/<int:contact_id>/restore', methods=['POST'])
def contact_restore(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    contact.is_active = True
    
    # Add restoration to history
    history = History(
        contact_id=contact.id,
        field_name='Status',
        old_value='Deleted',
        new_value='Active'
    )
    db.session.add(history)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/contact/<int:contact_id>/history')
def contact_history(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    history = History.query.filter_by(contact_id=contact_id)\
                         .order_by(History.changed_at.desc())\
                         .all()
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'contact_name': contact.full_name,
            'history': [{
                'changed_at': h.changed_at.isoformat(),
                'field_name': h.field_name,
                'old_value': h.old_value,
                'new_value': h.new_value
            } for h in history]
        })
    
    return render_template('contacts.html', contact=contact, history=history)

@app.route('/ldap-search', methods=['POST'])
def ldap_search():
    try:
        search_term = request.json.get('search_term', '').strip()
        exclude_students = request.json.get('exclude_students', False)
        exclude_alumni = request.json.get('exclude_alumni', False)
        
        if not search_term:
            return jsonify({
                'success': False,
                'error': 'Search term is required'
            })

        ldap_sync = LDAPSync()
        contacts = ldap_sync.search_user(
            search_term, 
            exclude_students=exclude_students,
            exclude_alumni=exclude_alumni
        )
        
        return jsonify({
            'success': True,
            'contacts': contacts
        })
    except Exception as e:
        app.logger.error(f"LDAP search error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/import-contact', methods=['POST'])
def import_contact():
    try:
        dn = request.json.get('dn')
        ldap_sync = LDAPSync()
        
        # Try to import and catch specific conflict exception
        try:
            result = ldap_sync.import_single_contact(dn)
            return jsonify({
                'success': True,
                'message': 'Contact imported successfully'
            })
        except LDAPSync.UIDConflict as e:  # We'll define this custom exception
            # Return conflict information instead of error
            return jsonify({
                'success': False,
                'conflict': True,
                'uid': e.uid,
                'contact_id': e.contact_id,
                'message': str(e)
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/export-csv')
def export_csv():
    # Create StringIO for text content first
    text_output = StringIO()
    writer = csv.writer(text_output, quoting=csv.QUOTE_ALL)
    
    # Write headers
    headers = ['First Name', 'Last Name', 'UID', 'Email', 'Phone', 
              'Department', 'Title', 'Phone Model', 'MAC Address', 
              'PIN', 'Notes', 'Last Sync']
    writer.writerow(headers)
    
    # Get all active contacts
    contacts = Contact.query.filter_by(is_active=True).all()
    
    # Write data rows
    for contact in contacts:
        writer.writerow([
            contact.first_name,
            contact.last_name,
            contact.uid,
            contact.email,
            contact.phone,
            contact.department,
            contact.title,
            contact.phone_model,
            contact.mac_address,
            contact.pin,
            contact.notes,
            contact.last_sync.strftime('%Y-%m-%d %H:%M') if contact.last_sync else ''
        ])
    
    # Get the string content and encode it
    text_content = text_output.getvalue()
    text_output.close()
    
    # Create binary output with BOM for Excel
    binary_output = BytesIO()
    binary_output.write(text_content.encode('utf-8-sig'))
    binary_output.seek(0)
    
    return send_file(
        binary_output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='contacts_export.csv'
    )

@app.route('/contact/<int:contact_id>/send-pin', methods=['POST'])
def send_pin_email(contact_id):
    try:
        contact = Contact.query.get_or_404(contact_id)
        
        # Use the MailService to send the email
        mail_service = MailService(Settings)
        success, error = mail_service.send_pin_email(contact)
        
        if not success:
            return jsonify({
                'success': False,
                'error': error
            }), 500

        # Add to history
        history = History(
            contact_id=contact.id,
            field_name='PIN Email',
            old_value='',
            new_value=f'Sent to {contact.email}'
        )
        db.session.add(history)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'PIN sent successfully'
        })
        
    except Exception as e:
        app.logger.error(f"Error sending PIN email: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)}
        ), 500

def format_mac_address(mac):
    """Format MAC address to add colons"""
    # Remove any non-hex characters
    mac = re.sub('[^0-9a-fA-F]', '', mac)
    # Convert to uppercase
    mac = mac.upper()
    # Add colons
    return ':'.join(mac[i:i+2] for i in range(0, len(mac), 2))

@app.route('/preview-import', methods=['POST'])
def preview_import():
    try:
        csv_data = request.json.get('csv_data', '')
        if not csv_data:
            return jsonify({'success': False, 'error': 'No CSV data provided'})

        # Parse CSV data
        reader = csv.DictReader(StringIO(csv_data))
        entries = []
        seen_usernames = set()

        # Store preview data in session
        preview_data = []

        for row in reader:
            if not all(key in row for key in ['username', 'mac', 'pin']):
                return jsonify({'success': False, 
                              'error': 'CSV must have username, mac, and pin columns'})

            username = row['username'].strip()
            mac = row['mac'].strip()
            pin = row['pin'].strip()
            
            # Skip empty rows
            if not username:
                continue
                
            if username in seen_usernames:
                continue
                
            seen_usernames.add(username)
            
            # Format MAC only if provided
            formatted_mac = format_mac_address(mac) if mac else None
            if formatted_mac and len(formatted_mac) != 17:  # Skip invalid MACs
                formatted_mac = None
            
            # Find matching contact
            contact = Contact.query.filter_by(uid=username).first()
            
            entry = {
                'username': username,
                'current_mac': contact.mac_address if contact else None,
                'new_mac': formatted_mac,
                'current_pin': contact.pin if contact else None,
                'new_pin': pin if pin else None,
                'status': 'Match' if contact else 'No match'
            }
            entries.append(entry)
            preview_data.append({
                'username': username,
                'mac': formatted_mac,
                'pin': pin if pin else None,
                'contact_id': contact.id if contact else None
            })
        
        # Store in session for later use
        session['preview_data'] = preview_data
        
        return jsonify({
            'success': True,
            'preview': {
                'total': len(entries),
                'matches': sum(1 for e in entries if e['status'] == 'Match'),
                'nonmatches': sum(1 for e in entries if e['status'] == 'No match'),
                'entries': entries
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/confirm-import', methods=['POST'])
def confirm_import():
    try:
        preview_data = session.get('preview_data', [])
        if not preview_data:
            return jsonify({'success': False, 'error': 'No import data found'})
        
        updated = 0
        for entry in preview_data:
            if entry['contact_id']:
                contact = Contact.query.get(entry['contact_id'])
                if contact:
                    changes = []
                    
                    # Check MAC Address changes - only update if new MAC is provided
                    if entry['mac'] is not None and contact.mac_address != entry['mac']:
                        changes.append(History(
                            contact_id=contact.id,
                            field_name='MAC Address',
                            old_value=contact.mac_address or '',
                            new_value=entry['mac']
                        ))
                        contact.mac_address = entry['mac']
                        
                    # Check PIN changes - only update if new PIN is provided
                    if entry['pin'] is not None and contact.pin != entry['pin']:
                        changes.append(History(
                            contact_id=contact.id,
                            field_name='PIN',
                            old_value=contact.pin or '',
                            new_value=entry['pin']
                        ))
                        contact.pin = entry['pin']
                    
                    # Add history records
                    if changes:
                        for change in changes:
                            db.session.add(change)
                        updated += 1
        
        db.session.commit()
        
        # Clear the preview data
        session.pop('preview_data', None)
        
        return jsonify({
            'success': True,
            'updated': updated
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/notifications')
def get_notifications():
    notifications = Notification.query.order_by(Notification.created_at.desc()).limit(20).all()
    return jsonify({
        'success': True,
        'notifications': [n.to_dict() for n in notifications]
    })

@app.route('/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    try:
        Notification.query.filter_by(unread=True).update({'unread': False})
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/notifications/clear-all', methods=['POST'])
def clear_all_notifications():
    try:
        Notification.query.delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/notifications/create-test', methods=['POST'])
def create_test_notification():
    try:
        data = request.json
        notification = Notification(
            title=data.get('title', 'Test Notification'),
            message=data.get('message', 'Test notification message'),
            unread=True
        )
        db.session.add(notification)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/contact/create', methods=['POST'])
def create_contact():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
            
        # Validate required fields
        required_fields = ['first_name', 'last_name', 'uid']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        contact = Contact(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            uid=data.get('uid'),
            email=data.get('email'),
            phone=data.get('phone'),
            department=data.get('department'),
            title=data.get('title'),
            phone_model=data.get('phone_model'),
            mac_address=data.get('mac_address'),
            pin=data.get('pin'),
            notes=data.get('notes'),
            source='manual',
            is_active=True,
            last_sync=datetime.utcnow()
        )
        
        db.session.add(contact)
        db.session.flush()  # Get the contact ID before committing
        
        # Add creation to history
        history = History(
            contact_id=contact.id,
            field_name='Creation',
            old_value='',
            new_value='Contact manually created'
        )
        db.session.add(history)
        
        # Create notification
        notification = Notification(
            title="New Contact Created",
            message=f"Contact {contact.first_name} {contact.last_name} was manually created.",
            unread=True
        )
        db.session.add(notification)
        
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Contact created successfully',
            'contact_id': contact.id
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error creating contact: {str(e)}")
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

@app.route('/conflicts')
def view_conflicts():
    conflicts = Contact.query.filter_by(has_conflict=True).all()
    return render_template('conflicts.html', conflicts=conflicts)

@app.route('/resolve-conflict/<int:contact_id>', methods=['POST'])
def resolve_conflict(contact_id):
    try:
        action = request.json.get('action')  # 'keep_manual', 'use_ldap', or 'merge_ldap'
        dn = request.json.get('dn')
        contact = Contact.query.get_or_404(contact_id)
        
        if not contact.has_conflict:
            return jsonify({'success': False, 'error': 'No conflict found'})

        if action == 'keep_manual':
            # Keep manual contact as is
            contact.has_conflict = False
            contact.conflict_with = None
            db.session.commit()
            
        elif action == 'use_ldap':
            # Completely replace with LDAP data
            ldap_sync = LDAPSync()
            ldap_sync.import_single_contact(dn, force=True)
            contact.has_conflict = False
            contact.conflict_with = None
            db.session.commit()
            
        elif action == 'merge_ldap':
            # Update empty fields and convert to LDAP contact
            ldap_sync = LDAPSync()
            ldap_sync.merge_contact(contact, dn)
            contact.has_conflict = False
            contact.conflict_with = None
            contact.source = 'ldap'  # Convert to LDAP contact
            contact.ldap_dn = dn     # Set LDAP DN
            db.session.commit()
            
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@app.route('/contact/<int:contact_id>/permanent-delete', methods=['POST'])
def contact_permanent_delete(contact_id):
    try:
        contact = Contact.query.get_or_404(contact_id)
        if contact.is_active:
            return jsonify({
                'success': False,
                'error': 'Cannot permanently delete an active contact'
            })
        
        # Add a notification
        notification = Notification(
            title="Contact Permanently Deleted",
            message=f"Contact {contact.full_name} ({contact.uid}) was permanently deleted.",
            unread=True
        )
        db.session.add(notification)
        
        # Delete associated history
        History.query.filter_by(contact_id=contact_id).delete()
        
        # Delete the contact
        db.session.delete(contact)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/test-cucm', methods=['POST'])
def test_cucm():
    """Test CUCM connection endpoint"""
    try:
        logger.info("Testing CUCM connection...")
        cucm = CUCMService()
        
        # Test connection with credentials
        client = cucm._get_client()  # This will now raise an error if auth fails
        
        # Make a test query
        result = client.listPhone(
            searchCriteria={'name': 'SEP%'},
            returnedTags={'name': ''},
            first=1
        )
        
        logger.info("CUCM connection test successful")
        return jsonify({
            'success': True,
            'message': 'CUCM connection successful'
        })
        
    except ValueError as e:
        # Handle authentication and configuration errors
        logger.error(f"CUCM configuration error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })
    except Exception as e:
        # Handle other errors
        logger.error(f"CUCM connection test failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        })

@app.route('/api/contact/<int:contact_id>/fetch-auth-code', methods=['POST'])
def fetch_auth_code(contact_id):
    try:
        contact = Contact.query.get_or_404(contact_id)
        if not contact.uid:
            return jsonify({
                'success': False,
                'error': 'Contact has no UID'
            })

        cucm = CUCMService()
        auth_code = cucm.fetchAuthCode(contact.uid)
        
        if auth_code:
            # Save old PIN for history
            old_pin = contact.pin
            
            # Update contact's PIN
            contact.pin = str(auth_code)
            
            # Add to history
            history = History(
                contact_id=contact.id,
                field_name='PIN',
                old_value=old_pin or '',
                new_value=str(auth_code)
            )
            db.session.add(history)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'pin': auth_code
            })
        
        return jsonify({
            'success': False,
            'error': 'No authorization code found for this user'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/debug/drop-all-contacts', methods=['POST'])
def debug_drop_all_contacts():
    """Debug endpoint to drop all contacts from the database"""
    try:
        # First check if this is a debug build/environment
        if not app.debug:
            return jsonify({
                'success': False,
                'error': 'This operation is only allowed in debug mode'
            }), 403

        # Get counts before deletion
        total_count = Contact.query.count()
        active_count = Contact.query.filter_by(is_active=True).count()
        
        # Delete all contact history first (due to foreign key constraints)
        History.query.delete()
        
        # Delete all contacts
        Contact.query.delete()
        
        # Add notification
        notification = Notification(
            title="Database Cleared",
            message=f"All contacts have been deleted: {active_count} active and {total_count - active_count} inactive contacts.",
            unread=True
        )
        db.session.add(notification)
        
        # Commit changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Deleted {total_count} contacts ({active_count} active)'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error dropping contacts: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/test-ldap-connection', methods=['POST'])
def test_ldap_connection():
    """Test LDAP connection with provided parameters"""
    try:
        # Log the raw request for debugging
        logger.info(f"LDAP test request - Content-Type: {request.content_type}")
        logger.info(f"LDAP test request - Data type: {type(request.data)}")
        
        # Try to get JSON data from request
        try:
            data = request.get_json()
            logger.info(f"Parsed request data: {data}")
        except Exception as e:
            logger.error(f"Error parsing JSON data: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Invalid JSON data: {str(e)}'
            })
        
        if not data:
            logger.error("No data provided or data not in JSON format")
            return jsonify({
                'success': False,
                'error': 'No data provided or invalid content type'
            })
        
        server = data.get('server')
        port = data.get('port')
        bind_dn = data.get('bind_dn')
        bind_password = data.get('bind_password')
        base_dn = data.get('base_dn') 
        use_ssl = data.get('use_ssl', False)
        allow_anonymous = data.get('allow_anonymous', False)
        
        # Log the parsed parameters (not including password)
        logger.info(f"LDAP test parameters - Server: {server}, Port: {port}")
        logger.info(f"LDAP test parameters - Bind DN: {bind_dn}")
        logger.info(f"LDAP test parameters - Base DN: {base_dn}")
        logger.info(f"LDAP test parameters - SSL: {use_ssl}, Allow Anonymous: {allow_anonymous}")
        
        # Server and base_dn are always required
        if not server or not port or not base_dn:
            return jsonify({
                'success': False,
                'error': 'Server, port and base DN are required'
            })
        
        # Check if credentials are incomplete (one provided but not the other)
        if (bind_dn and not bind_password) or (not bind_dn and bind_password):
            return jsonify({
                'success': False,
                'error': 'Both bind DN and password must be provided together'
            })
            
        # Credentials are either both provided or both missing
        has_credentials = bind_dn and bind_password
        
        # If anonymous binding is disabled and no credentials provided, fail early
        if not allow_anonymous and not has_credentials:
            return jsonify({
                'success': False,
                'error': 'Bind DN and password are required when anonymous binding is disabled'
            })
        
        # Will we use anonymous binding?
        use_anonymous = not has_credentials and allow_anonymous
        
        logger.info(f"LDAP Test - Anonymous binding allowed: {allow_anonymous}")
        logger.info(f"LDAP Test - Credentials provided: {has_credentials}")
        logger.info(f"LDAP Test - Will use anonymous: {use_anonymous}")
        
        # Try creating LDAPSync instance and connecting
        try:
            ldap_sync = LDAPSync(
                server=server,
                port=int(port) if port else None,
                bind_dn=bind_dn,
                bind_password=bind_password,
                base_dn=base_dn,
                use_ssl=use_ssl,
                allow_anonymous=allow_anonymous
            )
            
            conn = ldap_sync.connect()
            logger.info(f"LDAP connection successful, connection object: {conn}")
            
            # Try to perform a test search to verify everything works
            result = conn.search(
                search_base=base_dn,
                search_filter='(objectClass=*)',
                search_scope='BASE',
                attributes=['objectClass']
            )
            
            if result:
                # Check if we're authenticated (anonymous vs. bound)
                bound_user = conn.bound
                logger.info(f"Search successful. Authenticated: {bound_user}")
                
                # Get some basic info about the directory
                logger.info(f"Connected to: {conn.server.host}")
                logger.info(f"Authentication type: {'Anonymous' if use_anonymous else 'Authenticated'}")
                
                conn.unbind()
                return jsonify({
                    'success': True,
                    'message': f'LDAP connection successful! {"(anonymous)" if use_anonymous else f"(authenticated as {bind_dn})"}'
                })
            else:
                logger.warning(f"Search failed: {conn.result}")
                conn.unbind()
                return jsonify({
                    'success': False,
                    'error': f'Connected but search failed: {conn.result}'
                })
                
        except Exception as e:
            logger.error(f"LDAP connection test failed: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
            
    except Exception as e:
        logger.error(f"Request error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Request error: {str(e)}"
        })

if __name__ == '__main__':
    # Add database initialization option
    if len(sys.argv) > 1 and sys.argv[1] == '--init-db':
        init_db()
        sys.exit(0)
    app.run(debug=True)