# File Operation Flow - Step by Step Guide

## Assumptions
- User is authenticated and logged in
- User has valid session
- User has access to the game they're operating on
- Client worker is running on user's machine

---

## Worker-Session Association (Automatic)

**How Worker Gets Associated with User Session:**
- When worker registers → If user is logged in, `client_id` stored in session
- When worker sends heartbeat → If user is logged in, `client_id` updated in session; if user is logged out, `client_id` cleared from session
- When frontend checks connection → If user is logged in and worker is online, `client_id` stored/updated in session; if user is logged out, `client_id` cleared
- When user logs out → Session is flushed (all data cleared including `client_id`)
- This happens automatically - no manual configuration needed

**Revocation on Logout:**
- User logs out → `session.flush()` clears all session data including `client_id`
- Worker continues running → Next heartbeat detects user is logged out → Clears `client_id` from session (if it exists)
- This ensures worker association is revoked when user logs out, even if worker keeps running

---

## Scenario 1: SAVE Operation (Normal Flow)

### Step-by-Step Flow:

**1. User Initiates Save**
- User clicks "Save" button in UI
- Frontend sends POST to `/api/save-game/<game_id>/`
- Request body: `{ "local_save_path": "C:/Games/MyGame/saves" }`
  - Note: Worker is ALWAYS auto-assigned from session (no client_id needed in request)

**2. Backend Processing**
- ✅ Validates user is authenticated
- ✅ Validates game exists
- ✅ Validates local_save_path is provided
- ✅ **Worker Assignment (MANDATORY - From Session)**: 
  - Gets `client_id` from user's session (automatically set by worker registration/heartbeat)
  - If `client_id` found and worker is online → uses that worker
  - **CRITICAL**: If no `client_id` in session → **ERROR 503**: "No client worker available" - **Operation is NOT created**
  - **CRITICAL**: If worker is offline → **ERROR 503**: "Client worker is offline" - **Operation is NOT created**
  - App requires worker to function - no fallback to other workers
- ✅ **Database**: Read SaveFolders for user+game, Create/Update SaveFolder if needed
- ✅ **Database**: Create OperationQueue record (status='pending', client_worker assigned)
- ✅ Returns: `{ "operation_id": 123, "client_id": "PC-001", "save_folder_number": 1 }`

**3. Worker Polling**
- Worker polls `/api/client-worker/<client_id>/operations/` every 5 seconds
- **Database**: Check stuck operations (IN_PROGRESS > 30 min) → Update status='failed'
- **Database**: Atomic read+update - Get PENDING operations, Update status='in_progress'
- Backend returns operations to worker

**4. Worker Processing**
- Worker receives operation: `{ "type": "save", "local_save_path": "...", "remote_path": "user/gamename/save_1" }`
- Worker validates local path exists
- Worker uses rclone to upload files to FTP
- **Database**: Update OperationQueue progress (multiple times during upload)
- Worker completes: `POST /api/client-worker/<client_id>/operation/<id>/complete/`

**5. Operation Completion**
- **If FTP Success**: **Database**: Update OperationQueue status='completed', result_data stored
- **If FTP Failure**: **Database**: Update OperationQueue status='failed', error_message stored
- **Database**: SaveFolder remains in database (already created in step 2)

**6. Frontend Polling**
- Frontend polls `/api/check-operation-status/<operation_id>/`
- Status: PENDING → IN_PROGRESS → COMPLETED/FAILED
- Shows progress bar with file counts

**Result**: 
- ✅ **FTP Success**: SaveFolder exists in DB, OperationQueue status='completed', files on FTP
- ❌ **FTP Failure**: SaveFolder exists in DB, OperationQueue status='failed', no files on FTP

---

## Scenario 2: SAVE Operation - No Worker Available

### Flow:

**1-2. Same as Normal Flow**

**3. Worker Assignment Fails**
- `get_client_worker_or_error()` returns error
- **ERROR 503**: `{ "error": "No client worker available", "requires_worker": true }`

**Result**: ❌ Operation never created, user sees error message

---

## Scenario 3: SAVE Operation - Worker Goes Offline During Processing

### Flow:

**1-4. Same as Normal Flow (operation starts processing)**

**5. Worker Crashes/Goes Offline**
- Worker stops sending heartbeats
- Operation remains IN_PROGRESS
- After 30 minutes: Operation marked as FAILED (timeout)

