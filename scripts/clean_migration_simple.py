"""
Clean Migration File - Simple Version
=====================================
Removes Supabase system schemas/tables/functions from migration file,
keeping only custom public schema objects.
"""
import sys
import re

def clean_migration_file(input_file, output_file):
    """Clean migration file to only include public schema objects."""
    
    print(f"🔄 Cleaning migration file: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # System schemas to exclude
    excluded_schemas = [
        '_realtime', 'auth', 'extensions', 'graphql', 'graphql_public',
        'pgbouncer', 'realtime', 'storage', 'supabase_functions', 'vault'
    ]
    
    lines = content.split('\n')
    cleaned_lines = []
    skip_until_semicolon = False
    skip_until_end = False
    function_depth = 0
    
    i = 0
    while i < len(lines):
        line = lines[i]
        original_line = line.strip()
        
        # Check if line references a system schema
        is_system_schema = any(f'{schema}.' in line for schema in excluded_schemas)
        
        # Skip DROP statements for system schemas
        if 'DROP' in line.upper() and is_system_schema:
            i += 1
            continue
        
        # Skip CREATE SCHEMA for system schemas
        if original_line.startswith('CREATE SCHEMA'):
            schema_match = re.search(r'CREATE SCHEMA\s+([a-z_]+)', line, re.IGNORECASE)
            if schema_match and schema_match.group(1) in excluded_schemas:
                i += 1
                continue
        
        # Skip CREATE TYPE for system schemas
        if 'CREATE TYPE' in line.upper() and is_system_schema:
            # Skip until closing );
            i += 1
            while i < len(lines):
                if lines[i].strip().endswith(');'):
                    i += 1
                    break
                i += 1
            continue
        
        # Skip CREATE FUNCTION for system schemas
        if ('CREATE FUNCTION' in line.upper() or 'CREATE OR REPLACE FUNCTION' in line.upper()) and is_system_schema:
            # Skip function definition
            i += 1
            while i < len(lines):
                current = lines[i].strip()
                if current.upper().startswith('LANGUAGE') and current.endswith(';'):
                    i += 1
                    break
                if current.upper().startswith('AS $$'):
                    # Function body
                    i += 1
                    while i < len(lines):
                        if lines[i].strip() == '$$;' or lines[i].strip().endswith('$$;'):
                            i += 1
                            break
                        i += 1
                    break
                i += 1
            continue
        
        # Skip CREATE TABLE for system schemas
        if 'CREATE TABLE' in line.upper() and is_system_schema:
            # Skip table definition until );
            i += 1
            while i < len(lines):
                if lines[i].strip() == ');':
                    i += 1
                    break
                i += 1
            continue
        
        # Skip CREATE INDEX for system schemas
        if 'CREATE' in line.upper() and 'INDEX' in line.upper() and is_system_schema:
            i += 1
            continue
        
        # Skip CREATE TRIGGER for system schemas
        if 'CREATE TRIGGER' in line.upper() and is_system_schema:
            i += 1
            continue
        
        # Skip ALTER statements for system schemas
        if 'ALTER' in line.upper() and is_system_schema:
            i += 1
            continue
        
        # Skip SEQUENCE for system schemas
        if 'CREATE SEQUENCE' in line.upper() and is_system_schema:
            i += 1
            while i < len(lines):
                if lines[i].strip().endswith(';'):
                    i += 1
                    break
                i += 1
            continue
        
        # Keep the line
        cleaned_lines.append(line)
        i += 1
    
    # Join and clean up
    cleaned_content = '\n'.join(cleaned_lines)
    
    # Remove multiple empty lines
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    
    # Add transaction wrapper
    if not cleaned_content.strip().startswith('BEGIN'):
        cleaned_content = 'BEGIN;\n\n' + cleaned_content.strip()
    
    if not cleaned_content.strip().endswith('COMMIT;'):
        cleaned_content = cleaned_content.rstrip() + '\n\nCOMMIT;'
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    print(f"✅ Cleaned migration file: {output_file}")
    print(f"📊 Original: {len(content) / 1024:.2f} KB")
    print(f"📊 Cleaned: {len(cleaned_content) / 1024:.2f} KB")
    print(f"📉 Removed: {((len(content) - len(cleaned_content)) / len(content) * 100):.1f}%")
    
    return output_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/clean_migration_simple.py <migration_file>")
        print("\nExample:")
        print("  python scripts/clean_migration_simple.py supabase/migrations/20260119152740_migrate_local_to_cloud.sql")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = input_file.replace('.sql', '_cleaned.sql')
    
    clean_migration_file(input_file, output_file)
    print(f"\n✅ Next step: Replace the original file with the cleaned version:")
    print(f"   Move-Item {output_file} {input_file} -Force")

