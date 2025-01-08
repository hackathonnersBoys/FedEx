from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
from django.urls import path
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .serializers import TruckSerializer
from .models import *
from .traccar_models import *
from django.db.models import Max
import random
import os
import math

# from dataset_handler import save_uploaded_data
# from predictor import predict_demand


TRACCAR_BASE_URL = "http://localhost:8082/api"
ROUTING_API_BASE_URL = "http://localhost:5000/route/v1/driving"

TRACCAR_AUTH_TOKEN = "RzBFAiEA9TdPYZkOoZGFxxv4ol07LdqDxc1N47-oljwMKoAMJ3MCID-fPyu0Yp77V7J0Qj0-9rVH2AFcIcJx00vpeBi5hGTPeyJ1IjoxLCJlIjoiMjAyNi0wMi0yOFQxNTozMDowMC4wMDArMDA6MDAifQ"

HEADERS = {
    "Authorization": f"Bearer {TRACCAR_AUTH_TOKEN}"
}

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        try:
            user = Users.objects.get(username=username, password=password)
            return JsonResponse({
                'success': True,
                'role': user.role,
                'warehouse_access': user.warehouse_access or '',
                'truck_access': user.truck_access or ''
            })
        except Users.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@api_view(['POST'])
def get_all_drivers(request):
    try:
        drivers = Driver.objects.all()
        driver_data = [
            {
                "truck_id": driver.truck_id,
                "name": driver.name,
                "phone_number": driver.phone_number
            }
            for driver in drivers
        ]
        return JsonResponse({"drivers": driver_data}, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['POST'])
def get_all_mms(request):
    try:
        mmss = MMS.objects.all()
        mms_data = [
            {
                "mms_id": mms.mms_id,
                "name": mms.name,
                "dedicated_phone_numbers" : mms.dedicated_phone_numbers
            }
            for mms in mmss
        ]
        return JsonResponse({"mms": mms_data}, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def get_vehicle_positions(request):
    try:
        response = requests.get(f"{TRACCAR_BASE_URL}/positions", headers=HEADERS)
        response.raise_for_status()
        return JsonResponse(response.json(), safe=False)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)

def get_vehicle_path(request):
    device_id = request.GET.get("deviceId")
    from_date = request.GET.get("from")
    to_date = request.GET.get("to")

    if not (device_id and from_date and to_date):
        return JsonResponse({"error": "Missing required parameters"}, status=400)

    try:
        url = f"{TRACCAR_BASE_URL}/positions?deviceId={device_id}&from={from_date}&to={to_date}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return JsonResponse(response.json(), safe=False)
    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)

# @csrf_exempt
# def geofences(request):
#     """Handle geofence operations"""
#     if request.method == 'GET':
#         # Get all geofences
#         try:
#             response = requests.get(f"{TRACCAR_BASE_URL}/geofences", headers=HEADERS)
#             response.raise_for_status()
#             return JsonResponse(response.json(), safe=False)
#         except requests.RequestException as e:
#             return JsonResponse({"error": str(e)}, status=500)

#     elif request.method == 'POST':
#         # Create new geofence
#         try:
#             data = json.loads(request.body)
#             response = requests.post(
#                 f"{TRACCAR_BASE_URL}/geofences",
#                 headers=HEADERS,
#                 json=data
#             )

#             Warehouse.create()

#             response.raise_for_status()
#             return JsonResponse(response.json(), status=201)
#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=500)

#     return JsonResponse({"error": "Method not allowed"}, status=405)





@csrf_exempt
def geofences(request):
    """Handle geofence operations"""
    if request.method == 'GET':
        try:
            # Get geofences from Traccar
            response = requests.get(f"{TRACCAR_BASE_URL}/geofences", headers=HEADERS)
            response.raise_for_status()
            geofences_data = response.json()

            # Enhance geofence data with warehouse info
            enhanced_geofences = []
            for geofence in geofences_data:
                try:
                    warehouse = Warehouse.objects.get(geofence_id=geofence['id'])
                    geofence['loadCapacity'] = warehouse.load
                    geofence['unloadCapacity'] = warehouse.unload
                except Warehouse.DoesNotExist:
                    geofence['loadCapacity'] = 0
                    geofence['unloadCapacity'] = 0
                enhanced_geofences.append(geofence)

            return JsonResponse(enhanced_geofences, safe=False)
        except requests.RequestException as e:
            return JsonResponse({"error": str(e)}, status=500)

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create geofence in Traccar
            traccar_data = {
                "name": data["name"],
                "description": data["description"],
                "area": data["area"]
            }
            
            # Create geofence in Traccar first
            response = requests.post(
                f"{TRACCAR_BASE_URL}/geofences",
                headers=HEADERS,
                json=traccar_data
            )
            response.raise_for_status()
            traccar_response = response.json()
            
            # Create warehouse with the Traccar geofence ID
            warehouse = Warehouse.objects.create(
                geofence_id=traccar_response['id'],
                load=data.get('loadCapacity', 0),
                unload=data.get('unloadCapacity', 0)
            )
            
            # Combine the responses
            response_data = {
                **traccar_response,
                "loadCapacity": warehouse.load,
                "unloadCapacity": warehouse.unload
            }
            
            return JsonResponse(response_data, status=201)
            
        except requests.RequestException as e:
            return JsonResponse({"error": f"Traccar API error: {str(e)}"}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@api_view(['POST'])
def get_devices(request):
    """
    Fetch devices from Traccar and append Truck details if `id` matches `Truck.actual_id`.
    Exclude devices without a matching Truck.
    """

    # retreuve ids from database
    # filter devices wrt ids

    try:
        # Fetch devices from Traccar
        response = requests.get(f"{TRACCAR_BASE_URL}/devices", headers=HEADERS)  # Using GET for Traccar
        response.raise_for_status()
        devices = response.json()  # List of devices
        print("DEVICES", devices)
        # Filter devices to only include those with a matching Truck
        filtered_devices = []
        for device in devices:
            try:
                # Match the device ID with `Truck.actual_id`
                truck = Truck.objects.get(truck_id=device['uniqueId'])

                # Directly append truck fields to the device dictionary
                device.update({
                    "truck_id": truck.truck_id,
                    "name": truck.name,
                    "truck_status": truck.truck_status,
                    "filled_capacity": truck.filled_capacity,
                    "current_volume": truck.current_volume,
                    "current_weight": truck.current_weight,
                    "max_volume": truck.max_volume,
                    "max_weight": truck.max_weight,
                    "current_location": truck.current_location,
                    "current_destination": truck.current_destination,
                    "live_status": truck.live_status,
                    "is_at_warehouse": truck.is_at_warehouse,
                    "is_on_route": truck.is_on_route,
                    "issues": truck.issues,
                })
                filtered_devices.append(device)  # Add to the filtered list
            except Exception as e:
                # Skip devices without a matching Truck
                print(e)

        return JsonResponse(filtered_devices, safe=False)

    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)

