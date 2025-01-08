# NOT WORKING

import threading
import time
from .models import Truck  
from traccar_models import TcEvents  
import requests


def get_unique_id(device_id):
    """
    Fetch the uniqueId for a given deviceId from the Traccar API.
    """
    try:
        response = requests.get(f"localhost:8000/devices/getUniqueId?id={device_id}")
        response.raise_for_status()
        return response.json().get("uniqueId")  # Adjust based on the actual API response
    except requests.exceptions.RequestException as e:
        print(f"Error fetching uniqueId for deviceId {device_id}: {e}")
        return None

def monitor_geofence_events():
    """
    Monitor the tc_events table in the Traccar database for geofenceEnter events
    and update the Truck status in the default database.
    """
    while True:
        try:
            # Fetch unprocessed geofenceEnter events
            geofence_events = TcEvent.objects.using("traccar").filter(type="geofenceEnter", processed=False)
            print("THREAD RUNNING")
            for event in geofence_events:
                device_id = event.deviceid  # Replace with the actual field for deviceId in TcEvent

                # Get uniqueId for the deviceId from the Traccar API
                unique_id = get_unique_id(device_id)
                if not unique_id:
                    print(f"Failed to fetch uniqueId for deviceId {device_id}")
                    continue

                # Update the Truck table in your database
                try:
                    truck = Truck.objects.get(truck_id=unique_id)
                    truck.status = "reached warehouse"
                    truck.save()
                    print(f"Updated Truck {unique_id} status to 'reached warehouse'")
                except Truck.DoesNotExist:
                    print(f"Truck with uniqueId {unique_id} not found in the Truck table.")

                # Mark the event as processed
                event.processed = True
                event.save(using="traccar")

        except Exception as e:
            print(f"Error monitoring geofence events: {e}")

        time.sleep(60)  # Sleep for 60 seconds before checking again


class EventMonitorThread(threading.Thread):
    def run(self):
        print("Starting Geofence Event Monitor Thread...")
        monitor_geofence_events()
