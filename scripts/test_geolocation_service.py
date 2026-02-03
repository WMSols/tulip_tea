"""
Test Script for Geolocation Service
=====================================
Interactive test script for geolocation validation.

This script allows you to:
1. Calculate distance between two GPS coordinates
2. Test creation location validation (shop/warehouse registration)
3. Test visit location validation (shop/warehouse visits)

Usage:
    python scripts/test_geolocation_service.py
"""
import sys
import os

# Add parent directory to path to import services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from decimal import Decimal
from services.geolocation_service import GeolocationService


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def calculate_distance_between_coordinates():
    """Calculate distance between two GPS coordinates."""
    print_header("DISTANCE CALCULATOR")
    
    print("\nEnter two GPS coordinates to calculate the distance between them.")
    print("Example: 33.6844, 73.0479 (Islamabad)")
    
    try:
        # Get first coordinate
        print("\n📍 First Location:")
        lat1_input = input("  Latitude:  ").strip()
        lng1_input = input("  Longitude: ").strip()
        
        lat1 = float(lat1_input)
        lng1 = float(lng1_input)
        
        # Get second coordinate
        print("\n📍 Second Location:")
        lat2_input = input("  Latitude:  ").strip()
        lng2_input = input("  Longitude: ").strip()
        
        lat2 = float(lat2_input)
        lng2 = float(lng2_input)
        
        # Validate coordinates
        is_valid1, msg1 = GeolocationService.validate_coordinates(lat1, lng1)
        is_valid2, msg2 = GeolocationService.validate_coordinates(lat2, lng2)
        
        if not is_valid1:
            print(f"\n❌ Invalid first coordinate: {msg1}")
            return
        
        if not is_valid2:
            print(f"\n❌ Invalid second coordinate: {msg2}")
            return
        
        # Calculate distance
        distance_km = GeolocationService._calculate_distance(lat1, lng1, lat2, lng2)
        distance_m = distance_km * 1000
        
        # Display result
        print("\n" + "-" * 70)
        print("  DISTANCE RESULT")
        print("-" * 70)
        print(f"\n📍 Location 1: ({lat1}, {lng1})")
        print(f"📍 Location 2: ({lat2}, {lng2})")
        print(f"\n📏 Distance: {distance_km:.4f} km ({distance_m:.2f} meters)")
        
        # Show validation status
        print("\n" + "-" * 70)
        print("  VALIDATION STATUS")
        print("-" * 70)
        
        # Check if within creation threshold (100m)
        within_creation = distance_km <= GeolocationService.MAX_CREATION_DISTANCE_KM
        print(f"\n✅ Creation Validation (100m): {'PASS' if within_creation else 'FAIL'}")
        if within_creation:
            print(f"   ✓ Locations are within {GeolocationService.MAX_CREATION_DISTANCE_KM * 1000:.0f}m")
        else:
            print(f"   ✗ Locations are {distance_m:.0f}m apart (max: {GeolocationService.MAX_CREATION_DISTANCE_KM * 1000:.0f}m)")
        
        # Check if within visit threshold (100m)
        within_visit = distance_km <= GeolocationService.MAX_VISIT_DISTANCE_KM
        print(f"\n✅ Visit Validation (100m): {'PASS' if within_visit else 'FAIL'}")
        if within_visit:
            print(f"   ✓ Locations are within {GeolocationService.MAX_VISIT_DISTANCE_KM * 1000:.0f}m")
        else:
            print(f"   ✗ Locations are {distance_m:.0f}m apart (max: {GeolocationService.MAX_VISIT_DISTANCE_KM * 1000:.0f}m)")
        
    except ValueError as e:
        print(f"\n❌ Error: Invalid input. Please enter numeric values.")
        print(f"   Details: {str(e)}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


def test_creation_validation():
    """Test validate_creation_location() method."""
    print_header("TEST 1: Shop/Warehouse Creation Location Validation")
    
    # Test Case 1: Valid shop registration (user very close to shop)
    print("\n--- Test Case 1: Valid Shop Registration (User at Shop Location) ---")
    shop_lat = Decimal('33.6844')  # Islamabad coordinates
    shop_lng = Decimal('73.0479')
    user_lat = Decimal('33.6845')  # Very close (about 100m away)
    user_lng = Decimal('73.0480')
    
    is_valid, distance_km, message = GeolocationService.validate_creation_location(
        target_lat=shop_lat,
        target_lng=shop_lng,
        user_lat=user_lat,
        user_lng=user_lng,
        entity_type="shop"
    )
    print(f"\n{'✅ PASS' if is_valid else '❌ FAIL'} - Shop Registration - Close Location")
    print(f"   Distance: {distance_km:.4f} km ({distance_km * 1000:.2f} meters)")
    print(f"   Message: {message}")
    
    # Test Case 2: Invalid shop registration (user too far from shop)
    print("\n--- Test Case 2: Invalid Shop Registration (User Too Far) ---")
    shop_lat = Decimal('33.6844')
    shop_lng = Decimal('73.0479')
    user_lat = Decimal('33.6900')  # About 600m away (exceeds 100m limit)
    user_lng = Decimal('73.0500')
    
    is_valid, distance_km, message = GeolocationService.validate_creation_location(
        target_lat=shop_lat,
        target_lng=shop_lng,
        user_lat=user_lat,
        user_lng=user_lng,
        entity_type="shop"
    )
    print(f"\n{'✅ PASS' if is_valid else '❌ FAIL'} - Shop Registration - Far Location")
    print(f"   Distance: {distance_km:.4f} km ({distance_km * 1000:.2f} meters)")
    print(f"   Message: {message}")


def test_visit_validation():
    """Test validate_visit_location() method."""
    print_header("TEST 2: Shop Visit Location Validation")
    
    # Test Case 1: Valid visit (order booker at shop)
    print("\n--- Test Case 1: Valid Shop Visit (Order Booker at Shop) ---")
    shop_lat = Decimal('33.6844')
    shop_lng = Decimal('73.0479')
    visit_lat = Decimal('33.6845')  # About 100m from shop (within 100m limit)
    visit_lng = Decimal('73.0480')
    
    is_valid, distance_km, message = GeolocationService.validate_visit_location(
        target_lat=shop_lat,
        target_lng=shop_lng,
        visit_lat=visit_lat,
        visit_lng=visit_lng,
        entity_type="shop"
    )
    print(f"\n{'✅ PASS' if is_valid else '❌ FAIL'} - Shop Visit - Close Location")
    print(f"   Distance: {distance_km:.4f} km ({distance_km * 1000:.2f} meters)")
    print(f"   Message: {message}")
    
    # Test Case 2: Invalid visit (order booker too far from shop)
    print("\n--- Test Case 2: Invalid Shop Visit (Order Booker Too Far) ---")
    shop_lat = Decimal('33.6844')
    shop_lng = Decimal('73.0479')
    visit_lat = Decimal('33.6900')  # About 600m away (exceeds 100m limit)
    visit_lng = Decimal('73.0550')
    
    is_valid, distance_km, message = GeolocationService.validate_visit_location(
        target_lat=shop_lat,
        target_lng=shop_lng,
        visit_lat=visit_lat,
        visit_lng=visit_lng,
        entity_type="shop"
    )
    print(f"\n{'✅ PASS' if is_valid else '❌ FAIL'} - Shop Visit - Far Location")
    print(f"   Distance: {distance_km:.4f} km ({distance_km * 1000:.2f} meters)")
    print(f"   Message: {message}")
    
    # Test Case 3: Visit at exact shop location
    print("\n--- Test Case 3: Visit at Exact Shop Location ---")
    shop_lat = Decimal('33.6844')
    shop_lng = Decimal('73.0479')
    visit_lat = Decimal('33.6844')  # Exact same location
    visit_lng = Decimal('73.0479')
    
    is_valid, distance_km, message = GeolocationService.validate_visit_location(
        target_lat=shop_lat,
        target_lng=shop_lng,
        visit_lat=visit_lat,
        visit_lng=visit_lng,
        entity_type="shop"
    )
    print(f"\n{'✅ PASS' if is_valid else '❌ FAIL'} - Shop Visit - Exact Location")
    print(f"   Distance: {distance_km:.4f} km ({distance_km * 1000:.2f} meters)")
    print(f"   Message: {message}")


def test_real_world_scenarios():
    """Test with real-world scenarios using actual Pakistan coordinates."""
    print_header("TEST 3: Real-World Scenarios (Pakistan Locations)")
    
    # Scenario 1: Shop in Islamabad, order booker nearby
    print("\n--- Scenario 1: Shop in Islamabad, Order Booker Nearby ---")
    shop_lat = Decimal('33.6844')  # Islamabad
    shop_lng = Decimal('73.0479')
    user_lat = Decimal('33.6844')  # Same location
    user_lng = Decimal('73.0479')
    
    is_valid, distance_km, message = GeolocationService.validate_creation_location(
        target_lat=shop_lat,
        target_lng=shop_lng,
        user_lat=user_lat,
        user_lng=user_lng,
        entity_type="shop"
    )
    print(f"\n{'✅ PASS' if is_valid else '❌ FAIL'} - Islamabad Shop Registration")
    print(f"   Distance: {distance_km:.4f} km ({distance_km * 1000:.2f} meters)")
    print(f"   Message: {message}")
    
    # Scenario 2: Shop in Lahore, visit from nearby
    print("\n--- Scenario 2: Shop in Lahore, Visit from Nearby ---")
    shop_lat = Decimal('31.5204')  # Lahore
    shop_lng = Decimal('74.3587')
    visit_lat = Decimal('31.5210')  # About 70m away
    visit_lng = Decimal('74.3590')
    
    is_valid, distance_km, message = GeolocationService.validate_visit_location(
        target_lat=shop_lat,
        target_lng=shop_lng,
        visit_lat=visit_lat,
        visit_lng=visit_lng,
        entity_type="shop"
    )
    print(f"\n{'✅ PASS' if is_valid else '❌ FAIL'} - Lahore Shop Visit")
    print(f"   Distance: {distance_km:.4f} km ({distance_km * 1000:.2f} meters)")
    print(f"   Message: {message}")
    
    # Scenario 3: Shop in Karachi, user far away (should fail)
    print("\n--- Scenario 3: Shop in Karachi, User Far Away (Should Fail) ---")
    shop_lat = Decimal('24.8607')  # Karachi
    shop_lng = Decimal('67.0011')
    user_lat = Decimal('24.8700')  # About 1km away (exceeds 100m limit)
    user_lng = Decimal('67.0100')
    
    is_valid, distance_km, message = GeolocationService.validate_creation_location(
        target_lat=shop_lat,
        target_lng=shop_lng,
        user_lat=user_lat,
        user_lng=user_lng,
        entity_type="shop"
    )
    print(f"\n{'✅ PASS' if is_valid else '❌ FAIL'} - Karachi Shop Registration (Far)")
    print(f"   Distance: {distance_km:.4f} km ({distance_km * 1000:.2f} meters)")
    print(f"   Message: {message}")


def print_summary():
    """Print test summary."""
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    print("\n✅ All tests completed!")
    print("\nKey Points:")
    print("  • Creation validation: Default threshold = 100m (0.1 km)")
    print("  • Visit validation: Default threshold = 100m (0.1 km)")
    print("  • Both methods return: (is_valid, distance_km, message)")
    print("  • Distance is calculated using geodesic formula (accounts for Earth's curvature)")
    print("\nTo change thresholds, edit:")
    print("  • services/geolocation_service.py")
    print("  • MAX_CREATION_DISTANCE_KM (line 24)")
    print("  • MAX_VISIT_DISTANCE_KM (line 25)")
    print("\n" + "=" * 70)


def show_menu():
    """Display main menu."""
    print("\n" + "=" * 70)
    print("  GEOLOCATION SERVICE TEST SCRIPT")
    print("=" * 70)
    print("\nSelect an option:")
    print("  1. Calculate distance between two coordinates")
    print("  2. Test creation location validation (with dummy data)")
    print("  3. Test visit location validation (with dummy data)")
    print("  4. Test real-world scenarios (with dummy data)")
    print("  5. Run all automated tests")
    print("  0. Exit")
    print("\n" + "-" * 70)


def main():
    """Main interactive menu."""
    while True:
        show_menu()
        
        try:
            choice = input("\nEnter your choice (0-5): ").strip()
            
            if choice == "0":
                print("\n👋 Goodbye!")
                break
            
            elif choice == "1":
                calculate_distance_between_coordinates()
                input("\nPress Enter to continue...")
            
            elif choice == "2":
                print_header("TEST: Creation Location Validation")
                test_creation_validation()
                input("\nPress Enter to continue...")
            
            elif choice == "3":
                print_header("TEST: Visit Location Validation")
                test_visit_validation()
                input("\nPress Enter to continue...")
            
            elif choice == "4":
                test_real_world_scenarios()
                input("\nPress Enter to continue...")
            
            elif choice == "5":
                print_header("RUNNING ALL AUTOMATED TESTS")
                test_creation_validation()
                test_visit_validation()
                test_real_world_scenarios()
                print_summary()
                input("\nPress Enter to continue...")
            
            else:
                print("\n❌ Invalid choice. Please enter a number between 0-5.")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()

