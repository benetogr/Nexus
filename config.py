from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SQLITE_DB = 'sqlite:///app.db'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = SQLITE_DB
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    @staticmethod
    def get_setting(key, default=None):
        try:
            from models import Settings
            setting = Settings.query.filter_by(key=key).first()
            return setting.value if setting else default
        except:
            return default
    
    # Dynamic LDAP Configuration
    @property
    def LDAP_SERVER(self):
        return self.get_setting('LDAP_SERVER', 'ldap://ldap.duth.gr:389')
    
    @property
    def LDAP_BASE_DN(self):
        return self.get_setting('LDAP_BASE_DN', 'dc=example,dc=com')
    
    @property
    def LDAP_USER_DN(self):
        return self.get_setting('LDAP_USER_DN', None)
    
    @property
    def LDAP_PASSWORD(self):
        return self.get_setting('LDAP_PASSWORD', None)
    
    @property
    def LDAP_USE_ANONYMOUS(self):
        return self.get_setting('LDAP_USE_ANONYMOUS', 'False').lower() == 'true'
    
    @property
    def LDAP_EXCLUDE_STUDENTS(self):
        return self.get_setting('LDAP_EXCLUDE_STUDENTS', 'False').lower() == 'true'
    
    # Dynamic Sync Configuration
    @property
    def SYNC_INTERVAL(self):
        return int(self.get_setting('SYNC_INTERVAL', '24'))
    
    @property
    def RETENTION_PERIOD(self):
        return int(self.get_setting('RETENTION_PERIOD', '30'))
    
    # CUCM Configuration
    @property
    def CUCM_HOST(self):
        return self.get_setting('CUCM_HOST', '')
    
    @property
    def CUCM_USERNAME(self):
        return self.get_setting('CUCM_USERNAME', '')
    
    @property
    def CUCM_PASSWORD(self):
        return self.get_setting('CUCM_PASSWORD', '')
    
    @property
    def CUCM_VERSION(self):
        return self.get_setting('CUCM_VERSION', '12.5')
    
    @property
    def CUCM_VERIFY_CERT(self):
        return self.get_setting('CUCM_VERIFY_CERT', 'False').lower() == 'true'
    
    @property
    def CUCM_CACHE_TTL(self):
        return int(self.get_setting('CUCM_CACHE_TTL', '3600'))
    
    @property
    def CUCM_SEARCH_LIMIT(self):
        return int(self.get_setting('CUCM_SEARCH_LIMIT', '100'))
