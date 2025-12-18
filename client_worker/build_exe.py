"""
Build script for creating standalone executable
Run this script to build the client worker as a portable .exe file
"""
import PyInstaller.__main__
import os
import sys
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()

def build_exe():
    """Build standalone executable using PyInstaller"""
    
    print("=" * 60)
    print("Building SaveNLoad Client Worker Standalone Executable")
    print("=" * 60)
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
        print("2. Create a .env file in the same directory with:")
        print("   - SMB_SERVER=your_smb_server")
        print("   - SMB_SHARE=your_share_name")
        print("   - SMB_USERNAME=your_username")
        print("   - SMB_PASSWORD=your_password")
        print("   - SMB_DOMAIN=")
        print("   - SMB_PORT=445")
        print("   - SAVENLOAD_SERVER_URL=http://192.168.88.X:8000")
        print("3. Run the executable (will request admin privileges)")
        print()
        print("See BUILD.md for more details.")
    except Exception as e:
        print(f"Error during build: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    build_exe()

