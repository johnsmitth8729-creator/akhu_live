# AKHU Screen Sharing Agent - Installation Guide

This subdirectory contains the lightweight desktop agent running on exam room computers to securely stream screen activities to the central **AKHU Live Exam Monitoring Platform** via WebRTC.

---

## 🛠️ Prerequisites

Before launching the agent, ensure the following are installed on the local Windows PC:

1. **Python 3.10+**:
   - Download and install from [python.org](https://www.python.org/downloads/).
   - **Crucial:** Make sure to check the box **"Add Python to PATH"** during installation.

2. **FFmpeg**:
   - Download the Windows build from [ffmpeg.org](https://ffmpeg.org/download.html) or [gyan.dev](https://www.gyan.dev/ffmpeg/builds/).
   - Extract the zip file (e.g., to `C:\ffmpeg`).
   - Add the `bin` folder (e.g., `C:\ffmpeg\bin`) to your Windows **System Environment Variable PATH**.
   - Verify by running `ffmpeg -version` in Command Prompt.

---

## 🚀 Setup & Execution

### 1. Install Dependencies
Open Command Prompt and install the required Python libraries:
```cmd
pip install requests psutil pystray Pillow
```

### 2. Register the Computer in the Dashboard
1. Log in to the AKHU platform as a **Region Admin** (or Super Admin).
2. Go to the **Computers** page from the navbar (`/screens/directory/`).
3. Click **Register Computer** and fill in the machine details (Computer Name, Asset Number, Building, Room, Floor, Department).
4. Save the registration.
5. In the directory listing, copy the **Agent ID** (UUID) and **Agent Secret Key** generated for your computer.

### 3. Configure the Agent
In the `agent/` folder, open/create `config.json` and insert your platform parameters:
```json
{
    "server_url": "http://127.0.0.1:8000",
    "agent_id": "YOUR-COPIED-AGENT-UUID",
    "agent_secret_key": "YOUR-COPIED-AGENT-SECRET-KEY",
    "heartbeat_interval": 10,
    "fps": 15,
    "bitrate": 1500,
    "mediamtx_rtsp_host": "127.0.0.1"
}
```
*Change `server_url` and `mediamtx_rtsp_host` to match your central server's actual IP address/domain in production.*

### 4. Run the Agent
Run the agent in Command Prompt:
```cmd
python screen_agent.py
```

---

## ⚙️ Background Operations

- **Tray Integration:** Once launched, the agent runs silently in the Windows system tray (blue monitor icon). Right-click the tray icon to stop sharing.
- **Diagnostics:** The agent automatically gathers local system resource utilization metrics (CPU, RAM, Disk Space, Active Resolution, Hostname, local IP, MAC address) and updates the central server dashboard every 10 seconds.
- **Auto Reconnect:** If the network goes down or MediaMTX crashes, the agent will dynamically restart the GDI grabber stream once connection is recovered.
