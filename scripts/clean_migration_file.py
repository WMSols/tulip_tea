"""
Clean Migration File
===================
Removes Supabase system schemas/tables/functions from migration file,
keeping only custom public schema objects.
"""
import re
import sys

def clean_migration_file(input_file, output_file):
    """Clean migration file to only include public schema objects."""
    
    print(f"🔄 Cleaning migration file: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into lines for processing
    lines = content.split('\n')
    cleaned_lines = []
    skip_block = False
    in_drop_statement = False
    
    # Schemas to exclude (Supabase system schemas)
    excluded_schemas = [
        '_realtime', 'auth', 'extensions', 'graphql', 'graphql_public',
        'pgbouncer', 'realtime', 'storage', 'supabase_functions', 'vault'
    ]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        original_line = line
        
        # Skip DROP statements for system schemas/tables
        if 'DROP' in line.upper():
            # Check if it's dropping a system schema/table
            for schema in excluded_schemas:
                if f'{schema}.' in line or f'ONLY {schema}.' in line:
                    skip_block = True
                    in_drop_statement = True
                    break
            if not skip_block:
                cleaned_lines.append(line)
            i += 1
            continue
        
        # Skip CREATE SCHEMA for system schemas
        if line.strip().startswith('CREATE SCHEMA'):
            schema_name = None
            # Extract schema name from CREATE SCHEMA statement
            match = re.search(r'CREATE SCHEMA\s+([a-z_]+)', line, re.IGNORECASE)
            if match:
                schema_name = match.group(1)
            
            if schema_name and schema_name in excluded_schemas:
                # Skip this schema and its comment block
                i += 1
                # Skip comment lines before schema
                while i < len(lines) and (lines[i].strip().startswith('--') or lines[i].strip() == ''):
                    i += 1
                continue
            else:
                cleaned_lines.append(line)
                i += 1
                continue
        
        # Skip CREATE TYPE for system schemas
        if 'CREATE TYPE' in line.upper():
            for schema in excluded_schemas:
                if f'{schema}.' in line:
                    # Skip this type definition block
                    i += 1
                    while i < len(lines) and not (lines[i].strip().startswith(';') and ')' in lines[i-1] if i > 0 else False):
                        if lines[i].strip() == ');':
                            i += 1
                            break
                        i += 1
                    skip_block = False
                    break
            if not skip_block:
                cleaned_lines.append(line)
            i += 1
            continue
        
        # Skip CREATE FUNCTION for system schemas
        if 'CREATE FUNCTION' in line.upper() or 'CREATE OR REPLACE FUNCTION' in line.upper():
            for schema in excluded_schemas:
                if f'{schema}.' in line:
                    # Skip this function definition block
                    i += 1
                    depth = 0
                    while i < len(lines):
                        if 'BEGIN' in lines[i].upper():
                            depth += 1
                        if 'END' in lines[i].upper() and ';' in lines[i]:
                            if depth <= 1:
                                i += 1
                                break
                            depth -= 1
                        if lines[i].strip().endswith(';') and 'LANGUAGE' in lines[i].upper():
                            i += 1
                            break
                        i += 1
                    skip_block = False
                    break
            if not skip_block:
                cleaned_lines.append(line)
            i += 1
            continue
        
        # Skip CREATE TABLE for system schemas
        if 'CREATE TABLE' in line.upper():
            for schema in excluded_schemas:
                if f'{schema}.' in line:
                    # Skip this table definition block
                    i += 1
                    while i < len(lines):
                        if lines[i].strip() == ');':
                            i += 1
                            break
                        i += 1
                    skip_block = False
                    break
            if not skip_block:
                cleaned_lines.append(line)
            i += 1
            continue
        
        # Skip CREATE INDEX for system schemas
        if 'CREATE' in line.upper() and 'INDEX' in line.upper():
            for schema in excluded_schemas:
                if f'ON {schema}.' in line or f'ON ONLY {schema}.' in line:
                    i += 1
                    skip_block = False
                    break
            if not skip_block:
                cleaned_lines.append(line)
            i += 1
            continue
        
        # Skip CREATE TRIGGER for system schemas
        if 'CREATE TRIGGER' in line.upper():
            for schema in excluded_schemas:
                if f'{schema}.' in line:
                    i += 1
                    skip_block = False
                    break
            if not skip_block:
                cleaned_lines.append(line)
            i += 1
            continue
        
        # Skip ALTER statements for system schemas
        if 'ALTER' in line.upper():
            for schema in excluded_schemas:
                if f'{schema}.' in line:
                    i += 1
                    skip_block = False
                    break
            if not skip_block:
                cleaned_lines.append(line)
            i += 1
            continue
        
        # Reset skip_block if we're past a statement
        if skip_block and (line.strip().endswith(';') or line.strip() == ''):
            skip_block = False
            in_drop_statement = False
        
        # Add line if not skipping
        if not skip_block:
            cleaned_lines.append(line)
        
        i += 1
    
    # Join cleaned lines
    cleaned_content = '\n'.join(cleaned_lines)
    
    # Remove multiple consecutive empty lines
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    
    # Add transaction wrapper at the beginning
    if not cleaned_content.strip().startswith('BEGIN'):
        cleaned_content = 'BEGIN;\n\n' + cleaned_content
    
    # Add commit at the end
    if not cleaned_content.strip().endswith('COMMIT;'):
        cleaned_content = cleaned_content.rstrip() + '\n\nCOMMIT;'
    
    # Write cleaned file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    print(f"✅ Cleaned migration file created: {output_file}")
    print(f"📊 Original size: {len(content) / 1024:.2f} KB")
    print(f"📊 Cleaned size: {len(cleaned_content) / 1024:.2f} KB")
    print(f"📉 Reduction: {((len(content) - len(cleaned_content)) / len(content) * 100):.1f}%")
    
    return output_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/clean_migration_file.py <input_file> [output_file]")
        print("\nExample:")
        print("  python scripts/clean_migration_file.py supabase/migrations/20260119152740_migrate_local_to_cloud.sql")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.sql', '_cleaned.sql')
    
    clean_migration_file(input_file, output_file)

