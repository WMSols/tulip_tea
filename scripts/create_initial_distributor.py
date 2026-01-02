"""
Script to create the initial distributor (faraz).
Run this once to set up the test distributor.
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from config.database import SessionLocal
from services.distributor_service import DistributorService

def create_initial_distributor():
    """Create the initial distributor with credentials: faraz / faraz12"""
    db: Session = SessionLocal()
    
    try:
        result = DistributorService.create_distributor(
            db=db,
            name="faraz",
            email="faraz@tuliptea.com",
            phone="03001234567",
            assigned_zone="islamabad",
            password="faraz12"
        )
        
        print("✅ Distributor created successfully!")
        print(f"   ID: {result['id']}")
        print(f"   Name: {result['name']}")
        print(f"   Phone: {result['phone']}")
        print(f"   Zone: {result['assigned_zone']}")
        print(f"\n📋 Login Credentials:")
        print(f"   Phone: {result['phone']}")
        print(f"   Password: faraz12")
        print(f"\n🌐 You can now login at: http://localhost:8000/docs")
        print(f"   Or use the HTML dashboard: tests/distributor_dashboard.html")
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("   Distributor might already exist. Try logging in instead.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_initial_distributor()

