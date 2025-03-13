# config_watcher.py
import os
import time
import logging
import threading
from typing import Callable

# Global variable to control watcher thread
_stop_watching = False
_watcher_thread = None

def watch_config_file(file_path: str, callback: Callable) -> bool:
    """
    Watch a configuration file for changes and call the callback when it changes.
    
    Args:
        file_path: Path to the configuration file to watch
        callback: Function to call when the file changes
        
    Returns:
        bool: True if watching started successfully, False otherwise
    """
    if not os.path.exists(file_path):
        logging.warning(f"Cannot watch non-existent file: {file_path}")
        return False
    
    global _watcher_thread, _stop_watching
    _stop_watching = False
    
    # Function to run in the watcher thread
    def watch_file():
        try:
            last_modified = os.stat(file_path).st_mtime
            logging.info(f"Started watching {file_path} for changes")
            
            while not _stop_watching:
                try:
                    # Check if the file has been modified
                    current_modified = os.stat(file_path).st_mtime
                    if current_modified > last_modified:
                        logging.info(f"Detected change in {file_path}")
                        last_modified = current_modified
                        
                        # Call the callback function
                        try:
                            callback()
                        except Exception as e:
                            logging.error(f"Error in callback: {e}")
                    
                    # Sleep to reduce CPU usage
                    time.sleep(1)
                    
                except FileNotFoundError:
                    logging.warning(f"Watched file not found: {file_path}")
                    time.sleep(5)  # Wait a bit longer if file is missing
                    
                except Exception as e:
                    logging.error(f"Error watching file: {e}")
                    time.sleep(5)  # Wait a bit longer on error
        
        except Exception as e:
            logging.error(f"Watcher thread error: {e}")
    
    # Create and start the watcher thread
    _watcher_thread = threading.Thread(target=watch_file, daemon=True)
    _watcher_thread.start()
    
    return True

def stop_watching() -> bool:
    """
    Stop watching all configuration files.
    
    Returns:
        bool: True if watching was stopped, False if it wasn't running
    """
    global _stop_watching, _watcher_thread
    
    if _watcher_thread is None or not _watcher_thread.is_alive():
        logging.warning("Config watcher not running")
        return False
    
    _stop_watching = True
    _watcher_thread.join(timeout=2)
    
    if _watcher_thread.is_alive():
        logging.warning("Failed to stop watcher thread")
        return False
    
    logging.info("Config watcher stopped")
    return True 