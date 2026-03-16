# Geolocation Validation Architecture

## Overview

This document explains the geolocation validation implementation and standard practices for GPS coordinate validation in the Tulip Tea WMS system.

## Use Cases

### Use Case 1: GPS Coordinate Validation During Registration
**When**: Order booker registers a new shop or warehouse  
**What**: Frontend sends GPS coordinates from device  
**Validation**: 
- Validate GPS coordinates format and range (latitude: -90 to +90, longitude: -180 to +180)
- If user's current location is provided, validate user is within 100m of shop location
- Save validated coordinates to database

### Use Case 2: Visit Location Validation
**When**: Order booker or delivery man visits a shop/warehouse  
**What**: Frontend sends user's current GPS location  
**Validation**: 
- Get shop/warehouse GPS location from database
- Compare user's location with shop/warehouse location
- Validate user is within 100 meters of shop/warehouse location

## Standard Practice: Integrated Validation

**✅ RECOMMENDED APPROACH: Integrated Validation in Existing Endpoints**

Validation is **automatically performed** in the existing endpoints. This is the industry standard because:

1. **Security**: Cannot bypass validation - it's enforced at the API level
2. **Consistency**: All requests go through the same validation logic
3. **Simplicity**: Frontend doesn't need to make extra API calls
4. **Single Source of Truth**: Validation logic is centralized in one place
5. **Error Handling**: Consistent error responses across all endpoints

### Implementation

Validation is integrated into these endpoints:

#### 1. Shop Registration
- **Endpoint**: `POST /shops/order-booker/{order_booker_id}`
- **Validation**:
  - Validates GPS coordinates format/range before saving
  - If `user_gps_lat` and `user_gps_lng` provided, validates user is within 100m of shop location
- **Error Response**: `400 Bad Request` with validation message

#### 2. Shop Visit Registration
- **Endpoint**: `POST /shop-visits/order-booker/{order_booker_id}`
- **Validation**: 
  - Automatically validates visit GPS is within 100m of shop GPS (from database)
- **Error Response**: `400 Bad Request` with distance information

#### 3. Warehouse Creation (Future)
- **Endpoint**: `POST /warehouses/`
- **Note**: Warehouses currently don't have GPS coordinates in the model
- **When GPS is added**: Will validate coordinates format and user location

## API Endpoints with Validation

### Shop Registration Endpoint

**POST** `/shops/order-booker/{order_booker_id}`

**Request Body:**
```json
{
  "name": "Ali General Store",
  "owner_name": "Ahmed Ali",
  "owner_phone": "03001234567",
  "gps_lat": 33.6844,           // Shop location (required)
  "gps_lng": 73.0479,           // Shop location (required)
  "user_gps_lat": 33.6845,      // User's current location (optional, for validation)
  "user_gps_lng": 73.0480,      // User's current location (optional, for validation)
  "zone_id": 1,
  "credit_limit": 50000.00
}
```

**Validation Flow:**
1. ✅ Validates `gps_lat` and `gps_lng` format and range
2. ✅ If `user_gps_lat` and `user_gps_lng` provided, validates user is within 100m
3. ✅ Saves shop to database with validated GPS coordinates

**Success Response (201):**
```json
{
  "id": 1,
  "name": "Ali General Store",
  "gps_lat": 33.6844,
  "gps_lng": 73.0479,
  ...
}
```

**Error Response (400):**
```json
{
  "detail": "Invalid latitude: 95.0. Latitude must be between -90 and +90 degrees."
}
```
or
```json
{
  "detail": "Location too far: 0.15km (150m) from shop location (max allowed: 100m). Please ensure you are at the shop location when registering."
}
```

### Shop Visit Endpoint

**POST** `/shop-visits/order-booker/{order_booker_id}`

**Request Body:**
```json
{
  "shop_id": 1,
  "visit_types": ["order_booking"],
  "gps_lat": 33.6844,    // User's current location (required for validation)
  "gps_lng": 73.0479,   // User's current location (required for validation)
  "visit_time": "2026-01-07T10:30:00",
  "photo": "data:image/jpeg;base64,...",
  "reason": "Regular order booking visit"
}
```

**Validation Flow:**
1. ✅ Gets shop GPS coordinates from database
2. ✅ Validates user's visit GPS is within 100m of shop GPS
3. ✅ Creates visit record if validation passes

**Success Response (201):**
```json
{
  "id": 1,
  "shop_id": 1,
  "shop_name": "Ali General Store",
  "gps_lat": 33.6844,
  "gps_lng": 73.0479,
  ...
}
```

