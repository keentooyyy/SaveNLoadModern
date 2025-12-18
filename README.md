# SaveNLoadModern

<div align="center">

![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)

</div>

## About

SaveNLoadModern is a modern, web-based game save file management system built with Django. It provides a centralized platform for users to save, load, and manage their game progress across multiple games and save slots. The system features a client worker application that runs on user machines to handle local save file operations, SMB/CIFS network share integration for fast LAN storage, and a comprehensive admin dashboard for managing games, users, and operations.

### Key Features

- **Game Save Management**: Save and load game files with support for multiple save slots per game

- **Client Worker Application**: Standalone Python executable that runs on client PCs to handle save/load operations

- **SMB/CIFS Network Storage**: Fast SMB/CIFS (Windows Network Share) integration for storing save files on LAN (can achieve 100+ MB/s on gigabit networks)

- **User Authentication**: Custom authentication system with role-based access (Admin/User)

- **Admin Dashboard**: Comprehensive admin panel for managing games, users, and operations

- **RAWG API Integration**: Automatic game information retrieval using RAWG API for banners and metadata

- **Operation Queue**: Asynchronous operation queue system for handling save/load requests

- **Password Reset**: Secure OTP-based password reset functionality with email notifications

- **Multi-Save Support**: Support for up to 10 save folders per user per game

- **Modern UI**: Responsive Bootstrap 5 interface with custom styling

## Prerequisites

> **Recommended Deployment Method:** Docker is the recommended deployment method for SaveNLoadModern. Docker containers automatically manage the Django application, PostgreSQL database, and Node.js dependencies. However, a Windows Network Share (SMB/CIFS) must be configured separately on a Windows machine or SMB-compatible server.

Before setting up the project, ensure you have the following installed:

