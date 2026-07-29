import requests
import time
from datetime import datetime
from django.utils import timezone
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

# for registration what do i need? url, payload, 
# try:
#     register_payload = {
#     'host_name': 'node-test--3',
#     'mac_address': '00:11:22:33:76',
#     'os_version': 'Miko 24.04',
#     'password': 'K3epYour$erver$ecure!',
#     'status':'ONLINE' 
#     }
#     print(register_payload)

#     r_response = requests.post(REGISTER_URL, json = register_payload)
#     print(r_response.status_code)
#     print(r_response.text)
# except requests.exceptions.ConnectionError:
#     'log the network error'
#     print("Error: Could not connect to the server. Is your Django app running?")
    
#     if r_response.status_code == 201:
try:
    # r_response_data = r_response.json() # convert to python dict

    login_data = {
    'host_name':'node-test--3',
    'password':'K3epYour$erver$ecure!'
    }
    login_response = requests.post(LOGIN_URL, json = login_data)

    print("--- Client Login Debugging ---")
    print(login_response.status_code)
    print(f"Target URL: {login_response.request.url}")
    print(f"Sent Headers: {login_response.request.headers}")
    print(f"Sent Payload: {login_response.request.body}")
    print(f"Received Payload: {login_response.text}")
except requests.exceptions.ConnectionError:
    print("Error: Could not connect to the server. Is your Django app running?")


if login_response.status_code == 200:
    r_response_data = login_response.json()
    token = r_response_data.get('token', '')
    headers = {
                "Authorization": f"Token {token}",
                "Content-Type": "application/json"
        }
    while True:
        try:
            now = datetime.now()
            time_string = now.isoformat()
            metrics = {
                    "node_server":4,
                    "server":'Debian',
                    "cpu": 75,
                    "time_stamp":time_string     
                }
            response = requests.post(METRICS_URL, json = metrics, headers = headers)
            
            print("--- Client Metrics Debugging ---")
            print(response.status_code)
            print(f"Target URL: {response.request.url}")
            print(f"Sent Headers: {response.request.headers}")
            print(f"Sent Payload: {response.request.body}")
            print(f"Received Payload: {response.text}")

            time.sleep(5)
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to the server. Is your Django app running?")


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