"""
Migration script to add assigned_zone column to distributors table.
Run this once to update your database schema.
"""
from sqlalchemy import text
from config.database import engine, settings

def add_assigned_zone_column():
    """Add assigned_zone column to distributors table if it doesn't exist."""
    try:
        print("🔄 Adding assigned_zone column to distributors table...")
        
        with engine.connect() as conn:
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='distributors' AND column_name='assigned_zone'
            """)
            result = conn.execute(check_query)
            exists = result.fetchone()
            
            if exists:
                print("✅ Column 'assigned_zone' already exists in distributors table.")
                return
            
            # Add the column
            alter_query = text("""
                ALTER TABLE distributors 
                ADD COLUMN assigned_zone TEXT NOT NULL DEFAULT 'Default Zone'
            """)
            conn.execute(alter_query)
            conn.commit()
            
            print("✅ Successfully added 'assigned_zone' column to distributors table.")
            print("   Default value 'Default Zone' was set for existing rows.")
            
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    print(f"📊 Database: {settings.database_url[:50]}...")
    add_assigned_zone_column()
    print("\n✅ Migration complete!")