@api_view(['POST'])
def get_user_devices(request):
    """
    Fetch devices from Traccar and append Truck details if `id` matches `Truck.actual_id`.
    - If `username` is provided, fetch devices for the trucks in the user's `truck_access`.
    - If `username` is not provided, fetch all devices and filter them by matching Truck.
    """
    username = request.data.get('username')
    print(username)
    try:
        if username:
            # Fetch truck access for the user
            try:
                user = Users.objects.get(username=username)
                print()
                truck_access = set(user.truck_access.split(','))  # Assuming truck_access is a comma-separated string
            except Users.DoesNotExist:
                return JsonResponse({"error": "User not found"}, status=404)

            # Filter trucks based on truck_access
            filtered_devices = []
            for truck_id in truck_access:
                try:
                    # Fetch the matching truck and device
                    truck = Truck.objects.get(truck_id=truck_id)
                    device_response = requests.get(f"{TRACCAR_BASE_URL}/devices/{truck.actual_id}", headers=HEADERS)
                    device_response.raise_for_status()
                    device = device_response.json()

                    # Append truck fields to the device
                    device.update({
                        "truck_id": truck.truck_id,
                        "name": truck.name,
                        "truck_status": truck.truck_status,
                        "filled_capacity": truck.filled_capacity,
                        "current_volume": truck.current_volume,
                        "current_weight": truck.current_weight,
                        "max_volume": truck.max_volume,
                        "max_weight": truck.max_weight,
                        "current_location": truck.current_location,
                        "current_destination": truck.current_destination,
                        "live_status": truck.live_status,
                        "is_at_warehouse": truck.is_at_warehouse,
                        "is_on_route": truck.is_on_route,
                        "issues": truck.issues,
                    })
                    filtered_devices.append(device)

                except (Truck.DoesNotExist, requests.RequestException) as e:
                    # Skip trucks/devices that don't exist or have errors
                    continue

            return JsonResponse(filtered_devices, safe=False)

        else:
            # Fetch all devices from Traccar
            response = requests.get(f"{TRACCAR_BASE_URL}/devices", headers=HEADERS)
            response.raise_for_status()
            devices = response.json()  # List of devices

            # Filter devices to only include those with a matching Truck
            filtered_devices = []
            for device in devices:
                try:
                    # Match the device ID with `Truck.actual_id`
                    truck = Truck.objects.get(actual_id=device['id'])

                    # Directly append truck fields to the device dictionary
                    device.update({
                        "truck_id": truck.truck_id,
                        "name": truck.name,
                        "truck_status": truck.truck_status,
                        "filled_capacity": truck.filled_capacity,
                        "current_volume": truck.current_volume,
                        "current_weight": truck.current_weight,
                        "max_volume": truck.max_volume,
                        "max_weight": truck.max_weight,
                        "current_location": truck.current_location,
                        "current_destination": truck.current_destination,
                        "live_status": truck.live_status,
                        "is_at_warehouse": truck.is_at_warehouse,
                        "is_on_route": truck.is_on_route,
                        "issues": truck.issues,
                    })
                    filtered_devices.append(device)  # Add to the filtered list
                except Truck.DoesNotExist:
                    # Skip devices without a matching Truck
                    continue

            return JsonResponse(filtered_devices, safe=False)

    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def geofence_detail(request, geofence_id):
    """Handle individual geofence operations"""
    if request.method == 'GET':
        # Get specific geofence
        try:
            response = requests.get(
                f"{TRACCAR_BASE_URL}/geofences?{geofence_id}",
                headers=HEADERS
            )
            response.raise_for_status()
            return JsonResponse(response.json())
        except requests.RequestException as e:
            return JsonResponse({"error": str(e)}, status=500)

    elif request.method == 'DELETE':
        # Delete geofence
        try:
            response = requests.delete(
                f"{TRACCAR_BASE_URL}/geofences/{geofence_id}",
                headers=HEADERS
            )
            response.raise_for_status()
            return JsonResponse({}, status=204)
        except requests.RequestException as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def device_geofences(request, device_id):
    """Handle device-geofence assignments"""
    if request.method == 'GET':
        # Get geofences assigned to device
        try:
            response = requests.get(
                f"{TRACCAR_BASE_URL}/devices/{device_id}/geofences",
                headers=HEADERS
            )
            response.raise_for_status()
            return JsonResponse(response.json(), safe=False)
        except requests.RequestException as e:
            return JsonResponse({"error": str(e)}, status=500)

    elif request.method == 'POST':
        # Assign geofence to device
        try:
            data = json.loads(request.body)
            geofence_id = data.get('geofenceId')
            if not geofence_id:
                return JsonResponse({"error": "geofenceId is required"}, status=400)

            response = requests.post(
                f"{TRACCAR_BASE_URL}/permissions",
                headers=HEADERS,
                json={
                    "deviceId": device_id,
                    "geofenceId": geofence_id
                }
            )
            response.raise_for_status()
            return JsonResponse({}, status=201)
        except (json.JSONDecodeError, requests.RequestException) as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)





@csrf_exempt
def get_truck_route(request, device_id):
    """
    Fetch assigned warehouses for a truck using geofences API,
    extract coordinates, and generate a route.
    """
    try:
        # Step 1: Fetch warehouses assigned to the truck
        geofences_response = requests.get(
            f"{TRACCAR_BASE_URL}/geofences?deviceId={device_id}",
            headers=HEADERS
        )
        geofences_response.raise_for_status()
        geofences = geofences_response.json()
        if not geofences:
            return JsonResponse({"error": "No warehouses assigned to this truck."}, status=404)

        # Step 2: Extract coordinates from the geofences
        coordinates = []
        for geofence in geofences:
            area = geofence.get("area", "")
            if area.startswith("POLYGON((") and area.endswith("))"):
                points = area.replace("POLYGON((", "").replace("))", "").split(",")
                first_point = points[0].strip().split()
                longitude, latitude = map(float, first_point)
                coordinates.append(f"{longitude},{latitude}")
        
        print("COORDINATES: ")
        print(coordinates)

        if len(coordinates) < 2:
            return JsonResponse({"error": "Not enough warehouses to create a route."}, status=400)

        # Step 3: Fetch the route using the routing API
        coordinates_str = ";".join(coordinates)
        routing_url = f"{ROUTING_API_BASE_URL}/{coordinates_str}?overview=full&geometries=geojson"
        routing_response = requests.get(routing_url)
        routing_response.raise_for_status()
        
        # Step 4: Return the routing data
        return JsonResponse(routing_response.json(), safe=False)

    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)




@csrf_exempt
def manage_truck_geofence(request, device_id):
    """
    Manage geofence for a truck:
    - Check if a geofence exists for the truck.
    - If it exists, return the geofence.
    - If not, fetch warehouses, calculate the route, and create the geofence.
    """
    try:
        # Step 1: Check if the device has a geofence assigned
        geofences_response = requests.get(
            f"{TRACCAR_BASE_URL}/geofences?deviceId={device_id}",
            headers=HEADERS
        )

        geofences_response.raise_for_status()  # Ensure a 4xx/5xx error raises an exception
        geofences = geofences_response.json()

        # Filter geofences with LineString areas
        linestring_geofences = [
            geofence for geofence in geofences
            if geofence.get("area", "").startswith("LINESTRING(")
        ]

        if linestring_geofences:
            # Geofence exists, return it
            return JsonResponse({
                "message": "Geofence already exists for this truck.",
                "geofence": linestring_geofences[0]
            })

        # Step 2: Fetch warehouses for the truck
        warehouses_response = requests.get(
            f"{TRACCAR_BASE_URL}/geofences?deviceId={device_id}",
            headers=HEADERS
        )
        warehouses_response.raise_for_status()
        warehouses = warehouses_response.json()
        
        if not warehouses:
            return JsonResponse({"error": "No warehouses assigned to this truck."}, status=404)

        # Step 3: Extract coordinates from the warehouses
        # Step 3: Extract coordinates from the warehouses
        coordinates = []
        for warehouse in warehouses:
            area = warehouse.get("area", "")
            if area.startswith("POLYGON((") and area.endswith("))"):
                points = area.replace("POLYGON((", "").replace("))", "").split(",")
                first_point = points[0].strip().split()
                latitude, longitude = map(float, first_point)  # Swap the order here
                coordinates.append((longitude, latitude))  # Build (lon, lat) tuples for routing API

        if len(coordinates) < 2:
            return JsonResponse({"error": "Not enough warehouses to create a geofence."}, status=400)
        
        # Step 4: Fetch the route connecting the warehouses
        coordinates_str = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
        routing_url = f"{ROUTING_API_BASE_URL}/{coordinates_str}?overview=full&geometries=geojson"
        routing_response = requests.get(routing_url)
        routing_response.raise_for_status()
        routing_data = routing_response.json()

        if "routes" not in routing_data or not routing_data["routes"]:
            return JsonResponse({"error": "Unable to generate route."}, status=500)

        path_coordinates = routing_data["routes"][0]["geometry"]["coordinates"]

        

 
         # Step 5: Create a geofence in Traccar
        # Step 5: Create a geofence in Traccar
        if not path_coordinates or len(path_coordinates) < 2:
            return JsonResponse({"error": "Invalid path coordinates for LINESTRING."}, status=400)

        # Swap lon and lat to lat lon for Traccar's expected coordinate order
        geofence_area = f"LINESTRING({','.join(f'{lat} {lon}' for lon, lat in path_coordinates)})"
        print(f"Generated LINESTRING: {geofence_area}")

        geofence_data = {
            "name": f"Truck {device_id} Geofence",
            "area": geofence_area,
            "description": f"Geofence for truck {device_id}",
        }

        # Debug the request data
        # print("Geofence Data:", geofence_data)

        try:
            geofence_response = requests.post(
                f"{TRACCAR_BASE_URL}/geofences",
                headers=HEADERS,
                json=geofence_data
            )
            geofence_response.raise_for_status()
            geofence = geofence_response.json()

            # print("Geofence Created:", geofence)

        except requests.RequestException as e:
            print(f"Failed to create geofence: {e}")
            return JsonResponse({"error": f"Failed to create geofence: {e}"}, status=500)




        # Step 6: Assign the geofence to the truck
        permission_data = {
            "deviceId": int(device_id),
            "geofenceId": geofence["id"]
        }
        permission_response = requests.post(
            f"{TRACCAR_BASE_URL}/permissions",
            headers=HEADERS,
            json=permission_data
        )
        permission_response.raise_for_status()

        return JsonResponse({
            "message": "Geofence created and assigned to truck successfully.",
            "geofence": geofence

        }, status=201)

    except requests.RequestException as e:
        return JsonResponse({"error": str(e)}, status=500)




