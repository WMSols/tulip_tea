"""
Migration script to add missing columns to warehouses table.
Run this once to update your database schema.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from config.database import engine, settings

def migrate_warehouse_columns():
    """Add missing columns (is_active, updated_at, deleted_at) to warehouses table."""
    try:
        print("Adding missing columns to warehouses table...")
        
        with engine.begin() as conn:
            # Add is_active column
            check_is_active = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='warehouses' AND column_name='is_active'
            """)
            result = conn.execute(check_is_active)
            exists = result.fetchone()
            
            if not exists:
                print("  Adding is_active column...")
                alter_is_active = text("""
                    ALTER TABLE public.warehouses
                    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE
                """)
                conn.execute(alter_is_active)
                print("  Added is_active column")
            else:
                print("  Column is_active already exists")
            
            # Add updated_at column
            check_updated_at = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='warehouses' AND column_name='updated_at'
            """)
            result = conn.execute(check_updated_at)
            exists = result.fetchone()
            
            if not exists:
                print("  Adding updated_at column...")
                alter_updated_at = text("""
                    ALTER TABLE public.warehouses
                    ADD COLUMN updated_at TIMESTAMP WITHOUT TIME ZONE NULL
                """)
                conn.execute(alter_updated_at)
                print("  Added updated_at column")
            else:
                print("  Column updated_at already exists")
            
            # Add deleted_at column
            check_deleted_at = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='warehouses' AND column_name='deleted_at'
            """)
            result = conn.execute(check_deleted_at)
            exists = result.fetchone()
            
            if not exists:
                print("  Adding deleted_at column...")
                alter_deleted_at = text("""
                    ALTER TABLE public.warehouses
                    ADD COLUMN deleted_at TIMESTAMP WITHOUT TIME ZONE NULL
                """)
                conn.execute(alter_deleted_at)
                
                # Create index for soft delete queries
                create_index = text("""
                    CREATE INDEX IF NOT EXISTS idx_warehouses_deleted_at
                    ON public.warehouses(deleted_at)
                    WHERE deleted_at IS NULL
                """)
                conn.execute(create_index)
                print("  Added deleted_at column and index")
            else:
                print("  Column deleted_at already exists")
        
        print("Successfully migrated warehouses table!")
        
    except Exception as e:
        print(f"Error migrating warehouses table: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate_warehouse_columns()

