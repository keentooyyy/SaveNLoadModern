# SaveNLoadModern

<div align="center">

![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)

</div>

## About

SaveNLoadModern is a modern, web-based game save file management system built with Django. It provides a centralized platform for users to save, load, and manage their game progress across multiple games and save slots. The system features a client worker application that runs on user machines to handle local save file operations, FTP storage integration using rclone for reliable file transfers, and a comprehensive admin dashboard for managing games, users, and operations.

### Architecture Overview

- **Django Backend**: Manages user authentication, game database, operation queue, and API endpoints
- **Client Worker**: Standalone executable that runs on user PCs to perform actual file operations (save/load/delete)
- **FTP Server**: Stores all save files (configured separately, accessible via rclone)
- **Operation Flow**: Backend queues operations → Client worker polls and executes → Results reported back to backend

### Key Features

- **Game Save Management**: Save and load game files with support for multiple save slots per game
- **Multi-Path Save/Load**: Support for games with multiple save file locations - all paths are saved/loaded simultaneously with automatic subfolder organization
- **Client Worker Application**: Standalone Python executable that runs on client PCs to handle save/load operations
- **FTP Storage**: FTP storage integration using rclone for reliable file transfers with progress tracking and parallel transfers
- **User Authentication**: Custom authentication system with role-based access (Admin/User)
- **Admin Dashboard**: Comprehensive admin panel for managing games, users, and operations
- **Admin Account Management**: Searchable user management interface for admins to view users and reset passwords
- **RAWG API Integration**: Automatic game information retrieval using RAWG API for banners and metadata
- **Operation Queue**: Asynchronous operation queue system for handling save/load requests
- **Password Reset**: Secure OTP-based password reset functionality with email notifications
- **Multi-Save Support**: Support for up to 10 save folders per user per game
- **Open Save Location**: Quick access to open save file locations directly from the game management interface
- **Modern UI**: Responsive Bootstrap 5 interface with custom styling

## Prerequisites

> **Recommended Deployment Method:** Docker is the recommended deployment method for SaveNLoadModern. Docker containers automatically manage the Django application, PostgreSQL database, and Node.js dependencies.

Before setting up the project, ensure you have the following installed:

