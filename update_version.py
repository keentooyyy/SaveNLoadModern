#!/usr/bin/env python3
"""
Simple version updater.
Format: 0.3.50b (major.iteration.count[suffix])
"""
import re
from pathlib import Path

def main():
    # Assume version.txt is in the same directory as this script
    version_file = Path(__file__).parent / 'version.txt'
    
    if not version_file.exists():
        print(f"Error: {version_file} not found")
        return

    current_version = version_file.read_text(encoding='utf-8').strip()
    print(f"Current version: {current_version}")
    
    # Match pattern: number.number.number + optional suffix
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)([a-zA-Z]*)$', current_version)
    
    if not match:
        print(f"Error: Invalid version format: {current_version}")
        return
    
    major, iteration, count, suffix = match.groups()
    new_version = f"{major}.{iteration}.{int(count) + 1}{suffix}"
    
    version_file.write_text(new_version, encoding='utf-8')
    print(f"Updated to: {new_version}")

if __name__ == '__main__':
    main()
