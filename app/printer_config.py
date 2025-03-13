# printer_config.py
import os
import logging

def parse_printers_config(file_path="printers.config"):
    """
    Parse the simplified printers.config file into a dictionary.
    
    Format is:
    printer_name = ip_address
    
    Lines starting with # are treated as comments.
    The .epos domain suffix will be automatically handled by the DNS server.
    
    Args:
        file_path (str): Path to the printers.config file
        
    Returns:
        dict: Dictionary mapping printer names to IP addresses
    """
    printers = {}
    
    if not os.path.exists(file_path):
        logging.warning(f"Printers config file not found: {file_path}")
        return printers
    
    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                # Skip empty lines and comments
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Split by equals sign
                parts = line.split('=', 1)
                if len(parts) != 2:
                    logging.warning(f"Invalid line {line_num} in {file_path}: {line}")
                    continue
                
                printer_name = parts[0].strip()
                ip_address = parts[1].strip()
                
                # Validate printer name and IP address
                if not printer_name:
                    logging.warning(f"Empty printer name at line {line_num} in {file_path}")
                    continue
                
                if not ip_address:
                    logging.warning(
                        f"Empty IP address for {printer_name} at line {line_num} in {file_path}"
                    )
                    continue
                
                # Remove any .epos suffix from printer name as DNS server will add it
                if printer_name.endswith(".epos"):
                    printer_name = printer_name[:-5]  # Remove .epos suffix
                    logging.info(f"Removed .epos suffix from printer name: {printer_name}")
                
                # Add http:// prefix if not present
                if not ip_address.startswith(('http://', 'https://')):
                    ip_address = f"http://{ip_address}"
                
                printers[printer_name] = ip_address
                logging.info(f"Configured printer: {printer_name} -> {ip_address} (will be available as {printer_name}.epos)")
        
        if not printers:
            logging.warning(f"No valid printer configurations found in {file_path}")
        
        return printers
    
    except Exception as e:
        logging.error(f"Error parsing printers config: {e}")
        return {} 