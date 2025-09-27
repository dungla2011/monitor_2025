#!/bin/bash

# GLX Monitor Service Installation Script
# Run this script as root to install the monitoring service

set -e

SERVICE_NAME="monitor-service"
SERVICE_FILE="monitor_service.service"
SYSTEMD_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
CURRENT_DIR="$(pwd)"

echo "🔧 Installing GLX Monitor Service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file $SERVICE_FILE not found in current directory"
    exit 1
fi

# Copy service file to systemd directory
echo "📋 Copying service file to $SYSTEMD_PATH"
cp "$SERVICE_FILE" "$SYSTEMD_PATH"

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
echo "✅ Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"

# Start the service
echo "🚀 Starting service..."
systemctl start "$SERVICE_NAME"

# Check service status
echo "📊 Service status:"
systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "✅ GLX Monitor Service installed successfully!"
echo ""
echo "📝 Useful commands:"
echo "   Start service:   sudo systemctl start $SERVICE_NAME"
echo "   Stop service:    sudo systemctl stop $SERVICE_NAME"
echo "   Restart service: sudo systemctl restart $SERVICE_NAME"
echo "   Check status:    sudo systemctl status $SERVICE_NAME"
echo "   View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo "   Disable service: sudo systemctl disable $SERVICE_NAME"
echo ""