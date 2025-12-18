# SaveNLoadModern

<div align="center">

![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)

</div>

## About

SaveNLoadModern is a modern, web-based game save file management system built with Django. It provides a centralized platform for users to save, load, and manage their game progress across multiple games and save slots. The system features a client worker application that runs on user machines to handle local save file operations, FTP integration for cloud storage, and a comprehensive admin dashboard for managing games, users, and operations.

### Key Features

- **Game Save Management**: Save and load game files with support for multiple save slots per game

- **Client Worker Application**: Standalone Python executable that runs on client PCs to handle save/load operations

- **FTP Cloud Storage**: Secure FTP server integration for storing save files remotely

- **User Authentication**: Custom authentication system with role-based access (Admin/User)

- **Admin Dashboard**: Comprehensive admin panel for managing games, users, and operations

- **RAWG API Integration**: Automatic game information retrieval using RAWG API for banners and metadata

- **Operation Queue**: Asynchronous operation queue system for handling save/load requests

- **Password Reset**: Secure OTP-based password reset functionality with email notifications

- **Multi-Save Support**: Support for up to 10 save folders per user per game

- **Modern UI**: Responsive Bootstrap 5 interface with custom styling

## Prerequisites

> **Recommended Deployment Method:** Docker is the recommended deployment method for SaveNLoadModern. Docker containers automatically manage the Django application, PostgreSQL database, and Node.js dependencies. However, FileZilla Server must be installed separately as a standalone service.

Before setting up the project, ensure you have the following installed:

**Required:**
- **[Docker](https://www.docker.com/get-started)** and **Docker Compose** - Primary deployment method for the Django application and database

**Separate Services (Required, not included in Docker):**
- **[FileZilla Server](https://filezilla-project.org/download.php?type=server)** - FTP server for storing save files (must be installed separately on the host system or a remote server)
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

> **Deployment Recommendation:** Docker is the recommended deployment method for SaveNLoadModern. It automatically handles the Django application, PostgreSQL database, and Node.js dependencies. Note that FileZilla Server must be installed separately as a standalone service, as it is not included in the Docker containers.

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

# FTP Configuration (for client worker)
FTP_HOST=your-ftp-server.com
FTP_PORT=21
FTP_USERNAME=your-ftp-username
FTP_PASSWORD=your-ftp-password
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
│   ├── ftp_client.py           # FTP client implementation
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
- **FTP Storage**: Save files stored on FTP server for cloud access
- **Operation Queue**: Asynchronous processing of save/load operations
- **Progress Tracking**: Track operation progress and status

### Client Worker

- **Standalone Application**: Python executable that runs on client PCs
- **Save Operations**: Upload local save files to FTP server
- **Load Operations**: Download save files from FTP to local machine
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
- **FTP Credentials**: Set via environment variables or `.env` file

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

### FTP Configuration

> **Important:** FileZilla Server is a separate service that must be installed independently on your host system or a remote server. It is not included in the Docker containers. The Django application connects to FileZilla Server via FTP protocol.

> **Recommended:** [FileZilla Server](https://filezilla-project.org/download.php?type=server) is recommended for FTP file storage. It provides a free, reliable, and easy-to-configure solution that integrates seamlessly with SaveNLoadModern.

**Setting up FileZilla Server (Separate Installation Required):**

1. Download and install [FileZilla Server](https://filezilla-project.org/download.php?type=server) on your host system or a dedicated FTP server
2. Launch FileZilla Server Admin and create a user account
3. Configure a shared folder for save files with appropriate permissions
4. Note the FTP server hostname/IP address, port, username, and password

**Configure FTP Connection in Client Worker:**

FTP settings are configured in the client worker's `.env` file:

```env
FTP_HOST=your-ftp-server.com  # IP address or hostname of FileZilla Server
FTP_PORT=21
FTP_USERNAME=your-username     # User account created in FileZilla Server
FTP_PASSWORD=your-password     # Password for the FileZilla Server user
```

> **Note:** Ensure FileZilla Server is running and accessible from both the Django server and client worker machines. The FTP server can be on the same machine as Docker or on a separate server.

### Email Configuration

Gmail SMTP settings for password reset emails:

```env
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
EMAIL_ICON_URL=https://your-domain.com/static/images/icon.png
```

> **Note:** Gmail requires an [App Password](https://support.google.com/accounts/answer/185833) for SMTP authentication. Regular passwords won't work.

### RAWG API

The application uses RAWG API for game information. No API key is required for basic usage, but you can configure one in `SaveNLoad/views/rawg_api.py` for higher rate limits.

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

### FTP Connection Issues

If FTP operations fail:

1. **Check FTP Server**: Ensure FTP server is accessible (recommended: [FileZilla Server](https://filezilla-project.org/download.php?type=server))
2. **Check Credentials**: Verify FTP credentials in client worker `.env`
3. **Check Firewall**: Ensure FTP port (21) is not blocked
4. **Check Permissions**: Verify FTP user has write permissions
5. **Check Logs**: Review client worker logs for detailed errors

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
3. **Check FTP Config**: Verify FTP credentials are set
4. **Check Network**: Ensure client can reach server and FTP
5. **Check Logs**: Review client worker output for errors

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
- **File Storage**: [FileZilla Server](https://filezilla-project.org/download.php?type=server)
- **Email Service**: Gmail SMTP
- **Game API**: RAWG API
- **Client Worker**: Python 3.12, PyInstaller

## Dependencies

### Python Packages

- **Django**: Web framework
- **psycopg2-binary**: PostgreSQL adapter
- **python-dotenv**: Environment variable management
- **requests**: HTTP library for API calls
- **ftputil**: FTP client library
- **gunicorn**: Production WSGI server
- **whitenoise**: Static file serving

### Node.js Packages

- **Bootstrap**: CSS framework
- **Sass**: CSS preprocessor

### Client Worker Packages

- **requests**: HTTP client
- **ftputil**: FTP operations
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