**6. Frontend Polling**
- Frontend polls status
- Status: IN_PROGRESS → FAILED
- Error message: "Operation timed out after 30 minutes"

**Result**: ❌ Operation failed, user must retry

---

## Scenario 4: LOAD Operation (Normal Flow)

### Step-by-Step Flow:

**1. User Initiates Load**
- User clicks "Load" button
- Frontend sends POST to `/api/load-game/<game_id>/`
- Request body: `{ "local_save_path": "C:/Games/MyGame/saves", "save_folder_number": 1 }`

**2. Backend Processing**
- ✅ Validates user, game, save folder exists
- ✅ **Worker Assignment**: Uses `client_id` from session
  - If worker is online → uses that worker
  - If no `client_id` in session or worker offline → **ERROR 503**
- ✅ **Database**: Read SaveFolder by number
- ✅ **Database**: Create OperationQueue record (status='pending', client_worker assigned)
- ✅ Returns: `{ "operation_id": 124, "client_id": "PC-001" }`

**3. Worker Polling**
- **Database**: Atomic read+update - Get PENDING operations, Update status='in_progress'

**4. Worker Processing**
- Worker downloads files from FTP using rclone
- **Database**: Update OperationQueue progress (multiple times during download)

**5. Operation Completion**
- **If FTP Success**: **Database**: Update OperationQueue status='completed'
- **If FTP Failure**: **Database**: Update OperationQueue status='failed', error_message stored
- **Database**: SaveFolder remains unchanged

**Result**: 
- ✅ **FTP Success**: Files downloaded to local, OperationQueue status='completed'
- ❌ **FTP Failure**: No files downloaded, OperationQueue status='failed'

---

## Scenario 5: DELETE Save Folder Operation

### Step-by-Step Flow:

**1. User Initiates Delete**
- User clicks "Delete Save" button
- Frontend sends POST to `/api/delete-save-folder/<game_id>/`
- Request body: `{ "save_folder_number": 1 }`

**2. Backend Processing**
- ✅ Validates save folder exists and belongs to user
- ✅ **Worker Assignment**: Uses `client_id` from session
  - If worker is online → uses that worker
  - If no `client_id` in session or worker offline → **ERROR 503**
- ✅ **Database**: Read SaveFolder by number
- ✅ **Database**: Create OperationQueue record (status='pending', client_worker assigned)
- ✅ Returns: `{ "operation_id": 125 }`

**3. Worker Polling**
- **Database**: Atomic read+update - Get PENDING operations, Update status='in_progress'

**4. Worker Processing**
- Worker uses rclone to delete remote directory: `ftp:user/gamename/save_1`

**5. Operation Completion**
- **If FTP Success**: 
  - **Database**: Update OperationQueue status='completed'
  - **Database**: Delete SaveFolder from database
- **If FTP Failure**: 
  - **Database**: Update OperationQueue status='failed', error_message stored
  - **Database**: SaveFolder remains in database (not deleted)

**Result**: 
- ✅ **FTP Success**: SaveFolder deleted from DB, OperationQueue status='completed', files deleted from FTP
- ❌ **FTP Failure**: SaveFolder remains in DB, OperationQueue status='failed', files remain on FTP

---

## Scenario 6: DELETE All Saves Operation

### Step-by-Step Flow:

**1. User Initiates Delete All**
- User clicks "Delete All Saves" button
- Frontend sends POST to `/api/delete-all-saves/<game_id>/`

**2. Backend Processing**
- ✅ **Database**: Read all SaveFolders for user+game
- ✅ **Worker Assignment**: Uses `client_id` from session
  - If worker is online → uses that worker
  - If no `client_id` in session or worker offline → **ERROR 503**
- ✅ **Database**: Create multiple OperationQueue records (one per save folder, all assigned to same worker)
- ✅ Returns: `{ "operation_ids": [126, 127, 128] }`

**3. Worker Processing (Sequential)**
- Worker processes each DELETE operation one by one
- **Database**: Update each OperationQueue status='in_progress' (as worker picks it up)
- Each operation deletes one save folder from FTP

**4. Operation Completion (Per Operation)**
- **If FTP Success**: 
  - **Database**: Update OperationQueue status='completed'
  - **Database**: Delete corresponding SaveFolder from database
