"""
Safe Database Backup Script for Supabase Cloud
===============================================
This script creates a complete backup of your Supabase cloud database including:
- Schema (tables, columns, data types)
- Constraints (Primary Keys, Foreign Keys, Check Constraints, Unique Constraints)
- Indexes
- Triggers
- Functions
- Sequences

Usage:
    python backup_database.py

Backups are saved to: ./database backup/ directory

Configuration:
    Set DATABASE_URL in .env file or environment variables
    Format: postgresql://user:password@host:port/database
"""

import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, unquote

def find_pg_dump():
    """Find pg_dump executable - checks PATH and common locations"""
    # First, try if pg_dump is in PATH
    try:
        result = subprocess.run(
            ["pg_dump", "--version"],
            capture_output=True,
            check=True,
            text=True
        )
        return "pg_dump"  # Found in PATH
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Common PostgreSQL installation paths (including pgAdmin runtime)
    common_paths = [
        r"C:\Program Files\PostgreSQL\17\pgAdmin 4\runtime\pg_dump.exe",  # Your location
        r"C:\Program Files\PostgreSQL\16\pgAdmin 4\runtime\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\15\pgAdmin 4\runtime\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
        r"C:\Program Files (x86)\PostgreSQL\17\bin\pg_dump.exe",
        r"C:\Program Files (x86)\PostgreSQL\16\bin\pg_dump.exe",
    ]
    
    # Try common paths
    for path in common_paths:
        if os.path.exists(path):
            print(f"✅ Found pg_dump at: {path}")
            return path
    
    return None

def load_env_file():
    """Manually load .env file if it exists"""
    env_file = Path(".env")
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            print(f"⚠️  Warning: Could not read .env file: {e}")

