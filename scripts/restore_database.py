"""
Safe Database Restore Script for Supabase
==========================================
This script restores a backup to your local Supabase database.

Usage:
    python restore_database.py backup_file.dump
    
    Or to see available backups:
    python restore_database.py --list
"""

import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime

def find_pg_restore():
    """Find pg_restore executable - checks PATH and common locations"""
    # First, try if pg_restore is in PATH
    try:
        result = subprocess.run(
            ["pg_restore", "--version"],
            capture_output=True,
            check=True,
            text=True
        )
        return "pg_restore"  # Found in PATH
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Common PostgreSQL installation paths (including pgAdmin runtime)
    common_paths = [
        r"C:\Program Files\PostgreSQL\17\pgAdmin 4\runtime\pg_restore.exe",  # Your location
        r"C:\Program Files\PostgreSQL\16\pgAdmin 4\runtime\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\15\pgAdmin 4\runtime\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\17\bin\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\16\bin\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\15\bin\pg_restore.exe",
        r"C:\Program Files\PostgreSQL\14\bin\pg_restore.exe",
        r"C:\Program Files (x86)\PostgreSQL\17\bin\pg_restore.exe",
        r"C:\Program Files (x86)\PostgreSQL\16\bin\pg_restore.exe",
    ]
    
    # Try common paths
    for path in common_paths:
        if os.path.exists(path):
            print(f"✅ Found pg_restore at: {path}")
            return path
    
    return None

def get_db_config():
    """Get database configuration"""
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

def list_backups():
    """List all available backups"""
    backup_dir = Path("./backups")
    
    if not backup_dir.exists():
        print("❌ No backups directory found!")
        return []
    
    backups = sorted(backup_dir.glob("supabase_backup_*.dump"), 
                    key=lambda x: x.stat().st_mtime, 
                    reverse=True)
    
    if not backups:
        print("❌ No backup files found!")
        return []
    
    print("=" * 60)
    print("  AVAILABLE BACKUPS")
    print("=" * 60)
    print()
    
    for i, backup in enumerate(backups, 1):
        file_size = backup.stat().st_size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"{i}. {backup.name}")
        print(f"   Size: {file_size:.2f} MB")
        print(f"   Date: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    return backups

def restore_backup(backup_filename):
    """Restore database from backup"""
    
    print("=" * 60)
    print("  SUPABASE DATABASE RESTORE TOOL")
    print("=" * 60)
    print()
    
    # Find pg_restore
    pg_restore_path = find_pg_restore()
    
    if not pg_restore_path:
        print("❌ ERROR: pg_restore not found!")
        print()
        print("Please ensure PostgreSQL is installed.")
        print("Expected location: C:\\Program Files\\PostgreSQL\\17\\pgAdmin 4\\runtime\\pg_restore.exe")
        print()
        sys.exit(1)
    
    # Find backup file
    backup_dir = Path("./backups")
    backup_file = backup_dir / backup_filename
    
    if not backup_file.exists():
        # Try with full path
        backup_file = Path(backup_filename)
        if not backup_file.exists():
            print(f"❌ ERROR: Backup file not found: {backup_filename}")
            print()
            print("Available backups:")
            list_backups()
            sys.exit(1)
    
    print(f"📦 Backup file: {backup_file.name}")
    print(f"📁 Location: {backup_file.absolute()}")
    print()
    
    # Get database configuration
    config = get_db_config()
    
    print("📋 Database Configuration:")
    print(f"   Host: {config['host']}")
    print(f"   Port: {config['port']}")
    print(f"   User: {config['user']}")
    print(f"   Database: {config['name']}")
    print()
    
    # SAFETY CHECK
    print("⚠️  WARNING: This will REPLACE all data in the database!")
    print()
    response = input("Are you sure you want to continue? (type 'YES' to confirm): ")
    
    if response != "YES":
        print("❌ Restore cancelled.")
        sys.exit(0)
    
    print()
    print("🔄 Starting restore...")
    print()
    
    # Set password in environment
    env = os.environ.copy()
    env["PGPASSWORD"] = config["password"]
    
    # Build pg_restore command
    # -c = Clean (drop objects before creating)
    # -v = Verbose
    # -1 = Single transaction (all or nothing)
    cmd = [
        pg_restore_path,  # Use found path
        "-h", config["host"],
        "-p", config["port"],
        "-U", config["user"],
        "-d", config["name"],
        "-c",  # Clean (drop existing objects)
        "-v",  # Verbose
        "-1",  # Single transaction
        str(backup_file)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            check=True,
            capture_output=True,
            text=True
        )
        
        print()
        print("=" * 60)
        print("✅ RESTORE COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("Your database has been restored from the backup.")
        print()
        
    except subprocess.CalledProcessError as e:
        print()
        print("=" * 60)
        print("❌ RESTORE FAILED!")
        print("=" * 60)
        print()
        print("Error details:")
        if e.stderr:
            print(e.stderr)
        if e.stdout:
            print(e.stdout)
        print()
        print("Common issues:")
        print("  1. Database not running")
        print("  2. Active connections to database (close all connections)")
        print("  3. Wrong connection details")
        print()
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore_database.py <backup_file.dump>")
        print("   Or: python restore_database.py --list")
        print()
        list_backups()
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_backups()
    else:
        try:
            restore_backup(sys.argv[1])
        except KeyboardInterrupt:
            print("\n\n⚠️  Restore cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)