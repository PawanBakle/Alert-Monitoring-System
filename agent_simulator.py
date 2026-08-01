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
        self.server_name = server_name
        self.interval = interval
        self.server_id = None
        self.password = 'K3epYour$erver$ecure!'
        self.token = None
        self.seq_id = None
        self.logger = logging.getLogger(__name__)
        # during registration
        self.mac_address = None
        self.os_version = None
        self.session = None
        

        if self.seq_id == None:
            self.seq_id = 1
        # login

        
        # metrics
        
        self.state = None
        self.cpu = None
        self.memory = None
        self.disk = None
        self.time_stamp = None


        # urls & constants
        self.BASE_URL = 'http://127.0.0.1:8000'
        self.REGISTER_URL = f'{self.BASE_URL}/api/register/'
        self.LOGIN_URL = f'{self.BASE_URL}/api/login/'
        self.METRICS_URL = f'{self.BASE_URL}/api/metrics/'
        self.TIMEOUT_SECONDS = 5
        self.RETRY_TOTAL = 3
        self.BACKOFF_FACTOR = 1  # Sleeps: 0s, 1s, 2s...
        self.METRICS_INTERVAL = 5



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

        server = self.assign_server_data("12.31","12:31:13:195")
        if server:
            payload = {
            'node_name': self.server_name,
            'mac_address': self.mac_address,
            'os_version': self.os_version,
            'password': self.password
        }
        try:
            response = self.session.post(f'{self.REGISTER_URL}', json=payload, timeout=self.TIMEOUT_SECONDS)
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
        login_payload = {'node_name': self.server_name, 'password': self.password}
        try:
            response = self.session.post(f'{self.LOGIN_URL}', json=login_payload, timeout=self.TIMEOUT_SECONDS)
            response.raise_for_status()
            self.server_id = response.json().get('id')
            self.token = response.json().get('token')
            print(response.text)
            if self.token:
                self.logger.info("Login successful.")
                return self.token
            self.logger.error("No token received in login response.")
            return None
        except (HTTPError, ConnectionError, Timeout) as e:
            self.logger.error(f"Login failed: {e}")
            return None


    # what do i need for metrics - token, seq-id cpu, memory, disk, time-stamp, state

    def generate_metrics(self):
       # seq-id cpu, memory, disk, time-stamp, state
       self.cpu = random.randint(1, 10)
       self.memory = random.randint(25,70)
       self.disk = random.randint(1,100)
       return {"cpu":self.cpu, "memory":self.memory,"disk":self.disk}

    def send_metrics(self):
        metrics = self.generate_metrics()
        metrics["server_id"] = self.server_id
        self.seq_id += 1
        data = {"server_id":self.server_id,"seq_id":self.seq_id,"time_stamp": datetime.now(timezone.utc).isoformat(),"metrics":metrics}
        headers = {"Authorization": f"Token {self.token}", "Content-Type": "application/json"}
        try:
            response = self.session.post(f'{self.METRICS_URL}', json=data, headers=headers, timeout=self.TIMEOUT_SECONDS)
            response.raise_for_status()
            self.logger.debug(f"Metrics sent successfully (Status: {response.status_code})")
            return True
        except HTTPError as e:
            if e.response.status_code == 401:
                self.logger.error("Authentication failed. Token may be expired.")
                return False # Stop loop, need re-login
            self.logger.error(f"Metrics rejected (HTTP {e.response.status_code}): {e.response.text}")
            return True # Continue loop, might be temporary data issue
        except (ConnectionError, Timeout) as e:
            self.logger.warning(f"Network error sending metrics: {e}. Retrying next cycle...")

    def main(self):
        self.session = self.get_retry_session()
        if not self.register():
            self.logger.warning("Registration failed or node already exists. Attempting login anyway...")
        self.token = self.login_node()
        if not self.token:
            self.logger.critical("Exiting due to login failure.")
            return

        # assuming register returns serverid

        # 3. Metrics Loop
        self.logger.info(f"Starting metrics loop (interval: {self.METRICS_INTERVAL}s)...")
        while True:
            success = self.send_metrics()
            if success is False: # Explicit check if auth failed (401)
                self.logger.error("Stopping metrics loop due to authentication error.")
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
