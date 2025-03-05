from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport
from zeep.exceptions import Fault
from zeep.plugins import HistoryPlugin
from requests import Session
from requests.auth import HTTPBasicAuth
import urllib3
from models import Settings
import logging
import os

class CUCMService:
    def __init__(self):
        self.logger = logging.getLogger('CUCMService')
        self._client = None
        self._history = HistoryPlugin()  # For debugging SOAP messages
        self._session = None
        self._wsdl = os.path.join(os.path.dirname(__file__), 'schema', 'AXLAPI.wsdl')
        # Change cache directory to instance folder
        self._cache_dir = os.path.join(os.path.dirname(__file__), 'instance')
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

    def _get_client(self):
        """Initialize SOAP client with zeep"""
        if self._client is None:
            settings = {
                'host': Settings.get_value('CUCM_HOST'),
                'username': Settings.get_value('CUCM_USERNAME'),
                'password': Settings.get_value('CUCM_PASSWORD'),
                'verify': Settings.get_value('CUCM_VERIFY_CERT', 'False').lower() == 'true'
            }

            if not all([settings['host'], settings['username'], settings['password']]):
                raise ValueError("CUCM settings not configured properly")

            # Create session with basic auth
            session = Session()
            session.auth = HTTPBasicAuth(settings['username'], settings['password'])
            session.verify = settings['verify']
            session.timeout = (30, 30)  # (connect timeout, read timeout)

            if not settings['verify']:
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            try:
                # Setup zeep client with caching and history
                transport = Transport(
                    session=session,
                    cache=SqliteCache(path=os.path.join(self._cache_dir, 'cucm_zeep.db')),
                    timeout=30,
                    operation_timeout=30
                )

                # Create zeep client using WSDL
                self._client = Client(
                    wsdl=self._wsdl,
                    transport=transport,
                    plugins=[self._history]
                )

                # Create AXL service
                self._service = self._client.create_service(
                    "{http://www.cisco.com/AXLAPIService/}AXLAPIBinding",
                    f"https://{settings['host']}:8443/axl/"
                )

                # Test authentication with a simple query
                try:
                    self._service.listPhone(
                        {'name': 'SEP%'},
                        {'name': ''},
                        1
                    )
                except Fault as e:
                    if 'Authentication failed' in str(e) or '401' in str(e):
                        raise ValueError("Authentication failed - check username and password")
                    raise
                except Exception as e:
                    raise ValueError(f"Connection failed: {str(e)}")

            except Exception as e:
                self.logger.error(f"CUCM connection error: {str(e)}")
                raise ValueError(f"Failed to connect to CUCM: {str(e)}")

        return self._service  # Return the service instead of the client

    def get_phone_by_mac(self, mac_address):
        """Get phone details from CUCM by MAC address"""
        try:
            service = self._get_client()  # Get the AXL service
            mac = mac_address.replace(':', '').upper()
            
            try:
                # Make the service call
                response = service.getPhone(name=f"SEP{mac}")
                
                # SOAP responses in zeep can have different structures depending on the CUCM version
                # Let's handle all possible structures
                if response:
                    if 'return' in response:
                        # Dict-like response
                        phone_data = response['return']
                    elif hasattr(response, 'return_'):
                        # Object-like response - use return_ attribute instead of return
                        phone_data = response.return_
                    else:
                        # Direct response
                        phone_data = response
                    
                    # Now we need to handle the phone_data which might be an object or dict
                    return {
                        'name': self._get_value(phone_data, 'name', 'Unknown'),
                        'description': self._get_value(phone_data, 'description', ''),
                        'model': self._get_value(phone_data, 'model', ''),
                        'product': self._get_value(phone_data, 'product', ''),
                        'class': self._get_value(phone_data, 'class', ''),
                        'protocol': self._get_value(phone_data, 'protocol', ''),
                        'status': 'Registered' if self._get_value(phone_data, 'registered', False) else 'Not Registered'
                    }
                return None
                
            except Fault as e:
                if 'was not found' in str(e):
                    self.logger.warning(f"Phone with MAC {mac_address} not found")
                    return None
                raise

        except Fault as e:
            self.logger.error(f"CUCM Fault: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting phone: {str(e)}")
            return None

    def _get_value(self, obj, attr, default=None):
        """Helper method to get a value from an object or dictionary safely"""
        try:
            # Try dictionary access first
            if isinstance(obj, dict) and attr in obj:
                return obj[attr]
            
            # Then try object attribute access
            if hasattr(obj, attr):
                return getattr(obj, attr)
            
            # Finally try direct dictionary access
            return obj.get(attr, default)
        except:
            return default

    def search_phones(self, search_pattern="", limit=100):
        """Search for phones in CUCM"""
        try:
            service = self._get_client()  # Get the AXL service
            response = service.listPhone(
                {'name': '%' + search_pattern + '%'},
                {
                    'name': '',
                    'description': '',
                    'model': '',
                    'product': '',
                    'class': '',
                    'protocol': ''
                },
                limit
            )

            if response:
                return [{
                    'name': phone['name'],
                    'description': phone.get('description', ''),
                    'model': phone.get('model', ''),
                    'mac': phone['name'][3:] if phone['name'].startswith('SEP') else ''
                } for phone in response['return']['phone']]
            return []

        except Fault as e:
            self.logger.error(f"CUCM Fault: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Error searching phones: {str(e)}")
            return []

    def get_registration_status(self, mac_address):
        """Get phone registration status"""
        try:
            client = self._get_client()
            mac = mac_address.replace(':', '').upper()
            
            response = client.service.getPhoneRegistrationStatus(
                name=f"SEP{mac}"
            )
            
            if response:
                return {
                    'status': response.get('status', 'Unknown'),
                    'ip_address': response.get('ipAddress', ''),
                    'timestamp': response.get('timestamp', '')
                }
            return None

        except Fault as e:
            self.logger.error(f"CUCM Fault: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting registration status: {str(e)}")
            return None

    def fetchAuthCode(self, uid):
        """Fetch authorization code (FAC) for a given UID using AXL"""
        try:
            self.logger.info(f"Fetching auth code for UID: {uid}")
            
            # Get AXL service client
            service = self._get_client()
            
            # Use listFacInfo AXL API with correct field names
            try:
                response = service.listFacInfo(
                    searchCriteria={'name': uid},
                    returnedTags={'code': ''}
                )
                
                # Safely access the return value
                if response is None:
                    self.logger.info(f"No authorization code found for {uid}")
                    return None
                    
                # Check for 'return' key in response
                if 'return' not in response:
                    self.logger.info(f"Response doesn't contain 'return' key for {uid}")
                    return None
                    
                return_value = response['return']
                
                # Check if facInfo exists and has values
                if return_value is None or 'facInfo' not in return_value or not return_value['facInfo']:
                    self.logger.info(f"User {uid} doesn't have an authorization code")
                    return None
                
                fac_list = return_value['facInfo']
                
                # Make sure we have at least one item in the list
                if not fac_list or len(fac_list) == 0:
                    self.logger.info(f"Empty facInfo list for {uid}")
                    return None
                    
                # Safe way to extract the code
                first_fac = fac_list[0]
                if isinstance(first_fac, dict):
                    if 'code' not in first_fac:
                        self.logger.info(f"No 'code' field found in facInfo for {uid}")
                        return None
                    return first_fac['code']
                elif hasattr(first_fac, 'code'):
                    return first_fac.code
                else:
                    self.logger.info(f"Cannot extract code from facInfo for {uid}")
                    return None
                    
            except Fault as e:
                if 'was not found' in str(e):
                    self.logger.info(f"No authorization code found for {uid}")
                    return None
                raise
                
        except Exception as e:
            self.logger.error(f"Error fetching auth code: {str(e)}")
            # Don't raise error, just return None with a log message
            self.logger.info(f"User {uid} doesn't have an authorization code")
            return None

    def find_phone_by_owner(self, uid):
        """Find a phone assigned to a specific user by UID/username"""
        try:
            service = self._get_client()  # Get the AXL service
            
            # Direct phone search by description containing user ID
            self.logger.info(f"Searching phones with description pattern: %{uid}%")
            
            try:
                phone_resp = service.listPhone(
                    searchCriteria={'description': f'%{uid}%'},  # Search for phones with description containing UID
                    returnedTags={
                        'name': '',
                        'description': '',
                        'model': '',
                        'product': ''
                    }
                )
                
                # Check if we got a valid response
                if not phone_resp or 'return' not in phone_resp:
                    self.logger.info(f"No phones found with description containing {uid}")
                    return None
                
                return_data = phone_resp['return']
                
                if not return_data or 'phone' not in return_data or not return_data['phone']:
                    self.logger.info(f"No phones found with description containing {uid}")
                    return None
                
                phones = return_data['phone']
                
                # Ensure phones is a list we can iterate over
                if not isinstance(phones, list):
                    phones = [phones]
                
                if not phones:
                    self.logger.info(f"No phones found with description containing {uid}")
                    return None
                
                # Get the first phone that matches
                phone = phones[0]
                
                name = self._get_value(phone, 'name', '')
                
                # Extract MAC from SEP device name
                mac = ''
                if name and isinstance(name, str) and name.startswith('SEP'):
                    mac = name[3:]
                    self.logger.info(f"Found phone for {uid}: {name}")
                
                return {
                    'name': name,
                    'description': self._get_value(phone, 'description', ''),
                    'model': self._get_value(phone, 'model', ''),
                    'mac': mac
                }
                
            except Exception as e:
                self.logger.error(f"Error searching phone by description for {uid}: {str(e)}")
                return None

        except Exception as e:
            self.logger.error(f"Error finding phone by owner: {str(e)}")
            return None

