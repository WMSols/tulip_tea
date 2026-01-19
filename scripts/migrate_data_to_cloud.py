"""
Migrate Data from Local Supabase to Cloud Supabase
==================================================
This script migrates data (not schema) from local Supabase to Supabase Cloud.

IMPORTANT: Schema must already be migrated before running this script!

Usage:
    python scripts/migrate_data_to_cloud.py
"""

import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path

# Cloud project details
CLOUD_PROJECT_ID = "lpncpprlegzoqmmzjxwx"
CLOUD_DB_HOST = f"db.{CLOUD_PROJECT_ID}.supabase.co"
CLOUD_DB_PORT = "5432"
CLOUD_DB_NAME = "postgres"
CLOUD_DB_USER = "postgres"

# Local database details
LOCAL_DB_HOST = "localhost"
LOCAL_DB_PORT = "54322"
LOCAL_DB_NAME = "postgres"
LOCAL_DB_USER = "postgres"
LOCAL_DB_PASSWORD = "postgres"

def find_pg_tool(tool_name):
    """Find pg_dump or psql executable."""
    try:
        subprocess.run([tool_name, "--version"], capture_output=True, check=True)
        return tool_name
    except:
        pass
    
    common_paths = [
        r"C:\Program Files\PostgreSQL\17\pgAdmin 4\runtime\{}.exe".format(tool_name),
        r"C:\Program Files\PostgreSQL\17\bin\{}.exe".format(tool_name),
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    return None

def dump_local_data():
    """Dump data from local database."""
    print("=" * 60)
    print("  STEP 1: Dumping Data from Local Database")
    print("=" * 60)
    
    pg_dump = find_pg_tool("pg_dump")
    if not pg_dump:
        print("❌ ERROR: pg_dump not found!")
        sys.exit(1)
    
    temp_dir = Path("./temp_data_migration")
    temp_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = temp_dir / f"local_data_dump_{timestamp}.sql"
    
    print(f"📦 Dumping data to: {dump_file.name}")
    
    env = os.environ.copy()
    env["PGPASSWORD"] = LOCAL_DB_PASSWORD
    
    cmd = [
        pg_dump,
        "--host", LOCAL_DB_HOST,
        "--port", LOCAL_DB_PORT,
        "--username", LOCAL_DB_USER,
        "--dbname", LOCAL_DB_NAME,
        "--schema", "public",
        "--data-only",
        "--no-owner",
        "--no-privileges",
        "--file", str(dump_file)
    ]
    
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"✅ Data dump completed!")
        return dump_file
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def restore_to_cloud(dump_file):
    """Restore data to cloud database."""
    print("\n" + "=" * 60)
    print("  STEP 2: Restoring Data to Cloud Database")
    print("=" * 60)
    
    psql = find_pg_tool("psql")
    if not psql:
        print("❌ ERROR: psql not found!")
        sys.exit(1)
    
    print(f"\n🔐 Cloud Database: {CLOUD_DB_HOST}")
    cloud_password = input("Enter your cloud database password: ").strip()
    
    if not cloud_password:
        print("❌ Password required!")
        sys.exit(1)
    
    print("\n⚠️  WARNING: This will INSERT data into cloud database!")
    response = input("Continue? (type 'YES'): ")
    if response != "YES":
        print("❌ Cancelled.")
        sys.exit(0)
    
    print("\n🔄 Restoring data...")
    
    env = os.environ.copy()
    env["PGPASSWORD"] = cloud_password
    
    cmd = [
        psql,
        "--host", CLOUD_DB_HOST,
        "--port", CLOUD_DB_PORT,
        "--username", CLOUD_DB_USER,
        "--dbname", CLOUD_DB_NAME,
        "--file", str(dump_file),
        "--quiet"
    ]
    
    try:
        subprocess.run(cmd, env=env, check=True)
        print("\n✅ DATA MIGRATION COMPLETED!")
        dump_file.unlink()  # Clean up
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"💾 Dump file saved at: {dump_file}")
        sys.exit(1)

if __name__ == "__main__":
    dump_file = dump_local_data()
    restore_to_cloud(dump_file)