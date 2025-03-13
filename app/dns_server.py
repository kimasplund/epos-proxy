"""
Simple DNS server to resolve printer hostnames to their IP addresses.
"""
import logging
import threading
import ipaddress
import socket
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from dnslib import DNSRecord, RR, QTYPE, A, SOA, NS

# Configure logger
logger = logging.getLogger(__name__)

# Domain suffix for all names
DOMAIN_SUFFIX = "epos"
# Hostname for the proxy server
PROXY_HOSTNAME = "proxy"

class PrinterResolver:
    """Resolve printer hostnames based on a provided host map."""
    
    def __init__(self, host_map: Optional[Dict[str, str]] = None):
        """
        Initialize resolver with a host map.
        
        Args:
            host_map: Dictionary mapping hostnames to IP addresses or URLs
        """
        self.host_map = {}
        # Default TTL for records (60 seconds)
        self.default_ttl = 60
        # Proxy server IP
        self.proxy_ip = None
        # Try to get host IP
        self.update_proxy_ip()
        
        if host_map:
            self.update_host_map(host_map)
    
    def update_proxy_ip(self):
        """Update the proxy server IP address."""
        try:
            # Try to get the host's primary IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Connect to any external IP to determine local interface
            s.connect(("8.8.8.8", 80))
            self.proxy_ip = s.getsockname()[0]
            s.close()
            logger.info(f"Detected proxy server IP: {self.proxy_ip}")
        except Exception as e:
            logger.warning(f"Could not detect proxy server IP: {e}")
            # Fallback to loopback if no external IP found
            self.proxy_ip = "127.0.0.1"
            logger.warning(f"Using fallback IP for proxy: {self.proxy_ip}")
    
    def update_host_map(self, host_map: Dict[str, str]):
        """
        Update the hostname to IP address mapping.
        
        Args:
            host_map: Dictionary mapping hostnames to IP addresses or URLs
        """
        # Convert any URLs to IP addresses and store mapping
        self.host_map = {}
        
        # Add proxy server record
        proxy_fqdn = f"{PROXY_HOSTNAME}.{DOMAIN_SUFFIX}."
        self.host_map[proxy_fqdn] = self.proxy_ip
        logger.info(f"Added proxy server mapping: {proxy_fqdn} -> {self.proxy_ip}")
        
        # Add all printer records
        for hostname, url in host_map.items():
            # Skip entries with empty hostname
            if not hostname:
                continue
                
            # Add domain suffix if not present
            if not hostname.endswith(f".{DOMAIN_SUFFIX}"):
                hostname = f"{hostname}.{DOMAIN_SUFFIX}"
                
            # Ensure hostname ends with a dot
            if not hostname.endswith('.'):
                hostname = f"{hostname}."
                
            # Extract IP from URL if needed
            try:
                parsed_url = urlparse(url)
                ip_address = parsed_url.netloc.split(':')[0]
                
                # Validate IP address
                ipaddress.ip_address(ip_address)
                self.host_map[hostname] = ip_address
                logger.info(f"Mapped {hostname} -> {ip_address}")
            except ValueError:
                logger.error(f"Invalid IP address in URL: {url}")
                continue
    
    def resolve(self, request):
        """
        Resolve DNS query based on the host map.
        
        Args:
            request: DNSRecord request to resolve
            
        Returns:
            DNSRecord: DNS response
        """
        reply = request.reply()
        qname = str(request.q.qname)
        qtype = request.q.qtype
        
        logger.debug(f"DNS Query: {qname} (Type: {QTYPE.get(qtype)})")
        
        # Handle A record queries
        if qtype == QTYPE.A:
            # Check if hostname is in our map
            if qname in self.host_map:
                ip = self.host_map[qname]
                logger.info(f"Resolving {qname} to {ip}")
                reply.add_answer(RR(
                    qname, 
                    QTYPE.A, 
                    ttl=self.default_ttl,  # Short TTL for frequent updates
                    rdata=A(ip)
                ))
            else:
                # Try adding domain suffix for bare hostnames
                # Check if query might be missing the domain suffix
                name_parts = qname.strip('.').split('.')
                if len(name_parts) == 1 or DOMAIN_SUFFIX not in name_parts:
                    # Single-part name, try with suffix
                    alternative_name = f"{name_parts[0]}.{DOMAIN_SUFFIX}."
                    if alternative_name in self.host_map:
                        ip = self.host_map[alternative_name]
                        logger.info(f"Resolving {qname} to {ip} (via {alternative_name})")
                        reply.add_answer(RR(
                            qname, 
                            QTYPE.A, 
                            ttl=self.default_ttl,
                            rdata=A(ip)
                        ))
        elif qtype == QTYPE.SOA:
            # Return SOA for authoritative response
            reply.add_answer(RR(
                qname,
                QTYPE.SOA,
                ttl=self.default_ttl,
                rdata=SOA(
                    f"ns1.{DOMAIN_SUFFIX}.",
                    f"admin.{DOMAIN_SUFFIX}.",
                    (2023010100, 3600, 3600, 3600, 3600)
                )
            ))
        elif qtype == QTYPE.NS:
            # Return NS for name server queries
            reply.add_answer(RR(
                qname,
                QTYPE.NS,
                ttl=self.default_ttl,
                rdata=NS(f"ns1.{DOMAIN_SUFFIX}.")
            ))
            
        return reply


