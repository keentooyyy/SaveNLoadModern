# SaveNLoad Client Worker

The Client Worker runs on each client PC to handle save/load operations with proper file system permissions.

## Architecture

```
1. Client Worker/Service (MUST RUN FIRST)
    ↓ (registers & sends heartbeats)
2. Django Server (tracks worker connection)
    ↓ (blocks web UI if worker not connected)
3. Web UI (Browser) - Only accessible if worker is connected
    ↓ (clicks Save/Load)
4. Django Server (sends operation to worker)
    ↓ (worker processes operation)
5. Client Worker (has file system access)
    ↓ (performs file operations)
6. Local Files + FTP Server
```

**Key Point:** The web UI cannot be accessed unless the client worker is running and connected!

## Why Client Worker is Needed

The Django server cannot directly access files on client PCs. The Client Worker:
- ✅ Runs on the client PC with proper permissions
- ✅ Can access local save files
- ✅ Handles FTP upload/download operations
- ✅ Communicates with Django server

## Setup

### 1. Install Dependencies

```bash
cd client_worker
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the `client_worker` directory:

```env
# FTP Server Configuration
FTP_HOST=192.168.88.101
FTP_PORT=21
FTP_USERNAME=your_ftp_username
FTP_PASSWORD=your_ftp_password

# Django Server URL
SAVENLOAD_SERVER_URL=http://192.168.88.101:8000

# Optional: Unique client identifier
CLIENT_ID=client_pc_1
```

### 3. Run the Client Worker

Simply run the client service:

```bash
python client_service.py --server http://192.168.88.101:8000
```

The client worker will run and poll the Django server for operations. Keep it running while you want to use save/load functionality.

## How It Works

1. **START CLIENT WORKER FIRST** - Run `python client_service.py`
2. **Client Worker registers** with Django server and starts sending heartbeats
3. **Django server tracks** worker connection status
4. **Web UI checks** if worker is connected before allowing access
5. **If worker not connected** - Web UI shows "Worker Required" page
6. **When user clicks Save/Load** in web UI:
   - Django server verifies worker is connected
   - Django server sends operation to worker
   - Client worker performs the file operation
   - Client worker reports result back to Django server
7. **Web UI updates** with success/error message

## Permissions

The Client Worker needs:
- ✅ Read/write access to game save directories
- ✅ Network access to Django server and FTP server
- ✅ Run with appropriate permissions to access save file locations

## Troubleshooting

**Check logs:**
- Windows: `%USERPROFILE%\.savenload\logs\client_worker.log`
- Linux: `~/.savenload/logs/client_worker.log`

**Verify connection:**
- Ensure Django server is accessible
- Ensure FTP server is accessible
- Check firewall settings

**Permission issues:**
- Run as administrator (Windows) or with sudo (Linux)
- Check file/folder permissions for save directories

