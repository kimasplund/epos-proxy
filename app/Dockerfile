FROM python:3.12-slim

WORKDIR /app

# Install OpenSSL for certificate generation
RUN apt-get update && apt-get install -y openssl && apt-get clean

# Copy application files first to leverage Docker cache
COPY *.py ./
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create required directories
RUN mkdir -p cert log data

# Create config_watcher.py file
RUN echo '# config_watcher.py\n\
import os\n\
import time\n\
import logging\n\
import threading\n\
from typing import Callable\n\
\n\
# Global variable to control watcher thread\n\
_stop_watching = False\n\
_watcher_thread = None\n\
\n\
def watch_config_file(file_path: str, callback: Callable) -> bool:\n\
    """\n\
    Watch a configuration file for changes and call the callback when it changes.\n\
    \n\
    Args:\n\
        file_path: Path to the configuration file to watch\n\
        callback: Function to call when the file changes\n\
        \n\
    Returns:\n\
        bool: True if watching started successfully, False otherwise\n\
    """\n\
    if not os.path.exists(file_path):\n\
        logging.warning(f"Cannot watch non-existent file: {file_path}")\n\
        return False\n\
    \n\
    global _watcher_thread, _stop_watching\n\
    _stop_watching = False\n\
    \n\
    # Function to run in the watcher thread\n\
    def watch_file():\n\
        try:\n\
            last_modified = os.stat(file_path).st_mtime\n\
            logging.info(f"Started watching {file_path} for changes")\n\
            \n\
            while not _stop_watching:\n\
                try:\n\
                    # Check if the file has been modified\n\
                    current_modified = os.stat(file_path).st_mtime\n\
                    if current_modified > last_modified:\n\
                        logging.info(f"Detected change in {file_path}")\n\
                        last_modified = current_modified\n\
                        \n\
                        # Call the callback function\n\
                        try:\n\
                            callback()\n\
                        except Exception as e:\n\
                            logging.error(f"Error in callback: {e}")\n\
                    \n\
                    # Sleep to reduce CPU usage\n\
                    time.sleep(1)\n\
                    \n\
                except FileNotFoundError:\n\
                    logging.warning(f"Watched file not found: {file_path}")\n\
                    time.sleep(5)  # Wait a bit longer if file is missing\n\
                    \n\
                except Exception as e:\n\
                    logging.error(f"Error watching file: {e}")\n\
                    time.sleep(5)  # Wait a bit longer on error\n\
        \n\
        except Exception as e:\n\
            logging.error(f"Watcher thread error: {e}")\n\
    \n\
    # Create and start the watcher thread\n\
    _watcher_thread = threading.Thread(target=watch_file, daemon=True)\n\
    _watcher_thread.start()\n\
    \n\
    return True\n\
\n\
def stop_watching() -> bool:\n\
    """\n\
    Stop watching all configuration files.\n\
    \n\
    Returns:\n\
        bool: True if watching was stopped, False if it was not running\n\
    """\n\
    global _stop_watching, _watcher_thread\n\
    \n\
    if _watcher_thread is None or not _watcher_thread.is_alive():\n\
        logging.warning("Config watcher not running")\n\
        return False\n\
    \n\
    _stop_watching = True\n\
    _watcher_thread.join(timeout=2)\n\
    \n\
    if _watcher_thread.is_alive():\n\
        logging.warning("Failed to stop watcher thread")\n\
        return False\n\
    \n\
    logging.info("Config watcher stopped")\n\
    return True' > /app/config_watcher.py

# Create a custom entry script that properly handles asyncio
RUN echo '#!/usr/bin/env python3\n\
# Custom entry script for ePOS Proxy Server\n\
import os\n\
import sys\n\
import asyncio\n\
import subprocess\n\
import logging\n\
\n\
# Configure logging\n\
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")\n\
logger = logging.getLogger("entrypoint")\n\
\n\
async def generate_certificates():\n\
    """Generate self-signed certificates if they do not exist."""\n\
    cert_path = "/app/cert/server.cert"\n\
    key_path = "/app/cert/server.key"\n\
    \n\
    if not os.path.exists(cert_path) or not os.path.exists(key_path):\n\
        logger.info("Generating self-signed certificates...")\n\
        command = [\n\
            "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",\n\
            "-keyout", key_path, "-out", cert_path, "-days", "3650",\n\
            "-subj", "/CN=localhost"\n\
        ]\n\
        \n\
        process = await asyncio.create_subprocess_exec(\n\
            *command,\n\
            stdout=asyncio.subprocess.PIPE,\n\
            stderr=asyncio.subprocess.PIPE\n\
        )\n\
        \n\
        stdout, stderr = await process.communicate()\n\
        \n\
        if process.returncode != 0:\n\
            logger.error(f"Certificate generation failed with exit code {process.returncode}")\n\
            logger.error(stderr.decode())\n\
            sys.exit(1)\n\
        \n\
        logger.info("Certificates generated successfully")\n\
    else:\n\
        logger.info("Certificates already exist, skipping generation")\n\
\n\
async def initialize_database():\n\
    """Initialize the database for the web interface."""\n\
    try:\n\
        from database import init_db\n\
        from web_setup import setup_database, setup_default_assets\n\
        \n\
        await init_db()\n\
        logger.info("Database initialized")\n\
        \n\
        await setup_default_assets()\n\
        await setup_database()\n\
        logger.info("Web interface database and assets initialized")\n\
    except Exception as e:\n\
        logger.error(f"Failed to initialize database: {e}")\n\
\n\
async def main():\n\
    """Main entry point."""\n\
    # Generate certificates\n\
    await generate_certificates()\n\
    \n\
    # Initialize database for web interface\n\
    await initialize_database()\n\
    \n\
    # Run the main application\n\
    logger.info("Starting ePOS Proxy Server...")\n\
    \n\
    # Import the main module\n\
    import main as main_module\n\
    \n\
    # Parse command-line arguments\n\
    args = main_module.parse_args()\n\
    \n\
    # Create server (without starting it)\n\
    server = main_module.ProxyServer(\n\
        config_path=args.config,\n\
        enable_dns=not args.no_dns,\n\
        dns_port=args.dns_port,\n\
        watch_config=not args.no_watch_config,\n\
        enable_web=not args.no_web,\n\
        web_secret_key=args.web_secret_key\n\
    )\n\
    \n\
    # Now run the server with HTTPS\n\
    # Since run() is now async, we need to await it\n\
    await server.run(host=args.host, port=args.port)\n\
\n\
if __name__ == "__main__":\n\
    asyncio.run(main())\n\
' > /app/entrypoint.py

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.py

# Expose HTTPS and DNS ports
EXPOSE 443
EXPOSE 53/udp

# Run the application
ENTRYPOINT ["python", "/app/entrypoint.py"] 