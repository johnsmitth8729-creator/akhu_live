#!/bin/bash
# AKHU Monitor daily backup script

BACKUP_DIR="/var/backups/akhu"
DATE_STR=$(date +%Y-%m-%d_%H-%M-%S)
POSTGRES_CONTAINER="postgres"
DB_NAME="akhu_monitoring"
DB_USER="postgres"

mkdir -p "$BACKUP_DIR"

# 1. Backup PostgreSQL Database
echo "Starting PostgreSQL database backup..."
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" -F c > "$BACKUP_DIR/db_$DATE_STR.dump"

# 2. Backup configurations and settings
echo "Archiving service configuration files..."
tar -czf "$BACKUP_DIR/config_$DATE_STR.tar.gz" /app/nginx.conf /app/turnserver.conf /app/mediamtx.yml

# 3. Clean up backups older than 14 days to conserve disk space
echo "Performing rotation cleaning..."
find "$BACKUP_DIR" -type f -mtime +14 -delete

echo "System backup successfully compiled under $BACKUP_DIR!"
