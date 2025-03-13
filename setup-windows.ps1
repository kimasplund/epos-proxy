# PowerShell setup script for ePOS Proxy Server
# This script helps set up the ePOS Proxy Server on Windows

# Function to print colored messages
function Write-ColoredMessage {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [string]$Color = "White"
    )
    
    Write-Host $Message -ForegroundColor $Color
}

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-ColoredMessage "This script works best when run as administrator. Some features may not work properly." -Color Yellow
}

# Check if Docker is installed
$dockerInstalled = $null -ne (Get-Command docker -ErrorAction SilentlyContinue)
$dockerComposeInstalled = $null -ne (Get-Command docker-compose -ErrorAction SilentlyContinue)

Write-ColoredMessage "ePOS Proxy Server Setup for Windows" -Color Cyan
Write-ColoredMessage "===============================" -Color Cyan
Write-ColoredMessage ""

Write-ColoredMessage "Select setup method:" -Color Green
Write-ColoredMessage "1. Using Docker (recommended)" -Color Green
Write-ColoredMessage "2. Native Python installation" -Color Green
Write-ColoredMessage "3. Exit" -Color Green

$choice = Read-Host "Enter your choice (1-3)"

switch ($choice) {
    "1" {
        # Docker setup
        if (-not $dockerInstalled) {
            Write-ColoredMessage "Docker is not installed or not in PATH." -Color Red
            Write-ColoredMessage "Please install Docker Desktop from https://www.docker.com/products/docker-desktop/" -Color Yellow
            exit 1
        }
        
        if (-not $dockerComposeInstalled) {
            Write-ColoredMessage "Docker Compose is not installed or not in PATH." -Color Red
            Write-ColoredMessage "It should be included with Docker Desktop." -Color Yellow
            exit 1
        }
        
        Write-ColoredMessage "Docker is installed. Proceeding with Docker setup..." -Color Green
        
        # Check if config.json exists
        if (-not (Test-Path -Path "app\config.json")) {
            Write-ColoredMessage "Configuration file not found at app\config.json." -Color Red
            Write-ColoredMessage "Please create and configure this file before proceeding." -Color Yellow
            exit 1
        }
        
        # Create simplified printers.config if it doesn't exist
        if (-not (Test-Path -Path "printers.config")) {
            Write-ColoredMessage "Creating simplified printer configuration file..." -Color Green
            @"
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
"@ | Out-File -FilePath "printers.config" -Encoding utf8
            Write-ColoredMessage "Created printers.config. Please edit it with your printer details." -Color Yellow
        }
        
        # Create required directories
        Write-ColoredMessage "Creating required directories..." -Color Green
        if (-not (Test-Path -Path "app\cert")) {
            New-Item -ItemType Directory -Path "app\cert" | Out-Null
        }
        if (-not (Test-Path -Path "app\log")) {
            New-Item -ItemType Directory -Path "app\log" | Out-Null
        }
        if (-not (Test-Path -Path "app\data")) {
            New-Item -ItemType Directory -Path "app\data" | Out-Null
        }
        
        # Generate SSL certificates if they don't exist
        if ((-not (Test-Path -Path "app\cert\server.cert")) -or (-not (Test-Path -Path "app\cert\server.key"))) {
            Write-ColoredMessage "SSL certificates not found. These will be automatically generated when the Docker container starts." -Color Yellow
            Write-ColoredMessage "No action required for Docker deployment." -Color Green
        }
        
        # Start Docker containers
        Write-ColoredMessage "Starting Docker containers..." -Color Green
        docker-compose up -d
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColoredMessage "Docker containers started successfully!" -Color Green
            Write-ColoredMessage "The ePOS Proxy Server is now running." -Color Green
            Write-ColoredMessage "Access it at https://localhost/" -Color Green
        } else {
            Write-ColoredMessage "Failed to start Docker containers. Please check the error messages above." -Color Red
        }
    }
    "2" {
        # Native Python setup
        Write-ColoredMessage "Running native Python setup..." -Color Green
        
        # Navigate to app directory and run setup.ps1
        Push-Location app
        if (Test-Path -Path "setup.ps1") {
            Write-ColoredMessage "Running setup.ps1..." -Color Green
            .\setup.ps1
        } else {
            Write-ColoredMessage "setup.ps1 not found. Please make sure the file exists." -Color Red
            exit 1
        }
        Pop-Location
        
        Write-ColoredMessage "Setup complete!" -Color Green
        Write-ColoredMessage "To start the server, navigate to the app directory and run:" -Color Green
        Write-ColoredMessage ".\start-server.bat" -Color Cyan
    }
    "3" {
        Write-ColoredMessage "Exiting setup..." -Color Yellow
        exit 0
    }
    default {
        Write-ColoredMessage "Invalid choice. Exiting..." -Color Red
        exit 1
    }
} 