- **If FTP Failure**: 
  - **Database**: Update OperationQueue status='failed', error_message stored
  - **Database**: SaveFolder remains in database

**Result**: 
- ✅ **All FTP Success**: All SaveFolders deleted from DB, all OperationQueue status='completed', all files deleted from FTP
- ⚠️ **Partial Success**: Some SaveFolders deleted, some remain (failed operations), OperationQueue shows mixed statuses
- ❌ **All FTP Failure**: All SaveFolders remain in DB, all OperationQueue status='failed', files remain on FTP

---

## Scenario 7: Admin DELETE Game Operation

### Step-by-Step Flow:

**1. Admin Initiates Game Deletion**
- Admin clicks "Delete Game" button
- Frontend sends DELETE to `/api/admin/game/<game_id>/`

**2. Backend Processing**
- ✅ Validates admin is authenticated
- ✅ **Database**: Read all SaveFolders for this game (across ALL users)
- ✅ **Worker Assignment**: Uses `client_id` from session
  - If worker is online → uses that worker
  - If no `client_id` in session or worker offline → **ERROR 503** - Game deletion BLOCKED
- ✅ **Database**: Create OperationQueue records (one per user's game directory, all assigned to admin's worker)
- ✅ **If worker unavailable**: **ERROR 503** - Game deletion BLOCKED, Game remains in DB
- ✅ **Game deletion is NOT performed yet** - operations must complete first

**3. Worker Processing**
- Worker processes each DELETE operation
- **Database**: Update each OperationQueue status='in_progress' (as worker picks it up)
- Each operation deletes entire game directory: `ftp:username/gamename/`

**4. Operation Completion**
- **If FTP Success**: **Database**: Update OperationQueue status='completed'
- **If FTP Failure**: **Database**: Update OperationQueue status='failed', error_message stored

**5. Game Deletion (After All Operations Complete)**
- **Backend checks all operations for this game**:
  - **If ALL operations succeeded**: **Database**: Delete Game from database
    - **CASCADE**: All SaveFolders and OperationQueue records for this game automatically deleted
  - **If ANY operation failed**: **Database**: Game remains in database, OperationQueue records remain (some with status='failed')

**Result**: 
- ✅ **All FTP Success**: Game deleted from DB, all OperationQueue status='completed', all FTP saves purged
- ❌ **Any FTP Failure**: Game remains in DB, OperationQueue shows mixed statuses (some 'completed', some 'failed'), some FTP saves may remain
- **Note**: Game deletion only happens AFTER all FTP operations complete successfully - if any FTP operation fails, game is NOT deleted

---

## Scenario 8: Admin DELETE Game - No Worker Available

### Flow:

**1-2. Same as Scenario 7**

**3. Worker Assignment Fails**
- `get_client_worker_or_error()` returns error
- `_queue_game_deletion_operations()` returns `(False, "No active client worker available...")`
- **ERROR 503**: Game deletion BLOCKED
- Game remains in database

**Result**: ❌ Game NOT deleted, error message shown to admin

---

## Scenario 9: Multiple Workers - Collision Prevention

### Flow:

**1. User A and User B Both Save Same Game**
- User A's operation → Assigned to Worker A (User A's worker)
- User B's operation → Assigned to Worker B (User B's worker)

**2. Worker Polling**
- Worker A polls → Gets only operations assigned to Worker A
- Worker B polls → Gets only operations assigned to Worker B
- Uses `select_for_update(skip_locked=True)` for atomic locking

**3. Processing**
- Each worker processes their own operations
- No collisions because operations are pre-assigned

**Result**: ✅ Both operations complete successfully, no conflicts

---

## Scenario 10: Operation Timeout (Stuck Operation)

### Flow:

**1-3. Normal Flow (operation starts)**

**4. Operation Gets Stuck**
- Worker starts processing but hangs (network issue, file locked, etc.)
- Operation remains IN_PROGRESS for 30+ minutes

**5. Next Worker Poll**
- Worker polls for new operations
- Backend detects stuck operation: `started_at < (now - 30 minutes)`
- Backend marks operation as FAILED: "Operation timed out after 30 minutes"

**6. Frontend Polling**
- Frontend polls status
- Status: IN_PROGRESS → FAILED
- Error message displayed

**Result**: ❌ Operation failed, user must retry

---