@api_view(['GET'])
def manage_truck_geofence2(request):
    """
    Manage geofence for a truck:
    - Check if geofences exist for the truck.
    - Return all geofences categorized as LINESTRING and POLYGON.
    - If no LINESTRING geofence exists, create one.
    """
    device_id = request.GET.get('deviceId')

    if not device_id:
        return JsonResponse({"error": "deviceId is required"}, status=400)

    try:
        # Step 1: Check if the device has geofences assigned
        geofences_response = requests.get(
            f"{TRACCAR_BASE_URL}/geofences?deviceId={device_id}",
            headers=HEADERS
        )
        geofences_response.raise_for_status()  # Raise exception for HTTP errors
        geofences = geofences_response.json()

        # Categorize geofences by type
        linestring_geofences = [
            geofence for geofence in geofences
            if geofence.get("area", "").startswith("LINESTRING(")
        ]
        polygon_geofences = [
            geofence for geofence in geofences
            if geofence.get("area", "").startswith("POLYGON((")
        ]

        response_data = {
            "linestring_geofences": linestring_geofences,
            "polygon_geofences": polygon_geofences,
        }

        # Step 2: If no LINESTRING geofence exists, create one
        if not linestring_geofences:
            # Fetch warehouses for the truck
            warehouses_response = requests.get(
                f"{TRACCAR_BASE_URL}/geofences?deviceId={device_id}",
                headers=HEADERS
            )
            warehouses_response.raise_for_status()
            warehouses = warehouses_response.json()

            if not warehouses:
                return JsonResponse({"error": "No warehouses assigned to this truck."}, status=404)

            # Extract coordinates from warehouses
            coordinates = []
            for warehouse in warehouses:
                area = warehouse.get("area", "")
                if area.startswith("POLYGON((") and area.endswith("))"):
                    points = area.replace("POLYGON((", "").replace("))", "").split(",")
                    first_point = points[0].strip().split()
                    latitude, longitude = map(float, first_point)  # Swap order for routing
                    coordinates.append((longitude, latitude))  # (lon, lat)

            if len(coordinates) < 2:
                return JsonResponse({"error": "Not enough warehouses to create a geofence."}, status=400)

            # Fetch the route connecting the warehouses
            coordinates_str = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
            routing_url = f"{ROUTING_API_BASE_URL}/route/v1/driving/{coordinates_str}?overview=full&geometries=geojson"
            routing_response = requests.get(routing_url)
            routing_response.raise_for_status()
            routing_data = routing_response.json()

            if "routes" not in routing_data or not routing_data["routes"]:
                return JsonResponse({"error": "Unable to generate route."}, status=500)

            path_coordinates = routing_data["routes"][0]["geometry"]["coordinates"]

            if not path_coordinates or len(path_coordinates) < 2:
                return JsonResponse({"error": "Invalid path coordinates for LINESTRING."}, status=400)

            # Swap lon and lat for Traccar's expected coordinate order
            geofence_area = f"LINESTRING({','.join(f'{lat} {lon}' for lon, lat in path_coordinates)})"
            geofence_data = {
                "name": f"Truck {device_id} Geofence",
                "area": geofence_area,
                "description": f"Geofence for truck {device_id}",
            }

            # Create a new geofence
            geofence_response = requests.post(
                f"{TRACCAR_BASE_URL}/geofences",
                headers=HEADERS,
                json=geofence_data
            )
            geofence_response.raise_for_status()
            created_geofence = geofence_response.json()

            # Add the newly created LINESTRING geofence to the response
            response_data["linestring_geofences"].append(created_geofence)

        return JsonResponse(response_data)

    except requests.RequestException as e:
        return JsonResponse({"error": f"An error occurred: {e}"}, status=500)






@api_view(['POST'])
def create_traccar_device(request):

    device_data = request.data
    required_fields = ['name', 'uniqueId', 'max_volume', 'max_weight', 'mms_allocated_id', 'driver_id']
    for field in required_fields:
        if field not in device_data:
            return JsonResponse({'error': f'Missing required field: {field}'}, status=400)

    payload = {
        'name': device_data['name'],
        'uniqueId': device_data['uniqueId'],
    }

    try:
        response = requests.post(f"{TRACCAR_BASE_URL}/devices", json=payload, headers=HEADERS)

        # Step 4: Handle the Traccar API response
        if response.status_code == 200:  # Successful creation
    
            traccar_device = response.json()  

            device_id = traccar_device['id']  

            # UPDATE HERE HERE 

            truck = Truck.objects.create(
                truck_id=device_data['uniqueId'],  
                truck_status='enroute',  
                max_volume=device_data['max_volume'],  
                current_volume=0.0,  
                max_weight=device_data['max_weight'],  
                current_weight=0.0,  
                threshold_volume=0.0,  
                filled_capacity=0.0,  
                mms_allocated_id=device_data['mms_allocated_id'],  
                driver_id=device_data['driver_id'],  
                route=''
            )

            return JsonResponse({'message': 'Device created successfully', 'device': response.json()})
        else:
            return JsonResponse({'error': f'Failed to create device. {response.text}'}, status=response.status_code)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Error connecting to Traccar API: {str(e)}'}, status=500)


@api_view(['POST'])
def get_all_notifications(request):
    try:
        # Fetch all notifications
        notifications = Notifications.objects.filter(is_resolved=False)


        # Serialize the notifications data into a list of dictionaries
        notification_data = [
            {
                "id": notification.id,
                "truck_id": notification.truck_id,
                "notification_type": notification.notification_type,
                "geofence_id": notification.geofence_id,
                "is_resolved": notification.is_resolved,
            }
            for notification in notifications
        ]

        # Return the serialized data
        return JsonResponse({"notifications": notification_data}, status=200)

    except Exception as e:
        # Handle any errors and return an error response
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['POST'])
def get_drivers(request):
    try:
        truck_id = request.data.get('truck_id')
        driver = Driver.objects.get(truck_id=truck_id).name
        return JsonResponse({"driver" : driver})
    except Exception as e:
        print(e)
        return JsonResponse({"error" : f"{str(e)}"})



@api_view(['POST'])
def create_notification(request):
    truck_id = request.data.get('truck_id')
    notification_type = request.data.get('notification_type')
    geofence_id = request.data.get('geofence_id')

    try:
        Notifications.objects.create(
            truck_id=truck_id,
            notification_type=notification_type,
            geofence_id=geofence_id
        )

    except Exception as e:
        print(e)
        return JsonResponse({'error': f'{str(e)}'}, status=400)

    return JsonResponse({'message': 'Notification created'}, status=200)

@api_view(['POST'])
def set_notification_resolve(request):
    id = request.data.get('id')
    try:
        notification = Notifications.objects.get(id=id)

        notification.is_resolved = 1

        notification.save()
    except Exception as e:
        print(e)
        return JsonResponse({'error': f'{str(e)}'}, status=400)

    return JsonResponse({'message': 'Notification resolved'}, status=200)



@api_view(['POST'])
def dynamicRoute(request):
    try:
        # Extract data from request - expecting direct list of warehouses
        warehouses_data = request.data
        warehouse_ids = []

        # print("assigned the route" if response.status_code == 200 else f"Error: {response.status_code} - {response.text}")

        strategy = 'shortest'  # default strategy
        osrm_url = 'http://localhost:8080'  # default OSRM URL

        # Validate that input is a list
        if not isinstance(warehouses_data, list):
            return JsonResponse({"error": "Input must be a list of warehouses"}, status=400)

        # Validate required fields
        if not warehouses_data:
            return JsonResponse({"error": "No warehouses provided"}, status=400)

        # Process warehouses data
        warehouses = []
        route = []
        full_route = []
        route_details = []
        coordinates_with_ids = []  # New list to store coordinates with warehouse IDs

        # Step 1: Process warehouse data
        for idx, wh in enumerate(warehouses_data):
            if not all(key in wh for key in ['lat', 'lng', 'load', 'unload']):
                return JsonResponse(
                    {"error": f"Missing required fields in warehouse {idx}"}, 
                    status=400
                )
            
            # Use existing data if available, otherwise generate defaults
            warehouse = {
                'id': wh.get('id', f'W{idx + 1}'),
                'name': wh.get('name', f'Warehouse {idx + 1}'),
                'lat': float(wh['lat']),
                'lng': float(wh['lng']),
                'load': float(wh['load']),
                'unload': float(wh['unload']),
                'processingTime': wh.get('processingTime', random.randint(25, 40))
            }
            warehouses.append(warehouse)

        # Step 2: Calculate route order
        if warehouses:
            route = [warehouses[0]]
            remaining = warehouses[1:].copy()

            while remaining:
                current = route[-1]
                best_next_index = None
                best_score = float('inf')

                for idx, warehouse in enumerate(remaining):
                    # Calculate distance using Haversine formula
                    R = 6371  # Earth's radius in kilometers
                    lat1, lng1 = current['lat'], current['lng']
                    lat2, lng2 = warehouse['lat'], warehouse['lng']
                    
                    dLat = math.radians(lat2 - lat1)
                    dLon = math.radians(lng2 - lng1)
                    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * \
                        math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
                    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                    distance = R * c

                    # Calculate score (using 'shortest' strategy)
                    score = distance

                    if score < best_score:
                        best_score = score
                        best_next_index = idx

                if best_next_index is not None:
                    route.append(remaining.pop(best_next_index))
                else:
                    break

        # Step 3: Get route coordinates
        for i in range(len(route) - 1):
            start = route[i]
            end = route[i + 1]
            
            try:
                # Construct OSRM API URL
                route_url = f"{osrm_url}/route/v1/driving/{start['lng']},{start['lat']};{end['lng']},{end['lat']}?overview=full&geometries=geojson"
                
                response = requests.get(route_url)
                response.raise_for_status()
                data = response.json()
                
                if data['code'] == 'Ok':
                    coordinates = [(coord[1], coord[0]) for coord in data['routes'][0]['geometry']['coordinates']]
                    
                    # Add coordinates with associated warehouse IDs
                    if coordinates:
                        # Add first point with start warehouse ID if this is the first segment
                        if not coordinates_with_ids:
                            coordinates_with_ids.append({
                                'coordinate': coordinates[0],
                                'warehouse_id': start['id'],
                                'warehouse_name': start['name']
                            })
                        
                        # Add all other points with end warehouse ID
                        for coord in coordinates[1:]:
                            coordinates_with_ids.append({
                                'coordinate': coord,
                                'warehouse_id': end['id'],
                                'warehouse_name': end['name']
                            })
                    
                    if full_route:
                        full_route.extend(coordinates[1:])
                    else:
                        full_route.extend(coordinates)
                        
                    route_details.append({
                        'from_id': start['id'],
                        'from_name': start['name'],
                        'to_id': end['id'],
                        'to_name': end['name'],
                        'coordinates_count': len(coordinates)
                    })

                    warehouse_ids.append(start['id'])

            except Exception as e:
                print(f"Error fetching route between {start['name']} and {end['name']}: {str(e)}")
                continue

        # Prepare response
        response_data = {
            'success': True,
            'route_coordinates': coordinates_with_ids,  # Updated to include IDs
            'route_details': route_details,
            'warehouse_order': [{
                'id': w['id'],
                'name': w['name'],
                'processing_time': w['processingTime']
            } for w in route]
        }
        
        try:                     
            # Fetch the truck based on truck_id
            print("")
            # print("WAREHOUSE ", warehouses_data)
            # truck = Truck.objects.get(truck_id=warehouses_data)
            # # Convert warehouse_ids list into a comma-separated string
            # route = ",".join(map(str, warehouse_ids))
            # print(route)
            # # Update the truck's route
            # truck.route = route
            # truck.save()

        except Exception as e:
            print(e)

        return JsonResponse(response_data, status=200)

    except Exception as e:
        return JsonResponse(
            {"error": str(e)}, 
            status=500
        )    



