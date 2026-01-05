import os
from pathlib import Path

# Configuration: Strictly excluding documentation and environment noise
EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', 'env', '.env'}
# Added requirements, lock files, and the output file itself to exclusion
EXCLUDE_FILES = {
    '.DS_Store', 'package-lock.json', 'project_context.md', 
    'requirements.txt', 'README.md', '.gitignore'
}
# Only include actual script/logic extensions (Removed .md and .txt)
CODE_EXTENSIONS = {'.py', '.js', '.ts', '.html', '.css', '.yaml', '.yml', '.json', '.sql', '.sh'}

def generate_context(root_dir=".", output_file="project_context.md"):
    base_path = Path(root_dir)
    context_lines = ["# Project Logic Context\n", "## Directory Structure (Scripts Only)\n", "```text"]

    # 1. Generate visual tree structure
    def build_tree(path, prefix=""):
        try:
            # Filter entries: Must not be in exclude lists AND must not be a .md file
            entries = sorted([
                e for e in path.iterdir() 
                if e.name not in EXCLUDE_DIRS 
                and e.name not in EXCLUDE_FILES 
                and e.suffix != '.md'
            ])
        except PermissionError:
            return

        for i, entry in enumerate(entries):
            connector = "└── " if i == len(entries) - 1 else "├── "
            context_lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                build_tree(entry, prefix + ("    " if i == len(entries) - 1 else "│   "))

    build_tree(base_path)
    context_lines.append("```\n\n## Source Code\n")

    # 2. Extract code from script files only
    for path in base_path.rglob("*"):
        # Skip if path contains excluded dir, is an excluded file, or is a markdown file
        if (any(part in EXCLUDE_DIRS for part in path.parts) or 
            path.name in EXCLUDE_FILES or 
            path.suffix == '.md'):
            continue
        
        if path.is_file() and path.suffix in CODE_EXTENSIONS:
            relative_path = path.relative_to(base_path)
            
            context_lines.append(f"### File: `{relative_path}`")
            lang = path.suffix[1:] if path.suffix else 'text'
            context_lines.append(f"```{lang}")
            
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                context_lines.append(content)
            except Exception as e:
                context_lines.append(f"[Error reading file: {e}]")
            
            context_lines.append("```\n")

    # 3. Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(context_lines))
    print(f"✅ Logic context generated: {output_file}")

if __name__ == "__main__":
    generate_context()
