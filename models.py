from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ldap_dn = db.Column(db.String(255), unique=True)
    uid = db.Column(db.String(100), unique=True)  # Add unique constraint
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    phone_model = db.Column(db.String(255))
    mac_address = db.Column(db.String(255))
    pin = db.Column(db.String(255))
    notes = db.Column(db.Text)  # Changed to Text for longer content
    is_active = db.Column(db.Boolean, default=True)
    last_sync = db.Column(db.DateTime, default=datetime.utcnow)
    department = db.Column(db.String(255))  # for ou field
    title = db.Column(db.String(255))      # for eduPersonAffiliation field
    source = db.Column(db.String(20), default='manual')  # 'ldap' or 'manual'
    has_conflict = db.Column(db.Boolean, default=False)  # New field
    conflict_with = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=True)  # New field
    
    history = db.relationship('History', backref='contact', lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def custom_fields(self):
        return {
            'Phone Model': self.phone_model,
            'MAC Address': self.mac_address,
            'PIN': self.pin,
            'Notes': self.notes,
        }

    def to_dict(self):
        return {
            'id': self.id,
            'uid': self.uid,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'phone_model': self.phone_model,
            'mac_address': self.mac_address,
            'pin': self.pin,
            'notes': self.notes,
            'is_active': self.is_active,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'department': self.department,
            'title': self.title,
        }

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    field_name = db.Column(db.String(50))
    old_value = db.Column(db.String(255))
    new_value = db.Column(db.String(255))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    changed_by = db.Column(db.String(100))

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True)
    value = db.Column(db.Text)
    description = db.Column(db.String(256))
    type = db.Column(db.String(32))  # string, boolean, integer, text
    category = db.Column(db.String(32))  # ldap, email, etc.
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_value(key, default=None):
        """Get setting value directly from database"""
        try:
            setting = Settings.query.filter_by(key=key).first()
            if setting:
                return setting.value
            return default
        except Exception:
            return default

    @staticmethod
    def get_default_cucm_settings():
        return [
            ('CUCM_HOST', '10.1.20.12', 'CUCM Server Host', 'string', 'cucm'),
            ('CUCM_USERNAME', '', 'CUCM AXL Username', 'string', 'cucm'),
            ('CUCM_PASSWORD', '', 'CUCM AXL Password', 'string', 'cucm'),
            ('CUCM_VERSION', '14.0.1', 'CUCM Version', 'string', 'cucm'),
            ('CUCM_VERIFY_CERT', 'False', 'Verify SSL Certificate', 'boolean', 'cucm')
        ]

    @staticmethod
    def get_default_ldap_settings():
        return [
            # Connection settings
            ('LDAP_SERVER', 'ldap.duth.gr', 'LDAP Server Address', 'string', 'ldap'),
            ('LDAP_PORT', '389', 'LDAP Port', 'string', 'ldap'),
            ('LDAP_USE_SSL', 'False', 'Use SSL/TLS for LDAP Connection', 'boolean', 'ldap'),
            
            # Authentication settings
            ('LDAP_BIND_DN', '', 'LDAP Bind DN (Username)', 'string', 'ldap'),
            ('LDAP_BIND_PASSWORD', '', 'LDAP Bind Password', 'string', 'ldap'),
            ('LDAP_ALLOW_ANONYMOUS', 'True', 'Allow Anonymous Binding', 'boolean', 'ldap'),  # Changed default to 'True'
            
            # Directory search settings
            ('LDAP_BASE_DN', '', 'LDAP Base DN for searches', 'string', 'ldap'),
            ('LDAP_USER_FILTER', '(uid=*)', 'LDAP User Filter', 'string', 'ldap'),
            
            # Synchronization settings
            ('LDAP_SYNC_ENABLED', 'False', 'Enable Automatic LDAP Sync', 'boolean', 'ldap'),
            ('LDAP_SYNC_INTERVAL', '60', 'LDAP Sync Interval (minutes)', 'integer', 'ldap'),
            ('LDAP_PAGE_SIZE', '100', 'LDAP Page Size', 'integer', 'ldap'),
            ('LDAP_MAX_ENTRIES', '1000', 'Max LDAP Entries (0 for no limit)', 'integer', 'ldap'),
        ]

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    unread = db.Column(db.Boolean, default=True)

    def to_dict(self):
        now = datetime.utcnow()
        delta = now - self.created_at
        
        if delta < timedelta(minutes=1):
            time_ago = "just now"
        elif delta < timedelta(hours=1):
            mins = int(delta.total_seconds() / 60)
            time_ago = f"{mins} minute{'s' if mins != 1 else ''} ago"
        elif delta < timedelta(days=1):
            hours = int(delta.total_seconds() / 3600)
            time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = delta.days
            time_ago = f"{days} day{'s' if days != 1 else ''} ago"
            
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'time_ago': time_ago,
            'unread': self.unread
        }
