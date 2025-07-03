#!/bin/bash

# Set variables
AGENT_PATH="/usr/local/bin/snap-agent"
SERVICE_PATH="/etc/systemd/system/snap-agent.service"

# Check for root
if [[ $EUID -ne 0 ]]; then
  echo "❌ This script must be run as root."
  exit 1
fi

# Check if the agent file exists
if [[ ! -f "$AGENT_PATH" ]]; then
  echo "❌ snap-agent not found at $AGENT_PATH"
  exit 1
fi

# Ensure executable
chmod +x "$AGENT_PATH"

# Create systemd service
echo "➜ Creating systemd service..."

cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=Network Agent
After=network.target

[Service]
Type=simple
ExecStart=$AGENT_PATH
Restart=always
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_PATH"

# Reload and enable service
echo "➜ Reloading systemd and starting service..."
systemctl daemon-reload
systemctl enable snap-agent.service
systemctl start snap-agent.service

# Show status
echo "➜ Service status:"
systemctl status snap-agent.service --no-pager
