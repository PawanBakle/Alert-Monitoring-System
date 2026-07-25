import requests

'''
    host_name = models.CharField(max_length = 12)
    mac_address = models.CharField(max_length = 15)
    os_version = models.CharField(max_length = 15)
    objects = NodeManager()
'''


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

METRICS_URL = 'http://127.0.0.1:8000/api/metrics/'
# login_data = {
#     'host_name':'node-test-10',
#     'password':'K3epYour$erver$ecure!'
# }
# url = 'http://127.0.0.1:8000/api/login/'
try:
    # response = requests.post(url, json = login_data)
    # print(response.status_code)
    # response_json = response.json()
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
    token = '72342f67dae693bf4731ca63f16166cb5b3a5c95'
    headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
    }
    metrics = {
            "server":'Debian',
            "cpu": 22        
        }
    response = requests.post(METRICS_URL, json = metrics, headers = headers)
    print("--- Client Request Debugging ---")
    print(response.status_code)
    print(f"Target URL: {response.request.url}")
    print(f"Sent Headers: {response.request.headers}")
    print(f"Sent Payload: {response.request.body}")
    print(f"Sent Payload: {response.text}")
except requests.exceptions.ConnectionError:
    print("Error: Could not connect to the server. Is your Django app running?")