@api_view(['GET'])
def get_truck_warehouses(request):
    """
    Fetch geofences for a given device_id.
    """
    device_id = request.GET.get('uniqueId')
    if not device_id:
        return JsonResponse({'error': 'uniqueId is required'}, status=400)
    print("DEVICE ID IS : ", device_id)
    try:
        geofences_response = requests.get(
            f"{TRACCAR_BASE_URL}/geofences?uniqueId={device_id}",
            headers=HEADERS
        )

        geofences_response.raise_for_status()
        geofences = geofences_response.json()
        print(geofences)
        if not geofences:
            return JsonResponse({"error": "No geofences assigned to this device."}, status=404)

        # Extract coordinates
        coordinates = []
        for geofence in geofences:
            area = geofence.get("area", "")
            if area.startswith("POLYGON((") and area.endswith("))"):
                points = area.replace("POLYGON((", "").replace("))", "").split(",")
                first_point = points[0].strip().split()
                longitude, latitude = map(float, first_point)
                try:
                    print("GEOFENCES Z: ", geofence['id'])
                    coordinates.append({
                        'id': geofence['id'],  # Geofence ID
                        'name': geofence['name'],
                        'coordinates': f"{longitude},{latitude}",
                        'load' : Warehouse.objects.get(geofence_id=geofence['id']).load,
                        'unload' : Warehouse.objects.get(geofence_id=geofence['id']).unload                                        
                    })
                except Exception as e:
                    print(e)

        return JsonResponse({'geofences': coordinates})

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Error connecting to Traccar API: {str(e)}'}, status=500)


@api_view(['POST'])
def update_truck_route(request):
    """
    Update the truck route based on selected warehouse IDs.
    The warehouse IDs will be stored in the 'route' column as a comma-separated string.
    """
    truck_id = request.data.get('uniqueId')
    warehouse_ids = request.data.get('warehouseIds')  # List of warehouse IDs in order

    if not truck_id or not warehouse_ids:
        return JsonResponse({'error': 'uniqueId and warehouseIds are required'}, status=400)

    # Ensure warehouse_ids is a list
    if not isinstance(warehouse_ids, list):
        return JsonResponse({'error': 'warehouseIds must be a list'}, status=400)

    try:
        # Fetch the truck based on truck_id
        truck = Truck.objects.get(truck_id=truck_id)

        # Convert warehouse_ids list into a comma-separated string
        route = ",".join(map(str, warehouse_ids))
        print(route)
        # Update the truck's route
        truck.route = route
        truck.save()

        return JsonResponse({'message': 'Truck route updated successfully', 'truck_id': truck_id, 'route': truck.route})

    except Truck.DoesNotExist:
        return JsonResponse({'error': 'Truck not found'}, status=404)



# Warehouse APIs
@api_view(['POST'])
def assign_warehouses(request):
    deviceId = request.data.get('deviceId')
    geofenceId = request.data.get('geofenceId')

    data = {
            "deviceId": deviceId,
            "geofenceId": geofenceId
        }

    assign_warehouse = requests.post(
        f"{TRACCAR_BASE_URL}/permissions", 
        headers=HEADERS, 
        json=data
    )

    if assign_warehouse.status_code != 204:
        return JsonResponse(
            {'error': 'Failed to create user on Traccar', 'details': assign_warehouse.text}, 
            status=assign_warehouse.status_code
        )            

    return JsonResponse(
            {'success': 'Assigned warehouse to truck'}, 
            status=200
        )



@api_view(['GET'])
def get_incoming_trucks(request):
    warehouse_id = request.GET.get("warehouseId")

    if not warehouse_id:
        return JsonResponse({'error': 'warehouse_id must be passed'}, status=400)

    trucks = Truck.objects.all()
    serializer = TruckSerializer(trucks, many=True)
    data = serializer.data

    matching_truck_ids = []  # List to store matching truck IDs

    for truck in data:
        route = truck['route']  # Get the route as a comma-separated string
        route_tuple = tuple(route.split(","))  # Convert route to a tuple
        
        # Check if the warehouse_id is in the route
        if warehouse_id in route_tuple:
            matching_truck_ids.append(truck['truck_id'])

    # Return the list of matching truck IDs
    return JsonResponse({'incomingTrucks': matching_truck_ids})



@api_view(['GET'])
def get_all_trucks(request):
    all_trucks = []  # List to store matching truck details

    trucks = Truck.objects.all()

    serializer = TruckSerializer(trucks, many=True)

    
    data = serializer.data
    try:
        for truck in data:
            # Get the current destination of the truck
            
            current_location_name = TcGeofences.objects.using('traccar').get(id=str(truck['current_location'])).name
            current_destination_name = TcGeofences.objects.using('traccar').get(id=str(truck['current_destination'])).name
                
            all_trucks.append({
                'truck_id': truck['truck_id'],
                'name': truck['name'],  # Assuming 'name' is a field in Truck model
                'current_location': truck['current_location'],
                'current_destination': truck['current_destination'],
                'current_location_name' : current_location_name,
                'current_destination_name' : current_destination_name,
                'truck_status': truck['truck_status'],
                'current_weight': truck['current_weight'],
                'filled_capacity': truck['filled_capacity'],
                'is_on_route' : truck['is_on_route'],
                'is_at_warehouse' : truck['is_at_warehouse']
            })
    except Exception as e:
        print(e)
    # Return the list of matching trucks with their details
    return JsonResponse({'all': all_trucks})


@api_view(['GET'])
def get_incoming_live_trucks(request):
    warehouse_id = request.GET.get("warehouseId")

    if not warehouse_id:
        return JsonResponse({'error': 'warehouse_id must be passed'}, status=400)

    trucks = Truck.objects.all()
    serializer = TruckSerializer(trucks, many=True)
    data = serializer.data

    matching_trucks = []  # List to store matching truck details

    for truck in data:
        # Get the current destination of the truck
        current_destination = str(truck['current_destination'])
        print(truck)        
        # Check if the warehouse_id matches the current destination
        if warehouse_id == current_destination:
            current_location_name = TcGeofences.objects.using('traccar').get(id=str(truck['current_location'])).name
            current_destination_name = TcGeofences.objects.using('traccar').get(id=str(truck['current_destination'])).name
            
            matching_trucks.append({
                'truck_id': truck['truck_id'],
                'name': truck['name'],  # Assuming 'name' is a field in Truck model
                'current_location': truck['current_location'],
                'current_destination': truck['current_destination'],
                'current_location_name' : current_location_name,
                'current_destination_name' : current_destination_name,
                'truck_status': truck['truck_status'],
                'current_weight': truck['current_weight'],
                'filled_capacity': truck['filled_capacity'],
                'is_on_route' : truck['is_on_route'],
                'is_at_warehouse' : truck['is_at_warehouse']
            })

    # Return the list of matching trucks with their details
    return JsonResponse({'incomingTrucks': matching_trucks})




@api_view(['GET'])
def get_truck_routes(request):

    trucks = Truck.objects.all()

    
    serializer = TruckSerializer(trucks, many=True)

    
    data = serializer.data

    
    filtered_data = [
        {
            'truck_id': truck['truck_id'],
            'route': truck['route']
        }
        for truck in data
    ]

    # Return the filtered data in the response
    return JsonResponse({'incoming_trucks': filtered_data})



