#!/bin/bash

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python version
print_message "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d " " -f 2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 12 ]; then
    print_error "Python 3.12 or higher is required. Found: $PYTHON_VERSION"
    print_message "Please install Python 3.12 or higher and try again."
    exit 1
fi

print_message "Python version $PYTHON_VERSION detected. OK!"

# Prompt the user to confirm if they have configured printers in config.json
read -p "Have you configured the printers in config.json? (Y/N): " user_input

# Convert the input to uppercase to handle lower case responses
user_input=$(echo "$user_input" | tr '[:lower:]' '[:upper:]')

# Check the user's input
if [ "$user_input" == "Y" ]; then
    print_message "Continuing with the setup..."
elif [ "$user_input" == "N" ]; then
    print_error "Please configure the printers in config.json before running this script."
    exit 1
else
    print_error "Invalid input. Please enter Y or N."
    exit 1
fi

# Navigate to the script's directory
cd "$(dirname "$0")"

# Create virtual environment
print_message "Creating Python virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    print_error "Failed to create virtual environment. Please install python3-venv and try again."
    exit 1
fi

# Activate virtual environment
print_message "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_message "Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
print_message "Installing requirements..."
python -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    print_error "Failed to install requirements. Please check your internet connection and try again."
    exit 1
fi

# Ensure the cert directory exists
print_message "Setting up required directories..."
mkdir -p cert
mkdir -p log
mkdir -p data

# Check and generate SSL certificates
cert_file="./cert/server.cert"
if [ ! -f "$cert_file" ]; then
    print_message "SSL certificate not found. Generating a new one..."
    openssl req -nodes -new -x509 -keyout cert/server.key -out cert/server.cert -days 3650
else
    # Check expiration date
    expiration_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d '=' -f 2)
    expiration_secs=$(date -d "$expiration_date" +%s)
    current_secs=$(date +%s)
    days_left=$(( (expiration_secs - current_secs) / 86400 ))

    if [ "$days_left" -le 60 ]; then
        print_warning "SSL certificate is expiring in less than 60 days. Generating a new one..."
        openssl req -nodes -new -x509 -keyout cert/server.key -out cert/server.cert -days 3650
    else
        print_message "SSL certificate is valid for $days_left more days."
    fi
fi

# Create systemd service file
print_message "Creating systemd service file..."
SERVICE_FILE="epos-proxy.service"
cat > $SERVICE_FILE << EOL
[Unit]
Description=ePOS Proxy Server
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python $(pwd)/main.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=epos-proxy

[Install]
WantedBy=multi-user.target
EOL

print_message "The systemd service file has been created as '$SERVICE_FILE'."
print_message "To install it, run the following commands:"
echo "sudo cp $SERVICE_FILE /etc/systemd/system/"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable epos-proxy.service"
echo "sudo systemctl start epos-proxy.service"

print_message "Setup complete! You can now run the server with:"
echo "source venv/bin/activate && python main.py"