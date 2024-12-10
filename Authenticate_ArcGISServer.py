
'''
This script is for acquiring credentials and/or generating a token for an ArcGIS Server. Requires admin credentials to successfully run. 
Use with conjunction in other scripts. 

Requirements: Python 3+, Admin account for Arcgis Server, AGOL or Portal depending on how you run it
'''
import getpass
import requests

#get credentials
def get_creds():
    print(f"\nEnter GIS Admin Credentials:")
    username = getpass.getpass(prompt="User account: ")  
    password = getpass.getpass(prompt='Account password: ')
    return username, password

#generate token
def get_token(site, token_url):
    try:
        username, password = get_creds()

        payload = {
            'f': 'json',
            'username': username,
            'password': password,
            'client': "requestip"
        }
        response = requests.post(token_url, data=payload)
        
        if response.status_code != 200:
                print(f"Error: Unable to retrieve token. HTTP Status code: {response.status_code}")
                return None

        token = response.json().get('token')

        if not token:
            print("Error: Token not found in the response.")
            return None

        return username, password, token

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
