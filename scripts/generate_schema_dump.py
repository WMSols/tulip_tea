"""
Generate Database Schema Dump
=============================
Generates a complete SQL schema dump from local Supabase database
including tables, columns, constraints, indexes, and sequences.
"""
import os
import subprocess
import sys
from datetime import datetime

def generate_schema_dump():
    """Generate schema-only dump from local Supabase database."""
    
    # Local Supabase database connection
    db_host = "localhost"
    db_port = "54322"
    db_name = "postgres"
    db_user = "postgres"
    db_password = "postgres"
    
    # pg_dump location (Windows PostgreSQL installation)
    pg_dump_paths = [
        r"C:\Program Files\PostgreSQL\17\pgAdmin 4\runtime\pg_dump.exe",
        r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        "pg_dump"  # Fallback to system PATH
    ]
    
    # Find pg_dump executable
    pg_dump_exe = None
    for path in pg_dump_paths:
        if path == "pg_dump":
            # Check if pg_dump is in system PATH
            pg_dump_exe = "pg_dump"
            break
        elif os.path.exists(path):
            pg_dump_exe = path
            print(f"✅ Found pg_dump at: {path}")
            break
    
    if not pg_dump_exe:
        print("❌ Error: pg_dump not found!")
        print("   Checked locations:")
        for path in pg_dump_paths:
            print(f"   - {path}")
        print("\n   Please ensure PostgreSQL is installed or pg_dump is in your PATH")
        sys.exit(1)
    
    # Output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"schema_dump_{timestamp}.sql"
    
    print("🔄 Generating schema dump from local Supabase...")
    print(f"📁 Output file: {output_file}")
    
    # Set PGPASSWORD environment variable
    env = os.environ.copy()
    env['PGPASSWORD'] = db_password
    
    # pg_dump command for schema only (no data)
    # --schema-only: Only dump schema, no data
    # --no-owner: Don't output commands to set ownership
    # --no-privileges: Don't output commands to set privileges
    # --clean: Include DROP statements before CREATE
    # --if-exists: Use IF EXISTS for DROP statements
    # --verbose: Verbose mode
    cmd = [
        pg_dump_exe,
        f"--host={db_host}",
        f"--port={db_port}",
        f"--username={db_user}",
        f"--dbname={db_name}",
        "--schema-only",  # Schema only, no data
        "--no-owner",     # Don't set ownership
        "--no-privileges", # Don't set privileges
        "--clean",        # Include DROP statements
        "--if-exists",    # Use IF EXISTS
        "--verbose",      # Verbose output
        f"--file={output_file}"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        print("✅ Schema dump generated successfully!")
        print(f"📄 File: {output_file}")
        print(f"📊 Size: {os.path.getsize(output_file) / 1024:.2f} KB")
        
        # Also create a clean version without DROP statements for initial migration
        clean_output_file = f"schema_clean_{timestamp}.sql"
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Remove DROP statements for clean migration
            lines = content.split('\n')
            clean_lines = [line for line in lines if not line.strip().startswith('DROP')]
            clean_content = '\n'.join(clean_lines)
        
        with open(clean_output_file, 'w', encoding='utf-8') as f:
            f.write(clean_content)
        
        print(f"📄 Clean version (no DROP statements): {clean_output_file}")
        
        return output_file, clean_output_file
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating schema dump:")
        print(f"   {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Error: pg_dump executable not found!")
        print("   Expected location: C:\\Program Files\\PostgreSQL\\17\\pgAdmin 4\\runtime\\pg_dump.exe")
        print("   Alternative locations checked:")
        print("   - C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe")
        print("   - System PATH")
        print("\n   Please ensure PostgreSQL is installed or update the path in the script")
        sys.exit(1)

if __name__ == "__main__":
    generate_schema_dump()

