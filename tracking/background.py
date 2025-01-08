import time
import requests

# Define the URLs for the GET and POST endpoints
GET_URL = 'http://localhost:8000/api/getAlerts'
SET_URL = 'http://localhost:8000/api/setAlerts'

# Infinite loop that runs every second
while True:
    try:
        # Send a GET request to fetch the alert data
        response = requests.get(GET_URL)            
        print(f"Status code: {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {e}")
    
    # Sleep for 1 second before the next iteration
    time.sleep(1)
