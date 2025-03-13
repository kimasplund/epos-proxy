# logger.py
import logging
from logging.handlers import TimedRotatingFileHandler

from config import Config


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
        
        logging.info(f"Logger initialized with level: {self.config.log_level}")