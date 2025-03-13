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
echo_info "For more information, see the README.md file." 