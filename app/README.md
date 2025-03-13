# ePOS Proxy Server - App Directory

This directory contains the application code for the ePOS Proxy Server.

## Setup

For the full setup instructions, please refer to the [main README](../README.md) in the root directory.

You can set up the application directly from this directory:

### On Windows
```powershell
.\setup.ps1
```

### On Linux
```bash
chmod +x setup.sh
./setup.sh
```

## Configuration

Edit the `config.json` file to configure your printers:

```json
{
  "logLevel": "info",
  "logFile": "./log/epos-proxy.log",
  "logFileRetentionDays": 14,
  "savePath": "./data",
  "printFileRetentionDays": 30,
  "hostMap": {
    "epos-printer1.local": "http://192.168.14.217",
    "epos-printer2.local": "http://192.168.14.101"
  }
}
```

## Running the Application

### On Windows
```powershell
.\start-server.bat
```

### On Linux
```bash
source venv/bin/activate
python main.py
```

## Features

- HTTPS-to-HTTP proxy for ePOS printers
- Automatic logging of print jobs 
- Multi-printer support
- Configurable retention periods
- Health check endpoints