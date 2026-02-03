"""
Geolocation Service using Geopy
=================================
Handles distance calculations and proximity validation for location-based operations.

This service uses the geopy library to:
- Validate GPS coordinates format and range before saving to database
- Calculate distances between GPS coordinates
- Validate that users are at the correct location when creating shops/warehouses
- Validate that users are at the correct location when visiting shops/warehouses

USAGE:
1. validate_coordinates() - Validate GPS coordinates format/range before saving
2. validate_creation_location() - Use when creating/registering a shop or warehouse
3. validate_visit_location() - Use when visiting a shop or warehouse
"""
from geopy.distance import geodesic
from typing import Tuple
from decimal import Decimal


class GeolocationService:
    """Service for geolocation operations using geopy."""
    
    # Distance thresholds in kilometers
    MAX_CREATION_DISTANCE_KM = 0.1  # 100 meters - max distance when creating shop/warehouse
    MAX_VISIT_DISTANCE_KM = 0.1  # 100 meters - max distance for valid shop/warehouse visit
    
    # GPS coordinate valid ranges
    MIN_LATITUDE = -90.0
    MAX_LATITUDE = 90.0
    MIN_LONGITUDE = -180.0
    MAX_LONGITUDE = 180.0
    
    @staticmethod
    def validate_coordinates(lat: float, lng: float) -> Tuple[bool, str]:
        """
        Validate GPS coordinates format and range before saving to database.
        
        This ensures coordinates are in valid format and within acceptable ranges:
        - Latitude: -90 to +90
        - Longitude: -180 to +180
        
        Args:
            lat: Latitude coordinate (float)
            lng: Longitude coordinate (float)
        
        Returns:
            Tuple of (is_valid, message)
            - is_valid: True if coordinates are valid
            - message: Human-readable validation message
        
        Example:
            >>> is_valid, msg = GeolocationService.validate_coordinates(33.6844, 73.0479)
            >>> if not is_valid:
            ...     raise ValueError(msg)
        """
        # Check if coordinates are provided
        if lat is None or lng is None:
            return False, "GPS coordinates are required. Both latitude and longitude must be provided."
        
        # Check if coordinates are numbers
        try:
            lat_float = float(lat)
            lng_float = float(lng)
        except (TypeError, ValueError):
            return False, "Invalid GPS coordinate format. Coordinates must be numeric values."
        
        # Validate latitude range (-90 to +90)
        if lat_float < GeolocationService.MIN_LATITUDE or lat_float > GeolocationService.MAX_LATITUDE:
            return False, f"Invalid latitude: {lat_float}. Latitude must be between -90 and +90 degrees."
        
        # Validate longitude range (-180 to +180)
        if lng_float < GeolocationService.MIN_LONGITUDE or lng_float > GeolocationService.MAX_LONGITUDE:
            return False, f"Invalid longitude: {lng_float}. Longitude must be between -180 and +180 degrees."
        
        return True, f"GPS coordinates validated: ({lat_float}, {lng_float})"
    
    @staticmethod
    def _calculate_distance(
        lat1: float, lng1: float,
        lat2: float, lng2: float
    ) -> float:
        """
        Calculate distance between two GPS coordinates in kilometers.
        
        Uses geodesic distance (accounts for Earth's curvature) which is accurate
        for any two points on Earth.
        
        Args:
            lat1, lng1: First point coordinates (latitude, longitude)
            lat2, lng2: Second point coordinates (latitude, longitude)
        
        Returns:
            Distance in kilometers (float)
        """
        point1 = (lat1, lng1)
        point2 = (lat2, lng2)
        return geodesic(point1, point2).kilometers
    
    @staticmethod
    def validate_creation_location(
        target_lat: Decimal, target_lng: Decimal,
        user_lat: Decimal, user_lng: Decimal,
        max_distance_km: float = None,
        entity_type: str = "location"
    ) -> Tuple[bool, float, str]:
        """
        Validate that user is at the target location when creating/registering a shop or warehouse.
        
        This is a generic method that can be used for:
        - Shop registration (validates order booker is at shop location)
        - Warehouse creation (validates user is at warehouse location)
        - Any other entity creation that requires location validation
        
        Args:
            target_lat, target_lng: Target location GPS coordinates being registered (Decimal)
            user_lat, user_lng: User's current GPS coordinates from device (Decimal)
            max_distance_km: Maximum allowed distance in kilometers (default: MAX_CREATION_DISTANCE_KM)
            entity_type: Type of entity being created (e.g., "shop", "warehouse") for error messages
        
        Returns:
            Tuple of (is_valid, distance_km, message)
            - is_valid: True if user is within allowed distance of target location
            - distance_km: Calculated distance in kilometers
            - message: Human-readable validation message
        
        Example:
            >>> # For shop registration
            >>> is_valid, distance, msg = GeolocationService.validate_creation_location(
            ...     Decimal('33.6844'), Decimal('73.0479'),  # Shop location
            ...     Decimal('33.6845'), Decimal('73.0480'),  # User location
            ...     entity_type="shop"
            ... )
            >>> if not is_valid:
            ...     raise ValueError(msg)
            
            >>> # For warehouse creation
            >>> is_valid, distance, msg = GeolocationService.validate_creation_location(
            ...     Decimal('33.6844'), Decimal('73.0479'),  # Warehouse location
            ...     Decimal('33.6845'), Decimal('73.0480'),  # User location
            ...     entity_type="warehouse"
            ... )
        """
        if max_distance_km is None:
            max_distance_km = GeolocationService.MAX_CREATION_DISTANCE_KM
        
        # Check if coordinates are provided
        if not all([target_lat, target_lng, user_lat, user_lng]):
            return False, 0.0, f"GPS coordinates are missing. Please ensure {entity_type} location and your current location are provided."
        
        # Convert Decimal to float for geopy
        try:
            target_lat_float = float(target_lat)
            target_lng_float = float(target_lng)
            user_lat_float = float(user_lat)
            user_lng_float = float(user_lng)
        except (TypeError, ValueError) as e:
            return False, 0.0, f"Invalid GPS coordinate format: {str(e)}"
        
        # Calculate distance
        distance_km = GeolocationService._calculate_distance(
            target_lat_float, target_lng_float,
            user_lat_float, user_lng_float
        )
        
        # Validate distance
        is_valid = distance_km <= max_distance_km
        
        if is_valid:
            message = f"Location validated: {distance_km:.2f}km from {entity_type} location (max allowed: {max_distance_km}km)"
        else:
            message = f"Location too far: {distance_km:.2f}km from {entity_type} location (max allowed: {max_distance_km}km). Please ensure you are at the {entity_type} location when registering."
        
        return is_valid, distance_km, message
    
    @staticmethod
    def validate_visit_location(
        target_lat: Decimal, target_lng: Decimal,
        visit_lat: Decimal, visit_lng: Decimal,
        max_distance_km: float = None,
        entity_type: str = "shop"
    ) -> Tuple[bool, float, str]:
        """
        Validate that visit location is within acceptable distance of the target location.
        
        This ensures that order bookers/delivery men are actually at the shop/warehouse location
        when registering a visit, preventing fraudulent or inaccurate visit records.
        
        This is a generic method that can be used for:
        - Shop visits (validates visit GPS vs shop GPS)
        - Warehouse visits (validates visit GPS vs warehouse GPS)
        - Any other visit/check-in operations
        
        Args:
            target_lat, target_lng: Target location's registered GPS coordinates from database (Decimal)
            visit_lat, visit_lng: Visit GPS coordinates from user's device (Decimal)
            max_distance_km: Maximum allowed distance in kilometers (default: MAX_VISIT_DISTANCE_KM = 100m)
            entity_type: Type of entity being visited (e.g., "shop", "warehouse") for error messages
        
        Returns:
            Tuple of (is_valid, distance_km, message)
            - is_valid: True if visit is within allowed distance (100m)
            - distance_km: Calculated distance in kilometers
            - message: Human-readable validation message
        
        Example:
            >>> # For shop visit
            >>> is_valid, distance, msg = GeolocationService.validate_visit_location(
            ...     Decimal('33.6844'), Decimal('73.0479'),  # Shop location from database
            ...     Decimal('33.6845'), Decimal('73.0480'),  # Visit location from device
            ...     entity_type="shop"
            ... )
            >>> if not is_valid:
            ...     raise ValueError(msg)
            
            >>> # For warehouse visit
            >>> is_valid, distance, msg = GeolocationService.validate_visit_location(
            ...     Decimal('33.6844'), Decimal('73.0479'),  # Warehouse location from database
            ...     Decimal('33.6845'), Decimal('73.0480'),  # Visit location from device
            ...     entity_type="warehouse"
            ... )
        """
        if max_distance_km is None:
            max_distance_km = GeolocationService.MAX_VISIT_DISTANCE_KM
        
        # Check if coordinates are provided
        if not all([target_lat, target_lng, visit_lat, visit_lng]):
            return False, 0.0, f"GPS coordinates are missing. Please ensure {entity_type} location and visit location are provided."
        
        # Convert Decimal to float for geopy
        try:
            target_lat_float = float(target_lat)
            target_lng_float = float(target_lng)
            visit_lat_float = float(visit_lat)
            visit_lng_float = float(visit_lng)
        except (TypeError, ValueError) as e:
            return False, 0.0, f"Invalid GPS coordinate format: {str(e)}"
        
        # Calculate distance
        distance_km = GeolocationService._calculate_distance(
            target_lat_float, target_lng_float,
            visit_lat_float, visit_lng_float
        )
        
        # Validate distance (100 meters = 0.1 km)
        is_valid = distance_km <= max_distance_km
        
        if is_valid:
            message = f"Visit location validated: {distance_km:.2f}km ({distance_km * 1000:.0f}m) from {entity_type} (max allowed: {max_distance_km * 1000:.0f}m)"
        else:
            message = f"Visit location too far: {distance_km:.2f}km ({distance_km * 1000:.0f}m) from {entity_type} (max allowed: {max_distance_km * 1000:.0f}m). Please ensure you are at the {entity_type} location."
        
        return is_valid, distance_km, message