@api_view(['GET'])
def get_outgoing_trucks(request):
    # Fetch the warehouse_id from the request parameters
    warehouse_id = request.GET.get("warehouseId")

    if not warehouse_id:
        return JsonResponse({'error': 'warehouse_id must be provided'}, status=400)

    # Query for outgoing trucks: current_location matches warehouse_id and is_at_warehouse == 0
    outgoing_trucks = Truck.objects.filter(current_location=warehouse_id, is_at_warehouse=False)

    # Prepare the response data
    outgoing_trucks_data = []

    for truck in outgoing_trucks:
        try:
            # Fetch current location and destination names from the 'traccar' database
            current_location_name = TcGeofences.objects.using('traccar').get(id=truck.current_location).name
            current_destination_name = TcGeofences.objects.using('traccar').get(id=truck.current_destination).name
        except TcGeofences.DoesNotExist:
            current_location_name = "Unknown Location"
            current_destination_name = "Unknown Destination"

        # Add truck details to the outgoing_trucks_data list
        outgoing_trucks_data.append({
            'truck_id': truck.truck_id,
            'name': truck.name,
            'current_location': truck.current_location,
            'current_destination': truck.current_destination,
            'current_location_name': current_location_name,
            'current_destination_name': current_destination_name,
            'truck_status': truck.truck_status,  # Assuming you have this field
            'current_weight': truck.current_weight,
            'filled_capacity': truck.filled_capacity,  # Assuming you have this field
            'is_on_route' : truck.is_on_route,
            'is_at_warehouse' : truck.is_at_warehouse
        })

    # Return the response as JSON
    return JsonResponse({'outgoing_trucks': outgoing_trucks_data})

@api_view(['GET'])

def get_truck_capacity(request):
    truck_id = request.GET.get('truckId')  # 'truckId' is the query parameter name

    if truck_id:
        # Filter trucks by the truck_id (assuming truck_id is unique)
        trucks = Truck.objects.filter(truck_id=truck_id)

        # Check if any truck is found
        if trucks.exists():
            # Serialize the filtered trucks
            serializer = TruckSerializer(trucks, many=True)
            data = serializer.data

            filtered_data = [
                {
                    'truck_id': truck['truck_id'],
                    'filled_capacity': truck['filled_capacity']
                }
                for truck in data
            ]

            return JsonResponse({'incoming_trucks': filtered_data})
        else:
            # Return a 404 response if the truck with the given truck_id is not found
            return JsonResponse({'error': 'Truck not found'}, status=404)
    else:
        # If no truck_id is provided, return an error message
        return JsonResponse({'error': 'truckId parameter is required'}, status=400)


@api_view(['GET'])
def get_truck_status(request):
    truck_id = request.GET.get('uniqueId')

    if truck_id:
        try:
            truck = Truck.objects.get(truck_id=truck_id)  
            data = {
                'truck_id': truck.truck_id,
                'status': truck.truck_status,
                'live_status': truck.live_status,
                'on_route' : truck.is_on_route,
                'at_warehouse' : truck.is_at_warehouse
                
            }
            return JsonResponse(data)

        except Truck.DoesNotExist:
            return JsonResponse({'error': 'Truck not found'}, status=404)
    else:
        return JsonResponse({'error': 'truckId parameter is required'}, status=400)

@api_view(['POST'])
def get_warehouse_names(request):
    # Retrieve the list of warehouse IDs from the request body
    warehouse_ids = request.data.get('warehouseIds')  # List of warehouse IDs in order

    # Initialize an empty list to store warehouse names
    warehouse_names = []

    # Iterate over the warehouse IDs
    for warehouse_id in warehouse_ids:
        try:
            # Fetch the warehouse by ID and get its name
            warehouse = TcGeofences.objects.using('traccar').get(id=warehouse_id)
            warehouse_names.append(warehouse.name)
        except TcGeofences.DoesNotExist:
            # Handle the case where the warehouse does not exist
            warehouse_names.append(f"Warehouse ID {warehouse_id} not found")

    # Return the list of warehouse names as a response
    return JsonResponse({"warehouseNames": warehouse_names}) 


@api_view(['POST'])
def get_all_warehouses(request):
    warehouse_ids = []
    warehouse_names = []

    try:
        warehouses = TcGeofences.objects.using('traccar').all()  # Get all warehouses from the `traccar` database
        for warehouse in warehouses:
            warehouse_ids.append(warehouse.id)
            warehouse_names.append(warehouse.name)
    except Exception as e:
        # Handle any unexpected error
        return JsonResponse({"error": str(e)}, status=500)

    # Return the IDs and names as a JSON response
    return JsonResponse({"warehouse_ids": warehouse_ids, "warehouse_names": warehouse_names})



@api_view(['POST'])
def get_truck_deliveries(request):
    truck_id = request.data.get('truck_id')
    print(truck_id)
    try: 
        truck = Truck.objects.get(truck_id=truck_id)        
        print("TRUCK CURRENT ", truck.current_location)
        current_location_name = TcGeofences.objects.using('traccar').get(id=truck.current_location).name
        current_destination_name = TcGeofences.objects.using('traccar').get(id=truck.current_destination).name
        return JsonResponse({
            "current_location" : truck.current_location,
            "current_destination" : truck.current_destination,
            "current_location_name" : current_location_name,
            "current_destination_name" : current_destination_name

        })
    except Exception as e:
        pass
        print(e)
    return JsonResponse({"message": "done"}, status=200)
    # # 

@api_view(['GET'])
def get_scheduled_trucks(request):
    warehouse_id = request.query_params.get('warehouseId')  # Use GET query parameters
    if not warehouse_id:
        return JsonResponse({"error": "warehouseId is required"}, status=400)

    trucks = Truck.objects.all()
    warehouse_trucks = []  # List to hold trucks allocated to the warehouse

    for truck in trucks:
        # Check if the truck has a route defined
        if not truck.route:
            continue
            # retreive the warehouse's actual arrival time & departhure time:
            # get latest timestamp where of event_type = 'arrival' and warehouse 
        try:
            # Parse the route into a list of integers (warehouse IDs)
            route_list = [int(x.strip()) for x in truck.route.split(',') if x.strip().isdigit()]
            route_warehouse_names = []

            # Fetch warehouse names for the route
            for route_warehouse_id in route_list:
                try:
                    warehouse_name = TcGeofences.objects.using('traccar').get(id=route_warehouse_id).name
                    route_warehouse_names.append(warehouse_name)
                except TcGeofences.DoesNotExist:
                    # Skip if the warehouse ID does not exist in the database
                    continue

            # Check if the specified warehouse_id exists in the truck's route
            if int(warehouse_id) in route_list:
                warehouse_trucks.append({
                    "truck_id": truck.truck_id,
                    "truck_name": truck.name,
                    "route_warehouse_ids": route_list,
                    "route_warehouse_names": route_warehouse_names,
                    "route_estimated_arrival": truck.route_estimated_arrival,

                })

        except ValueError:
            # If route parsing fails for this truck, skip it
            continue

    # Return the list of trucks directly
    return JsonResponse(warehouse_trucks, safe=False, status=200)