class DNSServerManager:
    """Manages the DNS server lifecycle."""
    
    def __init__(self, port=53):
        """
        Initialize DNS server manager.
        
        Args:
            port: UDP port to listen on (default: 53)
        """
        self.port = port
        self.resolver = PrinterResolver()
        self.server_thread = None
        self.running = False
    
    def start(self):
        """Start the DNS server in a separate thread."""
        if self.running:
            logger.warning("DNS server already running")
            return False
            
        try:
            from dnslib.server import DNSServer
            
            dns_server = DNSServer(
                self.resolver,
                port=self.port,
                address="0.0.0.0"
            )
            
            self.server_thread = threading.Thread(
                target=dns_server.start_thread,
                daemon=True
            )
            self.server_thread.start()
            self.running = True
            logger.info(f"DNS server started on port {self.port}")
            
            # Log available hostnames
            self.log_available_hostnames()
            
            return True
        except Exception as e:
            logger.error(f"Failed to start DNS server: {e}")
            return False
    
    def log_available_hostnames(self):
        """Log all available hostnames for reference."""
        logger.info("Available DNS hostnames:")
        for hostname, ip in self.resolver.host_map.items():
            logger.info(f"  {hostname} -> {ip}")
    
    def stop(self):
        """Stop the DNS server."""
        if not self.running:
            logger.warning("DNS server not running")
            return False
            
        try:
            self.running = False
            # The thread is a daemon, so it will terminate when the main thread exits
            logger.info("DNS server stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop DNS server: {e}")
            return False
    
    def update_host_map(self, host_map: Dict[str, str]):
        """
        Update the hostname to IP address mapping.
        
        Args:
            host_map: Dictionary mapping hostnames to IP addresses or URLs
        """
        self.resolver.update_host_map(host_map)
        if self.running:
            self.log_available_hostnames()
        return True


# Singleton instance
_dns_server_instance = None

def get_dns_server(port=53) -> DNSServerManager:
    """
    Get the singleton DNS server instance.
    
    Args:
        port: UDP port to listen on (default: 53)
        
    Returns:
        DNSServerManager: Singleton DNS server instance
    """
    global _dns_server_instance
    if _dns_server_instance is None:
        _dns_server_instance = DNSServerManager(port=port)
    return _dns_server_instance


def update_dns_records(host_map: Dict[str, str]):
    """
    Update the DNS server records.
    
    Args:
        host_map: Dictionary mapping hostnames to IP addresses or URLs
        
    Returns:
        bool: True if successful, False otherwise
    """
    server = get_dns_server()
    return server.update_host_map(host_map) 