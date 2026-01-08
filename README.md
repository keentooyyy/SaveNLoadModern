# SaveNLoadModern

<div align="center">

![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192?style=for-the-badge&logo=postgresql&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=for-the-badge&logo=docker&logoColor=white) ![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)

</div>

## About

SaveNLoadModern is a web-based game save file management system built with Django. It gives users a central place to save, load, and manage game progress across multiple titles and save slots. A client worker runs on user machines to handle local file operations, while the backend manages authentication, metadata, and an async operation queue. Save files are stored remotely via rclone (typically to an FTP server).

### Architecture Overview

- **Django Backend**: Auth, game database, operation queue, API endpoints
- **Redis**: Operation queue, progress updates, worker heartbeat
- **Frontend (Vite + Vue)**: Built into static assets for Django/WhiteNoise in production
- **Client Worker**: Standalone Windows executable that performs save/load/delete operations
- **Remote Storage**: FTP (or any rclone-compatible backend)
- **Operation Flow**: Backend queues work in Redis → client worker polls → executes → reports progress

## Key Features

- Multi-game save management with up to 10 save slots per user per game
- Multi-path save/load support (games with multiple save locations)
- Client worker for local file operations and progress reporting
- Rclone-based FTP transfer support with parallel transfers
- Custom authentication with admin and user roles
- Admin dashboard for games, users, and operations
- RAWG API integration for game metadata and banners
- OTP-based password reset via email
- Quick access to local save locations
- Modern Bootstrap-based UI

## Prerequisites

> **Recommended Deployment Method:** Docker is the primary deployment path. Docker containers handle Django, PostgreSQL, Redis, and Node dependencies.

