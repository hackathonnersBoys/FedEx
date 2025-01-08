import math
import requests
from typing import List, Dict, Tuple

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the Haversine distance between two geographic points.
    
    Args:
        lat1 (float): Latitude of the first point.
        lng1 (float): Longitude of the first point.
        lat2 (float): Latitude of the second point.
        lng2 (float): Longitude of the second point.
    
    Returns:
        float: Distance between the two points in kilometers.
    """
    R = 6371  # Earth's radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lng2 - lng1)
    a = math.sin(dLat / 2) ** 2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dLon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_route_order(warehouses: List[Dict], strategy: str = 'shortest') -> List[Dict]:
    """
    Determine the order of warehouses based on the selected strategy.
    
    Args:
        warehouses (List[Dict]): List of warehouse dictionaries.
        strategy (str): Route optimization strategy ('shortest', 'balanced', 'efficient').
    
    Returns:
        List[Dict]: Ordered list of warehouses representing the route.
    """
    if not warehouses:
        return []
    
    # Initialize route with the first warehouse (assuming starting point)
    route = [warehouses[0]]
    remaining = warehouses[1:].copy()
    
    while remaining:
        current = route[-1]
        best_next_index = None
        best_score = float('inf')
        
        for idx, warehouse in enumerate(remaining):
            distance = calculate_distance(
                current['lat'], current['lng'],
                warehouse['lat'], warehouse['lng']
            )
            
            if strategy == 'shortest':
                # Score is purely based on distance
                score = distance
            elif strategy == 'balanced':
                # Score considers both distance and load/unload balance
                # Example: prioritize warehouses with higher load and unload
                load_balance = (warehouse['load'] + warehouse['unload']) / 2
                # Adding a small epsilon to prevent division by zero
                score = distance / (load_balance + 0.1)
            elif strategy == 'efficient':
                # Score considers distance and processing time
                # Assume average speed of 40 km/h for time calculation
                average_speed = 40  # km/h
                travel_time = distance / average_speed  # hours
                processing_time = warehouse['processingTime'] / 60  # hours
                score = travel_time + processing_time
            else:
                # Default to 'shortest' if unknown strategy
                score = distance
            
            if score < best_score:
                best_score = score
                best_next_index = idx
        
        if best_next_index is not None:
            # Append the best next warehouse to the route
            route.append(remaining.pop(best_next_index))
        else:
            # If no best next found (which shouldn't happen), break the loop
            break
    
    return route

def fetch_route_coordinates(start: Dict, end: Dict, osrm_url: str = 'http://localhost:5000') -> List[Tuple[float, float]]:
    """
    Fetch the route coordinates between two points using the OSRM API.
    
    Args:
        start (Dict): Starting warehouse dictionary with 'lat' and 'lng'.
        end (Dict): Ending warehouse dictionary with 'lat' and 'lng'.
        osrm_url (str): Base URL of the OSRM server.
    
    Returns:
        List[Tuple[float, float]]: List of (lat, lng) tuples representing the route.
    """
    coordinates = []
    try:
        # Construct the OSRM API URL
        route_url = f"{osrm_url}/route/v1/driving/{start['lng']},{start['lat']};{end['lng']},{end['lat']}?overview=full&geometries=geojson"
        
        response = requests.get(route_url)
        response.raise_for_status()
        data = response.json()
        
        if data['code'] != 'Ok':
            print(f"OSRM Error: {data['message']}")
            return coordinates
        
        route = data['routes'][0]
        geometry = route['geometry']
        
        # Extract coordinates from GeoJSON
        coordinates = [(coord[1], coord[0]) for coord in geometry['coordinates']]
        
    except requests.exceptions.RequestException as e:
        print(f"Request Exception: {e}")
    except KeyError as e:
        print(f"Key Error: {e}")
    except Exception as e:
        print(f"Unexpected Error: {e}")
    
    return coordinates

def get_optimized_route_coordinates(warehouses: List[Dict], strategy: str = 'shortest', osrm_url: str = 'http://localhost:5000') -> List[Tuple[float, float]]:
    """
    Calculate the optimized route coordinates for the given warehouses based on the selected strategy.
    
    Args:
        warehouses (List[Dict]): List of warehouse dictionaries.
        strategy (str): Route optimization strategy ('shortest', 'balanced', 'efficient').
        osrm_url (str): Base URL of the OSRM server.
    
    Returns:
        List[Tuple[float, float]]: Consolidated list of (lat, lng) tuples representing the entire route.
    """
    optimized_order = calculate_route_order(warehouses, strategy)
    print(f"Optimized Order based on '{strategy}' strategy:")
    for idx, wh in enumerate(optimized_order):
        print(f"{idx + 1}. {wh['name']}")

    full_route = []
    
    for i in range(len(optimized_order) - 1):
        start = optimized_order[i]
        end = optimized_order[i + 1]
        print(f"\nFetching route from '{start['name']}' to '{end['name']}'...")
        segment = fetch_route_coordinates(start, end, osrm_url)
        if segment:
            if full_route:
                # Avoid duplicating the last point of the previous segment
                full_route.extend(segment[1:])
            else:
                full_route.extend(segment)
            print(f"Fetched {len(segment)} coordinates for this segment.")
        else:
            print(f"Failed to fetch route between '{start['name']}' and '{end['name']}'.")

    print(f"\nTotal route coordinates fetched: {len(full_route)}")
    return full_route

# Example Usage
if __name__ == "_main_":
    # Sample warehouse data
    warehouses = [
        { 
            'id': 'W1', 
            'name': 'Central Hub',
            'lat': 18.5204, 
            'lng': 73.8554,            
            'load': 15,
            'unload': 13,
            'processingTime': 30
        },
        { 
            'id': 'W2',
            'name': 'North Depot',
            'lat': 18.5303, 
            'lng': 73.9024,            
            'load': 21,
            'unload': 23,
            'processingTime': 25
        },
        { 
            'id': 'W3',
            'name': 'South Warehouse',
            'lat': 18.4947, 
            'lng': 73.8372,
            'load': 45,
            'unload': 53,
            'processingTime': 35
        }
    ]
    
    # Choose the strategy: 'shortest', 'balanced', 'efficient'
    strategy = 'shortest'
    
    # OSRM server URL
    osrm_url = 'http://localhost:5000'  # Change if OSRM is hosted elsewhere
    
    # Get the optimized route coordinates
    route_coordinates = get_optimized_route_coordinates(warehouses, strategy, osrm_url)
    
    # Print the route coordinates
    print("\nFinal Optimized Route Coordinates:")
    for coord in route_coordinates:
        print(coord)