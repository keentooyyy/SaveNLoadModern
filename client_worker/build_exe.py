"""
Build script for creating standalone executable
Run this script to build the client worker as a portable .exe file
"""
import PyInstaller.__main__
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get script directory
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

# Import standalone version utility (no Django dependencies)
from version_utils import get_app_version

# Load environment variables
load_dotenv()

# Get version from GitHub or local version.txt file
# Can override GitHub URL via VERSION_GITHUB_URL environment variable
# Checks parent directory (project root) first, then current directory
APP_VERSION = get_app_version(
    base_dir=PROJECT_ROOT,
    github_url=os.getenv('VERSION_GITHUB_URL')
)

def semantic_to_windows_version(semantic_version: str) -> str:
    """
    Convert semantic version (e.g., '1.0.0') to Windows format (e.g., '1.0.0.0').
    
    If version couldn't be retrieved (error message), returns '0.0.0.0' as fallback.
    """
    # Handle error case where version couldn't be retrieved
    if 'couldn\'t get version' in semantic_version.lower() or not semantic_version:
        print("Warning: Using fallback version '0.0.0.0' for Windows manifest", file=sys.stderr)
        return '0.0.0.0'
    
    parts = semantic_version.split('.')
    while len(parts) < 3:
        parts.append('0')
    if len(parts) == 3:
        parts.append('0')
    return '.'.join(parts[:4])

def generate_manifest(manifest_path: Path):
    """
    Generate Windows manifest XML with version from GitHub or local version.txt file.
    
    The version is fetched from:
    1. GitHub (if VERSION_GITHUB_URL is set and accessible)
    2. Local version.txt file (fallback)
    3. Error message if both fail (will use '0.0.0.0' for Windows manifest)
    """
    version = semantic_to_windows_version(APP_VERSION)
    
    manifest_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity
    version="{version}"
    processorArchitecture="*"
    name="SaveNLoadClient"
    type="win32"
  />
  <description>SaveNLoad Client Worker - Requires administrator privileges for file operations</description>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
</assembly>
'''
    
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest_xml, encoding='utf-8')
    print(f"Generated manifest with version {version} (semantic version: {APP_VERSION})")

def build_exe():
    """Build standalone executable using PyInstaller"""
    
    print("=" * 60)
    print("Building SaveNLoad Client Worker Standalone Executable")
    print("=" * 60)
    print(f"Version: {APP_VERSION}")
    print()
    
    # Generate manifest with version from GitHub or local version.txt
    manifest_path = SCRIPT_DIR / "SaveNLoadClient.manifest"
    generate_manifest(manifest_path)
    print()
    
    # Check if spec file exists
    spec_file = SCRIPT_DIR / "SaveNLoadClient.spec"
    if not spec_file.exists():
        print("Error: SaveNLoadClient.spec not found!")
        print("Please ensure you're running this from the client_worker directory.")
        sys.exit(1)
    
    print("Using spec file:", spec_file)
    print("Output will be in: dist/SaveNLoadClient.exe")
    print()
    
    try:
        # Use the spec file for building
        PyInstaller.__main__.run([
            str(spec_file),
            '--clean',  # Clean cache before building
        ])
        print()
        print("=" * 60)
        print("Build completed successfully!")
        print("=" * 60)
        print(f"Executable location: {SCRIPT_DIR / 'dist' / 'SaveNLoadClient.exe'}")
        print()
        print("Next steps:")
        print("1. Copy SaveNLoadClient.exe to your desired location")
        print("   (The executable is self-contained - rclone and config are bundled inside)")
        print("2. Create a .env file in the same directory with:")
        print("   - SAVENLOAD_SERVER_URL=http://YOUR_SERVER_IP:8001")
        print("   - REDIS_HOST=YOUR_REDIS_HOST")
        print("   - REDIS_PORT=6379")
        print("   - REDIS_PASSWORD=YOUR_REDIS_PASSWORD (leave empty if none)")
        print("   - VERSION_GITHUB_URL=... (Optional)")
        print("3. Run the executable (will request admin privileges)")
        print()
    except Exception as e:
        print(f"Error during build: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    build_exe()