# ALERTS & STATUS UPDATION :
@api_view(['GET'])
def get_alerts(request):
    geofences_response = requests.get(
        f"{TRACCAR_BASE_URL}/geofences",
        headers=HEADERS
    )

    geofences_response.raise_for_status()  # Ensure a 4xx/5xx error raises an exception
    geofences = geofences_response.json()

    # matching_geofences = [geofence for geofence in geofences if geofence.get('id') == specific_id]

    # Exclude 'deviceUnknown' events and find the latest valid event for each deviceid
    latest_events = (
        TcEvents.objects.using('traccar')
        .exclude(type='deviceUnknown')
        .values('deviceid')
        .annotate(last_eventtime=Max('eventtime'))
        .order_by('deviceid')
    )

    # Retrieve the full records for these latest valid events
    latest_records = TcEvents.objects.using('traccar').filter(
        eventtime__in=[event['last_eventtime'] for event in latest_events]
    )

    # Convert QuerySet to a list of dictionaries
    alerts_data = list(latest_records.values(
        'id', 'type', 'eventtime', 'deviceid', 'positionid', 'geofenceid', 'attributes', 'maintenanceid'
    ))

    # # DUBUGGING PURPOSES
    # for alert in alerts_data:
    #     if alert['type']=='deviceOnline':
    #         alert['type']='geofenceEnter'
    #         alert['geofenceid']='42'

    # geofence_exit_alerts = [alert for alert in alerts_data if alert['type'] == 'geofenceExit']
    # geofence_enter_alerts = [alert for alert in alerts_data if alert['type'] == 'geofenceEnter']
    
    geofences_dict = {f'{g['id']}': g for g in geofences}

    for Alert in alerts_data:
        if Alert['type'] == 'geofenceEnter':
            geofence_id = Alert['geofenceid']
            device_id = Alert['deviceid']
            unique_id = requests.get(f'http://localhost:8000/api/devices/getUniqueId?id={device_id}').json().get('uniqueId')
            # geofencerw = geofences_dict.get(geofence_id)
            geofence = geofences_dict.get(f'{geofence_id}')
            if geofence:
                area = geofence.get('area', '')
                if area.startswith("POLYGON"):
                    # Update truck's current_location and current_destination
                    try:                    
                        truck = Truck.objects.get(truck_id=unique_id)
                        truck.current_location = geofence_id
                        truck.is_at_warehouse = 1
                        # Parse route field as a list of integers
                        route_list = [int(x.strip()) for x in truck.route.split(',')]   

                        Truck_log.objects.create(
                            truck_id=truck.truck_id,
                            actual_id=truck.actual_id,
                            event_type='arrival',
                            current_location=truck.current_location
                        )    

                        Notifications.objects.create(
                            truck_id=truck.truck_id,
                            notification_type='geofenceEnter',
                            geofence_id=truck.current_location
                        )

                        Truck_capacity_log.objects.create(
                            truck_id = truck.truck_id,
                            actual_id = truck.actual_id,
                            current_location = truck.current_location,
                            filled_capacity = truck.filled_capacity
                        )

                        if int(geofence_id) in route_list:
                            idx = route_list.index(int(geofence_id))
                            print("IDX: ", idx)
                            # Set current_destination to the next element if exists
                            if idx < len(route_list) - 1:
                                truck.current_destination = route_list[idx + 1]
                            else:
                                # If there's no next element, set current_destination to None or leave it unchanged
                                truck.current_destination = None

                        truck.save()
                    except Truck.DoesNotExist:
                        # Handle truck not found if necessary
                        pass

        elif Alert['type'] == 'geofenceExit':
            geofence_id = Alert['geofenceid']
            geofence = geofences_dict.get(f'{geofence_id}')
            device_id = Alert['deviceid']
            unique_id = requests.get(f'http://localhost:8000/api/devices/getUniqueId?id={device_id}').json().get('uniqueId')
            if geofence:
                area = geofence.get('area', '')
                if area.startswith("LINESTRING"):
                    try:
                        truck = Truck.objects.get(truck_id=unique_id)
                        truck.is_on_route = 0

                        Notifications.objects.create(
                            truck_id=truck.truck_id,
                            notification_type='geofenceExit',
                            geofence_id=truck.current_location,
                            is_on_route = 0
                        )
        
                        truck.save()
                    except Truck.DoesNotExist:
                        # Handle truck not found if necessary
                        pass
                elif area.startswith("POLYGON"):
                    try:
                        truck = Truck.objects.get(truck_id=unique_id)
                        truck.is_at_warehouse = 0

                        Truck_log.objects.create(
                            truck_id=truck.truck_id,
                            actual_id=truck.actual_id,
                            event_type='departure',
                            current_location=truck.current_location
                        )    


                        Notifications.objects.create(
                            truck_id=truck.truck_id,
                            notification_type='geofenceExit',
                            geofence_id=truck.current_location
                        )

                        Truck_capacity_log.objects.create(
                            truck_id = truck.truck_id,
                            actual_id = truck.actual_id,
                            current_location = truck.current_location,
                            filled_capacity = truck.filled_capacity
                        )

                        truck.save()
                    except Truck.DoesNotExist:
                        # Handle truck not found if necessary
                        pass
                        
        elif Alert['type'] == 'deviceMoving' or Alert['type'] == 'deviceStopped':
            device_id = Alert['deviceid']
            unique_id = requests.get(f'http://localhost:8000/api/devices/getUniqueId?id={device_id}').json().get('uniqueId')
            try: 
                truck = Truck.objects.get(truck_id=unique_id)
                truck.live_status = Alert['type']
                truck.save()

                Truck_live_status_log.objects.create(
                    truck_id = truck.truck_id,
                    live_status = truck.live_status
                )

            except Truck.DoesNotExist:                
                pass

    device_ids = [alert['deviceid'] for alert in alerts_data]
    # Map device ids to their uniqueIds (assuming actual_id and uniqueId fields)
    device_mapping = {
        device.actual_id: device.truck_id
        for device in Truck.objects.filter(actual_id__in=device_ids)
    }

    # Add uniqueId to each alert record
    for alert in alerts_data:
        alert['uniqueId'] = device_mapping.get(alert['deviceid'], None)

    return JsonResponse({'alerts': alerts_data}, safe=False)


@api_view(['POST'])
def set_alerts(request):
    # Check if the request contains the data
    if not request.data:
        return JsonResponse({'error': 'No data provided'}, status=400)

    # Expecting the alerts to be passed in the request body
    alerts_data = request.data.get('alerts', [])
    
    if not alerts_data:
        return JsonResponse({'error': 'No alerts in the request'}, status=400)

    updated_trucks = []  # To keep track of which trucks have been updated

    for alert in alerts_data:
        device_id = alert.get('uniqueId')
        status = alert.get('type')  # Assuming 'type' field in alert contains the status to update
        
        if not device_id or not status:
            continue  # Skip if the necessary fields are missing in the alert
        
        try:
            # Find the corresponding truck and update its status
            truck = Truck.objects.get(truck_id=device_id)  # Use the actual_id field to match
            truck.truck_status = status  # Update the status field
            truck.save()  # Save the changes to the database
            
            # Append to the updated list
            updated_trucks.append({'truck_id': truck.truck_id, 'new_status': truck.truck_status})
        except Truck.DoesNotExist:
            # If the truck is not found, log the error (optional)
            updated_trucks.append({'device_id': device_id, 'error': 'Truck not found'})

    # Return a response with the updated truck statuses
    return JsonResponse({'updated_trucks': updated_trucks}, safe=False)
    

@api_view(['POST'])
def set_call_alerts(request):
    uniqueId = request.data.get('uniqueId')
    truck_status = request.data.get('status')
    try:
        truck = Truck.objects.get(truck_id=uniqueId)
        truck.truck_status = truck_status
        truck.save()
    except Truck.DoesNotExist as e:    
        print(e)
    return JsonResponse({'truck': uniqueId, "truck_status": truck_status}, safe=False)
        

@api_view(['POST'])
def create_new_user(request):
    username = request.data.get('username')
    password = request.data.get('password')        
    role = request.data.get('role')    
    
    user = Users(
        username=username,
        password=password,
        role=role
    )

    try:
        user.save()
    except Exception as e:
        return JsonResponse({ "error" : r } )

    return JsonResponse({
        'username' : username,
        'password' : password,        
        'role' : role,
        })

@api_view(['POST'])
def create_token(request):
    try:
        # Extract data from the request
        username = request.data.get('username')
        password = request.data.get('password')
        expiration = request.data.get('expiration')  # Format: dd-mm-2024

        if not (username and password and expiration):
            return JsonResponse({'error': 'username, password, and expiration are required'}, status=400)

        # Format expiration to ISO format
        try:
            from datetime import datetime
            expiration_iso = datetime.strptime(expiration, '%d-%m-%Y').isoformat() + "Z"
            print("EXITERE", expiration_iso)
        except ValueError:
            return JsonResponse({'error': 'Invalid expiration format. Use dd-mm-2024.'}, status=400)

        # Step 1: Create a new user on Traccar
        user_payload = {
            "name": username,
            "email": f"{username}@example.com",  # Adjust email as needed
            "password": password,
            "administrator": False
        }
        create_user_response = requests.post(
            f"{TRACCAR_BASE_URL}/users", 
            headers=HEADERS, 
            json=user_payload
        )

        if create_user_response.status_code != 201:  # HTTP 201 Created
            return JsonResponse(
                {'error': 'Failed to create user on Traccar', 'details': create_user_response.text}, 
                status=create_user_response.status_code
            )

        # Step 2: Generate a token for the created user
        session_token_response = requests.post(
            f"{TRACCAR_BASE_URL}/session/token",
            auth=(username, password),  # Basic Auth
            data={"expiration": expiration_iso},  # Send expiration as form-data
        )

        if session_token_response.status_code != 200:  # HTTP 200 OK
            return JsonResponse(
                {'error': 'Failed to generate token', 'details': session_token_response.text},
                status=session_token_response.status_code
            )

        # Extract token
        token = session_token_response.json().get('token')

        if not token:
            return JsonResponse({'error': 'Token not found in the response'}, status=500)

        return JsonResponse({'token': token})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@api_view(['GET'])
def get_token(request):
    pass

@api_view(['POST'])
def get_all_users(request):
    users= Users.objects.all()
    
    users_list = []
    for user in users:
        users_list.append(
            {
                "id" : user.id,
                "username " : user.username,
                "role" : user.role,
                "warehouse_access" : user.warehouse_access,
                "truck_access" : user.truck_access
            }
        )
    
    return JsonResponse({"users" : users_list})


@api_view(['POST'])
def set_warehouse_permissions(request):
    username = request.data.get('username')
    warehouse_ids = request.data.get('warehouseIds')

    if username is None or warehouse_ids is None:
        return JsonResponse({'error': 'username or warehouse_ids not found in the response'}, status=404)

    try:
        user = Users.objects.get(username=username)
        user.warehouse_access = warehouse_ids
        user.save()
    except Exception as e:
        return JsonResponse({'error' : str(e)})
    
    return JsonResponse({'username': username, 'warehouse_ids' : warehouse_ids}, safe=False)