def get_db_config():
    """
    Get database configuration from DATABASE_URL or environment variables.
    Supports both connection string and individual parameters.
    """
    # Load .env file first
    load_env_file()
    
    # Try to get DATABASE_URL first (Supabase cloud connection string)
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("⚠️  Warning: DATABASE_URL not found in environment variables or .env file")
        print("   Please set DATABASE_URL in your .env file:")
        print("   DATABASE_URL=postgresql://user:password@host:port/database")
        print()
    
    if database_url:
        # Parse connection string
        try:
            # Handle URL-encoded passwords (common in connection strings)
            parsed = urlparse(database_url)
            db_user = unquote(parsed.username or "postgres")
            db_password = unquote(parsed.password or "")
            db_host = parsed.hostname or "localhost"
            db_port = parsed.port or 5432
            db_name = parsed.path.lstrip('/') or "postgres"
            
            # Check if using pooler connection - warn user
            if "pooler" in db_host.lower():
                print("⚠️  WARNING: Using pooler connection!")
                print("   pg_dump may not work with pooler connections.")
                print("   Please use the DIRECT connection string from Supabase:")
                print("   Settings → Database → Connection string → Direct connection")
                print()
            
            # If password is empty, try to get from environment
            if not db_password:
                db_password = os.getenv("DB_PASSWORD", "")
                if not db_password:
                    print("⚠️  WARNING: No password found in DATABASE_URL or environment!")
                    print("   Please ensure your DATABASE_URL includes the password:")
                    print("   DATABASE_URL=postgresql://user:password@host:port/database")
                    print()
            
            return {
                "host": db_host,
                "port": str(db_port),
                "user": db_user,
                "name": db_name,
                "password": db_password
            }
        except Exception as e:
            print(f"⚠️  Warning: Failed to parse DATABASE_URL: {e}")
            print("   Falling back to individual environment variables...")
    
    # Fallback to individual environment variables
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "54322")
    db_user = os.getenv("DB_USER", "postgres")
    db_name = os.getenv("DB_NAME", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    
    return {
        "host": db_host,
        "port": db_port,
        "user": db_user,
        "name": db_name,
        "password": db_password
    }

def create_backup():
    """Create a safe database backup"""
    
    print("=" * 60)
    print("  SUPABASE CLOUD DATABASE BACKUP TOOL")
    print("=" * 60)
    print()
    print("This script will create a complete backup including:")
    print("  • Schema (tables, columns, data types)")
    print("  • Constraints (Primary Keys, Foreign Keys, Check, Unique)")
    print("  • Indexes")
    print("  • Triggers")
    print("  • Functions and Procedures")
    print("  • Sequences")
    print("  • Data")
    print()
    
    # Find pg_dump
    pg_dump_path = find_pg_dump()
    
    if not pg_dump_path:
        print("❌ ERROR: pg_dump not found!")
        print()
        print("Please ensure PostgreSQL is installed.")
        print("Expected location: C:\\Program Files\\PostgreSQL\\17\\pgAdmin 4\\runtime\\pg_dump.exe")
        print()
        sys.exit(1)
    
    # Get database configuration
    config = get_db_config()
    
    print("📋 Database Configuration:")
    print(f"   Host: {config['host']}")
    print(f"   Port: {config['port']}")
    print(f"   User: {config['user']}")
    print(f"   Database: {config['name']}")
    
    # Warn if using localhost (might be wrong for cloud)
    if config['host'] in ['localhost', '127.0.0.1']:
        print()
        print("⚠️  WARNING: Connecting to localhost!")
        print("   If you want to backup Supabase cloud, set DATABASE_URL in .env file")
        print("   Example: DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres")
        print()
    
    print()
    
    # Create "database backup" directory if it doesn't exist
    backup_dir = Path("./database backup")
    backup_dir.mkdir(exist_ok=True)
    print(f"📁 Backup directory: {backup_dir.absolute()}")
    print()
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"supabase_backup_{timestamp}.dump"
    
    # Also create schema-only backup
    schema_backup_file = backup_dir / f"supabase_schema_{timestamp}.sql"
    
    print(f"🔄 Starting backup...")
    print(f"   File: {backup_file.name}")
    print()
    
    # Set password in environment
    env = os.environ.copy()
    env["PGPASSWORD"] = config["password"]
    
    # Build pg_dump command for full backup (data + schema)
    # -F c = Custom format (compressed, can restore selectively)
    # -Z 9 = Maximum compression
    # -v = Verbose (show progress)
    # Note: By default, pg_dump includes:
    #   - Schema (tables, columns, data types)
    #   - Constraints (Primary Keys, Foreign Keys, Check, Unique)
    #   - Indexes
    #   - Triggers
    #   - Functions
    #   - Sequences
    #   - Data
    cmd = [
        pg_dump_path,
        "-h", config["host"],
        "-p", config["port"],
        "-U", config["user"],
        "-d", config["name"],
        "-F", "c",  # Custom format (compressed binary)
        "-Z", "9",  # Maximum compression
        "-v",  # Verbose (show progress)
        "--no-owner",  # Don't include ownership commands
        "--no-privileges",  # Don't include privilege commands
        "-f", str(backup_file)
    ]
    
    # Build schema-only backup command (SQL format for readability)
    schema_cmd = [
        pg_dump_path,
        "-h", config["host"],
        "-p", config["port"],
        "-U", config["user"],
        "-d", config["name"],
        "-F", "p",  # Plain SQL format
        "-s",  # Schema only (no data)
        "-v",  # Verbose
        "--no-owner",  # Don't include ownership commands
        "--no-privileges",  # Don't include privilege commands
        "-f", str(schema_backup_file)
    ]
    
    try:
        # Run full backup (data + schema)
        print("🔄 Creating full backup (data + schema)...")
        result = subprocess.run(
            cmd, 
            env=env, 
            check=True, 
            capture_output=True, 
            text=True
        )
        
        # Get full backup file size
        file_size = backup_file.stat().st_size / (1024 * 1024)  # Convert to MB
        
        print()
        print("🔄 Creating schema-only backup (readable SQL)...")
        
        # Run schema-only backup
        schema_result = subprocess.run(
            schema_cmd,
            env=env,
            check=True,
            capture_output=True,
            text=True
        )
        
        # Get schema backup file size
        schema_file_size = schema_backup_file.stat().st_size / (1024 * 1024)  # Convert to MB
        
        print()
        print("=" * 60)
        print("✅ BACKUP COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("📦 Full Backup (Data + Schema):")
        print(f"   File: {backup_file.name}")
        print(f"   Location: {backup_file.absolute()}")
        print(f"   Size: {file_size:.2f} MB")
        print(f"   Format: Custom (compressed binary)")
        print()
        print("📄 Schema-Only Backup (SQL):")
        print(f"   File: {schema_backup_file.name}")
        print(f"   Location: {schema_backup_file.absolute()}")
        print(f"   Size: {schema_file_size:.2f} MB")
        print(f"   Format: Plain SQL (readable)")
        print()
        print("📋 Included in backup:")
        print("   ✅ Tables and columns")
        print("   ✅ Primary Keys")
        print("   ✅ Foreign Keys")
        print("   ✅ Indexes")
        print("   ✅ Triggers")
        print("   ✅ Functions and procedures")
        print("   ✅ Sequences")
        print("   ✅ Check constraints")
        print("   ✅ Unique constraints")
        print("   ✅ Data (in full backup only)")
        print()
        print("💡 To restore the full backup, use:")
        print(f"   pg_restore -h <host> -p <port> -U <user> -d <database> {backup_file.name}")
        print()
        print("💡 To restore the schema backup, use:")
        print(f"   psql -h <host> -p <port> -U <user> -d <database> -f {schema_backup_file.name}")
        print()
        
        return {
            "full_backup": str(backup_file),
            "schema_backup": str(schema_backup_file)
        }
        
    except subprocess.CalledProcessError as e:
        print()
        print("=" * 60)
        print("❌ BACKUP FAILED!")
        print("=" * 60)
        print()
        print("Error details:")
        if e.stderr:
            print(e.stderr)
        if e.stdout:
            print(e.stdout)
        print()
        print("Common issues:")
        print("  1. Wrong password in DATABASE_URL")
        print("  2. Using pooler connection (use DIRECT connection for pg_dump)")
        print("  3. Password needs URL encoding (special characters)")
        print("  4. Database credentials expired or changed")
        print()
        print("💡 Solutions:")
        print("  1. Get DIRECT connection string from Supabase:")
        print("     Settings → Database → Connection string → Direct connection")
        print("  2. Make sure password in DATABASE_URL is correct")
        print("  3. If password has special characters, URL-encode them:")
        print("     @ → %40, # → %23, $ → %24, etc.")
        print("  4. Example format:")
        print("     DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres")
        print()
        sys.exit(1)

if __name__ == "__main__":
    try:
        create_backup()
    except KeyboardInterrupt:
        print("\n\n⚠️  Backup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)