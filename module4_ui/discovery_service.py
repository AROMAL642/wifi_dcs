"""
WiFi-based node discovery service for auto-finding Master/Worker nodes.
Uses mDNS and network scanning for device discovery.
"""

import socket
import threading
import json
from typing import List, Dict, Callable, Optional
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import zeroconf
except ImportError:
    zeroconf = None


def get_local_ip() -> str:
    """
    Return a non-loopback local IP address by creating a UDP socket to a public host.
    This does not send packets, just determines the local interface used to reach the Internet/lan.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # connecting to a public IP (no packets are sent)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        # fallback to hostname resolution (may return 127.0.0.1 on some systems)
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"


class NodeDiscoveryService:
    """Service for discovering nodes on local network."""
    
    def __init__(self, service_type: str = "_distributed-compute._tcp.local.",
                 discovery_callback: Optional[Callable] = None):
        self.service_type = service_type
        self.discovery_callback = discovery_callback
        self.discovered_nodes = {}
        self.is_scanning = False
        self.scan_thread = None
    
    def start_discovery(self):
        """Start discovering nodes."""
        self.is_scanning = True
        self.scan_thread = threading.Thread(target=self._scan_network, daemon=True)
        self.scan_thread.start()
    
    def stop_discovery(self):
        """Stop discovering nodes."""
        self.is_scanning = False
        if self.scan_thread:
            self.scan_thread.join(timeout=2)
    
    def _scan_network(self):
        """Scan network for nodes using multiple methods."""
        if zeroconf:
            self._scan_mdns()
        else:
            self._scan_tcp_ports()
    
    def _scan_mdns(self):
        """Scan using mDNS (requires zeroconf)."""
        try:
            from zeroconf import ServiceBrowser, Zeroconf
            
            def on_service_state_change(zeroconf, service_type, name, state_change):
                if state_change.name == "Added":
                    info = zeroconf.get_service_info(service_type, name)
                    if info:
                        self._add_discovered_node(info)
            
            zeroconf_inst = Zeroconf()
            ServiceBrowser(zeroconf_inst, self.service_type, on_service_state_change)
            
            # Keep scanning for 30 seconds
            for _ in range(30):
                if not self.is_scanning:
                    break
                time.sleep(1)
            
            zeroconf_inst.close()
        except Exception as e:
            print(f"mDNS scan error: {e}")
    
    def _scan_tcp_ports(self):
        """Fallback: Scan TCP ports on local network."""
        try:
            # Determine local network using more reliable method
            local_ip = get_local_ip()
            network_prefix = ".".join(local_ip.split(".")[:-1])
            
            # Scan common ports
            ports = [6000, 6001, 6002, 6003, 6004, 6005]
            
            for i in range(1, 255):
                if not self.is_scanning:
                    break
                
                ip = f"{network_prefix}.{i}"
                if ip == local_ip:
                    continue
                
                for port in ports:
                    self._check_node(ip, port)
        except Exception as e:
            print(f"TCP scan error: {e}")
    
    def _check_node(self, ip: str, port: int):
        """Check if node is reachable."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                node_addr = f"{ip}:{port}"
                self.discovered_nodes[node_addr] = {
                    "ip": ip,
                    "port": port,
                    "discovered_at": time.time()
                }
                
                if self.discovery_callback:
                    self.discovery_callback(node_addr, "discovered")
        except:
            pass
    
    def _add_discovered_node(self, info):
        """Add discovered mDNS node."""
        try:
            addresses = [str(addr) for addr in info.addresses]
            for addr in addresses:
                node_addr = f"{addr}:{info.port}"
                self.discovered_nodes[node_addr] = {
                    "ip": addr,
                    "port": info.port,
                    "name": info.name,
                    "discovered_at": time.time()
                }
                
                if self.discovery_callback:
                    self.discovery_callback(node_addr, "discovered")
        except Exception as e:
            print(f"Error adding mDNS node: {e}")
    
    def get_discovered_nodes(self) -> List[str]:
        """Get list of discovered node addresses."""
        return list(self.discovered_nodes.keys())
    
    def get_node_info(self, node_addr: str) -> Optional[Dict]:
        """Get information about a discovered node."""
        return self.discovered_nodes.get(node_addr)


class AdvertiseService:
    """Service for advertising this node on the network."""
    
    def __init__(self, node_name: str, node_role: str, port: int):
        self.node_name = node_name
        self.node_role = node_role
        self.port = port
        self.zeroconf = None
    
    def start_advertising(self):
        """Start advertising this node."""
        if not zeroconf:
            print("zeroconf not available, skipping mDNS advertisement")
            return
        
        try:
            from zeroconf import ServiceInfo, Zeroconf
            
            self.zeroconf = Zeroconf()
            
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            info = ServiceInfo(
                "_distributed-compute._tcp.local.",
                f"{self.node_name}._distributed-compute._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties={"role": self.node_role, "version": "1.0"},
                server=f"{hostname}.local."
            )
            
            self.zeroconf.register_service(info)
        except Exception as e:
            print(f"Failed to advertise service: {e}")
    
    def stop_advertising(self):
        """Stop advertising this node."""
        if self.zeroconf:
            self.zeroconf.close()
