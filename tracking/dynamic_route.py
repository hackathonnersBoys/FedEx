import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import time

@dataclass
class ParcelOperation:
    load: float  # in tons
    unload: float  # in tons

@dataclass
class ThreePLRequest:
    source: str  # Point where 3PL wants to load
    destination: str  # Point where 3PL wants to unload
    volume: float  # in tons

class Point:
    def _init_(self, name: str, x: float, y: float, 
                 predetermined_ops: ParcelOperation,
                 potential_3pl_volume: float = 0):
        self.name = name
        self.x = x  # in km (relative to start)
        self.y = y  # in km (relative to start)
        self.predetermined_ops = predetermined_ops
        self.potential_3pl_volume = potential_3pl_volume  # in tons
        self.actual_3pl_volume = 0.0  # in tons
        self.actual_3pl_requests: List[ThreePLRequest] = []
    
    def distance_to(self, other: 'Point') -> float:
        return np.sqrt((self.x - other.x)*2 + (self.y - other.y)*2)
    
    def _repr_(self):
        return f"Point({self.name}, x={self.x}, y={self.y})"

class Truck:
    def _init_(self, total_capacity: float):  # capacity in tons
        self.total_capacity = total_capacity
        self.current_load = 0.0  # in tons
        self.load_history = []
    
    def can_accept_load(self, load_volume: float) -> bool:
        return self.current_load + load_volume <= self.total_capacity
    
    def get_available_capacity(self) -> float:
        return self.total_capacity - self.current_load
    
    def update_load(self, load_delta: float):
        self.current_load += load_delta
        self.load_history.append(self.current_load)
    
    def is_full(self) -> bool:
        return self.current_load >= self.total_capacity