**Error Response (400):**
```json
{
  "detail": "Visit location too far: 0.15km (150m) from shop (max allowed: 100m). Please ensure you are at the shop location."
}
```

## Validation Thresholds

Thresholds are configured in `services/geolocation_service.py`:

```python
MAX_CREATION_DISTANCE_KM = 0.1  # 100 meters - for shop/warehouse creation
MAX_VISIT_DISTANCE_KM = 0.1     # 100 meters - for shop/warehouse visits
```

**To change thresholds**, edit these constants in `services/geolocation_service.py` (lines 24-25).

## Methods Available

### 1. `validate_coordinates(lat, lng)`
**Purpose**: Validate GPS coordinates format and range before saving to database  
**When**: Called automatically during shop/warehouse registration  
**Returns**: `(is_valid: bool, message: str)`

### 2. `validate_creation_location(target_lat, target_lng, user_lat, user_lng, entity_type)`
**Purpose**: Validate user is at location when creating shop/warehouse  
**When**: Called automatically if user GPS provided during registration  
**Returns**: `(is_valid: bool, distance_km: float, message: str)`

### 3. `validate_visit_location(target_lat, target_lng, visit_lat, visit_lng, entity_type)`
**Purpose**: Validate user is within 100m when visiting shop/warehouse  
**When**: Called automatically during visit registration  
**Returns**: `(is_valid: bool, distance_km: float, message: str)`

## Frontend Integration

### Shop Registration Example

```javascript
// Get user's current location
navigator.geolocation.getCurrentPosition(
  (position) => {
    const shopData = {
      name: "Ali General Store",
      owner_name: "Ahmed Ali",
      owner_phone: "03001234567",
      gps_lat: position.coords.latitude,      // Shop location from device
      gps_lng: position.coords.longitude,    // Shop location from device
      user_gps_lat: position.coords.latitude, // User's current location (same or different)
      user_gps_lng: position.coords.longitude, // User's current location
      zone_id: 1,
      credit_limit: 50000.00
    };
    
    fetch('/shops/order-booker/1', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(shopData)
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(err => {
          alert(err.detail); // Shows validation error
          throw new Error(err.detail);
        });
      }
      return response.json();
    })
    .then(data => {
      console.log('Shop registered:', data);
    })
    .catch(error => {
      console.error('Error:', error);
    });
  }
);
```

### Shop Visit Example

```javascript
// Get user's current location for visit
navigator.geolocation.getCurrentPosition(
  (position) => {
    const visitData = {
      shop_id: 1,
      visit_types: ["order_booking"],
      gps_lat: position.coords.latitude,   // User's current location
      gps_lng: position.coords.longitude,  // User's current location
      visit_time: new Date().toISOString(),
      reason: "Regular order booking visit"
    };
    
    fetch('/shop-visits/order-booker/1', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(visitData)
    })
    .then(response => {
      if (!response.ok) {
        return response.json().then(err => {
          alert(err.detail); // Shows distance validation error
          throw new Error(err.detail);
        });
      }
      return response.json();
    })
    .then(data => {
      console.log('Visit registered:', data);
    })
    .catch(error => {
      console.error('Error:', error);
    });
  }
);
```

## Why Not Separate Endpoints?

**❌ NOT RECOMMENDED: Separate Validation Endpoints**

While you *could* create separate endpoints like:
- `POST /validate/shop-location`
- `POST /validate/visit-location`

This approach has **disadvantages**:

1. **Security Risk**: Frontend could skip validation endpoint and call create endpoint directly
2. **Extra API Calls**: Frontend needs to make 2 API calls (validate + create)
3. **Race Conditions**: User could move between validation and creation
4. **Code Duplication**: Validation logic would need to be in both endpoints
5. **Inconsistency**: Some requests might bypass validation

## Optional: Pre-Validation Endpoint (UX Enhancement)

If you want to provide **better UX** (show validation before user submits), you can add an **optional** pre-validation endpoint:

**POST** `/validate/shop-location` (optional, for UX only)

This would:
- Check if coordinates are valid
- Check if user is within range
- Return validation result **without saving to database**

**BUT**: The main validation **must still happen** in the actual create endpoint to ensure security.

## Summary

✅ **Standard Practice**: Integrated validation in existing endpoints  
✅ **Automatic**: Validation happens automatically, cannot be bypassed  
✅ **Simple**: Frontend just calls existing endpoints with GPS data  
✅ **Secure**: All validation enforced at API level  
✅ **Consistent**: Same validation logic for all requests  

The implementation follows industry best practices for location validation in REST APIs.





