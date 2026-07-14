# AKHU Live Exam Camera Monitoring Platform

An enterprise-ready, low-latency live camera monitoring system developed for Al-Khwarizmi University (AKHU). This platform enables university administrators to monitor live examination rooms securely across various remote campuses and testing centers using IP cameras (RTSP) transcoded and served via WebRTC and HLS using MediaMTX.

---

## Technical Stack
- **Backend:** Python 3.14+, Django 5+, PostgreSQL, Django REST Framework (DRF)
- **Frontend:** HTML5, CSS (theme.css), Bootstrap 5.3, JavaScript ES6
- **Desktop Agent:** Python 3.10+, psutil, pystray (Windows System Tray)
- **Streaming Server:** MediaMTX (integrated dynamically via REST API)
- **Protocols:** RTSP (Input), WebRTC (Low Latency <0.2s Output), HLS (Fallback Output)
- **Localization:** Django i18n (English - Default, Uzbek - Supported)

---

## Features Matrix

### 👤 Super Admin Console
- Secure admin login.
- **Analytics Dashboard:** Graphical widgets for online/offline status, regional counts, bandwidth usage, and physical server health metrics (CPU, Memory, Disk space).
- **Region Management:** Create, update, delete, activate/deactivate exam regions (automatically creates/suspends related administrative logins).
- **Global Monitoring:** Search and query all active streams across all regions, filter by buildings/status, and trigger manual connection probes.
- **System Audits:** View security logs tracking operator log-ins, log-outs, camera alterations, and network alerts.

### 🏢 Region Administrator Console
- Restricted login (sees only their assigned region).
- **Camera Management:** Add, edit, delete, start, and stop RTSP streams belonging to their campus.
- **Local Control Room:** Real-time multi-camera grid viewer with start/stop stream actions, automated indicator diagnostics, and live screenshot downloads.

### 🖥️ Live Screen Monitoring Module
- **Desktop Client Agent:** Python agent running in the Windows System Tray that captures desktops via FFmpeg and publishes to MediaMTX with sub-second latency.
- **Heartbeat & System Diagnostics:** Automatically pushes performance loads (CPU, RAM, Disk space, network speeds, uptime) and streaming FPS/resolution to the server dashboard.
- **Multi-Layout Video Wall:** Switch layouts instantly in 2x2, 3x3, 4x4, 5x5, and 6x6 configurations.
- **Server Snapshots:** Extract and store canvas screenshots in `media/screenshots/` tied to active computers, regions, and operator user audits.

### 🎥 Streaming Integration
- **WebRTC WHEP Client:** Ultra-low latency video streaming played directly in HTML5 `<video>` elements with no extra plugins.
- **On-Demand Streaming:** MediaMTX is configured to pull RTSP streams from camera devices *only when actively viewed* to optimize local bandwidth.
- **AJAX Polling Diagnostics:** Background JavaScript checks connection states every 15 seconds and updates visual status dots (Green = Online, Red = Offline, Gray = Unknown).
- **Local Snapshot Capture:** Canvas-based snapshot extraction directly from video frames with custom date/time watermark downloads.

---

## Database Architecture
1. **User:** Custom user model subclassing `AbstractUser` with a role toggle (`super_admin` vs `region_admin`).
2. **Region:** Campus profile linked 1-to-1 with a `User` account.
3. **Camera:** Device configuration (RTSP URL, credentials, IP, Port, Room, Floor, Building) belonging to a `Region`.
4. **CameraStatus:** Log of socket-level TCP handshake response times and error message logs.
5. **Computer:** Registered exam PC profile (Agent ID, secret credentials, diagnostics metrics, locations) belonging to a `Region`.
6. **ScreenSession:** Tracks active and completed desktop streams (resolution, framerate, bitrates, durations).
7. **ScreenSnapshot:** Records file paths of screen snapshots captured by admins, referencing the computer, region, and operator.
8. **Heartbeat:** Historical database records of agent performance metrics (CPU, RAM, Disk, Uptime) for diagnostics dashboards.
9. **AgentToken:** Security token used by desktop agents to sign REST API updates.
10. **StreamingLog:** Tracks start/stop stream actions and durations.
11. **ActivityLog:** User audit log (login, logout, CRUD history, client IP address).
12. **SystemSetting:** Configuration parameters.

---

## REST API Specifications

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` / `POST` | `/api/auth/` | Check auth status / Login / Logout |
| `GET` / `POST` | `/api/regions/` | List and create regions (Super Admin only) |
| `GET` / `POST` | `/api/cameras/` | CRUD camera details (scoped by login role) |
| `GET` / `POST` | `/api/screens/` | CRUD registered computers directory |
| `POST` | `/api/screens/register/` | Authenticate agent and issue session Token |
| `POST` | `/api/screens/heartbeat/` | Update live agent metrics and logs performance |
| `POST` | `/api/screens/start/` | Report desktop stream session started |
| `POST` | `/api/screens/stop/` | Report desktop stream session stopped |
| `POST` | `/api/screens/snapshot/` | Ingest screenshot file upload |
| `GET` | `/api/streams/` | View historical streaming logs |
| `GET` | `/api/status/` | Query camera connectivity check history |
| `GET` | `/api/logs/` | Query audit trail of user activities |

---

## Local Quick Start

### 1. Database Setup
Ensure PostgreSQL is running locally. The platform is pre-configured to connect using standard credentials:
- **Host:** `localhost`
- **Port:** `5432`
- **Username:** `postgres`
- **Password:** `root`
- **Database Name:** `akhu_monitoring` (automatically created by system configuration tests)

### 2. Startup Steps
Run the following commands in the project directory:
```bash
# 1. Activate Virtual Environment
venv\Scripts\activate

# 2. Run Database Migrations
python manage.py migrate

# 3. Seed Default System Settings
python manage.py seed_settings

# 4. Run Development Server
python manage.py runserver
```

### 3. Screen Sharing Agent Setup
Launch the desktop capture client on testing computers:
```bash
# 1. Install desktop agent dependencies
pip install requests psutil pystray Pillow

# 2. Open config.json and populate Server URL, Agent ID, and Secret Key
# 3. Start background desktop sharing process
python agent/screen_agent.py
```

### 3. Default Credentials
Log in from the navbar using the pre-seeded Super Admin account:
- **Username:** `admin`
- **Password:** `admin`

---

## MediaMTX Installation
Refer to [INSTALLATION.md](file:///c:/Users/admin/Desktop/akhu_platforms/akhu_live/INSTALLATION.md) for full instructions on setting up the local media server and background health check tasks.