## Scenario 11: No Worker in Session / Worker Offline

### Flow:

**1. User Initiates Operation**
- User clicks "Save" button
- No `client_id` in session OR worker in session is offline

**2. Backend Processing**
- ✅ Session has no `client_id` OR worker is offline
- ✅ **Worker Assignment**: Checks session for `client_id`
- ✅ **FAILS IMMEDIATELY**: **ERROR 503**: "No client worker available" or "Client worker is offline"
- ✅ Operation is NOT created

**Result**: ❌ Operation fails immediately - user must ensure worker is running on their machine

**Note**: The `client_id` is automatically set in session when:
- **Worker registers**: When worker starts, if user is logged in, `client_id` stored in session
- **Worker heartbeat**: Every 10 seconds, if user is logged in, `client_id` updated in session  
- **Frontend connection check**: When frontend verifies worker status (with `client_id` parameter), if user is logged in and worker is online, `client_id` stored/updated

If worker is not running or user is not logged in when worker starts, `client_id` won't be in session and operations will fail. User should ensure worker is running and refresh the page or wait for next heartbeat.

---

## Edge Cases Summary

| Edge Case | Result | HTTP Status |
|-----------|--------|-------------|
| No worker available | Operation not created | 503 |
| Worker goes offline during processing | Operation marked FAILED after 30 min | - |
| Operation times out (>30 min) | Operation marked FAILED | - |
| Multiple workers, same operation | No collision (pre-assigned) | - |
| Admin deletes game, no worker | Game deletion BLOCKED | 503 |
| Invalid local path | Worker reports error, operation FAILED | - |
| FTP connection fails | Worker reports error, operation FAILED | - |
| Database save folder missing | Operation not created | 404/500 |
| User tries to delete another user's save | Operation not created | 403/404 |
| No client_id in session | Operation NOT created, ERROR 503 | 503 |
| Worker in session is offline | Operation NOT created, ERROR 503 | 503 |
| Worker not running when user logs in | client_id not in session, operations fail | 503 |
| User logs in after worker starts | client_id set on next heartbeat/check | - |

---

## Key Safety Features

1. **Worker Assignment MANDATORY (Automatic Session Association)**: 
   - ALL operations MUST have a worker assigned when created
   - Worker automatically associates with user's session via:
     - **Worker registration**: When worker starts, if user is logged in, `client_id` stored in session
     - **Worker heartbeat**: Every 10 seconds, if user is logged in, `client_id` updated in session
     - **Frontend connection check**: When frontend verifies worker status, if user is logged in and worker is online, `client_id` stored/updated
   - Backend uses `client_id` from user's session (automatically set by worker)
   - If `client_id` not in session → **FAIL immediately** - Operation is NOT created
   - If worker is offline → **FAIL immediately** - Operation is NOT created
   - No fallback to other workers - app requires the user's worker to be running
   - `create_operation()` raises ValueError if `client_worker=None` (enforced at model level)
   - This ensures operations only run on the user's machine, preventing collisions
2. **Atomic Operations**: Database uses `select_for_update` to prevent race conditions
3. **Operation Locking**: Operations are pre-assigned to prevent collisions
4. **Timeout Handling**: Stuck operations automatically marked as FAILED after 30 minutes
5. **Game Deletion Protection**: Game cannot be deleted if FTP cleanup fails
6. **User Isolation**: Each user's operations go to their own worker (when possible)

---

## Status Flow Diagram

```
PENDING → IN_PROGRESS → COMPLETED ✅
                ↓
            FAILED ❌ (timeout, error, etc.)
```

---

---


---

## API Endpoints Reference

- `POST /api/save-game/<game_id>/` - Create save operation
- `POST /api/load-game/<game_id>/` - Create load operation
- `POST /api/delete-save-folder/<game_id>/` - Create delete operation
- `POST /api/delete-all-saves/<game_id>/` - Create multiple delete operations
- `DELETE /api/admin/game/<game_id>/` - Delete game (admin only)
- `GET /api/check-operation-status/<operation_id>/` - Check operation status
- `GET /api/client-worker/<client_id>/operations/` - Worker polls for operations
- `POST /api/client-worker/<client_id>/operation/<id>/complete/` - Worker reports completion
- `POST /api/client-worker/<client_id>/operation/<id>/progress/` - Worker reports progress

