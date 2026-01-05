"""
Script to create the initial distributor (faraz).
Run this once to set up the test distributor.

FLOW:
1. Creates a database session
2. Calls DistributorService.create_distributor() which:
   - Validates phone/email uniqueness
   - Hashes the password using bcrypt
   - Creates distributor record via DistributorRepository
   - Returns distributor data
3. Prints success message with credentials
4. Closes database session

USAGE:
    python scripts/create_initial_distributor.py
"""
import sys
import os

# Add parent directory to path so we can import from project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from config.database import SessionLocal
from services.distributor_service import DistributorService


def create_initial_distributor():
    """
    Create the initial distributor with credentials: faraz / faraz12
    
    This function:
    1. Opens a database session
    2. Calls the DistributorService to create a new distributor
    3. The service handles:
       - Phone/email validation (checks for duplicates)
       - Password hashing (using bcrypt)
       - Database insertion (via repository layer)
    4. Prints the created distributor details and login credentials
    5. Handles errors gracefully (e.g., if distributor already exists)
    
    Returns:
        None (prints results to console)
    """
    # Create database session (connection to PostgreSQL)
    db: Session = SessionLocal()
    
    try:
        # Call service layer to create distributor
        # Service handles business logic: validation, password hashing, etc.
        result = DistributorService.create_distributor(
            db=db,
            name="faraz",
            email="faraz@tuliptea.com",
            phone="03001234567",
            password="faraz12",
            zone_id=None  # Can be set later after creating zones
        )
        
        # Print success message with created distributor details
        print("✅ Distributor created successfully!")
        print(f"   ID: {result['id']}")
        print(f"   Name: {result['name']}")
        print(f"   Phone: {result['phone']}")
        print(f"   Zone ID: {result.get('zone_id', 'Not assigned')}")
        print(f"\n📋 Login Credentials:")
        print(f"   Phone: {result['phone']}")
        print(f"   Password: faraz12")
        print(f"\n🌐 You can now login at: http://localhost:8000/docs")
        print(f"   Or use the HTML dashboard: tests/distributor_dashboard.html")
        
    except ValueError as e:
        # Handle business logic errors (e.g., duplicate phone/email)
        print(f"❌ Error: {e}")
        print("   Distributor might already exist. Try logging in instead.")
    except Exception as e:
        # Handle unexpected errors (database connection, etc.)
        print(f"❌ Unexpected error: {e}")
    finally:
        # Always close database session to free resources
        db.close()


if __name__ == "__main__":
    # Entry point: run the function when script is executed directly
    create_initial_distributor()

