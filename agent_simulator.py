import argparse
import os
import random
import time
import logging
import requests
from requests.exceptions import ConnectionError, Timeout, HTTPError, RequestException
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from datetime import datetime, timezone


""" 
STATES - 
    server-name, 
    password,
    server-id (post registration),
    token (post login),
    mac-address, 
    os-version,

    Metrics - 
    cpu, 
    memory,
    disk,
    time-stamp
"""
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AgentSimulator:
    
    
    def __init__(self, server_name, interval,*kwargs):
        self.server_name = server_name or os.getenv("SERVER_NAME", "web_02")
        # self.interval = interval
        self.server_id = None
        self.password = os.getenv("SERVER_PASSWORD")
        if not self.password:
            raise ValueError("CRITICAL: SERVER_PASSWORD environment variable is missing!")
        self.access = None
        self.refresh = None
        self.seq_id = None
        self.logger = logging.getLogger(__name__)
        # during registration
        self.mac_address = None
        self.os_version = None
        self.session = None
        self.seq_id = 0
        
        # metrics
        
        self.cpu = None
        self.memory = None
        self.disk = None
        self.time_stamp = None
        self.SPIKE_PROBABILITY = 0.20

        # urls & constants
        self.BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
        self.REGISTER_URL = f'{self.BASE_URL}/api/register/'
        self.LOGIN_URL = f'{self.BASE_URL}/api/login/'
        self.METRICS_URL = f'{self.BASE_URL}/api/metrics/'
        self.REFRESH_TOKEN = f'{self.BASE_URL}/api/token/refresh/'
        self.TIMEOUT_SECONDS = 5
        self.RETRY_TOTAL = 3
        self.BACKOFF_FACTOR = 1 
        env_interval = os.getenv("METRICS_INTERVAL")
        self.METRICS_INTERVAL = interval if interval is not None else (int(env_interval) if env_interval else 5)


    def get_retry_session(self):
        """Creates a session with automatic retry logic for transient errors."""
        self.session = requests.Session()
        retry = Retry(
            total=self.RETRY_TOTAL,
            backoff_factor=self.BACKOFF_FACTOR,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        return self.session
    # assign server data details

    def assign_server_data(self, os, mac_address):
        if os and mac_address:
            self.os_version = os
            self.mac_address = mac_address
            return True
        else:
            return False
    # what do i need for registration?  - server name, os version, mac address, 
    def register(self):
        mac_address = ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)])
        server = self.assign_server_data("12.31",mac_address)
        if server:
            payload = {
            'node_name': self.server_name,
            'mac_address': self.mac_address,
            'os_version': self.os_version,
            'password': self.password
        }
        try:
            response = self.session.post(
                f'{self.REGISTER_URL}', 
                json=payload, 
                timeout=self.TIMEOUT_SECONDS
            )
            response.raise_for_status()

            self.logger.info("Node registered successfully.")
            
            return True
        except HTTPError as e:
            self.logger.error(f"Registration failed (HTTP {e.response.status_code}): {e.response.text}")
            return False
        except (ConnectionError, Timeout) as e:
            self.logger.error(f"Registration network error: {e}")
            return False


    # what do i need for login? - server id, password
    def login_node(self):
        #Authenticates and returns the token, or None if failed
        print(self.server_name, self.password)
        login_payload = {
            'node_name': self.server_name, 
            'password': self.password
            }
        try:
            response = self.session.post(
                f'{self.LOGIN_URL}', 
                json=login_payload, 
                timeout=self.TIMEOUT_SECONDS
            )
            response.raise_for_status()
            self.server_id = response.json().get('id')
            self.access = response.json().get('access')
            self.refresh = response.json().get('refresh')
            self.seq_id = response.json().get('last_sent_seq_id')
            
            print(response.text)
            if self.access:
                self.logger.info("Login successful.")
                return self.access
            self.logger.error("No token received in login response.")
            return None
        
        except HTTPError as e:
            if e.response.status_code == 401:
                
                self.logger.error(f"Login failed: {e}")
                return None
        except (ConnectionError, Timeout) as e:
            self.logger.warning(f"Network error sending metrics: {e}. Retrying next cycle...")
            return False
    def handle_expired_login(self):
        payload = {'refresh':self.refresh}
        try:
            response = self.session.post(
                f'{self.REFRESH_TOKEN}', 
                json=payload, 
                timeout=self.TIMEOUT_SECONDS
            )
            response.raise_for_status()
            self.access = response.json().get('access')
            self.refresh = response.json().get('refresh')
            self.logger.debug(f"Metrics sent successfully (Seq: {self.seq_id})")
            return True
        except HTTPError as e:
            if e.response.status_code == 401:
                self.logger.error('Refresh token expired .. need re-login')
                return False
            self.logger.error(f"Refresh request failed: {e.response.status_code}")
            return False
        except (ConnectionError, Timeout) as e:
            self.logger.warning(f"Network error sending metrics: {e}. Retrying next cycle...")
            return False
 # what do i need for metrics - token, seq-id cpu, memory, disk, time-stamp, state

    def generate_metrics(self):
       # seq-id cpu, memory, disk, time-stamp, state
       self.is_spike = random.random() < self.SPIKE_PROBABILITY
    #    self.cpu = random.randint(1, 10)
       self.memory = random.randint(25,70)
       self.disk = random.randint(1,100)
       if self.is_spike:
        self.cpu = random.randint(85, 99)  # High CPU to trigger alerts
        print("Simulating high CPU spike!")
       else:
        self.cpu = random.randint(5, 40)
       
       return {
        "cpu":self.cpu, 
        "memory":self.memory,
        "disk":self.disk,
        }

    def send_metrics(self):
            max_retries = 2
            attempt = 0

            while attempt < max_retries:
                attempt += 1
                metrics = self.generate_metrics()
                self.seq_id += 1
                
                data = {
                    "node_server": self.server_id,
                    "seq_id": self.seq_id,
                    "metrics": metrics
                }
                headers = {
                    "Authorization": f"Bearer {self.access}", 
                    "Content-Type": "application/json"
                }
                
                try:
                    response = self.session.post(
                        f'{self.METRICS_URL}',
                        json=data, 
                        headers=headers, 
                        timeout=self.TIMEOUT_SECONDS
                    )

                    print(f'last sent metric seq-id {self.seq_id}')
                    response.raise_for_status()
                    self.logger.debug(f"Metrics sent successfully (Status: {response.status_code})")
                    return True
                    
                except HTTPError as e:
                    if e.response.status_code == 401:
                        self.logger.error("Authentication failed. Token may be expired.")
                        if attempt < max_retries and self.handle_expired_login():
                            self.logger.info("Retrying metric transmission with fresh token...")
                            continue  # loop back to try posting metrics again safely
                        else:
                            self.logger.error("Token refresh failed or maximum retry limit reached.")
                            return False

                    self.logger.error(f"Metrics rejected (HTTP {e.response.status_code}): {e.response.text}")
                    return True 
                except Exception as e:
                    self.logger.error(f"Network or connection error: {e}")
                    return False
            
            return False

    def main(self):
        self.session = self.get_retry_session()
        if not self.register():
            self.logger.warning("Registration failed or node already exists. Attempting login anyway...")
        self.access = self.login_node()
        if not self.access:
            self.logger.critical("Exiting due to login failure.")
            return

        # assuming register returns serverid

        #Metrics Loop
        self.logger.info(f"Starting metrics loop (interval: {self.METRICS_INTERVAL}s)...")
        while True:
            success = self.send_metrics()
            if success is False: # Explicit check if auth failed (401)
                self.logger.error("Stopping metrics loop due to authentication or login error.")
                break
            time.sleep(self.METRICS_INTERVAL)



if __name__ == "__main__":
    #Set up the argument parser
    parser = argparse.ArgumentParser(description="Run the custom Agent Simulator.")
    

    parser.add_argument("--server-id", type=str, required=True, help="The ID of the server")
    parser.add_argument("--interval", type=int, default=5, help="Interval in seconds (default: 5)")
    

    args = parser.parse_args()
    
   
    agent = AgentSimulator(server_name=args.server_id, interval=args.interval)
    
    try:
        agent.main()
    except KeyboardInterrupt:
        agent.logger.info("Script stopped by user.")
