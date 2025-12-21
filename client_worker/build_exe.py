"""
Build script for creating standalone executable
Run this script to build the client worker as a portable .exe file
"""
import PyInstaller.__main__
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get version from environment variable (default: 1.0.0)
APP_VERSION = os.getenv('APP_VERSION')

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()

def semantic_to_windows_version(semantic_version: str) -> str:
    """Convert semantic version (e.g., '1.0.0') to Windows format (e.g., '1.0.0.0')"""
    parts = semantic_version.split('.')
    while len(parts) < 3:
        parts.append('0')
    if len(parts) == 3:
        parts.append('0')
    return '.'.join(parts[:4])

def generate_manifest(manifest_path: Path):
    """Generate Windows manifest XML with version from environment variable"""
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
    print(f"Generated manifest with version {version} (from APP_VERSION={APP_VERSION})")

def build_exe():
    """Build standalone executable using PyInstaller"""
    
    print("=" * 60)
    print("Building SaveNLoad Client Worker Standalone Executable")
    print("=" * 60)
    print()
    
    # Generate manifest with version from environment variable
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
        print("1. Copy SaveNLoadClient.exe and the rclone/ folder to your desired location")
        print("2. Ensure rclone.exe and rclone.conf are in the rclone/ directory")
        print("3. Configure rclone.conf with your FTP server settings:")
        print("   [ftp]")
        print("   type = ftp")
        print("   host = your_ftp_host")
        print("   user = your_ftp_username")
        print("   pass = your_ftp_password")
        print("4. Create a .env file in the same directory with:")
        print("   - SAVENLOAD_SERVER_URL=http://192.168.88.X:8000")
        print("5. Run the executable (will request admin privileges)")
        print()
    except Exception as e:
        print(f"Error during build: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    build_exe()

