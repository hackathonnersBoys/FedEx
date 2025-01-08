from django.db import models
import json
from django.utils import timezone

class Users(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    truck_access = models.TextField(null=True)
    warehouse_access = models.TextField(null=True)

class Truck(models.Model):
    truck_id = models.CharField(max_length=100, unique=True)
    actual_id = models.IntegerField(default=-1)
    mms_allocated_id = models.CharField(max_length=100, default='Not Assigned')  # Default value for MMS allocated ID
    driver_id = models.IntegerField(null=True, blank=True)  # Default null for driver if none assigned
    name = models.CharField(max_length=100, default='')
    truck_status = models.CharField(max_length=50,default='')
    filled_capacity = models.FloatField(default=0.0)  # Default value for filled capacity
    threshold_volume = models.FloatField(default=0.0)  # Default value for threshold volume
    max_volume = models.FloatField(default=0.0)  # Default value for max volume
    max_weight = models.FloatField(default=0.0)  # Default value for max weight
    current_volume = models.FloatField(default=0.0)  # Default value for current volume
    current_weight = models.FloatField(default=0.0)  # Default value for current weight
    route = models.TextField(default='')  # New field to store route as a comma-separated string
    route_estimated_arrival = models.TextField(default='')  # New field to store route as a comma-separated string
    route_estimated_departure = models.TextField(default='')  # New field to store route as a comma-separated string
    current_location = models.IntegerField(default=0)
    current_destination = models.IntegerField(default=0)
    live_status = models.CharField(max_length=100, default='')
    is_at_warehouse = models.BooleanField(default=0)
    is_on_route = models.BooleanField(default=1)
    issues = models.CharField(max_length=100, default='')
    
    
    def __str__(self):
        return self.truck_id

class Warehouse(models.Model):
    geofence_id = models.IntegerField(null=True)  # Store Traccar geofence ID
    load = models.IntegerField(default=0)
    unload = models.IntegerField(default=0)

    def __str__(self):
        return f"Warehouse {self.geofence_id} (Load: {self.load}, Unload: {self.unload})"
    

class Truck_log(models.Model):
    truck_id = models.CharField(max_length=100)
    actual_id = models.IntegerField(default=-1)
    event_type = models.CharField(default='', max_length=100)
    current_location = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.truck_id

class Truck_capacity_log(models.Model):
    truck_id = models.CharField(max_length=100)
    actual_id = models.IntegerField(default=-1)
    current_location = models.IntegerField(default=0)
    filled_capacity = models.FloatField(default=0.0)  # Default value for filled capacity
    timestamp = models.DateTimeField(auto_now_add=True, null=True)
    def __str__(self):
        return self.truck_id


class Notifications(models.Model):
    truck_id = models.CharField(max_length=100)
    notification_type = models.CharField(max_length=100, default='')
    geofence_id = models.IntegerField(null=True)
    is_on_route = models.BooleanField(default=1)
    is_resolved = models.BooleanField(default=0)


class Truck_issue_log(models.Model):
    truck_id = models.CharField(max_length=100)
    actual_id = models.IntegerField(default=-1)
    issues = models.CharField(max_length=100, default='')
    timestamp = models.DateTimeField(auto_now_add=True, null=True)

class Truck_live_status_log(models.Model):
    truck_id = models.CharField(max_length=100)
    actual_id = models.IntegerField(default=-1)
    live_status = models.CharField(max_length=100, default='')
    timestamp = models.DateTimeField(auto_now_add=True, null=True)

class MMS(models.Model):
    mms_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255, default='')  
    dedicated_phone_numbers = models.TextField(default='') 

    def __str__(self):
        return self.mms_id


class MMS_call_log(models.Model):
    truck_id = models.CharField(max_length=100)
    actual_id = models.IntegerField(default=-1)
    mms_id = models.CharField(max_length=100)
    issues = models.CharField(max_length=100, default='')

    def __str__(self):
        return self.mms_id


class Parcel(models.Model):
    tracking_id = models.CharField(max_length=100, unique=True)    
    weight = models.FloatField(default=0.0)  # Default value for parcel weight
    volume = models.FloatField(default=0.0)  # Default value for parcel volume
    destination = models.IntegerField(default=0)
    bag_id = models.IntegerField(default=0, null=True)
    current_location = models.IntegerField(default=0)
    current_destination = models.IntegerField(default=0)
    is_delivered = models.BooleanField(default=0)
    def __str__(self):
        return self.tracking_id 

class Parcel_log(models.Model):
    tracking_id = models.CharField(max_length=100)
    current_location = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True, null=True)    
    def __str__(self):
        return self.tracking_id 

class Bag(models.Model):
    bag_id = models.IntegerField(unique=True)
    truck_id = truck_id = models.CharField(max_length=100, null=True)  
    destination = models.IntegerField(default=0)
    current_location = models.IntegerField(default=0)
    current_destination = models.IntegerField(default=0)
    weight = models.FloatField(default=0.0)  # Default value for bag weight
    volume = models.FloatField(default=0.0)  # Default value for bag volume
    def __str__(self):
        return self.bag_id

class Driver(models.Model):
    truck_id = models.CharField(max_length=100, null=True)
    name = models.CharField(max_length=255, default='Unknown')  # Default value for driver name
    phone_number = models.BigIntegerField(default=0)
    def __str__(self):
        return self.driver_name


class ThirdPartyLogistics(models.Model):
    tracking_id = models.CharField(max_length=100)
    truck_id = truck_id = models.CharField(max_length=100, null=True)  

    def __str__(self):
        return f"3PL for {self.tracking_id}"



