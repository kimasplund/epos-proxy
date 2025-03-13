#!/bin/bash

# ANSI color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
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

print_header() {
    echo -e "${CYAN}$1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Print header
print_header "ePOS Proxy Server Setup for Linux"
print_header "================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_warning "This script works best when run as root. Some features may not work properly."
fi

# Check if Docker is installed
DOCKER_INSTALLED=false
DOCKER_COMPOSE_INSTALLED=false

if command_exists docker; then
    DOCKER_INSTALLED=true
fi

if command_exists docker-compose; then
    DOCKER_COMPOSE_INSTALLED=true
fi

# Prompt for setup method
print_message "Select setup method:"
echo "1. Using Docker (recommended)"
echo "2. Native Python installation"
echo "3. Exit"

read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        # Docker setup
        if [ "$DOCKER_INSTALLED" = false ]; then
            print_error "Docker is not installed."
            print_message "To install Docker, run: curl -fsSL https://get.docker.com | sh"
            exit 1
        fi
        
        if [ "$DOCKER_COMPOSE_INSTALLED" = false ]; then
            print_error "Docker Compose is not installed."
            print_message "To install Docker Compose, see: https://docs.docker.com/compose/install/"
            exit 1
        fi
        
        print_message "Docker is installed. Proceeding with Docker setup..."
        
        # Check if config.json exists
        if [ ! -f "app/config.json" ]; then
            print_error "Configuration file not found at app/config.json."
            print_message "Please create and configure this file before proceeding."
            exit 1
        fi
        
        # Create required directories
        print_message "Creating required directories..."
        mkdir -p app/cert app/log app/data
        
        # Generate SSL certificates if they don't exist
        if [ ! -f "app/cert/server.cert" ]; then
            print_message "SSL certificates not found. Generating..."
            
            # Check if OpenSSL is available
            if ! command_exists openssl; then
                print_error "OpenSSL not found. Please install OpenSSL or manually create SSL certificates."
                print_message "Place your certificates at app/cert/server.cert and app/cert/server.key"
                exit 1
            fi
            
            # Generate self-signed certificate
            (cd app/cert && openssl req -nodes -new -x509 -keyout server.key -out server.cert -days 3650)
        fi
        
        # Start Docker containers
        print_message "Starting Docker containers..."
        docker-compose up -d
        
        if [ $? -eq 0 ]; then
            print_message "Docker containers started successfully!"
            print_message "The ePOS Proxy Server is now running."
            print_message "Access it at https://localhost/"
        else
            print_error "Failed to start Docker containers. Please check the error messages above."
        fi
        ;;
    2)
        # Native Python setup
        print_message "Running native Python setup..."
        
        # Navigate to app directory and run setup.sh
        cd app
        if [ -f "setup.sh" ]; then
            print_message "Running setup.sh..."
            chmod +x setup.sh
            ./setup.sh
        else
            print_error "setup.sh not found. Please make sure the file exists."
            exit 1
        fi
        cd ..
        
        print_message "Setup complete!"
        print_message "To start the server, navigate to the app directory and run:"
        echo "source venv/bin/activate && python main.py"
        ;;
    3)
        print_message "Exiting setup..."
        exit 0
        ;;
    *)
        print_error "Invalid choice. Exiting..."
        exit 1
        ;;
esac 