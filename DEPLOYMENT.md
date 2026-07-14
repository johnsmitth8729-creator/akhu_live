# Production Deployment & Architecture Scaling Guide

This guide details instructions for setting up, securing, and deploying the **AKHU Live Exam Monitoring Platform** and its streaming infrastructure in a production cloud environment.

---

## 🐋 1. Docker Compose Multi-Container Stack (Recommended)

To launch the entire backend, media processing engine, TURN servers, and reverse proxy layer in a containerized environment:

### Prerequisites:
- Docker and Docker Compose installed.
- Production domain (e.g. `live.akhu.uz`) pointing to your server IP.

### Deployment:
1. Ensure `nginx.conf`, `turnserver.conf`, and `mediamtx.yml` in the root folder are updated with your domain name.
2. Run the deployment stack:
   ```bash
   docker compose up -d --build
   ```
3. Run initial database migration scripts:
   ```bash
   docker compose exec django python manage.py migrate
   docker compose exec django python manage.py seed_settings
   ```
4. Verify all running containers:
   ```bash
   docker compose ps
   ```

---

## 🌐 2. Native Ubuntu 22.04 LTS Production Setup

If you deploy without Docker directly on bare-metal or cloud VMs:

### Step 1: Install Nginx, PostgreSQL, and Redis
```bash
sudo apt update
sudo apt install -y nginx postgresql postgresql-contrib redis-server python3-pip python3-venv certbot python3-certbot-nginx
```

### Step 2: Install and Configure Coturn (TURN/STUN)
1. Install Coturn:
   ```bash
   sudo apt install -y coturn
   ```
2. Copy `turnserver.conf` from the repository:
   ```bash
   sudo cp turnserver.conf /etc/turnserver.conf
   ```
3. Enable the service:
   ```bash
   sudo systemctl enable coturn
   sudo systemctl restart coturn
   ```

### Step 3: Install and Configure MediaMTX
1. Download and extract MediaMTX:
   ```bash
   wget https://github.com/bluenviron/mediamtx/releases/download/v1.9.0/mediamtx_v1.9.0_linux_amd64.tar.gz
   tar -xzf mediamtx_v1.9.0_linux_amd64.tar.gz -C /opt/mediamtx/
   ```
2. Copy configuration rules:
   ```bash
   cp mediamtx.yml /opt/mediamtx/mediamtx.yml
   ```
3. Create Systemd service wrapper:
   ```ini
   # /etc/systemd/system/mediamtx.service
   [Unit]
   Description=MediaMTX Media Server
   After=network.target

   [Service]
   Type=simple
   ExecStart=/opt/mediamtx/mediamtx /opt/mediamtx/mediamtx.yml
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
4. Enable and start:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable mediamtx
   sudo systemctl start mediamtx
   ```

---

## 🔒 3. SSL Configuration & Automated Renewal (Let's Encrypt)

Obtain SSL certificate keys using Certbot for secure HTTPS proxy endpoints and WebRTC/WSS traffic:

```bash
# Obtain certificates using Nginx plugin
sudo certbot --nginx -d live.akhu.uz -d api.live.akhu.uz

# Set permissions for Coturn and MediaMTX to read certificates
sudo chmod -R 755 /etc/letsencrypt/live/
sudo chmod -R 755 /etc/letsencrypt/archive/
```

Certbot automatically configures a systemd timer that checks and renews certificates within 30 days of expiration.

---

## 🚀 4. Load Balancing & Scaling to 1000+ Streams

To scale the platform beyond a single VM:
1. **Database Decoupling**: Move PostgreSQL and Redis to managed cloud databases (e.g. AWS RDS or ElastiCache).
2. **Node Multiplication**: Deploy multiple MediaMTX VM instances across regions.
3. **Register Nodes**: Navigate to Django Admin and add `StreamingNode` records with their IP addresses.
4. Django's load balancer will automatically route remote exam cameras and client screen shares to nodes based on priority rankings and active CPU load feedback tracked by the health monitors.
