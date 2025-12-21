#!/usr/bin/env python3
"""
Auto-update version.txt based on git commits.

Version format: 0.3.50b
- First number (0): placeholder
- Second number (3): iteration number
- Third number (50): commit counter (auto-incremented)
- 'b': beta suffix

Usage:
    python update_version.py          # Just update version.txt
    python update_version.py --stage  # Update and stage for commit
    python update_version.py --hook   # For use in git hooks (auto-stages)
"""

import re
import sys
import subprocess
from pathlib import Path


def get_git_root():
    """Get the git repository root directory."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not a git repo or git not available, use current directory
        return Path.cwd()


def read_current_version(version_file: Path) -> str:
    """Read current version from version.txt."""
    if not version_file.exists():
        print(f"Error: {version_file} not found!", file=sys.stderr)
        sys.exit(1)
    
    version = version_file.read_text(encoding='utf-8').strip()
    if not version:
        print(f"Error: {version_file} is empty!", file=sys.stderr)
        sys.exit(1)
    
    return version


def parse_version(version: str) -> tuple:
    """
    Parse version string into components.
    
    Format: 0.3.50b
    Returns: (major, iteration, commit_count, suffix)
    """
    # Match pattern: number.number.number + optional suffix
    pattern = r'^(\d+)\.(\d+)\.(\d+)([a-zA-Z]*)$'
    match = re.match(pattern, version)
    
    if not match:
        print(f"Error: Invalid version format: {version}", file=sys.stderr)
        print("Expected format: 0.3.50b (major.iteration.commit_count[suffix])", file=sys.stderr)
        sys.exit(1)
    
    major = int(match.group(1))
    iteration = int(match.group(2))
    commit_count = int(match.group(3))
    suffix = match.group(4) if match.group(4) else ''
    
    return major, iteration, commit_count, suffix


def increment_version(major: int, iteration: int, commit_count: int, suffix: str) -> str:
    """
    Increment the commit count in the version.
    
    Args:
        major: Major version number (placeholder)
        iteration: Iteration number
        commit_count: Current commit count
        suffix: Version suffix (e.g., 'b' for beta)
    
    Returns:
        New version string with incremented commit count
    """
    new_commit_count = commit_count + 1
    return f"{major}.{iteration}.{new_commit_count}{suffix}"


def update_version_file(version_file: Path, new_version: str):
    """Write new version to version.txt (single line, no trailing newline)."""
    version_file.write_text(new_version, encoding='utf-8')
    print(f"Updated {version_file.name} to {new_version}")


def stage_file(git_root: Path, file_path: Path):
    """Stage the version file for commit."""
    try:
        # Get relative path from git root
        rel_path = file_path.relative_to(git_root)
        subprocess.run(
            ['git', 'add', str(rel_path)],
            cwd=git_root,
            check=True,
            capture_output=True
        )
        print(f"Staged {rel_path} for commit")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not stage file: {e.stderr.decode()}", file=sys.stderr)
    except FileNotFoundError:
        print("Warning: git not found, skipping staging", file=sys.stderr)


def main():
    """Main function to update version."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Auto-update version.txt based on git commits'
    )
    parser.add_argument(
        '--stage',
        action='store_true',
        help='Stage version.txt for commit after updating'
    )
    parser.add_argument(
        '--hook',
        action='store_true',
        help='Run in hook mode (auto-stages file)'
    )
    parser.add_argument(
        '--file',
        type=str,
        default='version.txt',
        help='Path to version file (default: version.txt)'
    )
    
    args = parser.parse_args()
    
    # Determine if we should stage
    should_stage = args.stage or args.hook
    
    # Get paths
    git_root = get_git_root()
    version_file = git_root / args.file
    
    # Read current version
    current_version = read_current_version(version_file)
    print(f"Current version: {current_version}")
    
    # Parse and increment
    major, iteration, commit_count, suffix = parse_version(current_version)
    new_version = increment_version(major, iteration, commit_count, suffix)
    
    # Update file
    update_version_file(version_file, new_version)
    
    # Stage if requested
    if should_stage:
        stage_file(git_root, version_file)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

