# Installation Guide

Follow these instructions to set up, configure, and execute the **AKHU Live Exam Camera Monitoring Platform** locally on Windows.

---

## 📋 Prerequisites
1. **Python 3.14+** installed.
2. **PostgreSQL** installed and running on port `5432` with user `postgres` and password `root` (or custom values modified in the project `.env` file).
3. **MediaMTX** executable downloaded for Windows (from [github.com/bluenviron/mediamtx/releases](https://github.com/bluenviron/mediamtx/releases)).

---

## ⚙️ Step-by-Step Installation

### Step 1: Environment Setup
Extract the project repository, open your terminal (PowerShell preferred on Windows), and navigate to the directory:
```powershell
# Create virtual environment if not already present
python -m venv .venv

# Activate the environment
.venv\Scripts\activate

# Install all package requirements
pip install -r requirements.txt
```

### Step 2: Database Initialization
Ensure PostgreSQL is running, then execute migrations and configuration seeds:
```powershell
# Run migrations
python manage.py migrate

# Seed required system settings
python manage.py seed_settings
```
*(The system is pre-configured to automatically create a default Super Admin account with username `admin` and password `admin` on the first database build. You can also run `python manage.py createsuperuser` to create your own account).*

### Step 3: Media Server Setup
To transcode RTSP cameras to WebRTC/HLS, configure and launch MediaMTX:
1. Download the MediaMTX zip file for Windows from the GitHub releases page.
2. Extract the archive.
3. Copy the compiled `mediamtx.yml` file from the project root directory and paste it into the folder where you extracted MediaMTX (overwriting the default configuration file).
4. Run `mediamtx.exe` (this starts the media engine, making HTTP API accessible on port `9997`, WebRTC WHEP on port `8889`, and HLS on port `8888`).

### Step 4: Configure Automatic Camera Health Checks
To poll camera availability states and record history logs automatically, configure a recurring task that executes `python manage.py check_cameras` every 60 seconds.

#### On Windows:
1. Open **Task Scheduler**.
2. Click **Create Basic Task**.
3. Set Trigger to **Daily**.
4. Set action to **Start a Program**.
5. Set Program/script to:
   `C:\Users\admin\Desktop\akhu_platforms\akhu_live\.venv\Scripts\python.exe`
6. Set Arguments to:
   `manage.py check_cameras`
7. Set Start in to:
   `C:\Users\admin\Desktop\akhu_platforms\akhu_live`
8. Finish and open task properties. In the **Triggers** tab, edit the trigger and select **Repeat task every: 1 minute** for a duration of Indefinitely.

---

## 🚀 Running the Platform
1. Ensure **MediaMTX** is running in a terminal.
2. Activate your virtual environment and run the Django web server:
   ```powershell
   .venv\Scripts\activate
   python manage.py runserver
   ```
3. Open your browser and navigate to `http://127.0.0.1:8000/`.
4. Log in using `admin` / `admin` to access dashboard controls.
