# file_operations.py
import time
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import Config


class FileOperations:
    """File operations for the ePOS Proxy Server."""
    
    def __init__(self, config: Config):
        self.config = config
    
    async def save_print_data(self, data: str, target: str, request_id: Optional[str] = None) -> None:
        """Save print data to a file.
        
        Args:
            data: The print data to save
            target: The target printer URL
            request_id: Optional request ID for tracking
        """
        try:
            date_part = datetime.now().strftime("%Y-%m-%d")
            # Remove protocol and any path from the target to use as directory name
            clean_target = target.replace("http://", "").replace("https://", "").split('/')[0]
            target_dir = Path(self.config.save_path) / clean_target / date_part
            target_dir.mkdir(exist_ok=True, parents=True)
            
            timestamp = int(time.time() * 1000)
            filename = f"{timestamp}_{request_id}.xml" if request_id else f"{timestamp}.xml"
            file_path = target_dir / filename
            
            # Run file writing in a separate thread to avoid blocking the event loop
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
            else:
                logging.debug("No old print files to delete")
            
        except Exception as e:
            logging.error(f"Error deleting old print files: {e}")
    
    async def list_saved_files(self, days: int = 7) -> dict:
        """List saved print files grouped by printer and date.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dict with printer and date information
        """
        result = {}
        try:
            save_path = Path(self.config.save_path)
            if not save_path.exists():
                return result
            
            # Get all printer directories
            for printer_dir in save_path.iterdir():
                if not printer_dir.is_dir():
                    continue
                
                printer_name = printer_dir.name
                result[printer_name] = {}
                
                # Get all date directories for this printer
                for date_dir in printer_dir.iterdir():
                    if not date_dir.is_dir():
                        continue
                    
                    # Only include recent dates based on the days parameter
                    try:
                        dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                        if dir_date < datetime.now() - timedelta(days=days):
                            continue
                    except ValueError:
                        # Skip directories that don't follow the date format
                        continue
                    
                    # Count files in this date directory
                    file_count = sum(1 for _ in date_dir.glob("*.xml"))
                    result[printer_name][date_dir.name] = file_count
        
        except Exception as e:
            logging.error(f"Error listing saved files: {e}")
        
        return result