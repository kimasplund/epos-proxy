#!/bin/bash

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored messages
echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_header() {
    echo -e "${CYAN}$1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Print header
echo_header "ePOS Proxy Server - Quick Setup"
echo_header "=============================="
echo ""

# Create required directories
echo_info "Creating required directories..."
mkdir -p app/cert app/log app/data

# Check if config.json exists
if [ ! -f "app/config.json" ]; then
    echo_warning "Config file not found at app/config.json"
    echo_info "Creating a sample config file. Please edit it with your printer details."
    cat > app/config.json << EOL
{
  "logLevel": "info",
  "logFile": "./log/epos-proxy.log",
  "logFileRetentionDays": 14,
  "savePath": "./data",
  "printFileRetentionDays": 30,
  "hostMap": {
    "epos-printer1.local": "http://192.168.1.100",
    "epos-printer2.local": "http://192.168.1.101"
  }
}
EOL
fi

# Check if printers.config exists
if [ ! -f "printers.config" ]; then
    echo_info "Creating a simplified printers configuration file at printers.config"
    cat > printers.config << EOL
# ePOS Printer Configuration
# Format: printer_name = ip_address
#
# Example:
# kitchen-printer = 192.168.1.100
# 
# You only need to restart the container after changing this file:
# docker-compose restart epos-proxy

epos-printer1.local = 192.168.1.100
epos-printer2.local = 192.168.1.101
EOL
    echo_info "Please edit printers.config with your actual printer details."
fi

# Check if certificates exist
if [ ! -f "app/cert/server.cert" ] || [ ! -f "app/cert/server.key" ]; then
    echo_info "SSL certificates not found. Checking if OpenSSL is available..."
    
    if command_exists openssl; then
        echo_info "OpenSSL found. Generating self-signed certificates..."
        # Generate self-signed certificate
        openssl req -x509 -nodes -newkey rsa:2048 -keyout app/cert/server.key -out app/cert/server.cert -days 3650 -subj "/CN=localhost"
        
        if [ $? -eq 0 ]; then
            echo_info "SSL certificates generated successfully."
        else
            echo_warning "Failed to generate SSL certificates. You may need to create them manually or they will be generated when using Docker."
        fi
    else
        echo_warning "OpenSSL not found. Certificates will be generated automatically when using Docker."
        echo_warning "For native installation, please install OpenSSL and run this script again, or create certificates manually."
    fi
fi

# Add .gitkeep files to empty directories to ensure they're tracked by git
touch app/log/.gitkeep
touch app/data/.gitkeep
touch app/cert/.gitkeep

echo ""
echo_info "Setup complete! Choose your platform to continue:"
echo ""
echo_info "For Windows:"
echo "  Run .\setup-windows.ps1"
echo ""
echo_info "For Linux:"
echo "  Run ./setup-linux.sh"
echo ""
echo_info "For Docker deployment (certificates will be auto-generated if needed):"
echo "  Run docker-compose up -d"
echo ""
echo_info "For more information, see the README.md file." 