class RouteOptimizer:
    def _init_(self, 
                 points: List[Point], 
                 truck: Truck,
                 distance_matrix: Dict[str, Dict[str, float]],
                 allocation_touch_points: List[str]):
        self.points = points
        self.truck = truck
        self.distance_matrix = distance_matrix
        self.allocation_touch_points = allocation_touch_points
        self.current_point = points[0]  # Start at the first point (Depot)
        self.remaining_points = points[1:]  # All points except the start
        self.route = [self.current_point]
        self.step_logs = []
        self.threepl_requests: List[ThreePLRequest] = []  # Predefined 3PL requests

    def log_step(self, step_type: str, details: Dict):
        step = {
            'type': step_type,
            'current_point': self.current_point.name,
            'truck_load': self.truck.current_load,
            'available_capacity': self.truck.get_available_capacity(),
            'timestamp': time.strftime('%H:%M:%S'),
            'details': details
        }
        self.step_logs.append(step)
    
    def add_threepl_request(self, request: ThreePLRequest):
        self.threepl_requests.append(request)
    
    def notify_threepl(self, point: Point):
        available_space = self.truck.get_available_capacity()
        if available_space <= 0:
            return  # No space available
        
        # Find 3PL requests that want to load at this point and have destinations on the route
        eligible_requests = [req for req in self.threepl_requests 
                             if req.source == point.name and 
                             req.destination in [p.name for p in self.points]]
        
        for req in eligible_requests:
            if req.volume <= available_space and req.destination in self.allocation_touch_points:
                # Allocate space
                point.actual_3pl_volume += req.volume
                self.truck.update_load(req.volume)
                # Assign the request
                point.actual_3pl_requests.append(req)
                # Remove the request from pending
                self.threepl_requests.remove(req)
                print(f"3PL Booking: Allocated {req.volume} tons from {req.source} to {req.destination}.")
                # Log the allocation
                self.log_step("3PL_ALLOCATION", {
                    'allocated_volume': req.volume,
                    'source': req.source,
                    'destination': req.destination
                })
                # Update available space
                available_space -= req.volume
                if available_space <= 0:
                    break  # No more space

    def process_point_operations(self, point: Point):
        operations_details = {}
        
        # Handle unload operations
        if point.predetermined_ops.unload > 0:
            print(f"\nDestination {point.name} requires unloading {point.predetermined_ops.unload} tons.")
            if self.truck.current_load >= point.predetermined_ops.unload:
                self.truck.update_load(-point.predetermined_ops.unload)
                print(f"Unloaded {point.predetermined_ops.unload} tons. Current Load: {self.truck.current_load} tons.")
                operations_details['unloaded_weight'] = point.predetermined_ops.unload
            else:
                print(f"Error: Not enough load to unload at {point.name}.")
                operations_details['unloaded_weight'] = 0.0
        else:
            operations_details['unloaded_weight'] = 0.0
        
        # Handle load operations
        if point.predetermined_ops.load > 0:
            load_amount = point.predetermined_ops.load
            available_space = self.truck.get_available_capacity()
            max_load = min(load_amount, available_space)
            print(f"\nDestination {point.name} requires loading up to {load_amount} tons.")
            print(f"Available Space: {available_space} tons.")
            print(f"Maximum you can load here: {max_load} tons.")
            
            if max_load > 0:
                self.truck.update_load(max_load)
                print(f"Loaded {max_load} tons. Current Load: {self.truck.current_load} tons.")
                operations_details['loaded_weight'] = max_load
            else:
                print(f"Cannot load at {point.name}; Truck is full.")
                operations_details['loaded_weight'] = 0.0
        else:
            operations_details['loaded_weight'] = 0.0
        
        # Handle 3PL allocation
        self.notify_threepl(point)
        
        return operations_details

    def get_next_destination(self) -> Optional[Tuple[Point, Dict]]:
        """
        Select the next destination based on unloading priority and proximity for loading.
        """
        # Get connected points from current location using distance_matrix
        connected_point_names = self.distance_matrix.get(self.current_point.name, {})
        connected_points = [p for p in self.remaining_points if p.name in connected_point_names]
        
        if not connected_points:
            return None
        
        # Prioritize unload points with higher unload volume
        unload_points = [p for p in connected_points if p.predetermined_ops.unload > 0]
        if unload_points:
            # Select the unload point with the highest unload volume
            unload_points_sorted = sorted(unload_points, key=lambda p: p.predetermined_ops.unload, reverse=True)
            next_point = unload_points_sorted[0]
            decision_info = {'reason': 'Highest unload volume'}
            return next_point, decision_info
        
        # If no unload points, consider load points based on proximity and available capacity
        load_points = [p for p in connected_points if p.predetermined_ops.load > 0]
        if load_points and not self.truck.is_full():
            # Sort load points by distance from current
            load_points_sorted = sorted(load_points, key=lambda p: self.current_point.distance_to(p))
            next_point = load_points_sorted[0]
            decision_info = {'reason': 'Nearest load point'}
            return next_point, decision_info
        
        # If no feasible points
        return None

    def optimize_route(self) -> List[Point]:
        while self.remaining_points:
            next_destination = self.get_next_destination()
            if not next_destination:
                print("\nNo more feasible destinations to visit.")
                break
            
            next_point, decision_info = next_destination
            
            # Process operations at current point
            operations = self.process_point_operations(self.current_point)
            
            # Log the step
            self.log_step("POINT_OPERATIONS", {
                'location': self.current_point.name,
                'operations': operations,
                'next_point': next_point.name,
                'distance_to_next': self.current_point.distance_to(next_point),
                'selection_reason': decision_info['reason']
            })
            
            # Move to next point
            self.route.append(next_point)
            self.remaining_points.remove(next_point)
            previous_point = self.current_point
            self.current_point = next_point
            
            # Print detailed step information
            print(f"\nMoved to {next_point.name} based on {decision_info['reason']}.")
            distance_traveled = previous_point.distance_to(next_point)
            print(f"Distance traveled: {distance_traveled:.2f} km.")
        
        return self.route

