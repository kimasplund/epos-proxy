# config.py
import sys
import json
import os
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

# Import the printer_config module
from printer_config import parse_printers_config


class Config:
    """Configuration class for the ePOS Proxy Server."""
    
    def __init__(self, config_path: str = "config.json", printers_config_path: str = "printers.config"):
        self.path = config_path
        self.printers_path = printers_config_path
        self.data = self._load_config()
        self._integrate_printers_config()
        self.validate()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(self.path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            sys.exit(f"Configuration file not found: {self.path}")
        except json.JSONDecodeError:
            sys.exit(f"Invalid JSON in configuration file: {self.path}")
    
    def _integrate_printers_config(self) -> None:
        """Integrate printers from the simplified configuration file."""
        if os.path.exists(self.printers_path):
            logging.info(f"Reading printers from {self.printers_path}")
            printers = parse_printers_config(self.printers_path)
            
            # If we have any printers from the simplified config, use them
            if printers:
                # Create hostMap if it doesn't exist
                if "hostMap" not in self.data:
                    self.data["hostMap"] = {}
                
                # Add/update printers from the simplified config
                for name, ip in printers.items():
                    self.data["hostMap"][name] = ip
                    
                logging.info(f"Integrated {len(printers)} printers from {self.printers_path}")
    
    def validate(self) -> None:
        """Validate the configuration."""
        if not self.data.get("logLevel"):
            sys.exit("logLevel is not defined in config.json")
        
        if not self.data.get("logFile"):
            sys.exit("logFile is not defined in config.json")
        
        if not self.data.get("hostMap") or not isinstance(self.data["hostMap"], dict):
            sys.exit("hostMap is not properly defined in config.json")
        
        if not self.data.get("savePath"):
            sys.exit("savePath is not defined in config.json")
        
        # Create required directories
        save_path = Path(self.data["savePath"])
        save_path.mkdir(exist_ok=True, parents=True)
        
        log_dir = Path(self.data["logFile"]).parent
        log_dir.mkdir(exist_ok=True, parents=True)
        
        # Check SSL certificates
        cert_path = Path("cert/server.cert")
        key_path = Path("cert/server.key")
        
        if not cert_path.exists() or not key_path.exists():
            sys.exit("SSL certificates are not properly configured")
    
    @property
    def log_level(self) -> str:
        """Get the log level."""
        return self.data.get("logLevel", "info").upper()
    
    @property
    def log_file(self) -> str:
        """Get the log file path."""
        return self.data.get("logFile", "./log/epos-proxy.log")
    
    @property
    def log_retention_days(self) -> int:
        """Get the log retention days."""
        return int(self.data.get("logFileRetentionDays", 14))
    
    @property
    def save_path(self) -> str:
        """Get the save path for print files."""
        return self.data.get("savePath", "./data")
    
    @property
    def print_retention_days(self) -> int:
        """Get the print file retention days."""
        return int(self.data.get("printFileRetentionDays", 30))
    
    @property
    def host_map(self) -> Dict[str, str]:
        """Get the host map for printers."""
        return self.data.get("hostMap", {})
    
    @property
    def enable_dns(self) -> bool:
        """
        Get whether the DNS server is enabled.
        
        Defaults to True unless explicitly disabled.
        """
        return self.data.get("enableDns", True)
    
    @property
    def dns_port(self) -> int:
        """
        Get the DNS server port.
        
        Defaults to 53 (standard DNS port).
        """
        return int(self.data.get("dnsPort", 53))