import os
import time
import logging
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError, RequestException
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
'''
    host_name = models.CharField(max_length = 12)
    mac_address = models.CharField(max_length = 15)
    os_version = models.CharField(max_length = 15)
    objects = NodeManager()
'''


# need a base URL

BASE_URL = 'http://127.0.0.1:8000'
REGISTER_URL = f'{BASE_URL}/api/register/'
LOGIN_URL = f'{BASE_URL}/api/login/'
METRICS_URL = f'{BASE_URL}/api/metrics/'
HOST_NAME = 'node-test-10'
PASSWORD = 'K3epYour$erver$ecure!'
MAC_ADDRESS = '00:11:22:33:44'
OS_VERSION = 'Ubuntu 24.04'


# BASE_URL = os.getenv('METRICS_BASE_URL', 'http://127.0.0.1:8000')
# HOST_NAME = os.getenv('NODE_HOST_NAME', 'node-test-10')
# PASSWORD = os.getenv('NODE_PASSWORD', 'K3epYour$erver$ecure!')
# MAC_ADDRESS = os.getenv('NODE_MAC', '00:11:22:33:44:55')
# OS_VERSION = os.getenv('NODE_OS', 'Ubuntu 24.04')

# Constants
TIMEOUT_SECONDS = 5
RETRY_TOTAL = 3
BACKOFF_FACTOR = 1  # Sleeps: 0s, 1s, 2s...
METRICS_INTERVAL = 5
seq_id = 0
# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_retry_session():
    """Creates a session with automatic retry logic for transient errors."""
    session = requests.Session()
    retry = Retry(
        total=RETRY_TOTAL,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["POST", "GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def register_node(session):
    """Registers the node and returns True if successful."""
    payload = {
        'host_name': HOST_NAME,
        'mac_address': MAC_ADDRESS,
        'os_version': OS_VERSION,
        'password': PASSWORD
    }
    try:
        response = session.post(f'{REGISTER_URL}', json=payload, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        logger.info("Node registered successfully.")
        return True
    except HTTPError as e:
        logger.error(f"Registration failed (HTTP {e.response.status_code}): {e.response.text}")
        return False
    except (ConnectionError, Timeout) as e:
        logger.error(f"Registration network error: {e}")
        return False

def login_node(session):
    """Authenticates and returns the token, or None if failed."""
    payload = {'host_name': HOST_NAME, 'password': PASSWORD}
    try:
        response = session.post(f'{LOGIN_URL}', json=payload, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        token = response.json().get('token')
        print(response.text)
        if token:
            logger.info("Login successful.")
            return token
        logger.error("No token received in login response.")
        return None
    except (HTTPError, ConnectionError, Timeout) as e:
        logger.error(f"Login failed: {e}")
        return None

"""
    seq_id = models.IntegerField(unique = False) # it should be unique but for testing have used incremental
    node_server = models.ForeignKey('Node', on_delete = models.PROTECT)
    server = models.CharField(max_length = 12)
    cpu = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    time_stamp = models.DateTimeField(auto_now = True)
"""
def send_metrics(session, token):
    """Sends a single metric payload."""
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    global seq_id
    if seq_id == 0:
        metrics = {"seq_id":0,"node_server":1,"server": 'Red Hat', "cpu": 65}
        seq_id += 1
    else:
        metrics = {"seq_id":seq_id,"node_server":1,"server": 'Red Hat', "cpu": 65}
        seq_id += 1
    try:
        response = session.post(f'{METRICS_URL}', json=metrics, headers=headers, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        logger.debug(f"Metrics sent successfully (Status: {response.status_code})")
        return True
    except HTTPError as e:
        if e.response.status_code == 401:
            logger.error("Authentication failed. Token may be expired.")
            return False # Stop loop, need re-login
        logger.error(f"Metrics rejected (HTTP {e.response.status_code}): {e.response.text}")
        return True # Continue loop, might be temporary data issue
    except (ConnectionError, Timeout) as e:
        logger.warning(f"Network error sending metrics: {e}. Retrying next cycle...")
        return True # Continue loop

def main():
    session = get_retry_session()
    
    # 1. Register Ignore failure if already exists
    if not register_node(session):
        logger.warning("Registration failed or node already exists. Attempting login anyway...")

    # 2. Login
    token = login_node(session)
    if not token:
        logger.critical("Exiting due to login failure.")
        return

    # 3. Metrics Loop
    logger.info(f"Starting metrics loop (interval: {METRICS_INTERVAL}s)...")
    while True:
        if not send_metrics(session, token):
            logger.error("Stopping metrics loop due to authentication error.")
            break
        time.sleep(METRICS_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Script stopped by user.")   
    # response = requests.post(url, json = login_data)
    # print(response.status_code)
    # response_json = response.json() convert to object to access DATA 
    # token = response_json.get("token")
    # print(f'token post login {token}')
    # print(f'Response data {response.text}')
    # # print(f'Reponse Body: {response.text}')
    #     # Print what your client script actually sent
    # print("--- Client Request Debugging ---")
    # print(f"Target URL: {response.request.url}")
    # print(f"Sent Headers: {response.request.headers}")
    # print(f"Sent Payload: {response.request.body}")
    # response_json = response.json()
    
    # token = response_json.get("token")
    # print(f'token {token}')



# register_data = {
#     'host_name': 'node-test-10',
#     'mac_address': '00:11:22:33:12',
#     'os_version': 'Ubuntu 24.04',
#     'password': 'K3epYour$erver$ecure!' 
# }
# url = 'http://127.0.0.1:8000/api/register/'
# response = requests.post(url, json = register_data)
# print(response.status_code)
# print(f"Response Body: {response.text}") 

# METRICS_URL = 'http://127.0.0.1:8000/api/metrics/'
# # login_data = {
# #     'host_name':'node-test-10',
# #     'password':'K3epYour$erver$ecure!'
# # }
# # url = 'http://127.0.0.1:8000/api/login/'
# try:

#     token = '72342f67dae693bf4731ca63f16166cb5b3a5c95'
#     headers = {
#             "Authorization": f"Token {token}",
#             "Content-Type": "application/json"
#     }
#     metrics = {
#             "server":'Red Hat',
#             "cpu": 65       
#         }
#     response = requests.post(METRICS_URL, json = metrics, headers = headers)
#     print("--- Client Request Debugging ---")
#     print(response.status_code)
#     print(f"Target URL: {response.request.url}")
#     print(f"Sent Headers: {response.request.headers}")
#     print(f"Sent Payload: {response.request.body}")
#     print(f"Received Payload: {response.text}")
# except requests.exceptions.ConnectionError:
#     print("Error: Could not connect to the server. Is your Django app running?")


# register 
# login 
# every 5 seconds - send /metrics