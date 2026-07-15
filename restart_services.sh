#!/bin/bash
# Native Ubuntu production service restarter
# Only restarts services if they are installed on the system to prevent deployment failures.
set -e

restart_if_exists() {
    local service_name=$1
    if systemctl list-unit-files "${service_name}.service" >/dev/null 2>&1 || systemctl list-units --all --type=service | grep -Fq "${service_name}.service"; then
        echo "Restarting ${service_name}..."
        systemctl restart "$service_name"
    else
        echo "Service ${service_name} not found on this system. Skipping."
    fi
}

if [ -d "/opt/mediamtx" ] && [ -f "/home/boss/akhu_live/mediamtx.yml" ]; then
    echo "Updating MediaMTX configuration..."
    cp /home/boss/akhu_live/mediamtx.yml /opt/mediamtx/mediamtx.yml
fi

restart_if_exists "akhu_live"
restart_if_exists "mediamtx"
restart_if_exists "akhu_celery"
restart_if_exists "akhu_celerybeat"

echo "All available AKHU Live services handled successfully."
