from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [

    path('login', views.login_view, name='login_view'),
    path('getAllUsers', views.get_all_users, name='get_all_users'),
    path('setWarehousePermission', views.set_warehouse_permissions, name='set_warehouse_permissions'),
    path('setCredentials', views.set_credentials, name='set_credentials'),
    

    path('positions', views.get_vehicle_positions, name='get_vehicle_positions'),
    # path('path', views.get_vehicle_path, name='get_vehicle_path'),
    path('geofences', views.geofences, name='geofences'),
    path('devices', views.get_devices, name='get_devices'),
    path('userDevices', views.get_user_devices, name='get_user_devices'),
    
    # path('geofences/<int:geofence_id>', views.geofence_detail, name='geofence_detail'),
    # path('devices/<int:device_id>/geofences', views.device_geofences, name='device_geofences'),
    
    # for Tracking page
    path('devices/<int:device_id>/route', views.get_truck_route, name='get_truck_route'),
    path('devices/<int:device_id>/manage-geofence', views.manage_truck_geofence, name='manage_truck_geofence'),
    path('devices/manage-all-geofence', views.manage_truck_geofence2, name='manage_truck_geofence2'),
    
    path('devices/new', views.create_traccar_device, name='create_traccar_device'),
    path('devices/geofences', views.get_truck_warehouses, name='get_truck_warehouses'),
    path('devices/assignRoute', views.update_truck_route, name='update_truck_route'),
    path('devices/assignWarehouses', views.assign_warehouses, name='assign_warehouses'),
    
    path('devices/getUniqueId', views.get_uniqueId, name='get_uniqueId'), # converts actual_id to uniqueId
    path('devices/getId', views.get_id, name='get_id'), # converts uniqueId to actual_id



    # for geofence events:        
    path('getAlerts', views.get_alerts),
    path('setAlerts', views.set_alerts),
    path('setCallAlerts', views.set_call_alerts),        
    # path('devices/manage-geofence', views.manage_truck_geofence, name='manage_truck_geofence'),

    # for trucks:    
    path('getIncomingTrucks', views.get_incoming_trucks), # used for getting all trucks of the warehouse 
    path('getIncomingLiveTrucks', views.get_incoming_live_trucks), # used for getting all trucks TRAVELLING TO the warehouse 
    path('getOutgoingTrucks',  views.get_outgoing_trucks),
    path('getTruckCapacity', views.get_truck_capacity),
    path('getTruckStatus', views.get_truck_status),
    path('getWarehouseNames', views.get_warehouse_names),
    path('getAllWarehouseNames', views.get_all_warehouses),
    path('getScheduledTrucks', views.get_scheduled_trucks),
    path('getAllTrucks', views.get_all_trucks),
    path('setEstimatedArrival', views.set_route_estimated_arrival),
    path('getAllDrivers', views.get_all_drivers),
    path('getAllMMS', views.get_all_mms),
    path('getAllNotifications', views.get_all_notifications),    
    path('createNotification', views.create_notification),
    path('setNotificationResolve', views.set_notification_resolve),
    path('getDrivers', views.get_drivers),
    path('getTruckLocation', views.get_truck_deliveries),
    
    # path('getTruckDriverInfo', views.get_truck_driver_info),
        
    # for 3 PL:
    path('3pl/availableTrucks', views.get_3pl_trucks, name='get_3pl_trucks'),
    path('3pl/bookParcel', views.book_3pl, name='book_3pl'),
    
    
    # for parcels page:
    path('getParcelInfo', views.get_parcel_info),    
    path('setParcelToBag', views.allocate_parcel_to_bag),
    path('setBagToTruck', views.allocate_bag_to_truck),    
    path('removeBagFromTruck', views.deallocate_bag_from_truck),    
    
    # for reports 
    path('getSystemReport', views.get_system_report),
    path('getTruckReport', views.get_truck_report),
    path('getRegionReport', views.get_region_report),
    path('getRouteReport', views.get_route_report),
    

    path('dynamicRoute', views.dynamicRoute),
    

    # for users:
    path('createNewUser', views.create_new_user),
    path('createToken', views.create_token),    
    path('getToken', views.get_token),


    # for demand prediction:
    # path('predict-monthly', monthly_prediction_view, name='predict-monthly')
    # path('predict-quarterly', quarterly_prediction_view,name='predict-quarterly')


    # helper function:
    path('generateParcels', views.generate_and_insert_parcels),

    # path('predict-monthly/', monthly_prediction_view, name='predict-monthly'),
    # path('predict-quarterly/', quarterly_prediction_view, name='predict-quarterly'),
]
