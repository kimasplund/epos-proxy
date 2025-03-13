# PowerShell setup script for ePOS Proxy Server
# This script sets up the Python environment and certificates

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

# Check PowerShell version
$PSVersion = $PSVersionTable.PSVersion
Write-ColoredMessage "PowerShell version: $($PSVersion.Major).$($PSVersion.Minor)" -Color Green

# Check Python version
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 12)) {
            Write-ColoredMessage "Python 3.12 or higher is required. Found: $pythonVersion" -Color Red
            Write-ColoredMessage "Please install Python 3.12 or higher and try again." -Color Yellow
            exit 1
        }
        
        Write-ColoredMessage "Python version $pythonVersion detected. OK!" -Color Green
    }
}
catch {
    Write-ColoredMessage "Python is not installed or not in PATH." -Color Red
    Write-ColoredMessage "Please install Python 3.12 or higher and try again." -Color Yellow
    exit 1
}

# Prompt for configuration check
$configCheck = Read-Host "Have you configured the printers in config.json? (Y/N)"
if ($configCheck -ne "Y" -and $configCheck -ne "y") {
    Write-ColoredMessage "Please configure the printers in config.json before running this script." -Color Red
    exit 1
}

# Create virtual environment
Write-ColoredMessage "Creating Python virtual environment..." -Color Green
python -m venv venv
if (-not $?) {
    Write-ColoredMessage "Failed to create virtual environment." -Color Red
    exit 1
}

# Activate virtual environment
Write-ColoredMessage "Activating virtual environment..." -Color Green
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-ColoredMessage "Upgrading pip..." -Color Green
python -m pip install --upgrade pip

# Install requirements
Write-ColoredMessage "Installing requirements..." -Color Green
python -m pip install -r requirements.txt
if (-not $?) {
    Write-ColoredMessage "Failed to install requirements. Please check your internet connection and try again." -Color Red
    exit 1
}

# Create required directories
Write-ColoredMessage "Setting up required directories..." -Color Green
if (-not (Test-Path -Path "cert")) {
    New-Item -ItemType Directory -Path "cert" | Out-Null
}
if (-not (Test-Path -Path "log")) {
    New-Item -ItemType Directory -Path "log" | Out-Null
}
if (-not (Test-Path -Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

# Check and generate SSL certificates
$certFile = ".\cert\server.cert"
if (-not (Test-Path -Path $certFile)) {
    Write-ColoredMessage "SSL certificate not found. Generating a new one..." -Color Green
    
    # Check if OpenSSL is installed
    $openssl = Get-Command openssl -ErrorAction SilentlyContinue
    if (-not $openssl) {
        Write-ColoredMessage "OpenSSL is not installed or not in PATH." -Color Red
        Write-ColoredMessage "Please install OpenSSL and try again, or manually generate SSL certificates." -Color Yellow
        Write-ColoredMessage "You need to create cert/server.cert and cert/server.key files." -Color Yellow
        exit 1
    }
    
    # Generate self-signed certificate
    openssl req -nodes -new -x509 -keyout cert/server.key -out cert/server.cert -days 3650
}
else {
    Write-ColoredMessage "SSL certificate found. Checking expiration..." -Color Green
    
    try {
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2 $certFile
        $daysLeft = [math]::Floor(($cert.NotAfter - (Get-Date)).TotalDays)
        
        if ($daysLeft -le 60) {
            Write-ColoredMessage "SSL certificate is expiring in less than 60 days. Generating a new one..." -Color Yellow
            openssl req -nodes -new -x509 -keyout cert/server.key -out cert/server.cert -days 3650
        }
        else {
            Write-ColoredMessage "SSL certificate is valid for $daysLeft more days." -Color Green
        }
    }
    catch {
        Write-ColoredMessage "Failed to check certificate expiration. Generating a new one..." -Color Yellow
        openssl req -nodes -new -x509 -keyout cert/server.key -out cert/server.cert -days 3650
    }
}

# Setup complete
Write-ColoredMessage "Setup complete!" -Color Green
Write-ColoredMessage "You can now run the server with:" -Color Green
Write-Host ".\venv\Scripts\Activate.ps1; python main.py"

# Create a simple batch file to start the server
$batchContent = @"
@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
python main.py
pause
"@

Set-Content -Path "start-server.bat" -Value $batchContent
Write-ColoredMessage "A start-server.bat file has been created for easy startup." -Color Green 