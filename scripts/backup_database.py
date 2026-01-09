"""
Safe Database Backup Script for Supabase
=========================================
This script creates a backup of your local Supabase database.

Usage:
    python backup_database.py

Backups are saved to: ./backups/ directory
"""

import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path

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

def get_db_config():
    """Get database configuration from environment or defaults"""
    # Try to get from environment variables first
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "54322")  # Supabase default local port
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
    print("  SUPABASE DATABASE BACKUP TOOL")
    print("=" * 60)
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
    print()
    
    # Create backups directory
    backup_dir = Path("./backups")
    backup_dir.mkdir(exist_ok=True)
    print(f"📁 Backup directory: {backup_dir.absolute()}")
    print()
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"supabase_backup_{timestamp}.dump"
    
    print(f"🔄 Starting backup...")
    print(f"   File: {backup_file.name}")
    print()
    
    # Set password in environment
    env = os.environ.copy()
    env["PGPASSWORD"] = config["password"]
    
    # Build pg_dump command
    # -F c = Custom format (compressed, can restore selectively)
    # -Z 9 = Maximum compression
    # -v = Verbose (show progress)
    cmd = [
        pg_dump_path,  # Use found path (full path or "pg_dump" if in PATH)
        "-h", config["host"],
        "-p", config["port"],
        "-U", config["user"],
        "-d", config["name"],
        "-F", "c",  # Custom format
        "-Z", "9",  # Compression
        "-v",  # Verbose
        "-f", str(backup_file)
    ]
    
    try:
        # Run backup
        result = subprocess.run(
            cmd, 
            env=env, 
            check=True, 
            capture_output=True, 
            text=True
        )
        
        # Get file size
        file_size = backup_file.stat().st_size / (1024 * 1024)  # Convert to MB
        
        print()
        print("=" * 60)
        print("✅ BACKUP COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print(f"📦 Backup File: {backup_file.name}")
        print(f"📁 Location: {backup_file.absolute()}")
        print(f"💾 Size: {file_size:.2f} MB")
        print()
        print("💡 To restore this backup, use:")
        print(f"   python restore_database.py {backup_file.name}")
        print()
        
        return str(backup_file)
        
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
        print("  1. Database not running")
        print("  2. Wrong connection details (host, port, user, password)")
        print("  3. Database name incorrect")
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