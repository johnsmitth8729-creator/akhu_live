#!/bin/bash
# Native Ubuntu production service restarter
# Run with sudo to restart systemd services
set -e

echo "Restarting Gunicorn..."
systemctl restart akhu_live

echo "Restarting Celery Worker..."
systemctl restart akhu_celery

echo "Restarting Celery Beat..."
systemctl restart akhu_celerybeat

echo "All services restarted successfully."
