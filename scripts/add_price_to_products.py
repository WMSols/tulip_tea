"""
Migration script to add price column to products table.
Run this once to update your database schema.
"""
from sqlalchemy import text
from config.database import engine

def add_price_column():
    """Add price column to products table if it doesn't exist."""
    try:
        print("🔄 Adding price column to products table...")
        
        with engine.connect() as conn:
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='products' AND column_name='price'
            """)
            result = conn.execute(check_query)
            exists = result.fetchone()
            
            if exists:
                print("✅ Column 'price' already exists in products table.")
                return
            
            # Add the column
            alter_query = text("""
                ALTER TABLE products 
                ADD COLUMN price NUMERIC(10, 2) NULL
            """)
            conn.execute(alter_query)
            conn.commit()
            
            # Add comment
            comment_query = text("""
                COMMENT ON COLUMN products.price IS 'Product price per unit in Pakistani Rupees (PKR). NULL if price is not set.'
            """)
            conn.execute(comment_query)
            conn.commit()
            
            print("✅ Successfully added 'price' column to products table.")
            print("   You can now set prices for products in the database.")
            
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    add_price_column()
    print("\n✅ Migration complete!")

