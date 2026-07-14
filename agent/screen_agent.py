"""
AKHU Exam Monitor - Windows Desktop Screen Sharing Agent
--------------------------------------------------------
Prerequisites:
    1. Python 3.10+ (https://www.python.org/downloads/)
    2. FFmpeg installed and added to system PATH (or in same directory)
    3. Install python dependencies:
       pip install requests psutil pystray Pillow

Running:
    python screen_agent.py
"""

import os
import sys
import json
import time
import uuid
import socket
import getpass
import platform
import shutil
import subprocess
import threading
import logging
from PIL import Image, ImageDraw
import requests
import psutil

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("screen_agent.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("ScreenAgent")

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "server_url": "http://127.0.0.1:8000",
    "agent_id": "YOUR_AGENT_UUID",
    "agent_secret_key": "YOUR_AGENT_SECRET_KEY",
    "heartbeat_interval": 10,
    "fps": 15,
    "bitrate": 1500,
    "mediamtx_host": "127.0.0.1"
}


class ScreenAgent:
    def __init__(self):
        self.config = self.load_config()
        self.auth_token = None
        self.computer_name = None
        self.computer_id = None
        self.stream_name = None
        
        # Diagnostic state
        self.ffmpeg_cmd = ""
        self.ffmpeg_log_buffer = []
        
        # State control
        self.is_running = True
        self.is_streaming = False
        self.stream_process = None
        
        # Threads
        self.heartbeat_thread = None
        self.stream_monitor_thread = None
        
        # System Tray icon
        self.tray_icon = None

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            logger.info(f"Default config written to '{CONFIG_FILE}'. Please configure credentials first.")
            return DEFAULT_CONFIG
            
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def register(self):
        """
        Calls /api/screens/register/ to exchange Agent credentials for a session token.
        """
        url = f"{self.config['server_url'].rstrip('/')}/api/screens/register/"
        
        mac_num = uuid.getnode()
        mac_str = ':'.join(('%012X' % mac_num)[i:i+2] for i in range(0, 12, 2))
        
        payload = {
            "agent_id": self.config["agent_id"],
            "agent_secret_key": self.config["agent_secret_key"],
            "hostname": socket.gethostname(),
            "username": getpass.getuser(),
            "mac_address": mac_str,
            "os_version": f"{platform.system()} {platform.release()} ({platform.version()})"
        }
        
        logger.info(f"Connecting to registration server at {url}...")
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                self.auth_token = data["token"]
                self.computer_name = data["computer_name"]
                self.computer_id = data["computer_id"]
                self.stream_name = data["stream_name"]
                logger.info(f"Successfully registered! Associated computer: '{self.computer_name}' (ID: {self.computer_id}, Stream Name: {self.stream_name}).")
                return True
            else:
                logger.error(f"Registration failed with code {res.status_code}: {res.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to registration server: {e}")
            return False

    def get_auth_headers(self):
        return {
            "Authorization": f"Token {self.auth_token}",
            "Content-Type": "application/json"
        }

    def start(self):
        # 1. Authenticate / Register
        while self.is_running and not self.auth_token:
            if self.register():
                break
            logger.info("Retrying registration in 10 seconds...")
            time.sleep(10)

        if not self.is_running:
            return

        # 2. Start threads
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        self.stream_monitor_thread = threading.Thread(target=self.streaming_loop, daemon=True)
        self.stream_monitor_thread.start()

    def get_system_metrics(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = shutil.disk_usage("/").percent
            uptime_hrs = (time.time() - psutil.boot_time()) / 3600.0
        except Exception:
            cpu, ram, disk, uptime_hrs = 0, 0, 0, 0
            
        # Get active resolution
        resolution = "1920x1080"
        try:
            if platform.system() == "Windows":
                from ctypes import windll
                user32 = windll.user32
                resolution = f"{user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}"
        except Exception:
            pass

        metrics = {
            "cpu_usage": cpu,
            "ram_usage": ram,
            "disk_usage": disk,
            "uptime": round(uptime_hrs, 2),
            "network_speed": 100.0, # default mock mbps
            "resolution": resolution,
            "fps": self.config["fps"],
            "bitrate": self.config["bitrate"]
        }
        
        if getattr(self, 'ffmpeg_cmd', ''):
            metrics["ffmpeg_command"] = self.ffmpeg_cmd
        if getattr(self, 'ffmpeg_log_buffer', []):
            metrics["ffmpeg_stderr"] = "\n".join(self.ffmpeg_log_buffer)
            
        return metrics

    def heartbeat_loop(self):
        logger.info("Heartbeat worker started.")
        url = f"{self.config['server_url'].rstrip('/')}/api/screens/heartbeat/"
        
        while self.is_running:
            if self.auth_token:
                metrics = self.get_system_metrics()
                try:
                    res = requests.post(url, json=metrics, headers=self.get_auth_headers(), timeout=5)
                    if res.status_code == 401:
                        logger.warning("Agent token rejected. Re-authenticating...")
                        self.auth_token = None
                        self.register()
                except Exception as e:
                    logger.warning(f"Heartbeat transmission failed: {e}")
                    
            time.sleep(self.config["heartbeat_interval"])

    def check_ffmpeg(self):
        """Checks if FFmpeg is installed and accessible."""
        return shutil.which("ffmpeg") is not None

    def log_ffmpeg_stderr(self, process):
        try:
            for line in iter(process.stderr.readline, b''):
                decoded_line = line.decode('utf-8', errors='ignore').strip()
                if decoded_line:
                    logger.warning(f"[FFmpeg] {decoded_line}")
                    if not hasattr(self, 'ffmpeg_log_buffer'):
                        self.ffmpeg_log_buffer = []
                    self.ffmpeg_log_buffer.append(decoded_line)
                    if len(self.ffmpeg_log_buffer) > 20:
                        self.ffmpeg_log_buffer.pop(0)
        except Exception as e:
            logger.error(f"Error reading FFmpeg stderr: {e}")

    def start_ffmpeg_stream(self):
        """
        Spawns FFmpeg background process to record screen and stream via RTSP.
        Uses gdigrab (Windows desktop recorder capture engine).
        """
        # Server must be the ONLY authority. Use registration response stream_name.
        stream_path = getattr(self, 'stream_name', None)
        if not stream_path:
            stream_path = f"screen_{self.config['agent_id']}" # fallback
            
        # Verify FFmpeg is present
        if not self.check_ffmpeg():
            logger.error("FFmpeg not found! Please download it and add it to your system PATH.")
            return None

        # Read config mediamtx_host (never hardcode localhost)
        mediamtx_host = self.config.get("mediamtx_host", self.config.get("mediamtx_rtsp_host", "127.0.0.1"))
        rtsp_url = f"rtsp://{mediamtx_host}:8554/{stream_path}"
        
        # Windows command for GDI grabbing
        cmd = [
            "ffmpeg",
            "-f", "gdigrab",
            "-framerate", str(self.config["fps"]),
            "-i", "desktop",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-pix_fmt", "yuv420p",
            "-b:v", f"{self.config['bitrate']}k",
            "-maxrate", f"{self.config['bitrate']}k",
            "-bufsize", f"{self.config['bitrate'] * 2}k",
            "-f", "rtsp",
            "-rtsp_transport", "tcp",
            rtsp_url
        ]

        self.ffmpeg_cmd = ' '.join(cmd)
        logger.info(f"Launching screen capture stream: {self.ffmpeg_cmd}")
        
        # Hide command window in Windows (silent background operation)
        startupinfo = None
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0 # SW_HIDE

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo
        )
        
        # Spawn thread to read and write FFmpeg log output to screen_agent.log
        t = threading.Thread(target=self.log_ffmpeg_stderr, args=(process,), daemon=True)
        t.start()
        
        return process

    def report_stream_state(self, is_starting):
        endpoint = "start/" if is_starting else "stop/"
        url = f"{self.config['server_url'].rstrip('/')}/api/screens/{endpoint}"
        
        metrics = self.get_system_metrics()
        try:
            requests.post(url, json=metrics, headers=self.get_auth_headers(), timeout=5)
        except Exception as e:
            logger.warning(f"Failed to report stream status to server: {e}")

    def streaming_loop(self):
        logger.info("Screen streaming thread started.")
        
        while self.is_running:
            if not self.auth_token:
                time.sleep(2)
                continue

            if not self.is_streaming:
                # Spawn stream
                self.stream_process = self.start_ffmpeg_stream()
                if self.stream_process:
                    self.is_streaming = True
                    self.report_stream_state(True)
                    logger.info("Screen broadcast started.")
                else:
                    time.sleep(10)
                    continue

            # Monitor process health
            ret_code = self.stream_process.poll()
            if ret_code is not None:
                # Process terminated
                logger.warning(f"FFmpeg stream process exited with code {ret_code}.")
                
                self.is_streaming = False
                self.report_stream_state(False)
                logger.info("Reconnecting screen stream in 5 seconds...")
                time.sleep(5)
                
            time.sleep(2)

    def stop(self):
        logger.info("Stopping screen agent...")
        self.is_running = False
        
        if self.is_streaming:
            self.report_stream_state(False)
            
        if self.stream_process:
            self.stream_process.terminate()
            try:
                self.stream_process.wait(timeout=3)
            except Exception:
                self.stream_process.kill()
                
        if self.tray_icon:
            self.tray_icon.stop()

    def run_tray(self):
        # Create a simple system tray icon dynamically using Pillow
        image = Image.new('RGB', (64, 64), color=(11, 94, 215))
        d = ImageDraw.Draw(image)
        # Draw a mock computer/monitor silhouette
        d.rectangle([(12, 12), (52, 40)], fill=None, outline=(255, 255, 255), width=3)
        d.rectangle([(26, 40), (38, 52)], fill=(255, 255, 255))
        d.rectangle([(20, 50), (44, 52)], fill=(255, 255, 255))
        
        import pystray
        from pystray import MenuItem as item
        
        menu = pystray.Menu(
            item('Stop Sharing', self.stop),
        )
        
        self.tray_icon = pystray.Icon(
            "AKHUExtension",
            image,
            "AKHU Screen Sharing Agent",
            menu
        )
        
        logger.info("System Tray Icon started. Agent running silently in background.")
        self.tray_icon.run()


if __name__ == "__main__":
    agent = ScreenAgent()
    
    # Start agent workers in a separate thread
    agent_thread = threading.Thread(target=agent.start, daemon=True)
    agent_thread.start()
    
    # Run pystray main loop in the main thread (required by some GUI/system libraries)
    try:
        agent.run_tray()
    except KeyboardInterrupt:
        agent.stop()
