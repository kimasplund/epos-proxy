# proxy_server.py
import os
import sys
import json
import time
import logging
import ssl
import asyncio
import uvicorn
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from logging.handlers import TimedRotatingFileHandler


class Config:
    """Configuration class for the ePOS Proxy Server."""
    
    def __init__(self, config_path: str = "config.json"):
        self.path = config_path
        self.data = self._load_config()
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
        return self.data.get("logLevel", "info").upper()
    
    @property
    def log_file(self) -> str:
        return self.data.get("logFile", "./log/epos-proxy.log")
    
    @property
    def log_retention_days(self) -> int:
        return int(self.data.get("logFileRetentionDays", 14))
    
    @property
    def save_path(self) -> str:
        return self.data.get("savePath", "./data")
    
    @property
    def print_retention_days(self) -> int:
        return int(self.data.get("printFileRetentionDays", 30))
    
    @property
    def host_map(self) -> Dict[str, str]:
        return self.data.get("hostMap", {})


class Logger:
    """Logger setup for the ePOS Proxy Server."""
    
    def __init__(self, config: Config):
        self.config = config
        self.setup_logger()
    
    def setup_logger(self) -> None:
        """Set up the logger with console and file handlers."""
        log_level = getattr(logging, self.config.log_level)
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)
        
        # Root logger
        logger = logging.getLogger()
        logger.setLevel(log_level)
        
        # Clear existing handlers
        if logger.handlers:
            for handler in logger.handlers:
                logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = TimedRotatingFileHandler(
            self.config.log_file,
            when='midnight',
            interval=1,
            backupCount=self.config.log_retention_days
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


class FileOperations:
    """File operations for the ePOS Proxy Server."""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def save_print_data(self, data: str, target: str) -> None:
        """Save print data to a file."""
        try:
            date_part = datetime.now().strftime("%Y-%m-%d")
            target_dir = Path(self.config.save_path) / target.replace("http://", "") / date_part
            target_dir.mkdir(exist_ok=True, parents=True)
            
            file_path = target_dir / f"{int(time.time() * 1000)}.xml"
            await asyncio.to_thread(self._write_file, file_path, data)
            
            logging.info(f"Print data saved to {file_path}")
        except Exception as e:
            logging.error(f"Error saving print data: {e}")
    
    def _write_file(self, path: Path, data: str) -> None:
        """Write data to a file (run in thread to avoid blocking)."""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(data)
    
    async def delete_old_print_files(self) -> None:
        """Delete print files older than the retention period."""
        try:
            logging.info("Checking for old print files to delete...")
            save_path = Path(self.config.save_path)
            if not save_path.exists():
                return
            
            cutoff_date = datetime.now() - timedelta(days=self.config.print_retention_days)
            cutoff_timestamp = cutoff_date.timestamp()
            
            # Find and delete old files
            count = 0
            for path in save_path.glob('**/*.xml'):
                if path.stat().st_mtime < cutoff_timestamp:
                    path.unlink()
                    count += 1
            
            if count > 0:
                logging.info(f"Deleted {count} old print files")
            
        except Exception as e:
            logging.error(f"Error deleting old print files: {e}")


class ProxyServer:
    """ePOS Proxy Server implementation."""
    
    def __init__(self, config: Config, file_ops: FileOperations):
        self.config = config
        self.file_ops = file_ops
        self.app = FastAPI(title="ePOS Proxy Server")
        self.client = AsyncClient(verify=False)
        self.setup_routes()
        self.setup_scheduler()
    
    def setup_routes(self) -> None:
        """Set up the routes for the proxy server."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        @self.app.api_route("/{hostname}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def proxy_request(request: Request, hostname: str, path: str):
            if hostname not in self.config.host_map:
                raise HTTPException(status_code=404, detail=f"Unknown hostname: {hostname}")
            
            target = self.config.host_map[hostname]
            url = f"{target}/{path}"
            
            # Get request data
            body = await request.body()
            body_str = body.decode('utf-8') if body else ""
            
            # Save print data for POST requests with content
            if request.method == "POST" and body_str:
                await self.file_ops.save_print_data(body_str, target)
            
            # Forward the request
            headers = {k: v for k, v in request.headers.items() 
                      if k.lower() not in ('host', 'content-length')}
            
            try:
                response = await self.client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                    follow_redirects=True
                )
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except Exception as e:
                logging.error(f"Proxy error: {e}")
                raise HTTPException(status_code=502, detail=str(e))
    
    def setup_scheduler(self) -> None:
        """Set up the scheduler for periodic tasks."""
        scheduler = AsyncIOScheduler()
        
        # Schedule file cleanup task (run once a day)
        scheduler.add_job(
            self.file_ops.delete_old_print_files,
            'interval',
            hours=24,
            next_run_time=datetime.now() + timedelta(minutes=5)  # First run after 5 minutes
        )
        
        # Start the scheduler
        scheduler.start()
    
    def run(self, host: str = "0.0.0.0", port: int = 443) -> None:
        """Run the server."""
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain("cert/server.cert", "cert/server.key")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            ssl_certfile="cert/server.cert",
            ssl_keyfile="cert/server.key"
        )


def main():
    """Main entry point for the ePOS Proxy Server."""
    # Load configuration
    config = Config()
    
    # Set up logger
    Logger(config)
    
    # Print startup message
    logging.info("Starting ePOS Proxy Server...")
    logging.info(f"Log level: {config.log_level}")
    logging.info(f"Configured printers: {list(config.host_map.keys())}")
    
    # Set up file operations
    file_ops = FileOperations(config)
    
    # Create and run the proxy server
    server = ProxyServer(config, file_ops)
    server.run()


if __name__ == "__main__":
    main()