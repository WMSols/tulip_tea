"""
Quick test script to verify all imports work correctly.
Run this before starting the server to catch import errors.
"""
import sys

def test_imports():
    """Test all critical imports."""
    print("Testing imports...")
    
    try:
        print("  ✓ Testing config.database...")
        from config.database import settings, engine, Base
        print(f"     Database URL: {settings.database_url[:30]}...")
        
        print("  ✓ Testing models...")
        from models import distributor, order_booker, delivery_man, zone, route, shop, route_shop
        print(f"     Models loaded: distributor, order_booker, delivery_man, zone, route, shop, route_shop")
        
        print("  ✓ Testing routers...")
        from routers import auth, distributor as distributor_router, order_booker, delivery_man, zone, route, shop
        print("     All routers loaded successfully")
        
        print("  ✓ Testing main app...")
        from main import app
        print("     Main app imported successfully")
        
        print("\n✅ All imports successful! Server should start correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)