**Required:**
- **[Docker](https://www.docker.com/get-started)** and **Docker Compose** - Primary deployment method for the Django application and database
- **Windows Machine with Network Sharing** - A Windows PC or server with a shared folder configured for SMB/CIFS access (or Samba on Linux)

**Separate Services (Required, not included in Docker):**
- **Windows Network Share (SMB/CIFS)** - A shared folder on a Windows machine or SMB-compatible server for storing save files
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

## Project Setup

> **Deployment Recommendation:** Docker is the recommended deployment method for SaveNLoadModern. It automatically handles the Django application, PostgreSQL database, and Node.js dependencies. Note that a Windows Network Share (SMB/CIFS) must be configured separately on a Windows machine or SMB-compatible server, as it is not included in the Docker containers.

### Step 1: Environment Configuration

Create a `.env` file in the project root with the following variables:

```env
# Django Settings
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration
POSTGRES_DB=savenload_db
POSTGRES_USER=savenload_user
POSTGRES_PASSWORD=your-db-password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Email Configuration (Gmail)
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
EMAIL_ICON_URL=https://your-domain.com/static/images/icon.png

# Default Admin Account
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_EMAIL=admin@example.com
DEFAULT_ADMIN_PASSWORD=admin123

# RAWG API (Required for game search)
RAWG=your-rawg-api-key-here

# SMB/CIFS Configuration (for client worker and backend)
SMB_SERVER=192.168.88.101
SMB_SHARE=n_Saves
SMB_USERNAME=administrator
SMB_PASSWORD=123
SMB_DOMAIN=
SMB_PORT=445
```

> **Note:** For Gmail, you need to generate an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password. For production, set `DEBUG=False` and configure `ALLOWED_HOSTS` appropriately.

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

**Install Python Dependencies:**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Install Node.js Dependencies:**

```bash
npm install
npm run build
```

**Setup Database:**

1. Create PostgreSQL database:

```bash
createdb savenload_db
```

2. Run migrations:

```bash
python manage.py migrate
```

3. Create default admin user (optional, if not using Docker):

```bash
python manage.py create_default_admin
```

**Run Development Server:**

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Project Structure

```
SaveNLoadModern/
├── client_worker/              # Client worker application
│   ├── client_worker.py        # Main client worker logic
│   ├── client_service.py       # Service wrapper for Windows
│   ├── smb_client.py            # SMB/CIFS client implementation
│   ├── build_exe.py            # PyInstaller build script
│   ├── SaveNLoadClient.spec    # PyInstaller spec file
│   └── requirements.txt        # Client worker dependencies
│
├── config/                     # Django project configuration
│   ├── settings.py             # Django settings
│   ├── urls.py                # Root URL configuration
│   ├── wsgi.py                # WSGI configuration
│   └── asgi.py                # ASGI configuration
│
├── SaveNLoad/                  # Main Django application
│   ├── models/                 # Database models
│   │   ├── user.py            # User model
│   │   ├── game.py            # Game model
│   │   ├── save_folder.py    # Save folder model
│   │   ├── operation_queue.py # Operation queue model
│   │   ├── client_worker.py   # Client worker model
│   │   └── password_reset_otp.py # OTP model
│   │
│   ├── views/                  # View logic
│   │   ├── auth.py            # Authentication views
│   │   ├── dashboard.py       # Dashboard views
│   │   ├── save_load_api.py   # Save/load API endpoints
│   │   ├── client_worker_api.py # Client worker API
│   │   ├── rawg_api.py        # RAWG API integration
│   │   └── settings.py        # Settings views
│   │
│   ├── url_configs/           # URL routing
│   │   ├── user/              # User URLs
│   │   ├── admin/             # Admin URLs
│   │   └── client_worker/    # Client worker URLs
│   │
│   ├── templates/              # HTML templates
│   │   ├── SaveNLoad/         # App templates
│   │   │   ├── login.html
│   │   │   ├── register.html
│   │   │   ├── user/          # User dashboard
│   │   │   ├── admin/         # Admin dashboard
│   │   │   └── includes/      # Reusable components
│   │   └── base.html          # Base template
│   │
│   ├── utils/                  # Utility functions
│   │   └── email_service.py   # Email sending utilities
│   │
│   └── management/             # Management commands
│       └── commands/           # Custom commands
│
├── static/                      # Static files
│   ├── css/                    # Compiled CSS
│   ├── js/                     # JavaScript files
│   ├── scss/                   # Sass source files
│   └── images/                 # Images and icons
│
├── templates/                   # Global templates
├── media/                       # User uploaded media
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

## Key Systems

### Authentication System

- **Custom User Model**: Independent from Django's auth system
- **Role-Based Access**: Admin and User roles with different permissions
- **Session Management**: Django session-based authentication
- **Password Reset**: OTP-based password reset with email verification

### Game Management

- **Game Registration**: Add games manually or search via RAWG API
- **Save File Locations**: Configure save file paths for each game
- **Banner Images**: Automatic banner retrieval from RAWG API
- **Game Metadata**: Store game information and last played timestamps

### Save/Load System

- **Multiple Save Slots**: Support for up to 10 save folders per game per user
- **SMB/CIFS Storage**: Save files stored on Windows Network Share (SMB/CIFS) for fast LAN access
- **Operation Queue**: Asynchronous processing of save/load operations
- **Progress Tracking**: Track operation progress and status

### Client Worker

- **Standalone Application**: Python executable that runs on client PCs
- **Save Operations**: Upload local save files to SMB/CIFS network share
- **Load Operations**: Download save files from SMB/CIFS network share to local machine
- **API Integration**: Communicates with Django backend via REST API
- **Session Management**: Maintains authentication with Django server

### Admin Dashboard

- **User Management**: View and manage all users
- **Game Management**: Add, edit, and remove games
- **Operation Queue**: Monitor and manage save/load operations
- **Settings**: Configure system-wide settings
- **Statistics**: View usage statistics and analytics

## Building the Client Worker

The client worker is a standalone Python executable that users run on their machines.

### Development Build

```bash
cd client_worker
python build_exe.py
```

This will create `SaveNLoadClient.exe` in the `dist/` directory.

### Production Build

For production builds:

1. Ensure all dependencies are in `requirements.txt`
2. Run the build script:

```bash
cd client_worker
python build_exe.py --production
```

3. The executable will be in `client_worker/dist/SaveNLoadClient.exe`

### Client Worker Configuration

Users need to configure the client worker with:

- **Server URL**: Django server URL (e.g., `http://192.168.88.101:8000`)
- **Session Cookie**: Authentication cookie from web login
- **SMB/CIFS Credentials**: Set via environment variables or `.env` file (SMB_SERVER, SMB_SHARE, SMB_USERNAME, SMB_PASSWORD)

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

- `POST /api/save/` - Save game file
- `POST /api/load/` - Load game file
- `GET /api/save-folders/{game_id}/` - Get save folders for game
- `GET /api/operation-queue/` - Get operation queue status

### Client Worker API

- `POST /api/client-worker/register/` - Register client worker
- `GET /api/client-worker/status/` - Get client worker status
- `POST /api/client-worker/operation/` - Submit operation request

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

### SMB/CIFS Configuration

> **Important:** A Windows Network Share (SMB/CIFS) must be configured on a Windows machine or SMB-compatible server. It is not included in the Docker containers. The Django application and client worker connect to the SMB share via the SMB/CIFS protocol.

**Setting up Windows Network Share (Required):**

1. **Create a Shared Folder on Windows:**
   - Right-click on the folder you want to share (e.g., `C:\SaveNLoad` or `D:\Saves`)
   - Select "Properties" → "Sharing" tab
   - Click "Advanced Sharing"
   - Check "Share this folder"
   - Set a Share name (e.g., `n_Saves` or `SaveNLoad`)
   - Click "Permissions" and grant appropriate access (Read/Write) to the user account
   - Click "OK" to save

2. **Configure Network and Sharing Center:**
   - Open **Control Panel** → **Network and Internet** → **Network and Sharing Center**
   - Click "Change advanced sharing settings" in the left sidebar
   - Under "Private" network profile (or "All Networks" if needed):
     - Turn on "Network discovery"
     - Turn on "File and printer sharing"
     - Turn on "Turn on sharing so anyone with network access can read and write files in the Public folders" (if using Public folder)
   - Under "All Networks":
     - Turn off "Password protected sharing" (if you want easier access) OR
     - Turn on "Password protected sharing" (recommended for security) and ensure the user account has a password
   - Click "Save changes"

3. **Configure Windows Firewall (if needed):**
   - Ensure Windows Firewall allows SMB traffic (ports 445, 139)
   - File and Printer Sharing should be allowed through the firewall

4. **Note the SMB Share Details:**
   - **SMB Server**: IP address or hostname of the Windows machine (e.g., `192.168.88.101`)
   - **SMB Share**: The share name you configured (e.g., `n_Saves`)
   - **SMB Username**: Windows username with access to the share
   - **SMB Password**: Password for the Windows user account
   - **SMB Domain**: Leave empty for workgroup, or specify domain name if on a domain
   - **SMB Port**: Default is 445 (SMB over TCP/IP)

**Configure SMB Connection in Application:**

SMB settings are configured in the `.env` file (both Django backend and client worker):

```env
# SMB/CIFS Configuration (for client worker and backend)
SMB_SERVER=192.168.88.101        # IP address or hostname of Windows machine
SMB_SHARE=n_Saves                # Share name configured in Windows
SMB_USERNAME=administrator       # Windows username with share access
SMB_PASSWORD=your-password       # Password for the Windows user
SMB_DOMAIN=                      # Leave empty for workgroup, or domain name
SMB_PORT=445                     # Default SMB port
```

> **Note:** Ensure the Windows machine with the shared folder is accessible from both the Django server and client worker machines. The SMB share can be on the same machine as Docker or on a separate Windows server. The share must be accessible via UNC path: `\\SERVER_IP\SHARE_NAME`

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

## Development Notes

- **Static Files**: Use `npm run watch-css` to watch for SCSS changes during development
- **Migrations**: Run `python manage.py makemigrations` after model changes
- **Admin Panel**: Access at `/admin/` (requires admin account)
- **Debug Mode**: Set `DEBUG=True` in `.env` for development
- **Logging**: Logs are written to `logs/django.log`
- **Media Files**: User-uploaded files stored in `media/` directory
- **Session Storage**: Uses database-backed sessions

## Troubleshooting

### Database Connection Issues

If you encounter database connection errors:

1. **Check PostgreSQL Status**: Ensure PostgreSQL is running
2. **Check Credentials**: Verify database credentials in `.env`
3. **Check Host**: Use `localhost` for non-Docker, `db` for Docker
4. **Check Port**: Default PostgreSQL port is `5432`
5. **Check Database Exists**: Create database if it doesn't exist

### SMB/CIFS Connection Issues

If SMB operations fail:

1. **Check Windows Share**: Ensure the Windows machine is accessible and the share is properly configured
2. **Check Network Discovery**: Verify Network Discovery and File Sharing are enabled in Network and Sharing Center
3. **Check Credentials**: Verify SMB credentials in `.env` file (SMB_SERVER, SMB_SHARE, SMB_USERNAME, SMB_PASSWORD)
4. **Check Firewall**: Ensure Windows Firewall allows SMB traffic (ports 445, 139) and File and Printer Sharing
5. **Check Permissions**: Verify Windows user account has Read/Write permissions on the shared folder
6. **Check UNC Path**: Test accessing the share via UNC path: `\\SERVER_IP\SHARE_NAME` from Windows Explorer
7. **Check Network**: Ensure client can reach the Windows machine over the network (ping test)
8. **Check Advanced Sharing Settings**: Verify settings in Control Panel → Network and Internet → Network and Sharing Center → Advanced sharing settings
9. **Check Logs**: Review client worker and Django logs for detailed errors

### Email Sending Issues

If password reset emails don't send:

1. **Check Gmail App Password**: Ensure you're using App Password, not regular password
2. **Check 2FA**: Gmail requires 2FA enabled for App Passwords
3. **Check Credentials**: Verify `GMAIL_USER` and `GMAIL_APP_PASSWORD` in `.env`
4. **Check SMTP**: Test SMTP connection manually
5. **Check Logs**: Review `logs/django.log` for email errors

### Client Worker Issues

If client worker fails:

1. **Check Server URL**: Verify Django server is accessible
2. **Check Session Cookie**: Ensure valid session cookie is provided
3. **Check SMB Config**: Verify SMB credentials are set in `.env` (SMB_SERVER, SMB_SHARE, SMB_USERNAME, SMB_PASSWORD)
4. **Check Windows Share**: Verify the Windows share is accessible via UNC path (`\\SERVER_IP\SHARE_NAME`)
5. **Check Network**: Ensure client can reach both Django server and Windows SMB share
6. **Check Network Sharing Settings**: Verify Network Discovery and File Sharing are enabled in Windows Network and Sharing Center
7. **Check Logs**: Review client worker output for errors

### Build Errors

If Docker build fails:

1. **Check Dependencies**: Ensure all files are present
2. **Check Docker**: Verify Docker is running
3. **Check Ports**: Ensure ports 8000 and 5432 are available
4. **Check Logs**: Review Docker build logs
5. **Clean Build**: Try `docker-compose down -v` and rebuild

## Tech Stack

- **Backend Framework**: Django 6.0
- **Database**: PostgreSQL 16
- **Frontend**: Bootstrap 5.3, JavaScript (Vanilla)
- **Styling**: Sass/SCSS
- **Containerization**: Docker, Docker Compose
- **File Storage**: SMB/CIFS (Windows Network Share)
- **Email Service**: Gmail SMTP
- **Game API**: RAWG API
- **Client Worker**: Python 3.12, PyInstaller

## Dependencies

### Python Packages

- **Django**: Web framework
- **psycopg2-binary**: PostgreSQL adapter
- **python-dotenv**: Environment variable management
- **requests**: HTTP library for API calls
- **smbprotocol**: SMB/CIFS client library
- **gunicorn**: Production WSGI server
- **whitenoise**: Static file serving

### Node.js Packages

- **Bootstrap**: CSS framework
- **Sass**: CSS preprocessor

### Client Worker Packages

- **requests**: HTTP client
- **smbprotocol**: SMB operations
- **python-dotenv**: Environment variables
- **PyInstaller**: Executable building

## Production Deployment

> **Recommended Method:** Docker Compose is the recommended deployment method for production environments. It ensures consistent environments, simplifies scaling, and reduces maintenance overhead.

### Docker Compose Deployment (Recommended)

**Prerequisites:**
1. Set `DEBUG=False` in `.env`
2. Configure `ALLOWED_HOSTS` with your production domain
3. Generate a strong `SECRET_KEY`
4. Configure production database credentials
5. Set up SSL/HTTPS (recommended for production)

**Deployment:**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Docker Compose automatically handles:
- Service orchestration and networking
- Database initialization and migrations
- Static file collection
- Process management and health checks

### Manual Deployment (Alternative)

> **Note:** Manual deployment requires additional configuration and maintenance. Docker Compose is recommended for production environments.

1. Install production dependencies:

```bash
pip install gunicorn whitenoise
```

2. Collect static files:

```bash
python manage.py collectstatic
```

3. Run migrations:

```bash
python manage.py migrate
```

4. Start with Gunicorn:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

5. Configure reverse proxy (Nginx recommended) for SSL/HTTPS

## License

This project is for **personal use only**. Any commercial use is not the responsibility of the project maintainer. Users must ensure they have proper rights and licenses for all assets, libraries, and dependencies used in this project. The project maintainer assumes no liability for any misuse or unauthorized use of this software.