@api_view(['POST'])
def set_credentials(request):
    # Retrieve data from request
    username = request.data.get('username')
    new_password = request.data.get('password')

    if not username or not new_password:
        return JsonResponse({"error": "username, password are required fields."}, status=400)

    try:
        # Get the user object by username
        user = Users.objects.get(username=username)

        # Update credentials
        user.password = new_password  
        user.save()

        return JsonResponse({"message": f"Credentials updated successfully for user '{username}'."}, status=200)

    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    

@api_view(['POST'])
def set_route_estimated_arrival(request):
    """
    Set the estimated arrival times for a truck's route.
    """
    truck_id = request.data.get('uniqueId')
    estimated_arrival = request.data.get('estimated_arrival')

    """
    sample input for estimated_arrival


    [{"from": "Warehouse A", "to": "Warehouse B", "arrival_time": "2024-12-10T10:00:00Z"}, {"from": "Warehouse B", "to": "Warehouse C", "arrival_time": "2024-12-10T14:00:00Z"}]
    """

    if not truck_id or not estimated_arrival:
        return JsonResponse({"error": "uniqueId and estimated_arrival are required"}, status=400)

    try:
        # Validate that estimated_arrival is a list of dictionaries
        if not isinstance(estimated_arrival, list) or not all(
            isinstance(segment, dict) and 'from' in segment and 'to' in segment and 'arrival_time' in segment
            for segment in estimated_arrival
        ):
            return JsonResponse({"error": "Invalid estimated_arrival format"}, status=400)

        truck = Truck.objects.get(truck_id=truck_id)

        # Store the estimated arrival as a JSON string in the TextField
        truck.route_estimated_arrival = json.dumps(estimated_arrival)
        truck.save()

        return JsonResponse({"message": "Estimated arrival times updated successfully"})
    except Truck.DoesNotExist:
        return JsonResponse({"error": "Truck not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
    




@api_view(['GET'])
def get_truck_driver_info(request):
    truck_id = request.GET.get('truckId')
    
    
    data = {'truck_id': truck_id, 'driver_info': {'name': 'John Doe'}}
    return JsonResponse(data)

# Scanner APIs

@api_view(['GET'])

def get_parcel_info(request):
    tracking_id = request.GET.get('trackingId')

    parcel = Parcel.objects.get(tracking_id=tracking_id)

    data = {
        'tracking_id': tracking_id, 
        'weight' : parcel.weight,
        'volume' : parcel.volume,
        'bag_id' : parcel.bag_id,
        'current_destination' : parcel.current_destination,
        'current_location' : parcel.current_location,
        'destination' : parcel.destination
        }
    return JsonResponse(data)





# Report APIs

@api_view(['GET'])

def get_system_report(request):
    
    
    data = {'system_report': {'total_trucks': 100}}
    return JsonResponse(data)

@api_view(['GET'])

def get_truck_report(request):
    truck_id = request.GET.get('truckId')
    
    
    data = {'truck_id': truck_id, 'report': {'mileage': 15000}}
    return JsonResponse(data)

@api_view(['GET'])

def get_region_report(request):
    region_name = request.GET.get('regionName')
    
    
    data = {'region_name': region_name, 'report': {'deliveries': 500}}
    return JsonResponse(data)

@api_view(['GET'])

def get_route_report(request):
    src = request.GET.get('src')
    dst = request.GET.get('dst')
    
    data = {'route': f'{src} to {dst}', 'report': {'trips': 30}}
    return JsonResponse(data)



@api_view(['POST'])
def get_3pl_trucks(request):
    # Extract destination from the request data
    destination = request.data.get('destination')    
    # Validate input
    if destination is None:
        return JsonResponse({"error": "destination is required"}, status=400)
    
    # Retrieve all trucks (adjust model and query as needed)
    trucks = Truck.objects.all()
    
    sorted_trucks = []
    
    for truck in trucks:
        # Parse the route into a list of integers
        if not truck.route:
            continue
        try:
            route_list = [int(x.strip()) for x in truck.route.split(',') if x.strip().isdigit()]
            print(route_lis)
            route_warehouse_names = []
            for warehouse in route_list:                
                route_warehouse_names.append(TcGeofences.objects.using('traccar').get(id=str(warehouse)).name)

                
        
        # Check if the provided destination is in the truck's route
            
            if destination not in route_list:
                continue
            
            # Ensure the truck's current_destination is in the route
            if truck.current_destination not in route_list:
                continue
            
            # Find the positions of the current_destination and the given destination in the route
            current_dest_index = route_list.index(truck.current_destination)
            parcel_dest_index = route_list.index(destination)
            
            # Keep the truck if its current_destination is before the requested destination in the route
            if current_dest_index < parcel_dest_index:
                sorted_trucks.append({
                    "truck_id": truck.truck_id,
                    "current_destination": truck.current_destination,
                    "current_destination_name": TcGeofences.objects.using('traccar').get(id=str(truck.current_destination)).name,
                    "parcel_destination_name" : TcGeofences.objects.using('traccar').get(id=str(destination)).name,
                    "route": route_list,
                    "route_warehouse_names": route_warehouse_names,
                })
        
        except Exception as e:
            # If route parsing fails for this truck, skip it
            return JsonResponse({"error": f'{str(e)}'}, status=400)
    # Return the filtered trucks as a JSON response
    return JsonResponse({"trucks": sorted_trucks}, status=200)

@api_view(['POST'])
def book_3pl(request):
    truck_id = request.data.get('truck_id')
    weight = request.data.get('weight')
    volume = request.data.get('volume')
    current_location = request.data.get('current_location')
    current_destination = request.data.get('current_destination')
    destination = request.data.get('destination')

    if not truck_id or not weight or not volume or not current_location or not current_destination or not destination:
        return JsonResponse({'error': 'truck_id, weight and volume, current_location, current_destination, destination is required'}, status=400)

    truck = Truck.objects.get(truck_id=truck_id)

    if (truck.current_weight + weight > truck.max_weight or
                truck.current_volume + volume > truck.max_volume):
                return JsonResponse({
                    'error': (f'Parcel cannot be loaded: exceeds truck limits. '
                              f'Max Weight: {truck.max_weight}, Max Volume: {truck.max_volume}')
                })
                

    # Update truck's current weight, current volume, and filled capacity
    truck.current_weight += weight
    truck.current_volume += volume
    truck.filled_capacity = (truck.current_volume / truck.max_volume) * 100  # Calculate percentage filled
    truck.save()

    

    tracking_id = str(random.randint(100, 999))

    parcel = Parcel(
            tracking_id=tracking_id,
            weight=round(weight, 2),
            volume=round(volume, 2),
            destination=destination,
            bag_id=-1,
            current_location=current_location,
            current_destination=current_destination,
        )
    
    parcel.save()

    return JsonResponse({
        'tracking_id' : tracking_id,
        'truck_id' : truck.truck_id,
        'updated_truck_weight': truck.current_weight,
        'updated_truck_volume': truck.current_volume,
        'updated_filled_capacity': truck.filled_capacity
        }, safe=False)


@api_view(['GET'])
def get_uniqueId(request):
    if request.method == 'GET':
        # Retrieve the truck ID from the request
        truck_id = request.GET.get('id')
        if not truck_id:
            return JsonResponse({'error': 'id is required'}, status=400)

        try:
            # Send a GET request to the Traccar API
            response = requests.get(f"{TRACCAR_BASE_URL}/devices?id={truck_id}", headers=HEADERS)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Parse the JSON response
            data = response.json()

            # Ensure the response contains the 'uniqueId' field
            if isinstance(data, list) and len(data) > 0:
                uniqueId = data[0].get("uniqueId")  # Assuming `uniqueId` is in the first device entry
                if uniqueId:
                    return JsonResponse({'uniqueId': uniqueId}, status=200)
                else:
                    return JsonResponse({'error': 'uniqueId not found in the response'}, status=404)
            else:
                return JsonResponse({'error': 'No devices found with the provided ID'}, status=404)

        except requests.exceptions.RequestException as e:
            # Handle HTTP request errors
            print(f"HTTP request error: {e}")
            return JsonResponse({'error': 'Failed to retrieve data from Traccar API'}, status=500)

        except Exception as e:
            # Handle any other errors
            print(f"Unexpected error: {e}")
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

@api_view(['GET'])
def get_id(request):
    if request.method == 'GET':
        # Retrieve the truck ID from the request
        uniqueId = request.GET.get('uniqueId')
        if not uniqueId:
            return JsonResponse({'error': 'uniqueId is required'}, status=400)

        try:
            # Send a GET request to the Traccar API
            response = requests.get(f"{TRACCAR_BASE_URL}/devices?uniqueId={uniqueId}", headers=HEADERS)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Parse the JSON response
            data = response.json()

            # Ensure the response contains the 'uniqueId' field
            if isinstance(data, list) and len(data) > 0:
                id = data[0].get("id")  # Assuming `uniqueId` is in the first device entry
                if id:
                    return JsonResponse({'id': id}, status=200)
                else:
                    return JsonResponse({'error': 'id not found in the response'}, status=404)
            else:
                return JsonResponse({'error': 'No devices found with the provided ID'}, status=404)

        except requests.exceptions.RequestException as e:
            # Handle HTTP request errors
            print(f"HTTP request error: {e}")
            return JsonResponse({'error': 'Failed to retrieve data from Traccar API'}, status=500)

        except Exception as e:
            # Handle any other errors
            print(f"Unexpected error: {e}")
            return 


@api_view(['POST'])
def allocate_parcel_to_bag(request):
    # Get the parcel list from the request body
    parcel_ids = request.data.get('parcel_ids', [])  # Assuming parcel IDs are passed as a list in the POST body

    if not parcel_ids:
        return JsonResponse({'error': 'No parcel IDs provided'}, status=400)

    # Create a new Bag record with a random 4-digit bag_id and truck_id set to NULL
    bag_id = random.randint(1000, 9999)  # Generate a random 4-digit bag_id
    new_bag = Bag(
        bag_id=bag_id,
        truck_id=None,  # Set truck_id to NULL (None in Django)
        destination=0,  # Default destination
        current_location=0,  # Default current_location
        current_destination=0,  # Default current_destination
        weight=0,  # Initialize weight
        volume=0  # Initialize volume
    )
    new_bag.save()  # Save the new bag record to the database

    # Update the Parcel table: set the bag_id for each parcel in the list
    updated_parcels = []
    total_weight = 0  # Track total weight of the bag
    total_volume = 0  # Track total volume of the bag

    for parcel_id in parcel_ids:
        try:
            parcel = Parcel.objects.get(tracking_id=parcel_id)  # Find the parcel by tracking_id
            parcel.bag_id = new_bag.bag_id  # Set the bag_id of the parcel to the newly created bag
            parcel.save()  # Save the changes to the database

            # Accumulate weight and volume
            total_weight += parcel.weight
            total_volume += parcel.volume

            updated_parcels.append({
                'tracking_id': parcel.tracking_id,
                'new_bag_id': new_bag.bag_id
            })
        except Parcel.DoesNotExist:
            updated_parcels.append({'tracking_id': parcel_id, 'error': 'Parcel not found'})

    # Update the bag's weight and volume
    new_bag.weight = total_weight
    new_bag.volume = total_volume
    new_bag.save()  # Save the updated bag record

    return JsonResponse({'updated_parcels': updated_parcels, 'bag_id': new_bag.bag_id, 'bag_weight': new_bag.weight, 'bag_volume': new_bag.volume}, safe=False)


@api_view(['POST'])
def allocate_bag_to_truck(request):
    """
    Assigns bags to a truck after checking the truck's weight and volume capacities.
    If either max weight or max volume is exceeded, the bag is not allocated.
    """
    bag_ids = request.data.get('bag_ids', [])  # List of bag IDs from the request
    truck_id = request.data.get('truck_id')  # Truck ID from the request

    if not bag_ids or not truck_id:
        return JsonResponse({'error': 'Bag IDs and Truck ID are required'}, status=400)

    try:
        # Fetch the truck instance
        truck = Truck.objects.get(truck_id=truck_id)
    except Truck.DoesNotExist:
        return JsonResponse({'error': f'Truck with id {truck_id} not found'}, status=404)

    updated_bags = []
    errors = []

    for bag_id in bag_ids:
        try:
            # Fetch the bag by bag_id
            bag = Bag.objects.get(bag_id=bag_id)

            # Check if the truck can accommodate the bag's weight and volume
            if (truck.current_weight + bag.weight > truck.max_weight or
                truck.current_volume + bag.volume > truck.max_volume):
                errors.append({
                    'bag_id': bag_id,
                    'error': (f'Bag cannot be loaded: exceeds truck limits. '
                              f'Max Weight: {truck.max_weight}, Max Volume: {truck.max_volume}')
                })
                continue

            # Update truck's current weight, current volume, and filled capacity
            truck.current_weight += bag.weight
            truck.current_volume += bag.volume
            truck.filled_capacity = (truck.current_volume / truck.max_volume) * 100  # Calculate percentage filled
            truck.save()

            # Assign the bag to the truck
            bag.truck_id = truck.truck_id
            bag.save()

            updated_bags.append({
                'bag_id': bag.bag_id,
                'new_truck_id': truck.id,
                'updated_truck_weight': truck.current_weight,
                'updated_truck_volume': truck.current_volume,
                'updated_filled_capacity': truck.filled_capacity
            })

        except Bag.DoesNotExist:
            errors.append({'bag_id': bag_id, 'error': 'Bag not found'})

    response_data = {
        'updated_bags': updated_bags,
        'errors': errors
    }

    return JsonResponse(response_data, safe=False)


@api_view(['POST'])
def deallocate_bag_from_truck(request):
    """
    Removes bags from a truck, updates the truck's weight, volume, and capacity, 
    and deletes the bag from the database.
    """
    bag_ids = request.data.get('bag_ids', [])  # List of bag IDs to deallocate
    truck_id = request.data.get('truck_id')  # Truck ID from which bags are to be removed

    if not bag_ids or not truck_id:
        return JsonResponse({'error': 'Bag IDs and Truck ID are required'}, status=400)

    try:
        # Fetch the truck instance
        truck = Truck.objects.get(truck_id=truck_id)
    except Truck.DoesNotExist:
        return JsonResponse({'error': f'Truck with id {truck_id} not found'}, status=404)

    updated_bags = []
    errors = []

    for bag_id in bag_ids:
        try:
            # Fetch the bag by bag_id
            bag = Bag.objects.get(bag_id=bag_id, truck_id=truck.truck_id)  # Ensure bag is assigned to the truck

            # Update truck's weight and volume by removing the bag's values
            truck.current_weight -= bag.weight
            truck.current_volume -= bag.volume
            truck.filled_capacity = (truck.current_volume / truck.max_volume) * 100 if truck.max_volume > 0 else 0
            truck.save()

            # Delete the bag from the database
            bag.delete()

            updated_bags.append({
                'bag_id': bag_id,
                'removed_from_truck_id': truck.truck_id,
                'updated_truck_weight': truck.current_weight,
                'updated_truck_volume': truck.current_volume,
                'updated_filled_capacity': truck.filled_capacity
            })

        except Bag.DoesNotExist:
            errors.append({'bag_id': bag_id, 'error': 'Bag not found or not assigned to this truck'})

    response_data = {
        'updated_bags': updated_bags,
        'errors': errors
    }

    return JsonResponse(response_data, safe=False)



def monthly_prediction_view(request):
    """
    Endpoint for the next 30-day prediction with an alert for high demand.
    """
    try:
        response = predict_demand(periods=30, alert_for_monthly=True)
        # Ensure all values are JSON serializable
        response['alert'] = bool(response['alert'])  # Convert alert to True/False if it's a Python bool
        return JsonResponse(response, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def quarterly_prediction_view(request):
    """
    Endpoint for the next 90-day prediction without any alert.
    """
    try:
        response = predict_demand(periods=90, alert_for_monthly=False)
        return JsonResponse(response, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)






# HELPER METHOD TO INSERT RANDOM PARCEL ENTRIES
@api_view(['GET'])
def generate_and_insert_parcels(request):
    """
    This function generates random parcels and inserts them into the Parcel table.
    It is called via a GET request and does not take any parameters.
    """
    # Define the route and parameters within the function
    route = [39, 38, 40, 41, 42, 43, 44]
    num_entries = 10  # Number of parcels to insert
    
    def generate_parcel_data():
        """
        Generate a single parcel entry with random values based on the given constraints.
        """
        # Generate a random 3-digit tracking ID
        tracking_id = str(random.randint(100, 999))
        
        # Random weight and volume
        weight = random.uniform(1, 20)  # Weight between 1 and 20
        volume = random.uniform(500, 5000)  # Volume between 500 and 5000

        # Random destination (42, 43, or 44)
        destination = random.choice([43, 44])

        # Valid sources are values before the destination
        valid_sources = [location for location in route if location < destination]
        source = random.choice(valid_sources)

        # Current location can be source or ahead of source but not destination
        valid_current_locations = [loc for loc in route if loc >= source and loc < destination]
        current_location = random.choice(valid_current_locations)

        # Current destination should be just ahead of current_location in the route
        next_locations = [loc for loc in route if loc > current_location]
        current_destination = next_locations[0] if next_locations else destination

        # Bag ID should be NULL (None in Python)
        bag_id = None

        # Create a new Parcel instance
        parcel = Parcel(
            tracking_id=tracking_id,
            weight=round(weight, 2),
            volume=round(volume, 2),
            destination=destination,
            bag_id=bag_id,
            current_location=current_location,
            current_destination=current_destination,
        )

        return parcel

    # Insert parcels into the database
    inserted_parcels = []
    for _ in range(num_entries):
        parcel = generate_parcel_data()
        try:
            parcel.save()  # Save the parcel to the database
            inserted_parcels.append({
                'tracking_id': parcel.tracking_id,
                'current_location': parcel.current_location,
                'current_destination': parcel.current_destination
            })
        except Exception as e:
            print(e)
    # Return a response with the details of the inserted parcels
    return JsonResponse({'inserted_parcels': inserted_parcels}, safe=False)





    # gets parcel list as input 



#    !!!!    DONT    PASTE    CODE    BELOW    !!!!