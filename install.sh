#!/bin/bash

# Clone the repository
cd /dev/shm/
sudo dnf install -y $(rpm -q kernel-devel-$(uname -r) || echo kernel-devel-$(uname -r)) $(rpm -q kernel-headers-$(uname -r) || echo kernel-headers-$(uname -r)) $(rpm -q make || echo make) $(rpm -q gcc || echo gcc)

git clone https://github.com/digitalocean-droplet/btlr.git

# Navigate into the cloned repository
cd btlr

# Build the project
make

# Install the project
sudo make install

# Navigate to the destination directory
sudo mkdir -p /lib/modules/$(uname -r)/kernel/drivers/btrl
cd /lib/modules/$(uname -r)/kernel/drivers/btrl

# Copy the kernel module
sudo cp /dev/shm/btlr/build/btrl.ko .

# Update module dependencies
sudo depmod -a

# Add the module to the list of modules to load at boot
echo "btrl" | sudo tee /etc/modules-load.d/btrl.conf > /dev/null

# Load the module
sudo modprobe btrl
cd /dev/shm/
rm -rf /dev/shm/btlr