**Required:**
- **[Docker](https://www.docker.com/get-started)** and **Docker Compose** (includes Redis)
- **Remote Storage**: FTP server or any rclone-compatible backend
- **[rclone](https://rclone.org/downloads/)** (required only for building the client worker)

**Separate Services (required, not included in Docker):**
- **FTP Server**: Accessible from both the server and client worker machines
- **Gmail Account**: For email notifications (requires App Password)

**Optional (manual setup only):**
- **[Python 3.12](https://www.python.org/downloads/)**
- **[PostgreSQL 16](https://www.postgresql.org/download/)**
- **[Node.js 20.x](https://nodejs.org/)**

Verify Docker:

```bash
docker --version
docker-compose --version
```

### Redis Requirement

SaveNLoadModern depends on Redis for:
- Operation queueing
- Real-time progress updates
- Worker presence (pings/heartbeats)

**Docker Deployment** includes Redis automatically.
**Manual Deployment** requires a separate Redis instance.

## FTP Server Setup (Required)

The Django backend does not store files. All file operations are performed by the client worker using rclone. You must set up an FTP server separately.

1. Install FTP software (FileZilla Server, vsftpd, IIS FTP, etc.)
2. Create a user with read/write access
3. Configure ports (21 control + passive ports if enabled)
4. Record credentials and host details

Helpful resources:
- [FileZilla Server video guide](https://www.youtube.com/watch?time_continue=31&v=XXLnkeNjdCo)
- [FileZilla Server documentation](https://filezillapro.com/docs/server/basic-usage-instructions-server/configure-filezilla-server/)

## Project Setup

### Step 1: Environment Configuration

Create a `.env` file in the project root:

```env
# DJANGO CONFIGS
DEBUG=True
POSTGRES_DB=savenload
POSTGRES_USER=django
POSTGRES_PASSWORD=your-db-password-here
POSTGRES_HOST=db
POSTGRES_PORT=5432
SECRET_KEY=your-secret-key-here

# Default admin account
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_EMAIL=admin@example.com
DEFAULT_ADMIN_PASSWORD=your-admin-password-here

# Admin password reset (manage accounts feature)
RESET_PASSWORD_DEFAULT=ResetPassword123

# Redis Configuration
# For Docker: REDIS_HOST=redis
# For Local: REDIS_HOST=localhost
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1
REDIS_PASSWORD=

# Version
VERSION_GITHUB_URL=https://raw.githubusercontent.com/keentooyyy/SaveNLoadModern/refs/heads/main/version.txt
```

Notes:
- Use a Gmail App Password for SMTP
- Set `DEBUG=False` and configure `ALLOWED_HOSTS` for production
- Save file storage is handled by the client worker via rclone

### Step 2: Docker Deployment (Recommended)

**Development:**

```bash
docker-compose up --build
```

This will:
- Build containers
- Initialize PostgreSQL
- Run migrations
- Install npm dependencies and compile CSS
- Start the Django dev server

Visit `http://localhost:8000`.

**Production:**

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

This will:
- Build the production image (including Vite assets)
- Run migrations and collect static files on startup
- Serve assets via WhiteNoise

### Step 3: Manual Setup (Alternative)

Manual setup is intended only if Docker is not available. For full instructions, see [Manual Production Deployment](#manual-production-deployment).

## Building the Client Worker

The client worker is a standalone Windows executable that performs local file operations and reports progress back to the server.

### Prerequisites

- Python 3.12
- PyInstaller (via `client_worker/requirements.txt`)
- `rclone.exe` in `client_worker/rclone/`
- `rclone.conf` in `client_worker/rclone/`

### Step 1: Build Environment

```bash
cd client_worker
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 2: Configure rclone

> **Important:** The rclone configuration is bundled into the executable during build. Configure rclone before building.

1. Download rclone from [rclone.org](https://rclone.org/downloads/)
2. Place `rclone.exe` in `client_worker/rclone/`
3. Configure an FTP remote named `ftp`:

```bash
rclone.exe config
```

Copy the generated config to:

```
%APPDATA%\rclone\rclone.conf -> client_worker\rclone\rclone.conf
```

### Step 3: Build the Executable

```bash
python build_exe.py
```

Build output:
- `client_worker/dist/SaveNLoadClient.exe`
- `client_worker/build/` (safe to delete)

The build script reads version info from `VERSION_GITHUB_URL` (if set) or falls back to `version.txt` in the repo root.

### Step 4: Distribution Package

```
SaveNLoadClient/
├── SaveNLoadClient.exe
└── .env
```

### Step 5: User Configuration

Create a `.env` file next to `SaveNLoadClient.exe`:

```env
SAVENLOAD_SERVER_URL=http://YOUR_SERVER_IP:8000
VERSION_GITHUB_URL=https://raw.githubusercontent.com/keentooyyy/SaveNLoadModern/refs/heads/main/version.txt
```

### Step 6: Running the Client Worker

1. Run `SaveNLoadClient.exe` and approve admin privileges
2. Log in to the web UI (if prompted)
3. Use **Connect Device** to claim your worker
4. The worker will poll every 5 seconds and process queued operations

## Configuration

### Database

```env
POSTGRES_DB=savenload_db
POSTGRES_USER=savenload_user
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=db  # Use localhost for non-Docker
POSTGRES_PORT=5432
```

### Feature Flags and System Settings

Feature flags and integration settings are stored in the `system_settings` table and managed through **Admin Settings**. Defaults are seeded via migrations.

Feature flags:
- `feature.rawg.enabled` (bool, default `False`) - Enables RAWG integration
- `feature.email.enabled` (bool, default `False`) - Enables SMTP email features
- `feature.email.registration_required` (bool, default `True`) - Require email registration flows
- `feature.guest.enabled` (bool, default `False`) - Enables guest accounts
- `feature.guest.ttl_days` (int, default `14`) - Guest account TTL (1-14 days)

Integration settings:
- `rawg.api_key` (string, default empty) - RAWG API key (stored encrypted)
- `email.gmail_user` (string, default empty) - Gmail username
- `email.gmail_app_password` (string, default empty) - Gmail App Password (stored encrypted)
- `reset.default_password` (string, default empty) - Admin reset password default (stored encrypted)

### FTP (Client Worker)

FTP credentials live only in `client_worker/rclone/rclone.conf`. The backend never stores FTP credentials.

Non-interactive setup:

```bash
rclone.exe config create ftp ftp host=YOUR_FTP_SERVER_IP user=your_ftp_username pass=your_ftp_password
```

### Email

Gmail credentials are stored in **Admin Settings**. Use an App Password for SMTP.

### RAWG API

A RAWG API key is required for game search. Add it in **Admin Settings**.

## Production Deployment

**Recommended:** Docker Compose

```bash
docker-compose -f docker-compose.prod.yml up -d
```

Optional Vite preview:

```bash
docker-compose -f docker-compose.prod.yml --profile frontend up -d
```

## Key Systems

### Authentication

- Custom user model (separate from Django auth)
- Role-based access (Admin/User)
- Session-based auth
- OTP-based password reset

### Game Management

- Manual game registration or RAWG search
- Multiple save paths per game
- Banner and metadata storage
- Automated path mapping for multi-path games

### Save/Load System

- Up to 10 save slots per user per game
- Multi-path operations for games with multiple save locations
- Organized FTP storage (path_1, path_2, ...)
- Async operations with progress updates
- Backup downloads and local folder open shortcuts

### Client Worker

- Standalone Windows executable
- Rclone transfers with parallel workers
- Local save upload/download with progress
- Automatic folder creation and opening
- REST API communication with the backend

### Admin Dashboard

- User and account management
- Game management with multi-path support
- Operation queue monitoring
- System settings and statistics

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running
- Confirm credentials in `.env`
- Use `db` for Docker and `localhost` for manual setup
- Ensure port `5432` is open
- Create the database if missing

### FTP Connection Issues

- Confirm FTP server is reachable
- Verify credentials with `rclone.exe config show ftp`
- Ensure port 21 and passive ports are open
- Verify `rclone.exe` and `rclone.conf` exist in `client_worker/rclone/`
- Review client worker logs for transfer errors

### Email Sending Issues

- Use Gmail App Passwords (not the account password)
- Confirm SMTP credentials in Admin Settings
- Check Docker logs (`docker-compose logs web`) or console output

### Client Worker Issues

- Confirm `SAVENLOAD_SERVER_URL` is correct
- Log in to the web UI to refresh session cookies
- Rebuild if FTP settings change
- Run as administrator for file operations
- Review console output for errors

### Build Errors

- Ensure Python 3.12 is installed
- Install dependencies in `client_worker/` (`pip install -r requirements.txt`)
- Verify `rclone.exe` is present before building
- Install PyInstaller if missing (`pip install pyinstaller`)

## Project Structure

```
SaveNLoadModern/
├── client_worker/              # Client worker application
│   ├── client_service_rclone.py # Main client worker service
│   ├── rclone_client.py         # Rclone-based FTP client
│   ├── version_utils.py         # Version checking utilities
│   ├── rclone/                  # Rclone executable and config (for building)
│   │   ├── rclone.exe           # Rclone Windows executable (bundled into .exe)
│   │   └── rclone.conf          # Rclone FTP configuration (bundled into .exe)
│   ├── build_exe.py             # PyInstaller build script
│   ├── SaveNLoadClient.spec     # PyInstaller spec file
│   ├── requirements.txt         # Client worker dependencies
│   ├── dist/                    # Build output (after building)
│   │   └── SaveNLoadClient.exe  # Self-contained executable
│   └── build/                   # Build artifacts
│
├── config/                     # Django project configuration
│   ├── settings.py             # Django settings
│   ├── urls.py                 # Root URL configuration
│   ├── wsgi.py                 # WSGI configuration
│   └── asgi.py                 # ASGI configuration
│
├── SaveNLoad/                  # Main Django application
│   ├── legacy/                 # Legacy code and templates
│   ├── management/             # Management commands
│   ├── migrations/             # Database migrations
│   ├── models/                 # Database models
│   ├── services/               # Business logic services
│   ├── static/                 # App static files
│   ├── templates/              # App templates
│   ├── url_configs/            # URL routing
│   ├── utils/                  # Utility functions
│   ├── views/                  # View logic
│   └── ws_consumers/           # WebSocket consumers
│
├── frontend/                   # Vue + Vite frontend
├── static/                     # Static files
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
├── manage.py                   # Django management script
├── update_version.py           # Version update script
└── version.txt                 # Local version fallback
```

## Tech Stack

- **Backend**: Django 6.0
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis
- **Frontend**: Vue 3 + Vite
- **Styling**: Bootstrap 5.3, Sass/SCSS
- **Containerization**: Docker, Docker Compose
- **File Storage**: FTP via rclone
- **Email**: Gmail SMTP
- **Game API**: RAWG API
- **Client Worker**: Python 3.12, PyInstaller

## Manual Production Deployment

> **Note:** Docker Compose is recommended for production. Use manual deployment only when Docker is not available.

**Prerequisites:**
- [Python 3.12](https://www.python.org/downloads/)
- [PostgreSQL 16](https://www.postgresql.org/download/)
- [Redis](https://redis.io/download/)
- [Node.js 20.x](https://nodejs.org/)

**Setup Steps:**

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
npm install
npm run build

createdb savenload_db
redis-cli ping

python manage.py migrate
python manage.py seed_admin
python manage.py collectstatic --noinput

gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 120
```

Process management:
- **Windows**: NSSM or Task Scheduler
- **Linux**: systemd or supervisor

## License

This project is for **personal use only**. Any commercial use is not the responsibility of the project maintainer. Users must ensure they have proper rights and licenses for all assets, libraries, and dependencies used in this project.
