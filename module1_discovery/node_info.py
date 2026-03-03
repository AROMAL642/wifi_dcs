"""
Node Information Collection Module
Collects system information: CPU, RAM, storage, network bandwidth
"""

import psutil
import platform
import socket
import subprocess
import json
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class NodeInfo:
    """Data class to store node information"""
    hostname: str
    ip_address: str
    mac_address: str
    cpu_cores: int
    cpu_freq_mhz: float
    cpu_percent: float
    ram_total_gb: float
    ram_available_gb: float
    storage_total_gb: float
    storage_available_gb: float
    network_bandwidth_mbps: Optional[float]
    os_info: str


class NodeInfoCollector:
    """Collects comprehensive node information"""
    
    def __init__(self):
        self.hostname = socket.gethostname()
        
    def get_ip_address(self) -> str:
        """Get the primary IP address of the node"""
        try:
            # Create a socket to determine the primary network interface
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    def get_mac_address(self) -> str:
        """Get MAC address of the primary network interface"""
        try:
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(0, 2*6, 2)][::-1])
            return mac
        except Exception:
            return "00:00:00:00:00:00"
    
    def get_cpu_info(self) -> tuple:
        """Get CPU cores, frequency, and current usage"""
        cores = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        cpu_freq = freq.current if freq else 0.0
        cpu_percent = psutil.cpu_percent(interval=1)
        return cores, cpu_freq, cpu_percent
    
    def get_ram_info(self) -> tuple:
        """Get RAM total and available in GB"""
        ram = psutil.virtual_memory()
        total_gb = ram.total / (1024 ** 3)
        available_gb = ram.available / (1024 ** 3)
        return total_gb, available_gb
    
    def get_storage_info(self) -> tuple:
        """Get storage total and available in GB"""
        disk = psutil.disk_usage('/')
        total_gb = disk.total / (1024 ** 3)
        available_gb = disk.free / (1024 ** 3)
        return total_gb, available_gb
    
    def estimate_network_bandwidth(self) -> Optional[float]:
        """
        Estimate network bandwidth in Mbps
        This is a simple estimation based on network interface speed
        """
        try:
            # Get network interface statistics
            net_if_stats = psutil.net_if_stats()
            
            # Find the active interface (not loopback)
            for interface, stats in net_if_stats.items():
                if stats.isup and interface != 'lo':
                    # Speed is in Mbps
                    return float(stats.speed) if stats.speed > 0 else None
            
            return None
        except Exception:
            return None
    
    def get_os_info(self) -> str:
        """Get operating system information"""
        return f"{platform.system()} {platform.release()} ({platform.machine()})"
    
    def collect_all_info(self) -> NodeInfo:
        """Collect all node information and return as NodeInfo object"""
        ip_address = self.get_ip_address()
        mac_address = self.get_mac_address()
        cpu_cores, cpu_freq, cpu_percent = self.get_cpu_info()
        ram_total, ram_available = self.get_ram_info()
        storage_total, storage_available = self.get_storage_info()
        bandwidth = self.estimate_network_bandwidth()
        os_info = self.get_os_info()
        
        return NodeInfo(
            hostname=self.hostname,
            ip_address=ip_address,
            mac_address=mac_address,
            cpu_cores=cpu_cores,
            cpu_freq_mhz=cpu_freq,
            cpu_percent=cpu_percent,
            ram_total_gb=ram_total,
            ram_available_gb=ram_available,
            storage_total_gb=storage_total,
            storage_available_gb=storage_available,
            network_bandwidth_mbps=bandwidth,
            os_info=os_info
        )
    
    def to_json(self, node_info: NodeInfo) -> str:
        """Convert NodeInfo to JSON string"""
        return json.dumps(asdict(node_info), indent=2)
    
    def to_dict(self, node_info: NodeInfo) -> dict:
        """Convert NodeInfo to dictionary"""
        return asdict(node_info)


if __name__ == "__main__":
    # Test the collector
    collector = NodeInfoCollector()
    info = collector.collect_all_info()
    print("Node Information:")
    print(collector.to_json(info))
