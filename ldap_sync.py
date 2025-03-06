from ldap3 import Server, Connection, SUBTREE, ALL_ATTRIBUTES, ALL, LEVEL, MODIFY_REPLACE, Tls, SIMPLE, AUTO_BIND_NO_TLS, AUTO_BIND_TLS_BEFORE_BIND
import ssl
from models import db, Contact, Settings, Notification  # Add Notification to imports
from datetime import datetime
from config import Config
import logging
from cucm_service import CUCMService  # Add this import at the top

class LDAPSync:
    class UIDConflict(Exception):
        def __init__(self, uid, contact_id):
            self.uid = uid
            self.contact_id = contact_id
            super().__init__(f"UID conflict detected with existing contact: {uid}")

    def __init__(self, config=None, server=None, port=None, bind_dn=None, bind_password=None, base_dn=None, use_ssl=None, allow_anonymous=None):
        # Setup logging first so we can use it during initialization
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('LDAPSync')
        
        # Get fresh config instance to ensure latest settings
        if config is None:
            config = Config()
        
        # Allow parameter override or use config/settings
        self.ldap_server = server or Settings.get_value('LDAP_SERVER', '')
        self.base_dn = base_dn or Settings.get_value('LDAP_BASE_DN', '')
        
        # Get bind credentials - explicitly check for None to handle empty strings properly
        # First try parameters, then settings
        if bind_dn is not None:
            self.user_dn = bind_dn
        else:
            self.user_dn = Settings.get_value('LDAP_BIND_DN', '')
            
        if bind_password is not None:
            self.password = bind_password
        else:
            self.password = Settings.get_value('LDAP_BIND_PASSWORD', '')
        
        # Strip any leading/trailing whitespace from credentials
        if self.user_dn:
            self.user_dn = self.user_dn.strip()
        if self.password:
            self.password = self.password.strip()
            
        # Check if anonymous binding is allowed - default to False for security
        if allow_anonymous is not None:
            self.allow_anonymous = allow_anonymous
        else:
            self.allow_anonymous = Settings.get_value('LDAP_ALLOW_ANONYMOUS', 'False').lower() == 'true'
            
        self.logger.info(f"LDAP credentials - bind DN provided: {'Yes' if self.user_dn else 'No'}, password provided: {'Yes' if self.password else 'No'}")
        self.logger.info(f"Anonymous binding allowed: {self.allow_anonymous}")
        
        # Force the use of credentials when both bind_dn and password are provided
        if self.user_dn and self.password:
            self.use_anonymous = False
            self.logger.info("Will use authenticated binding with provided credentials")
        else:
            # Only use anonymous if allowed and credentials are missing
            self.use_anonymous = self.allow_anonymous
            if self.use_anonymous:
                self.logger.info("Will use anonymous binding (no complete credentials provided)")
            else:
                self.logger.error("Cannot use anonymous binding (disabled) and credentials are incomplete")
                missing = []
                if not self.user_dn:
                    missing.append("bind_dn")
                if not self.password:
                    missing.append("bind_password")
                raise ValueError(f"LDAP credentials incomplete: missing {', '.join(missing)}. Either provide complete credentials or enable anonymous binding.")

        # Port parameter (needed for SSL)
        self.port = port or int(Settings.get_value('LDAP_PORT', '389'))
        
        # Initialize use_ssl parameter
        if use_ssl is not None:
            self.use_ssl = use_ssl
        else:
            self.use_ssl = Settings.get_value('LDAP_USE_SSL', 'False').lower() == 'true'
        
        # Default to False if setting doesn't exist yet
        try:
            self.exclude_students = config.LDAP_EXCLUDE_STUDENTS
        except AttributeError:
            self.exclude_students = False
            
        self.page_size = 100
        # Update this limit to a much higher value or make it configurable
        self.max_entries = 1000  # Increased from 100 to 1000
        
        # Build search filter based on settings
        base_filter = "(objectClass=person)"
        if self.exclude_students:
            self.search_filter = f"(&{base_filter}(!(eduPersonAffiliation=student)))"
        else:
            self.search_filter = base_filter

    def connect(self):
        self.logger.info(f"Connecting to LDAP server: {self.ldap_server}, Port: {self.port}, SSL: {self.use_ssl}")
        
        if self.use_anonymous:
            self.logger.info("Using anonymous binding (explicitly enabled)")
        else:
            # Log credentials being used (don't log actual password)
            self.logger.info(f"Using authenticated binding with DN: '{self.user_dn}'")
            if not self.password:
                self.logger.warning("Password is empty but authenticated binding was requested")
        
        try:
            if self.use_anonymous:
                # Only use anonymous binding if explicitly allowed and credentials are missing
                self.logger.info("Connecting with anonymous binding")
                if self.use_ssl:
                    # Create TLS configuration for anonymous binding with SSL
                    tls = Tls(validate=ssl.CERT_NONE)
                    server = Server(self.ldap_server, port=self.port, use_ssl=True, tls=tls)
                else:
                    server = Server(self.ldap_server, port=self.port, get_info=ALL)
                conn = Connection(server, auto_bind=True)
            else:
                # Validate credentials before attempting to connect
                if not self.user_dn:
                    self.logger.error("Missing LDAP bind_dn")
                    raise ValueError("LDAP bind_dn is required for authentication")
                    
                if not self.password:
                    self.logger.error("Missing LDAP bind_password")
                    raise ValueError("LDAP bind_password is required for authentication")
                
                # Create server object with or without SSL
                if self.use_ssl:
                    # Create TLS configuration
                    tls = Tls(validate=ssl.CERT_NONE)
                    self.logger.info(f"Creating SSL server connection to {self.ldap_server}:{self.port}")
                    server = Server(self.ldap_server, port=self.port, use_ssl=True, tls=tls, get_info=ALL)
                else:
                    self.logger.info(f"Creating non-SSL server connection to {self.ldap_server}:{self.port}")
                    server = Server(self.ldap_server, port=self.port, get_info=ALL)
                
                # Attempt authenticated connection with proper credentials
                self.logger.info("Attempting authenticated binding...")
                conn = Connection(
                    server,
                    user=self.user_dn,
                    password=self.password,
                    authentication=SIMPLE,
                    auto_bind=True
                )
                self.logger.info(f"Bind successful! Connection: {conn}")
            
            # Verify base DN exists
            if not self._verify_base_dn(conn):
                raise Exception(f"Base DN '{self.base_dn}' not found or not accessible")
            
            self.logger.info("LDAP connection successful")
            return conn
        except Exception as e:
            self.logger.error(f"LDAP connection failed: {str(e)}")
            # Add more detailed debugging info about the connection
            self.logger.error(f"Connection details - Server: {self.ldap_server}, Port: {self.port}, SSL: {self.use_ssl}, Anonymous: {self.use_anonymous}")
            raise

    def _verify_base_dn(self, conn):
        """Verify that the base DN exists and is accessible"""
        try:
            # Try to read the base DN entry
            result = conn.search(
                search_base=self.base_dn,
                search_filter='(objectClass=*)',
                search_scope=LEVEL,
                attributes=['objectClass']
            )
            return result
        except Exception as e:
            self.logger.error(f"Base DN verification failed: {str(e)}")
            return False

    def get_root_dse(self, conn):
        """Get Root DSE to find available naming contexts"""
        try:
            conn.search('', '(objectClass=*)', search_scope=LEVEL, attributes=['namingContexts', 'defaultNamingContext'])
            if conn.entries:
                contexts = conn.entries[0].namingContexts
                self.logger.info(f"Available naming contexts: {contexts}")
                return contexts
            return []
        except Exception as e:
            self.logger.error(f"Failed to get Root DSE: {str(e)}")
            return []

    def sync_contacts(self):
        self.logger.info("Starting LDAP sync")
        conn = self.connect()
        total_entries = 0
        conflicts = []
        added_contacts = 0
        updated_contacts = 0
        
        try:
            # Use the configured base DN first
            base_dn = self.base_dn
            
            # If base DN verification fails, try to find an alternative
            if not self._verify_base_dn(conn):
                self.logger.warning(f"Base DN '{self.base_dn}' not found, attempting to find alternatives...")
                contexts = self.get_root_dse(conn)
                if contexts and len(contexts) > 0:
                    base_dn = str(contexts[0])
                    self.logger.info(f"Using alternative base DN: {base_dn}")
                else:
                    self.logger.error("No valid naming contexts found and base DN invalid")
                    raise Exception("No valid LDAP base DN found. Please check your LDAP settings.")

            # Set paged search control with size limit and exclude students
            self.logger.info(f"Performing LDAP search with filter: {self.search_filter}")
            
            # Use paged search to bypass server-side size limits
            entries_list = []
            cookie = None
            
            # Implement paged search
            self.logger.info("Using paged search to retrieve all entries")
            
            while True:
                # Use paged search control to retrieve entries in batches
                search_result = conn.search(
                    search_base=base_dn,
                    search_filter=self.search_filter,
                    search_scope=SUBTREE,
                    attributes=['uid', 'cn', 'sn', 'givenName', 'mail', 'telephoneNumber', 
                              'ou', 'eduPersonAffiliation'],
                    paged_size=self.page_size,
                    paged_cookie=cookie
                )
                
                if not search_result:
                    err_msg = conn.result.get('description', 'Unknown error')
                    self.logger.warning(f"LDAP search returned no results: {err_msg}")
                    break
                    
                entries_list.extend(conn.entries)
                self.logger.info(f"Retrieved {len(conn.entries)} entries in this page, total so far: {len(entries_list)}")
                
                cookie = conn.result.get('controls', {}).get('1.2.840.113556.1.4.319', {}).get('value', {}).get('cookie')
                if not cookie:
                    # No more pages
                    break

            self.logger.info(f"Found {len(entries_list)} total entries")
            current_time = datetime.utcnow()
            
            # Process all entries
            for entry in entries_list:
                # Remove size limit check, we'll process all entries
                # if total_entries >= self.max_entries:
                #    break

                self.logger.debug(f"Processing entry: {entry.entry_dn}")
                entry_data = entry.entry_attributes_as_dict
                entry_dn = entry.entry_dn
                uid = self._get_list_value(entry_data.get('uid', []))
                
                if not uid:  # Skip entries without UID
                    self.logger.warning(f"Skipping entry without UID: {entry_dn}")
                    continue

                # Check for existing contact
                existing_by_uid = Contact.query.filter_by(uid=uid).first()
                existing_by_dn = Contact.query.filter_by(ldap_dn=entry_dn).first()

                if existing_by_uid and existing_by_dn and existing_by_uid != existing_by_dn:
                    # We have a conflict - store it and skip this entry
                    self.logger.warning(f"Found conflict for UID {uid}")
                    existing_by_uid.has_conflict = True
                    existing_by_uid.conflict_with = existing_by_dn.id
                    conflicts.append({
                        'uid': uid,
                        'manual_contact_id': existing_by_uid.id,
                        'ldap_dn': entry_dn
                    })
                    continue

                if existing_by_dn:
                    self.logger.debug(f"Updating existing contact: {uid}")
                    contact = existing_by_dn
                    updated_contacts += 1
                else:
                    self.logger.debug(f"Creating new contact: {uid}")
                    contact = Contact(ldap_dn=entry_dn)
                    db.session.add(contact)
                    added_contacts += 1

                # Update contact attributes
                contact.uid = uid
                contact.first_name = self._get_list_value(entry_data.get('givenName', []))
                contact.last_name = self._get_list_value(entry_data.get('sn', []))
                contact.email = self._get_list_value(entry_data.get('mail', []))
                contact.phone = self._get_list_value(entry_data.get('telephoneNumber', []))
                contact.department = self._get_list_value(entry_data.get('ou', []))
                contact.title = self._get_list_value(entry_data.get('eduPersonAffiliation', []))
                contact.last_sync = current_time
                contact.source = 'ldap'
                contact.is_active = True
                
                # After contact is created/updated, enrich with CUCM data
                if contact:
                    self._enrich_with_cucm_data(contact)
                
                total_entries += 1
                
                if total_entries % 10 == 0:  # Commit more frequently
                    self.logger.info(f"Processed {total_entries} entries. Committing changes...")
                    db.session.commit()

            # Final commit
            db.session.commit()

            # Create notification for sync results
            notification = Notification(
                title="LDAP Sync Complete",
                message=f"Sync completed: {added_contacts} contacts added, {updated_contacts} updated{', ' + str(len(conflicts)) + ' conflicts found' if conflicts else ''}",
                unread=True
            )
            db.session.add(notification)
            db.session.commit()

            self.logger.info(f"Sync completed successfully. Total entries: {total_entries}, Added: {added_contacts}, Updated: {updated_contacts}")
            return conflicts
            
        except Exception as e:
            self.logger.error(f"Sync failed: {str(e)}")
            db.session.rollback()
            
            # Create error notification
            notification = Notification(
                title="LDAP Sync Failed",
                message=f"Error during sync: {str(e)}",
                unread=True
            )
            db.session.add(notification)
            db.session.commit()
            
            raise
        finally:
            conn.unbind()
            self.logger.info("LDAP connection closed")

    def import_single_contact(self, dn, force=False):
        """Import a single contact by DN. Set force=True to override existing data"""
        conn = self.connect()
        try:
            result = conn.search(
                search_base=dn,
                search_filter='(objectClass=*)',
                search_scope='BASE',
                attributes=['uid', 'cn', 'sn', 'givenName', 'mail', 
                           'telephoneNumber', 'ou', 'eduPersonAffiliation']
            )
            
            if not result or len(conn.entries) == 0:
                raise Exception("Contact not found")
                
            entry = conn.entries[0]
            entry_data = entry.entry_attributes_as_dict
            uid = self._get_list_value(entry_data.get('uid', []))
            
            # Check for existing contact with this UID
            existing_contact = Contact.query.filter_by(uid=uid).first()
            
            if existing_contact and not force:
                if existing_contact.source == 'manual':
                    # Raise our custom conflict exception
                    raise self.UIDConflict(uid, existing_contact.id)
            
            # Rest of the import logic remains the same
            if not existing_contact:
                contact = Contact(ldap_dn=dn)
                db.session.add(contact)
            else:
                contact = existing_contact
            
            # Update contact attributes
            contact.uid = uid
            contact.first_name = self._get_list_value(entry_data.get('givenName', []))
            contact.last_name = self._get_list_value(entry_data.get('sn', []))
            contact.email = self._get_list_value(entry_data.get('mail', []))
            contact.phone = self._get_list_value(entry_data.get('telephoneNumber', []))
            contact.department = self._get_list_value(entry_data.get('ou', []))
            contact.title = self._get_list_value(entry_data.get('eduPersonAffiliation', []))
            contact.last_sync = datetime.utcnow()
            contact.is_active = True
            contact.source = 'ldap'  # Mark as LDAP source
            
            # NEW: Try to enrich contact with CUCM data
            self._enrich_with_cucm_data(contact)
            
            db.session.commit()
            return True
            
        except self.UIDConflict:
            # Re-raise UIDConflict to be handled by the caller
            raise
        except Exception as e:
            db.session.rollback()
            raise e
        finally:
            conn.unbind()

    def merge_contact(self, contact, dn):
        """Update empty fields of an existing contact with LDAP data"""
        conn = self.connect()
        try:
            result = conn.search(
                search_base=dn,
                search_filter='(objectClass=*)',
                search_scope='BASE',
                attributes=['uid', 'cn', 'sn', 'givenName', 'mail', 
                           'telephoneNumber', 'ou', 'eduPersonAffiliation']
            )
            
            if not result or len(conn.entries) == 0:
                raise Exception("Contact not found")
                
            entry = conn.entries[0]
            entry_data = entry.entry_attributes_as_dict
            
            # Only update fields that are empty or None
            if not contact.first_name:
                contact.first_name = self._get_list_value(entry_data.get('givenName', []))
            if not contact.last_name:
                contact.last_name = self._get_list_value(entry_data.get('sn', []))
            if not contact.email:
                contact.email = self._get_list_value(entry_data.get('mail', []))
            if not contact.phone:
                contact.phone = self._get_list_value(entry_data.get('telephoneNumber', []))
            if not contact.department:
                contact.department = self._get_list_value(entry_data.get('ou', []))
            if not contact.title:
                contact.title = self._get_list_value(entry_data.get('eduPersonAffiliation', []))
            
            contact.last_sync = datetime.utcnow()
            return True
            
        finally:
            conn.unbind()

    def search_user(self, search_term, exclude_students=None, exclude_alumni=None):
        """Search for users in LDAP with flexible matching"""
        conn = self.connect()
        try:
            # Build base search filter
            base_search = f"(|(uid=*{search_term}*)" \
                       f"(cn=*{search_term}*)" \
                       f"(mail=*{search_term}*)" \
                       f"(sn=*{search_term}*)" \
                       f"(givenName=*{search_term}*)" \
                       f")"
            
            # Add exclusion filters if requested
            exclusions = []
            if exclude_students:
                exclusions.append("(!(eduPersonAffiliation=student))")
            if exclude_alumni:
                exclusions.append("(!(eduPersonAffiliation=alum))")
            
            # Combine filters
            if exclusions:
                search_filter = f"(&{base_search}{''.join(exclusions)})"
            else:
                search_filter = base_search
            
            self.logger.info(f"Searching with filter: {search_filter}")
            
            # Perform search with case-insensitive matching
            # Update search to use paging for user searches too
            entries_list = []
            cookie = None
            
            while True:
                result = conn.search(
                    search_base=self.base_dn,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=['uid', 'cn', 'sn', 'givenName', 'mail'],
                    paged_size=self.page_size,
                    paged_cookie=cookie
                )
                
                if not result:
                    self.logger.warning(f"No results found in this page: {conn.result}")
                    break
                
                entries_list.extend(conn.entries)
                
                cookie = conn.result.get('controls', {}).get('1.2.840.113556.1.4.319', {}).get('value', {}).get('cookie')
                if not cookie:
                    # No more pages
                    break
            
            if len(entries_list) == 0:
                self.logger.warning("No results found")
                return []
            
            # Process and return results
            contacts = []
            for entry in entries_list:
                contact = {
                    'dn': entry.entry_dn,
                    'name': entry.cn.value if hasattr(entry, 'cn') else '',
                    'uid': entry.uid.value if hasattr(entry, 'uid') else '',
                    'email': entry.mail.value if hasattr(entry, 'mail') else '',
                }
                contacts.append(contact)
                self.logger.debug(f"Found contact: {contact}")
            
            return contacts
            
        except Exception as e:
            self.logger.error(f"LDAP search failed: {str(e)}")
            raise
        finally:
            conn.unbind()

    def _get_list_value(self, value_list):
        """Safely get first value from LDAP attribute list"""
        return str(value_list[0]) if value_list else ''

    def _get_attr_value(self, attrs, attr_name):
        """Safely get attribute value from LDAP entry"""
        value = attrs.get(attr_name, [''])[0]
        return str(value) if value else ''

    def _get_attribute(self, entry, attr_name):
        """Safely get LDAP attribute value"""
        try:
            return entry[attr_name].value if hasattr(entry, attr_name) else ''
        except (AttributeError, KeyError):
            self.logger.warning(f"Attribute {attr_name} not found for {entry.entry_dn}")
            return ''

    def _enrich_with_cucm_data(self, contact):
        """Enrich contact with data from CUCM"""
        if not contact.uid:
            return
            
        try:
            # Initialize CUCM service
            cucm = CUCMService()
            
            # 1. Try to fetch authorization code (PIN)
            if not contact.pin:
                self.logger.info(f"Fetching PIN for {contact.uid} from CUCM")
                pin = cucm.fetchAuthCode(contact.uid)
                if pin:
                    self.logger.info(f"Found PIN for {contact.uid}")
                    contact.pin = pin
            
            # 2. Try to find a phone assigned to this user using their UID
            # This would require adding a method to CUCMService to search for phones by owner
            if not contact.mac_address or not contact.phone_model:
                self.logger.info(f"Searching for phone details for {contact.uid} in CUCM")
                phone_details = cucm.find_phone_by_owner(contact.uid)
                if phone_details:
                    self.logger.info(f"Found phone for {contact.uid}: {phone_details.get('name', 'Unknown')}")
                    
                    # Update MAC address if found
                    if 'mac' in phone_details and not contact.mac_address:
                        mac = phone_details['mac']
                        # Format MAC address with colons if needed
                        if len(mac) == 12:
                            mac = ':'.join([mac[i:i+2] for i in range(0, 12, 2)])
                        contact.mac_address = mac
                    
                    # Update phone model if found
                    if 'model' in phone_details and not contact.phone_model:
                        contact.phone_model = phone_details['model']
                    
        except Exception as e:
            self.logger.error(f"Error enriching contact with CUCM data: {str(e)}")
            # Don't let CUCM errors prevent LDAP import
            # We'll just continue without the additional data
