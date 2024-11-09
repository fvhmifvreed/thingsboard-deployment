#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print info messages
info() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

# Function to print warning messages
warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# Function to print error messages
error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root. Use sudo."
   exit 1
fi

# Update and upgrade system
info "Updating system packages..."
apt update && apt upgrade -y

# Install Python and pip
info "Installing Python3 and pip..."
apt install -y python3 python3-pip

# Verify Python installation
if ! command -v python3 &> /dev/null; then
    error "Python3 installation failed!"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    error "pip installation failed!"
    exit 1
fi

info "Python and pip installed successfully."

# Install required Python dependencies from requirements.txt
PIP_REQUIREMENTS="requirements.txt"

if [[ -f "$PIP_REQUIREMENTS" ]]; then
    info "Installing Python dependencies from $PIP_REQUIREMENTS..."
    pip3 install -r "$PIP_REQUIREMENTS"
else
    warn "$PIP_REQUIREMENTS not found. Skipping dependency installation."
fi

# Download Python script if not already present
PYTHON_SCRIPT="thingsboard_installer.py"
PYTHON_SCRIPT_URL="http://your-python-script-url-here/thingsboard_installer.py"

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    info "Downloading Python script: $PYTHON_SCRIPT..."
    curl -o "$PYTHON_SCRIPT" "$PYTHON_SCRIPT_URL"
fi

# Ensure Python script is executable
chmod +x "$PYTHON_SCRIPT"

# Run the Python script
info "Running the Python installation script..."
python3 "$PYTHON_SCRIPT"

# Final message
info "Installation process completed successfully!"

