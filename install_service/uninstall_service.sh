#!/bin/bash

# GLX Monitor Service Uninstallation Script
# Run this script as root to uninstall the monitoring service

set -e

SERVICE_NAME="monitor-service"
SYSTEMD_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

echo "🗑️  Uninstalling GLX Monitor Service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

# Stop the service if running
echo "🛑 Stopping service..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || echo "Service was not running"

# Disable service
echo "❌ Disabling service..."
systemctl disable "$SERVICE_NAME" 2>/dev/null || echo "Service was not enabled"

# Remove service file
if [ -f "$SYSTEMD_PATH" ]; then
    echo "🗑️  Removing service file..."
    rm "$SYSTEMD_PATH"
else
    echo "⚠️  Service file not found at $SYSTEMD_PATH"
fi

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

echo ""
echo "✅ GLX Monitor Service uninstalled successfully!"
echo ""