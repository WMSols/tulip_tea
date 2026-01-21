"""
Generate complete database schema SQL script.
This script creates a clean schema dump without route_shops and delivery_man_routes tables.
"""
import os
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.schema import CreateTable
from config.database import Base, settings
from models import (
    distributor, zone, order_booker, delivery_man, route, shop,
    order, order_item, payment, daily_collection, shop_visit,
    credit_limit_request, warehouse, inventory, delivery, delivery_item,
    product
)

def generate_schema_sql():
    """Generate SQL schema script for all tables."""
    
    engine = create_engine(settings.database_url)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    sql_statements = []
    sql_statements.append("-- ============================================")
    sql_statements.append("-- Tulip Tea Database Schema")
    sql_statements.append("-- Generated Schema (without route_shops and delivery_man_routes)")
    sql_statements.append("-- ============================================\n")
    sql_statements.append("-- Note: route_shops and delivery_man_routes tables are removed")
    sql_statements.append("-- Shops now use route_id directly")
    sql_statements.append("-- Delivery men work by zone, not routes\n")
    
    # Exclude the tables we're removing
    excluded_tables = ['route_shops', 'delivery_man_routes']
    
    # Create tables in dependency order
    table_order = [
        'distributors',
        'zones',
        'order_bookers',
        'delivery_men',
        'routes',
        'shops',
        'products',
        'warehouses',
        'inventory',
        'orders',
        'order_items',
        'deliveries',
        'delivery_items',
        'payments',
        'daily_collections',
        'shop_visits',
        'credit_limit_requests'
    ]
    
    # Get all tables from metadata
    all_tables = {name: table for name, table in metadata.tables.items() if name not in excluded_tables}
    
    # Reorder tables based on dependencies
    ordered_tables = []
    for table_name in table_order:
        if table_name in all_tables:
            ordered_tables.append((table_name, all_tables[table_name]))
            del all_tables[table_name]
    
    # Add any remaining tables
    for table_name, table in sorted(all_tables.items()):
        ordered_tables.append((table_name, table))
    
    # Generate CREATE TABLE statements
    for table_name, table in ordered_tables:
        sql_statements.append(f"\n-- Table: {table_name}")
        sql_statements.append(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
        
        # Generate CREATE TABLE statement
        create_sql = str(CreateTable(table).compile(engine))
        sql_statements.append(create_sql + ";")
    
    # Add indexes and constraints separately
    inspector = inspect(engine)
    for table_name, table in ordered_tables:
        # Get indexes
        indexes = inspector.get_indexes(table_name)
        for idx in indexes:
            if not idx.get('unique', False):
                idx_cols = ", ".join(idx['column_names'])
                sql_statements.append(f"\nCREATE INDEX IF NOT EXISTS {idx['name']} ON {table_name} ({idx_cols});")
        
        # Get foreign keys
        foreign_keys = inspector.get_foreign_keys(table_name)
        for fk in foreign_keys:
            fk_cols = ", ".join(fk['constrained_columns'])
            ref_table = fk['referred_table']
            ref_cols = ", ".join(fk['referred_columns'])
            fk_name = fk.get('name', f"{table_name}_{ref_table}_fkey")
            sql_statements.append(f"\nALTER TABLE {table_name}")
            sql_statements.append(f"    ADD CONSTRAINT {fk_name}")
            sql_statements.append(f"    FOREIGN KEY ({fk_cols}) REFERENCES {ref_table} ({ref_cols});")
    
    return "\n".join(sql_statements)

if __name__ == "__main__":
    try:
        schema_sql = generate_schema_sql()
        
        output_file = "sql/create_schema.sql"
        os.makedirs("sql", exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(schema_sql)
        
        print(f"✅ Schema generated successfully: {output_file}")
        print(f"📊 Note: route_shops and delivery_man_routes tables are excluded")
        
    except Exception as e:
        print(f"❌ Error generating schema: {e}")
        import traceback
        traceback.print_exc()