def generate_realistic_scenario() -> Tuple[List[Point], Truck, Dict[str, Dict[str, float]]]:
    # Define the distance matrix
    distance_matrix = {
        "A": {"B": 10, "C": 50},
        "B": {"C": 20},
        "C": {"E": 10},
        "E": {"D": 10},
        "D": {"E": 20},
        # Other routes are not directly reachable
    }
    
    # Initialize ParcelOperations for each point
    parcel_operations = {
        "A": ParcelOperation(load=0.0, unload=0.0),
        "B": ParcelOperation(load=0.0, unload=10.0),
        "C": ParcelOperation(load=50.0, unload=0.0),
        "E": ParcelOperation(load=5.0, unload=0.0),
        "D": ParcelOperation(load=0.0, unload=20.0)
    }
    
    # Initialize Points
    points = [
        Point("A", 0, 0, parcel_operations["A"], potential_3pl_volume=0.0),
        Point("B", 10, 0, parcel_operations["B"], potential_3pl_volume=0.0),
        Point("C", 30, 0, parcel_operations["C"], potential_3pl_volume=0.0),
        Point("E", 40, 0, parcel_operations["E"], potential_3pl_volume=0.0),
        Point("D", 50, 0, parcel_operations["D"], potential_3pl_volume=0.0)
    ]
    
    # Initialize Truck
    truck = Truck(total_capacity=100.0)
    truck.update_load(100.0)  # Starting with full load
    
    return points, truck, distance_matrix

def main():
    # Generate scenario
    points, truck, distance_matrix = generate_realistic_scenario()
    
    # Define allocation touch points where 3PL can allocate
    allocation_touch_points = ["C", "E"]  # Example touch points
    
    # Display initial information
    print("List of Points and Their Operations:")
    print("-------------------------------------")
    for point in points:
        print(f"Point {point.name}:")
        print(f"  Coordinates: ({point.x}, {point.y}) km")
        print(f"  Load: {point.predetermined_ops.load} tons")
        print(f"  Unload: {point.predetermined_ops.unload} tons")
        print(f"  Potential 3PL Volume: {point.potential_3pl_volume} tons\n")
    
    # Initialize RouteOptimizer
    optimizer = RouteOptimizer(
        points=points,
        truck=truck,
        distance_matrix=distance_matrix,
        allocation_touch_points=allocation_touch_points
    )
    
    # Example 3PL Requests
    # In a real-world scenario, these could come from a database or an API
    # Here, we're adding them manually for demonstration
    optimizer.add_threepl_request(ThreePLRequest(source="C", destination="E", volume=10.0))
    optimizer.add_threepl_request(ThreePLRequest(source="E", destination="D", volume=5.0))
    
    # Optimize route
    print("Starting Route Optimization...\n")
    optimized_route = optimizer.optimize_route()
    
    # Calculate total distance
    total_distance = 0.0
    for i in range(len(optimized_route)-1):
        current = optimized_route[i]
        next_point = optimized_route[i+1]
        distance = current.distance_to(next_point)
        total_distance += distance
    
    # Print step-by-step logs
    print("\nStep-by-Step Logs:")
    print("-------------------")
    for idx, log in enumerate(optimizer.step_logs):
        print(f"\nStep {idx + 1}:")
        print(f"Timestamp: {log['timestamp']}")
        print(f"Current Location: {log['current_point']}")
        print(f"Truck Load: {log['truck_load']} tons")
        print(f"Available Capacity: {log['available_capacity']} tons")
        print("Operations:")
        print(f"  Unloaded: {log['details']['operations']['unloaded_weight']} tons")
        print(f"  Loaded: {log['details']['operations']['loaded_weight']} tons")
        if '3pl_allocation_weight' in log['details']['operations']:
            print(f"  3PL Allocation: {log['details']['operations']['3pl_allocation_weight']} tons "
                  f"from {log['details']['operations'].get('source', 'N/A')} "
                  f"to {log['details']['operations'].get('destination', 'N/A')}")
        if 'next_point' in log['details']:
            print(f"Next Destination: {log['details']['next_point']}")
            print(f"Distance to Next: {log['details']['distance_to_next']} km")
            print(f"Selection Reason: {log['details']['selection_reason']}")
    
    # Print final route summary
    print("\nFinal Route Summary:")
    print("---------------------")
    print(f"Optimized Route: {' -> '.join([p.name for p in optimized_route])}")
    print(f"Total Distance Traveled: {round(total_distance, 2)} km")
    print(f"Final Truck Load: {optimizer.truck.current_load} tons")

if _name_ == "_main_":
    main()