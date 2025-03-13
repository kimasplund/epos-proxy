# main.py
import logging
import uuid
import ssl
import uvicorn
import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import (
    FastAPI, 
    Request, 
    Response, 
    HTTPException, 
    staticfiles
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from httpx import AsyncClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starlette.middleware.sessions import SessionMiddleware

from config import Config
from logger import Logger
from file_operations import FileOperations
from dns_server import (
    get_dns_server, 
    update_dns_records, 
    PROXY_HOSTNAME, 
    DOMAIN_SUFFIX
)
from config_watcher import watch_config_file, stop_watching
from database import init_db
from web_api import router as api_router


class ProxyServer:
    """ePOS Proxy Server implementation."""
    
    def __init__(
        self, 
        config_path: str = "config.json", 
        enable_dns: bool = True, 
        dns_port: int = 53, 
        watch_config: bool = True,
        enable_web: bool = True,
        web_secret_key: str = None,
    ):
        # Load configuration
        self.config_path = config_path
        self.config = Config(config_path)
        
        # Set up logger
        Logger(self.config)
        
        # Set DNS configuration
        self.enable_dns = enable_dns
        self.dns_port = dns_port
        self.dns_server = None
        self.watch_config = watch_config
        self.enable_web = enable_web
        self.web_secret_key = web_secret_key or "supersecretkey"
        
        # Print startup message
        logging.info("Starting ePOS Proxy Server...")
        logging.info(f"Log level: {self.config.log_level}")
        logging.info(f"Configured printers: {list(self.config.host_map.keys())}")
        
        # Set up file operations
        self.file_ops = FileOperations(self.config)
        
        # Start DNS server if enabled
        if self.enable_dns:
            self.dns_server = get_dns_server(port=self.dns_port)
            update_dns_records(self.config.host_map)
            dns_started = self.dns_server.start()
            if dns_started:
                logging.info(f"DNS server started on port {self.dns_port}")
                # Provide hostname info
                proxy_hostname = f"{PROXY_HOSTNAME}.{DOMAIN_SUFFIX}"
                logging.info(f"Server available at: https://{proxy_hostname}/")
                for printer in self.config.host_map.keys():
                    logging.info(f"Printer '{printer}' available at: https://{printer}.{DOMAIN_SUFFIX}/")
            else:
                logging.warning(f"Failed to start DNS server on port {self.dns_port}")
                logging.warning("DNS resolution will not be available")
                logging.warning(
                    "Try running with --dns-port=5353 if port 53 is already in use"
                )
        else:
            logging.info("DNS server is disabled")
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="ePOS Proxy Server",
            description="A proxy server for ePOS printing to printers that do not support HTTPS",
            version="1.1.0"
        )
        
        # Add session middleware for web interface
        self.app.add_middleware(SessionMiddleware, secret_key=self.web_secret_key)
        
        # Initialize HTTP client
        self.client = AsyncClient(verify=False, timeout=30.0)
        
        # Setup templates for web interface
        self.templates_dir = Path("templates")
        self.templates_dir.mkdir(exist_ok=True)
        self.templates = Jinja2Templates(directory=str(self.templates_dir))
        
        # Setup static files directory
        self.static_dir = Path("static")
        self.static_dir.mkdir(exist_ok=True)
        self.app.mount(
            "/static", 
            staticfiles.StaticFiles(directory=str(self.static_dir)), 
            name="static"
        )
        
        # Set up middleware
        self.setup_cors()
        
        # Set up web interface and API routes first (if enabled)
        if self.enable_web:
            # Setup the API router with explicit prefix
            self.app.include_router(
                api_router,
                prefix="/api"
            )
            # Setup web interface routes
            self._setup_web_routes()
            logging.info("Web interface enabled")
            
        # Setup other routes after web/API routes
        self.setup_routes()
        self.setup_scheduler()
        
        # Start config watcher if enabled
        if self.watch_config:
            self._start_config_watcher()
        
    def setup_cors(self):
        """Set up CORS middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _start_config_watcher(self):
        """Start watching configuration files for changes."""
        printers_config = "printers.config"
        
        # Define the callback to reload config when printers.config changes
        def reload_printers_config():
            try:
                logging.info("Reloading printer configuration...")
                
                # Reload configuration
                self.config = Config(self.config_path)
                
                # Update DNS records
                if self.enable_dns and self.dns_server:
                    update_dns_records(self.config.host_map)
                    logging.info("DNS records updated with new printer configuration")
                    # Log new printer hostnames
                    for printer in self.config.host_map.keys():
                        logging.info(f"Printer '{printer}' available at: https://{printer}.{DOMAIN_SUFFIX}/")
                
                logging.info("Printer configuration reloaded successfully")
                logging.info(f"Updated printers: {list(self.config.host_map.keys())}")
            except Exception as e:
                logging.error(f"Error reloading configuration: {e}")
        
        # Start watching printers.config
        watch_started = watch_config_file(printers_config, reload_printers_config)
        if watch_started:
            logging.info(f"Watching {printers_config} for changes")
        else:
            logging.warning(f"Failed to start watching {printers_config}")
    
    def _setup_web_routes(self):
        """Set up routes for the web interface."""
        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            """Redirect to web interface or show landing page."""
            return RedirectResponse(url="/web")
            
        @self.app.get("/web", response_class=HTMLResponse)
        async def web_interface(request: Request):
            """Serve the web interface SPA."""
            return self.templates.TemplateResponse(
                "index.html", 
                {
                    "request": request, 
                    "app_name": "ePOS Proxy",
                    "domain_suffix": DOMAIN_SUFFIX,
                    "proxy_hostname": PROXY_HOSTNAME
                }
            )
            
        @self.app.get("/web/{rest_of_path:path}", response_class=HTMLResponse)
        async def spa_routes(request: Request, rest_of_path: str):
            """Handle all other routes for the SPA."""
            return self.templates.TemplateResponse(
                "index.html", 
                {
                    "request": request, 
                    "app_name": "ePOS Proxy",
                    "domain_suffix": DOMAIN_SUFFIX,
                    "proxy_hostname": PROXY_HOSTNAME
                }
            )
    
    def setup_routes(self) -> None:
        """Set up the API routes for the proxy server."""
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy", 
                "timestamp": datetime.now().isoformat()
            }
        
        @self.app.get("/printers")
        async def list_printers():
            """List configured printers."""
            printers_info = {}
            for name, url in self.config.host_map.items():
                printers_info[name] = {
                    "url": url,
                    "dns_name": f"{name}.{DOMAIN_SUFFIX}"
                }
            return {"printers": printers_info}
        
        @self.app.get("/dns")
        async def dns_status():
            """DNS server status."""
            if self.enable_dns and self.dns_server:
                return {
                    "status": "enabled",
                    "running": self.dns_server.running,
                    "port": self.dns_port,
                    "hosts": len(self.config.host_map),
                    "domain_suffix": DOMAIN_SUFFIX,
                    "proxy_hostname": f"{PROXY_HOSTNAME}.{DOMAIN_SUFFIX}"
                }
            else:
                return {"status": "disabled"}
        
        @self.app.get("/config")
        async def config_status():
            """Configuration watch status."""
            return {
                "config_watching": self.watch_config,
                "printers_file": "printers.config",
                "printer_count": len(self.config.host_map)
            }
        
        @self.app.get("/files")
        async def list_files(days: int = 7):
            """List saved print files."""
            files = await self.file_ops.list_saved_files(days)
            return {"files": files}
        
        @self.app.api_route(
            "/{hostname}/{path:path}", 
            methods=["GET", "POST", "PUT", "DELETE"]
        )
        async def proxy_request(request: Request, hostname: str, path: str):
            """Main proxy endpoint that forwards requests to the configured printers."""
            # Skip if this is a web or api request
            if hostname in ["web", "api"]:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Not found: /{hostname}/{path}"
                )
                
            # Remove domain suffix if present
            if hostname.endswith(f".{DOMAIN_SUFFIX}"):
                hostname = hostname[:-len(f".{DOMAIN_SUFFIX}")]
            
            # Check if hostname is configured
            if hostname not in self.config.host_map:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Unknown printer: {hostname}"
                )
            
            target = self.config.host_map[hostname]
            url = f"{target}/{path}"
            
            # Generate request ID for tracking
            request_id = str(uuid.uuid4())
            logging.info(
                f"Request {request_id}: {request.method} {hostname}/{path} -> {url}"
            )
            
            # Get request data
            body = await request.body()
            body_str = body.decode('utf-8') if body else ""
            
            # Save print data for POST requests with content
            if request.method == "POST" and body_str:
                file_path = await self.file_ops.save_print_data(body_str, target, request_id)
                
                # Store print job in database for web interface if enabled
                if self.enable_web:
                    from database import PrintJob, async_session
                    
                    async with async_session() as session:
                        try:
                            # Create print job record
                            print_job = PrintJob(
                                job_id=request_id,
                                printer_name=hostname,
                                content=body_str,
                                status="success",
                                file_path=file_path
                            )
                            session.add(print_job)
                            await session.commit()
                            
                            logging.info(f"Print job recorded for web interface: {request_id}")
                        except Exception as e:
                            logging.error(f"Failed to record print job: {e}")
            
            # Forward the request
            headers = {
                k: v for k, v in request.headers.items() 
                if k.lower() not in ('host', 'content-length')
            }
            
            try:
                response = await self.client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                    follow_redirects=True
                )
                
                logging.info(
                    f"Request {request_id}: Status {response.status_code}"
                )
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except Exception as e:
                logging.error(f"Request {request_id}: Proxy error: {e}")
                raise HTTPException(status_code=502, detail=str(e))
    
    def setup_scheduler(self) -> None:
        """Set up the scheduler for periodic tasks."""
        try:
            # First try getting the current event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # If there's no running event loop, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
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
            logging.info("Scheduler started successfully")
        except Exception as e:
            logging.error(f"Failed to set up scheduler: {e}")
    
    async def initialize_database(self):
        """Initialize the database for web interface."""
        if self.enable_web:
            try:
                await init_db()
                logging.info("Database initialized")
                
                # Initialize default data
                from web_setup import setup_database, setup_default_assets
                
                await setup_default_assets()
                await setup_database()
                
                logging.info("Web interface database and assets initialized")
            except Exception as e:
                logging.error(f"Failed to initialize database: {e}")
                if "enable_web" in str(e):
                    self.enable_web = False
                    logging.warning("Web interface disabled due to database error")
    
    async def run(self, host: str = "0.0.0.0", port: int = 443) -> None:
        """Run the server with HTTPS."""
        # Set up SSL context
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain("cert/server.cert", "cert/server.key")
        
        try:
            # Use uvicorn with Config to avoid asyncio.run() calls
            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                ssl_certfile="cert/server.cert",
                ssl_keyfile="cert/server.key",
                log_level="info"
            )
            server = uvicorn.Server(config)
            # Use the existing event loop
            await server.serve()
        finally:
            # Clean up and stop services on exit
            if self.enable_dns and self.dns_server:
                self.dns_server.stop()
                logging.info("DNS server stopped")
            
            # Stop config watcher
            if self.watch_config:
                stop_watching()
                logging.info("Config watcher stopped")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="ePOS Proxy Server")
    parser.add_argument(
        "--config", 
        default="config.json", 
        help="Path to configuration file (default: config.json)"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0", 
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=443, 
        help="Port to bind the server to (default: 443)"
    )
    parser.add_argument(
        "--no-dns", 
        action="store_true", 
        help="Disable the built-in DNS server"
    )
    parser.add_argument(
        "--dns-port", 
        type=int, 
        default=53, 
        help="Port for the DNS server (default: 53, requires root/admin)"
    )
    parser.add_argument(
        "--no-watch-config",
        action="store_true",
        help="Disable watching configuration files for changes"
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Disable the web interface"
    )
    parser.add_argument(
        "--web-secret-key",
        help="Secret key for web sessions (generated if not provided)"
    )
    return parser.parse_args()


def main():
    """Main entry point for the ePOS Proxy Server."""
    args = parse_args()
    server = ProxyServer(
        config_path=args.config,
        enable_dns=not args.no_dns,
        dns_port=args.dns_port,
        watch_config=not args.no_watch_config,
        enable_web=not args.no_web,
        web_secret_key=args.web_secret_key
    )
    
    # Since run is now async, we need to use asyncio.run
    asyncio.run(server.run(host=args.host, port=args.port))


if __name__ == "__main__":
    main()