**Required:**
- **[Docker](https://www.docker.com/get-started)** and **Docker Compose** - Primary deployment method for the Django application and database
- **FTP Server** - An FTP server for storing save files (can be on the same machine or separate server)
- **[rclone](https://rclone.org/downloads/)** - Required for client worker file transfers (Windows executable needed for building client worker)

**Separate Services (Required, not included in Docker):**
- **FTP Server** - An FTP server accessible from both the Django server and client worker machines
- **Gmail Account** - Required for email notifications (requires App Password)

**Optional (for manual setup only):**
- **[Python 3.12](https://www.python.org/downloads/)** - Required only if not using Docker
- **[PostgreSQL 16](https://www.postgresql.org/download/)** - Required only if not using Docker
- **[Node.js 20.x](https://nodejs.org/)** - Required only if not using Docker (automatically handled by Docker)

You can verify Docker installation with:

```bash
docker --version
docker-compose --version
```

## FTP Server Setup

> **Important:** An FTP server must be configured separately and accessible from client worker machines. The Django backend does NOT handle file storage - it only manages the operation queue. All file operations are performed by the client worker using rclone.

You need to install and configure an FTP server yourself. The Django backend does not include an FTP server - you must set one up separately.

### Step 1: Install FTP Server Software

- **Recommended**: [FileZilla Server](https://filezilla-project.org/download.php?type=server) (Free, Windows/Linux)
- **Alternatives**: vsftpd (Linux), Windows IIS FTP, or any other FTP server software

### Step 2: Configure FTP Server

1. Create a user account with read/write permissions
2. Configure the FTP server to listen on port 21 (default) or your preferred port
3. Set up a directory for storing save files
4. Ensure firewall allows FTP traffic (ports 21 for control, and passive mode ports if enabled)

### Step 3: FileZilla Server Setup Resources

- **[Official FileZilla Server Video Tutorial](https://www.youtube.com/watch?time_continue=31&v=XXLnkeNjdCo)** - Step-by-step video guide
- **[Official FileZilla Server Documentation](https://filezillapro.com/docs/server/basic-usage-instructions-server/configure-filezilla-server/)** - Complete configuration guide

### Step 4: Note FTP Server Details

After setting up your FTP server, note the following details (you'll need these later):

- **FTP Host**: IP address or hostname of the FTP server (e.g., `YOUR_FTP_SERVER_IP` or `192.168.1.100`)
- **FTP Username**: Username for FTP access
- **FTP Password**: Password for the FTP user account

> **Note:** You'll configure these credentials in the client worker using rclone (see "Building the Client Worker" section).

## Project Setup

### Step 1: Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# DJANGO CONFIGS
DEBUG=True
POSTGRES_DB=savenload
POSTGRES_USER=django
POSTGRES_PASSWORD=your-db-password-here
POSTGRES_HOST=db
POSTGRES_PORT=5432
SECRET_KEY=your-secret-key-here

# RAWG API
RAWG=your-rawg-api-key-here

# Email Configuration (Gmail SMTP)
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-gmail-app-password-here
EMAIL_ICON_URL=https://i.ibb.co/5Xpxrkh7/icon.png

# Default admin account
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_EMAIL=admin@example.com
DEFAULT_ADMIN_PASSWORD=your-admin-password-here

# Admin password reset (for manage accounts feature)
RESET_PASSWORD_DEFAULT=ResetPassword123

# Version
VERSION_GITHUB_URL=https://raw.githubusercontent.com/keentooyyy/SaveNLoadModern/refs/heads/main/version.txt
```

> **Note:** 
> - For Gmail, you need to generate an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password
> - For production, set `DEBUG=False` and configure `ALLOWED_HOSTS` appropriately
> - File storage is handled entirely by the client worker via rclone - no backend storage configuration needed
> - `RESET_PASSWORD_DEFAULT` is used by admins to reset user passwords through the "Manage Accounts" feature. This password will be set when an admin resets a user's password.

### Step 2: Docker Deployment (Recommended)

Docker deployment automatically handles all system dependencies and configuration. This method is recommended for both development and production environments.

**Benefits of Docker Deployment:**
- Automatic dependency management (Python, PostgreSQL, Node.js)
- Consistent environments across different systems
- Simplified database setup and migrations
- Integrated service orchestration
- Reduced configuration complexity

**Development Environment:**

```bash
docker-compose up --build
```

This command will:
- Build the Docker containers
- Initialize PostgreSQL database
- Run database migrations
- Install npm dependencies and compile CSS
- Start the Django development server

The application will be available at `http://localhost:8000`

**Production Environment:**

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

> **Note:** Docker deployment eliminates dependency conflicts and ensures consistent environments. Manual setup should only be used when Docker is not available.

### Step 3: Manual Setup (Alternative)

> **Note:** Manual setup requires installing and configuring Python, PostgreSQL, Node.js, and all dependencies individually. This method is more complex and time-consuming than Docker deployment. Use this method only if Docker is not available in your environment.
> 
> For detailed manual setup instructions (development and production), see the [Manual Production Deployment](#manual-production-deployment) section at the bottom of this document.

## Building the Client Worker

The client worker is a standalone Python executable that users run on their Windows machines to handle save/load operations. It communicates with the Django backend via REST API and uses rclone for file transfers.

### Prerequisites for Building

Before building the client worker, ensure you have:

1. **Python 3.12** installed on your build machine
2. **PyInstaller** (will be installed automatically via requirements.txt)
3. **rclone.exe** in `client_worker/rclone/` directory
4. **rclone.conf** configured in `client_worker/rclone/` directory

### Step 1: Setup Build Environment

1. Navigate to the client worker directory:

```bash
cd client_worker
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

3. Install build dependencies:

```bash
pip install -r requirements.txt
```

This will install:
- `requests` - HTTP client for API communication
- `python-dotenv` - Environment variable management
- `pyinstaller` - Executable builder
- `rich` - Rich text and beautiful formatting for terminal output

### Step 2: Configure Rclone

> **IMPORTANT: Rclone MUST be configured BEFORE building the executable!** The rclone configuration (`rclone.conf`) is bundled into the executable during the build process. If you build without configuring rclone first, the executable will not have FTP access configured and will need to be rebuilt.

Before building, ensure rclone is properly configured:

1. **Download rclone**: Get the Windows executable from [rclone.org](https://rclone.org/downloads/)
2. **Place rclone.exe**: Copy `rclone.exe` to `client_worker/rclone/` directory
3. **Configure FTP Remote**: Use rclone's interactive configuration to set up the FTP remote:

```bash
# First, configure rclone (creates config in default location)
# You can run rclone from anywhere, or use the one in client_worker/rclone/
rclone.exe config

# Follow the prompts:
# 1. Type 'n' to create a new remote
# 2. Enter a name for the remote (e.g., 'ftp')
# 3. Select 'ftp' as the storage type (type the number for FTP)
# 4. Enter your FTP server host/IP
# 5. Enter your FTP username
# 6. Enter your FTP password
# 7. Configure other options as needed (or press Enter for defaults)
# 8. Type 'y' to confirm and save
```

**Example Configuration Flow:**
```
> rclone.exe config
Current remotes:

Name                 Type
====                 ====

e) Edit existing remote
n) New remote
d) Delete remote
r) Rename remote
c) Copy remote
s) Set configuration password
q) Quit config
e/n/d/r/c/s/q> n
name> ftp
Storage> 4  # Select FTP (number may vary)
FTP host to connect to> YOUR_FTP_SERVER_IP
FTP username> your_ftp_username
FTP password> [enter your password]
Use FTP over TLS (SSL)?> n
Edit advanced config?> n
Remote config
--------------------
[ftp]
type = ftp
host = YOUR_FTP_SERVER_IP
user = your_ftp_username
pass = *** ENCRYPTED ***
--------------------
y) Yes this is OK
e) Edit this remote
d) Delete this remote
y/e/d> y
```

4. **Copy rclone.conf to client_worker directory**: After configuration, copy the rclone config file from the default location (`%APPDATA%\rclone\rclone.conf`) to `client_worker/rclone/` directory.

> **CRITICAL NOTES:** 
> - **You MUST configure rclone BEFORE building the executable** - the configuration is bundled into the .exe during build
> - You must download `rclone.exe` manually and place it in `client_worker/rclone/` directory before building
> - The `rclone.exe` and `rclone.conf` files are bundled into the final executable during the PyInstaller build process
> - The configuration file must be manually copied from the default rclone location (`%APPDATA%\rclone\rclone.conf`) to `client_worker/rclone/` directory before building
> - If you need to change FTP settings after building, you must reconfigure rclone and rebuild the executable
> - For more detailed configuration options, see the [rclone config command documentation](https://rclone.org/commands/rclone_config/)

### Step 3: Build the Executable

> **IMPORTANT: Ensure rclone is configured (Step 2) before building!** The build process bundles `rclone.exe` and `rclone.conf` into the executable. If rclone is not configured before building, you will need to configure it and rebuild.

Run the build script:

```bash
python build_exe.py
```

This will:
- Fetch version from GitHub (if `VERSION_GITHUB_URL` is set in `.env`) or use local `version.txt` file
- Generate Windows manifest with version information
- Use PyInstaller to bundle all dependencies
- Include rclone.exe and rclone.conf in the executable
- Create `SaveNLoadClient.exe` in the `dist/` directory
- Request admin privileges (UAC) when running

> **Note:** The build script automatically fetches the version from GitHub (configured via `VERSION_GITHUB_URL` in `.env`) or falls back to the local `version.txt` file in the project root. This version is embedded in the Windows executable manifest.

**Build Output:**
- Executable: `client_worker/dist/SaveNLoadClient.exe` (includes rclone.exe and rclone.conf bundled inside)
- Build artifacts: `client_worker/build/` (can be deleted after build)

> **Note:** The executable is self-contained - rclone.exe and rclone.conf are bundled into the executable during the PyInstaller build process. Users only need the `.exe` file and a `.env` file for configuration.

### Step 4: Prepare Distribution Package

After building, create a distribution package for users:

1. **Required Files:**
   - `SaveNLoadClient.exe` (from `dist/` folder - includes rclone bundled inside)
   - `.env` file (for server URL configuration)

2. **Optional Files:**
   - `.env.example` template file (for reference)
   - README or setup instructions

3. **Directory Structure for Distribution:**
```
SaveNLoadClient/
├── SaveNLoadClient.exe  (self-contained, includes rclone)
└── .env                 (required for server URL)
```

### Step 5: User Configuration

Users need to configure the client worker before first use:

1. **Server URL Configuration:**
   - Create a `.env` file in the same directory as `SaveNLoadClient.exe`
   - Add the Django server URL and optional version URL:
   ```env
   # Django Server URL
   SAVENLOAD_SERVER_URL=http://YOUR_SERVER_IP:8000
   
   # Version (Optional - for version checking)
   VERSION_GITHUB_URL=https://raw.githubusercontent.com/keentooyyy/SaveNLoadModern/refs/heads/main/version.txt
   ```
   - Replace `YOUR_SERVER_IP` with your actual Django server IP/domain

2. **FTP Configuration:**
   - The rclone configuration is bundled in the executable
   - If you need to reconfigure FTP settings, you can extract rclone from the executable or rebuild with a new `rclone.conf`
   - For build-time configuration, see Step 2 in build instructions
   - The FTP remote must be named `ftp` in the rclone configuration (default remote name)

3. **Session Cookie (First Run):**
   - The client worker will open a browser window
   - User must log in to the web interface
   - The session cookie will be automatically captured

### Step 6: Running the Client Worker

1. **First Run:**
   - Double-click `SaveNLoadClient.exe`
   - Grant admin privileges when prompted (required for file operations)
   - Browser window will open for authentication
   - Log in to the web interface
   - Client worker will start polling for operations

2. **Subsequent Runs:**
   - Double-click `SaveNLoadClient.exe`
   - Grant admin privileges
   - Client worker will use saved session cookie

3. **Operation:**
   - Client worker runs in the background
   - Polls Django server every 5 seconds for pending operations
   - Automatically processes save/load/delete operations
   - Sends progress updates to the web interface

### Build Troubleshooting

**Issue: PyInstaller not found**
```bash
pip install pyinstaller
```

**Issue: rclone.exe not found**
- Ensure `rclone.exe` is in `client_worker/rclone/` directory
- Download from [rclone.org](https://rclone.org/downloads/) if missing

**Issue: Build fails with import errors**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that virtual environment is activated

**Issue: Executable is too large**
- This is normal - PyInstaller bundles Python interpreter and all dependencies
- Typical size: 50-100 MB
- Can be reduced with UPX compression (enabled by default)

**Issue: Executable doesn't run on other machines**
- Ensure target machine has Windows 10/11
- May need Visual C++ Redistributable (usually pre-installed)
- Check Windows Defender isn't blocking the executable

## Configuration

### Database Configuration

The application uses PostgreSQL. Configure connection in `.env`:

```env
POSTGRES_DB=savenload_db
POSTGRES_USER=savenload_user
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=db  # Use 'localhost' for non-Docker setup
POSTGRES_PORT=5432
```

### FTP Configuration in Client Worker

FTP settings are configured during the build process. The rclone configuration is bundled into the executable:

1. **Before Building:** Configure rclone in `client_worker/rclone/` directory:
   ```bash
   # Navigate to rclone directory
   cd client_worker/rclone
   
   # Run rclone config
   rclone.exe config
   
   # Follow prompts to create/edit 'ftp' remote
   # See "Building the Client Worker" section for detailed instructions
   ```

2. **Or use command-line configuration (non-interactive):**
   ```bash
   rclone.exe config create ftp ftp host=YOUR_FTP_SERVER_IP user=your_ftp_username pass=your_ftp_password
   ```

3. **The `rclone.conf` file** in `client_worker/rclone/` will be bundled into the executable during the PyInstaller build process.

> **Note:** 
> - The FTP server must be accessible from client worker machines
> - The FTP server can be on the same machine as Django or on a separate server
> - The rclone executable (`rclone.exe`) and configuration file (`rclone.conf`) are bundled into the final executable - no separate rclone folder needed for distribution
> - The Django backend does NOT need FTP credentials - it only manages the operation queue
> - For advanced configuration options, see the [rclone config command documentation](https://rclone.org/commands/rclone_config/)

### Email Configuration

Gmail SMTP settings for password reset emails:

```env
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
EMAIL_ICON_URL=https://your-domain.com/static/images/icon.png
```

> **Note:** Gmail requires an [App Password](https://support.google.com/accounts/answer/185833) for SMTP authentication. Regular passwords won't work.

### RAWG API

The application uses RAWG API for game information. **An API key is required** for game search functionality. 

To get a free API key:
1. Visit [RAWG API](https://rawg.io/apidocs)
2. Sign up for a free account
3. Get your API key from the dashboard
4. Add it to your `.env` file as `RAWG=your_api_key_here`

The API key must be set in your environment variables (or `.env` file) for the game search feature to work.

## Production Deployment

> **Recommended Method:** Docker Compose is the recommended deployment method for production environments. It ensures consistent environments, simplifies scaling, and reduces maintenance overhead.

### Docker Compose Deployment (Recommended)

**Prerequisites:**
1. Set `DEBUG=False` in `.env`
2. Configure `ALLOWED_HOSTS` with your production domain (or use `*` for local deployment)
3. Generate a strong `SECRET_KEY`
4. Configure production database credentials
5. Set up SSL/HTTPS (only needed if exposing to the internet; not required for local deployment)

**Deployment:**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Docker Compose automatically handles:
- Service orchestration and networking
- Database initialization and migrations
- Static file collection
- Process management and health checks

> **Alternative:** For manual deployment without Docker, see the [Manual Production Deployment](#manual-production-deployment) section at the bottom of this document.

## Key Systems

### Authentication System

- **Custom User Model**: Independent from Django's auth system
- **Role-Based Access**: Admin and User roles with different permissions
- **Session Management**: Django session-based authentication
- **Password Reset**: OTP-based password reset with email verification

### Game Management

- **Game Registration**: Add games manually or search via RAWG API
- **Multiple Save File Locations**: Configure multiple save file paths for each game (supports games that save to multiple directories)
- **Banner Images**: Automatic banner retrieval from RAWG API
- **Game Metadata**: Store game information and last played timestamps
- **Path Management**: Automatic path mapping and subfolder organization for multi-path games

### Save/Load System

- **Multiple Save Slots**: Support for up to 10 save folders per game per user
- **Multi-Path Support**: Games with multiple save locations are automatically handled - all paths are saved/loaded simultaneously
- **Path Organization**: Multiple save paths are organized into subfolders (path_1, path_2, etc.) on the FTP server for proper organization
- **FTP Storage**: Save files stored on FTP server using rclone for reliable transfers
- **Operation Queue**: Asynchronous processing of save/load operations with support for parallel multi-path operations
- **Progress Tracking**: Real-time progress tracking with file counts and transfer speeds for all paths
- **Empty Save Validation**: Automatic validation to prevent saving empty directories or files
- **Backup Operations**: Download all saves, zip them, and save to local Downloads folder
- **Open Save Location**: Quick access to open save file locations (opens all paths for multi-path games)

### Client Worker

- **Standalone Application**: Python executable that runs on client PCs
- **Rclone Integration**: Uses rclone for fast, reliable FTP file transfers with parallel workers
- **Save Operations**: Upload local save files to FTP server with progress tracking (supports multiple paths simultaneously)
- **Load Operations**: Download save files from FTP server to local machine with progress tracking (supports multiple paths simultaneously)
- **Multi-Path Operations**: Automatically handles games with multiple save locations - processes all paths in parallel
- **Backup Operations**: Download all saves for a game, zip them, and save to Downloads folder
- **Open Folder Operations**: Create local folders if needed and open them in file explorer (supports multiple paths)
- **API Integration**: Communicates with Django backend via REST API
- **Session Management**: Maintains authentication with Django server
- **Real-time Progress**: Sends real-time progress updates to web UI during transfers for all operations

### Admin Dashboard

- **User Management**: View and manage all users with searchable interface
- **Account Management**: Reset user passwords to default constant value (useful for password recovery)
- **Game Management**: Add, edit, and remove games with support for multiple save file locations
- **Operation Queue**: Monitor and manage save/load operations
- **Settings**: Configure system-wide settings
- **Statistics**: View usage statistics and analytics

## API Endpoints

### Authentication

- `POST /api/login/` - User login
- `POST /api/register/` - User registration
- `POST /api/logout/` - User logout
- `POST /api/forgot-password/` - Request password reset OTP
- `POST /api/verify-otp/` - Verify OTP and reset password

### Game Management

- `GET /api/games/` - List all games
- `POST /api/games/add/` - Add new game
- `GET /api/games/{id}/` - Get game details
- `PUT /api/games/{id}/` - Update game
- `DELETE /api/games/{id}/` - Delete game
- `GET /api/games/search/` - Search games via RAWG API

### Save/Load Operations

- `POST /api/save/{game_id}/` - Save game file (supports multiple save paths)
- `POST /api/load/{game_id}/` - Load game file (supports multiple save paths)
- `GET /api/save-folders/{game_id}/` - Get save folders for game
- `POST /api/open-save-location/{game_id}/` - Open save file location(s) in file explorer
- `GET /api/operation-queue/` - Get operation queue status

### Admin API (Admin Only)

- `GET /admin/users/` - List all users (with optional search query parameter)
- `POST /admin/users/{user_id}/reset-password/` - Reset user password to default constant value

### Client Worker API

- `POST /api/client-worker/register/` - Register client worker
- `GET /api/client-worker/operations/` - Get pending operations
- `POST /api/client-worker/progress/{operation_id}/` - Update operation progress
- `POST /api/client-worker/complete/{operation_id}/` - Mark operation complete

## Troubleshooting

### Database Connection Issues

If you encounter database connection errors:

1. **Check PostgreSQL Status**: Ensure PostgreSQL is running
2. **Check Credentials**: Verify database credentials in `.env`
3. **Check Host**: Use `localhost` for non-Docker, `db` for Docker
4. **Check Port**: Default PostgreSQL port is `5432`
5. **Check Database Exists**: Create database if it doesn't exist

### FTP Connection Issues

If FTP operations fail:

1. **Check FTP Server**: Ensure the FTP server is running and accessible
2. **Check Network**: Ensure client worker can reach the FTP server over the network (ping test)
3. **Check Credentials**: Verify FTP credentials using `rclone.exe config show ftp` or check `rclone.conf` (NOT in Django .env)
4. **Check Firewall**: Ensure firewall allows FTP traffic (port 21 for control, and passive mode ports if enabled)
5. **Check Permissions**: Verify FTP user account has Read/Write permissions on the FTP directory
6. **Check Rclone**: Ensure `rclone.exe` is in `client_worker/rclone/` directory
7. **Check Rclone Config**: Verify FTP remote is configured correctly using `rclone.exe config show ftp` or reconfigure with `rclone.exe config`
8. **Test FTP Connection**: Test FTP connection manually using an FTP client or rclone command line
9. **Check Logs**: Review client worker output for detailed errors

> **Note:** FTP issues are client worker issues, not Django backend issues. The Django backend only manages the operation queue.

### Email Sending Issues

If password reset emails don't send:

1. **Check Gmail App Password**: Ensure you're using App Password, not regular password
2. **Check 2FA**: Gmail requires 2FA enabled for App Passwords
3. **Check Credentials**: Verify `GMAIL_USER` and `GMAIL_APP_PASSWORD` in `.env`
4. **Check SMTP**: Test SMTP connection manually
5. **Check Logs**: Review `logs/django.log` for email errors

### Client Worker Issues

If client worker fails:

1. **Check Server URL**: Verify Django server is accessible (test in browser)
2. **Check .env File**: Ensure `SAVENLOAD_SERVER_URL` is set correctly in client worker directory (and optionally `VERSION_GITHUB_URL` for version checking)
3. **Check Session Cookie**: Ensure valid session cookie (log in via web interface first)
4. **Check Rclone**: Rclone is bundled in the executable - if FTP connection fails, the rclone configuration may need to be updated and the executable rebuilt
5. **Check Rclone Config**: The rclone configuration is bundled in the executable - verify FTP settings were correct during build (host, user, pass in `client_worker/rclone/rclone.conf`)
6. **Check FTP Server**: Verify the FTP server is accessible and credentials are correct
7. **Check Network**: Ensure client can reach both Django server and FTP server
8. **Check Admin Privileges**: Client worker requires admin privileges for file operations
9. **Check Logs**: Review client worker console output for errors

### Build Errors

If Docker build fails:

1. **Check Dependencies**: Ensure all files are present
2. **Check Docker**: Verify Docker is running
3. **Check Ports**: Ensure ports 8000 and 5432 are available
4. **Check Logs**: Review Docker build logs
5. **Clean Build**: Try `docker-compose down -v` and rebuild

If client worker build fails:

1. **Check Python Version**: Ensure Python 3.12 is installed
2. **Check Dependencies**: Run `pip install -r requirements.txt` in client_worker directory
3. **Check Rclone**: Ensure `rclone.exe` is in `client_worker/rclone/` directory before building (it will be bundled into the executable)
4. **Check Virtual Environment**: Ensure virtual environment is activated
5. **Check PyInstaller**: Verify PyInstaller is installed: `pip install pyinstaller`

## Project Structure

```
SaveNLoadModern/
├── client_worker/              # Client worker application
│   ├── client_service_rclone.py # Main client worker service
│   ├── rclone_client.py         # Rclone-based FTP client
│   ├── rclone/                  # Rclone executable and config (for building)
│   │   ├── rclone.exe          # Rclone Windows executable (bundled into .exe)
│   │   └── rclone.conf         # Rclone FTP configuration (bundled into .exe)
│   ├── build_exe.py            # PyInstaller build script
│   ├── SaveNLoadClient.spec    # PyInstaller spec file
│   ├── requirements.txt        # Client worker dependencies
│   ├── dist/                    # Build output (after building)
│   │   └── SaveNLoadClient.exe # Self-contained executable (includes rclone)
│   └── build/                   # Build artifacts (can be deleted)
│
├── config/                     # Django project configuration
│   ├── settings.py             # Django settings
│   ├── urls.py                 # Root URL configuration
│   ├── wsgi.py                 # WSGI configuration
│   └── asgi.py                 # ASGI configuration
│
├── SaveNLoad/                  # Main Django application
│   ├── models/                 # Database models
│   │   ├── user.py             # User model
│   │   ├── game.py             # Game model
│   │   ├── save_folder.py     # Save folder model
│   │   ├── operation_queue.py  # Operation queue model
│   │   ├── client_worker.py    # Client worker model
│   │   └── password_reset_otp.py # OTP model
│   │
│   ├── views/                  # View logic
│   │   ├── auth.py             # Authentication views
│   │   ├── dashboard.py        # Dashboard views
│   │   ├── save_load_api.py    # Save/load API endpoints
│   │   ├── client_worker_api.py # Client worker API
│   │   ├── rawg_api.py         # RAWG API integration
│   │   └── settings.py         # Settings views
│   │
│   ├── url_configs/            # URL routing
│   │   ├── user/               # User URLs
│   │   ├── admin/               # Admin URLs
│   │   └── client_worker/      # Client worker URLs
│   │
│   ├── templates/              # HTML templates
│   │   ├── SaveNLoad/          # App templates
│   │   │   ├── login.html
│   │   │   ├── register.html
│   │   │   ├── user/           # User dashboard
│   │   │   ├── admin/          # Admin dashboard
│   │   │   └── includes/       # Reusable components
│   │   └── base.html           # Base template
│   │
│   ├── utils/                  # Utility functions
│   │   └── email_service.py    # Email sending utilities
│   │
│   └── management/             # Management commands
│       └── commands/           # Custom commands
│
├── static/                     # Static files
│   ├── css/                    # Compiled CSS
│   ├── js/                     # JavaScript files
│   ├── scss/                   # Sass source files
│   └── images/                 # Images and icons
│
├── templates/                  # Global templates
├── media/                      # User uploaded media
├── postgres_data/              # PostgreSQL data (Docker)
│
├── docker-compose.yml          # Development Docker config
├── docker-compose.prod.yml     # Production Docker config
├── Dockerfile                  # Development Dockerfile
├── Dockerfile.prod             # Production Dockerfile
├── requirements.txt            # Python dependencies
├── package.json                # Node.js dependencies
└── manage.py                   # Django management script
```

## Development Notes

- **Static Files**: Use `npm run watch-css` to watch for SCSS changes during development
- **Migrations**: Run `python manage.py makemigrations` after model changes
- **Admin Panel**: Access at `/admin/` (requires admin account)
- **Debug Mode**: Set `DEBUG=True` in `.env` for development
- **Logging**: Logs are written to `logs/django.log`
- **Media Files**: User-uploaded files stored in `media/` directory
- **Session Storage**: Uses database-backed sessions

## Tech Stack

- **Backend Framework**: Django 6.0
- **Database**: PostgreSQL 16
- **Frontend**: Bootstrap 5.3, JavaScript (Vanilla)
- **Styling**: Sass/SCSS
- **Containerization**: Docker, Docker Compose
- **File Storage**: FTP
- **File Transfer**: rclone (for client worker FTP operations)
- **Email Service**: Gmail SMTP
- **Game API**: RAWG API
- **Client Worker**: Python 3.12, PyInstaller

## Dependencies

### Python Packages

- **Django**: Web framework
- **psycopg2-binary**: PostgreSQL adapter
- **python-dotenv**: Environment variable management
- **requests**: HTTP library for API calls
- **gunicorn**: Production WSGI server
- **whitenoise**: Static file serving

### Node.js Packages

- **Bootstrap**: CSS framework
- **Sass**: CSS preprocessor

### Client Worker Packages

- **requests**: HTTP client for API communication
- **python-dotenv**: Environment variable management
- **PyInstaller**: Executable building
- **rich**: Rich text and beautiful formatting for terminal output
- **rclone**: External executable for FTP operations (included in `rclone/` directory)

## Manual Production Deployment

> **Note:** Manual deployment requires additional configuration and maintenance. Docker Compose is recommended for production environments. Only use this method if Docker is not available in your environment.

**Prerequisites:**
- **[Python 3.12](https://www.python.org/downloads/)** installed
- **[PostgreSQL 16](https://www.postgresql.org/download/)** installed and running
- **[Node.js 20.x](https://nodejs.org/)** installed

**Setup Steps:**

1. **Create and activate virtual environment:**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

2. **Install Python dependencies:**

```bash
pip install -r requirements.txt
```

This installs all required packages including Django, PostgreSQL adapter, gunicorn, whitenoise, and other dependencies. See `requirements.txt` for the complete list.

3. **Install Node.js dependencies and build CSS:**

```bash
npm install
npm run build
```

See `package.json` for the complete list of Node.js dependencies.

4. **Setup PostgreSQL database:**

```bash
# Create database (if not exists)
createdb savenload_db
```

5. **Configure environment variables:**

Ensure your `.env` file is properly configured with production settings:
- Set `DEBUG=False`
- Configure `ALLOWED_HOSTS` with your production domain
- Set strong `SECRET_KEY`
- Configure production database credentials
- Set email and RAWG API credentials

6. **Run database migrations:**

```bash
python manage.py migrate
```

7. **Create admin user (if not exists):**

```bash
python manage.py seed_admin
```

8. **Collect static files:**

```bash
python manage.py collectstatic --noinput
```

9. **Start with Gunicorn:**

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 120
```

**Process Management (Recommended for Production):**

For production environments, use a process manager to automatically restart Gunicorn if it crashes:

- **Windows**: Use [NSSM (Non-Sucking Service Manager)](https://nssm.cc/) to run Gunicorn as a Windows service, or use Windows Task Scheduler to run it at startup
- **Linux**: Use systemd or supervisor to manage the Gunicorn process

**Optional: Reverse Proxy (For External Access Only):**

If you need to expose the application to the internet (not just local network), set up a reverse proxy like Nginx in front of Gunicorn for better performance and SSL/HTTPS termination. For local deployment, this is not necessary.

## License

This project is for **personal use only**. Any commercial use is not the responsibility of the project maintainer. Users must ensure they have proper rights and licenses for all assets, libraries, and dependencies used in this project. The project maintainer assumes no liability for any misuse or unauthorized use of this software.
