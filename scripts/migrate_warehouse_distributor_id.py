"""
Migration Script: Add distributor_id to warehouses table
========================================================
This script adds the distributor_id column to the warehouses table and migrates existing data.

Run this script before creating new distributors to ensure the schema is up to date.

Usage:
    python scripts/migrate_warehouse_distributor_id.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from config.database import engine, SessionLocal


def run_migration():
    """Run the migration to add distributor_id to warehouses table."""
    print("=" * 60)
    print("Migration: Add distributor_id to warehouses table")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Step 1: Check if column already exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'warehouses' 
            AND column_name = 'distributor_id'
        """)
        result = db.execute(check_query).fetchone()
        
        if result:
            print("✅ Column 'distributor_id' already exists in warehouses table.")
            print("   Migration may have already been run.")
            return True
        
        print("\n📋 Step 1: Adding distributor_id column (nullable)...")
        db.execute(text("""
            ALTER TABLE warehouses 
            ADD COLUMN distributor_id BIGINT
        """))
        db.commit()
        print("   ✅ Column added successfully")
        
        print("\n📋 Step 2: Making zone_id nullable...")
        db.execute(text("""
            ALTER TABLE warehouses 
            ALTER COLUMN zone_id DROP NOT NULL
        """))
        db.commit()
        print("   ✅ zone_id is now nullable")
        
        print("\n📋 Step 3: Migrating existing warehouses to distributors...")
        # Try to assign warehouses to distributors based on zones
        update_query = text("""
            UPDATE warehouses w
            SET distributor_id = (
                SELECT DISTINCT d.id
                FROM distributors d
                INNER JOIN zones z ON z.id = w.zone_id
                WHERE w.zone_id IS NOT NULL
                LIMIT 1
            )
            WHERE w.distributor_id IS NULL 
              AND w.zone_id IS NOT NULL
              AND EXISTS (
                SELECT 1 FROM zones z WHERE z.id = w.zone_id
              )
        """)
        result = db.execute(update_query)
        db.commit()
        updated_count = result.rowcount
        print(f"   ✅ Assigned {updated_count} warehouse(s) to distributors based on zones")
        
        # For remaining warehouses, assign to first distributor if available
        print("\n📋 Step 4: Assigning remaining warehouses to default distributor...")
        update_query2 = text("""
            UPDATE warehouses w
            SET distributor_id = (
                SELECT id FROM distributors ORDER BY id LIMIT 1
            )
            WHERE w.distributor_id IS NULL
              AND EXISTS (SELECT 1 FROM distributors LIMIT 1)
        """)
        result2 = db.execute(update_query2)
        db.commit()
        updated_count2 = result2.rowcount
        if updated_count2 > 0:
            print(f"   ✅ Assigned {updated_count2} warehouse(s) to default distributor")
        
        # Check for warehouses that still don't have distributor_id
        check_null = text("""
            SELECT COUNT(*) FROM warehouses WHERE distributor_id IS NULL
        """)
        null_count = db.execute(check_null).scalar()
        
        if null_count > 0:
            print(f"\n⚠️  Warning: {null_count} warehouse(s) still have NULL distributor_id")
            print("   These need to be manually assigned before making the column NOT NULL")
            print("   Run this query to see them:")
            print("   SELECT id, name, zone_id FROM warehouses WHERE distributor_id IS NULL;")
            
            response = input("\n   Do you want to continue anyway? (y/n): ")
            if response.lower() != 'y':
                print("   Migration cancelled. Please assign warehouses manually first.")
                return False
        
        print("\n📋 Step 5: Making distributor_id NOT NULL...")
        db.execute(text("""
            ALTER TABLE warehouses 
            ALTER COLUMN distributor_id SET NOT NULL
        """))
        db.commit()
        print("   ✅ distributor_id is now NOT NULL")
        
        print("\n📋 Step 6: Adding foreign key constraint...")
        db.execute(text("""
            ALTER TABLE warehouses
            ADD CONSTRAINT warehouses_distributor_id_fkey 
            FOREIGN KEY (distributor_id) 
            REFERENCES distributors(id)
        """))
        db.commit()
        print("   ✅ Foreign key constraint added")
        
        print("\n📋 Step 7: Adding index...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_warehouses_distributor 
            ON warehouses(distributor_id)
        """))
        db.commit()
        print("   ✅ Index created")
        
        print("\n📋 Step 8: Adding unique constraint (one warehouse per distributor)...")
        # Check for duplicates first
        check_duplicates = text("""
            SELECT distributor_id, COUNT(*) as count
            FROM warehouses 
            WHERE deleted_at IS NULL
            GROUP BY distributor_id 
            HAVING COUNT(*) > 1
        """)
        duplicates = db.execute(check_duplicates).fetchall()
        
        if duplicates:
            print(f"   ⚠️  Warning: Found {len(duplicates)} distributor(s) with multiple warehouses:")
            for dist_id, count in duplicates:
                print(f"      Distributor {dist_id}: {count} warehouse(s)")
            print("   Unique constraint not added. Please clean up duplicates first.")
        else:
            db.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_warehouses_distributor_unique 
                ON warehouses(distributor_id) 
                WHERE deleted_at IS NULL
            """))
            db.commit()
            print("   ✅ Unique constraint added")
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        
        # Verification
        print("\n📊 Verification:")
        verify_query = text("""
            SELECT 
                d.id as distributor_id,
                d.name as distributor_name,
                COUNT(w.id) as warehouse_count
            FROM distributors d 
            LEFT JOIN warehouses w ON w.distributor_id = d.id AND w.deleted_at IS NULL
            GROUP BY d.id, d.name
            ORDER BY d.id
        """)
        results = db.execute(verify_query).fetchall()
        
        if results:
            print("\n   Distributor → Warehouse mapping:")
            for dist_id, dist_name, warehouse_count in results:
                print(f"   - {dist_name} (ID: {dist_id}): {warehouse_count} warehouse(s)")
        else:
            print("   No distributors found")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)


