"""
WiFi Node Discovery Service
Uses multiple scanning methods: ARP cache, arp-scan, nmap, ICMP ping sweep
Collects detailed device information including signal strength, MAC, etc.
"""

import socket
import json
import threading
import time
import subprocess
import re
import ipaddress
from typing import Dict, Callable, Optional, List, Set, Tuple
from node_info import NodeInfoCollector, NodeInfo


class DiscoveryService:
    """
    WiFi-based node discovery service using multiple scanning methods
    """
    
    DISCOVERY_PORT = 5555
    SCAN_INTERVAL = 10  # seconds between scans
    
    def __init__(self, scan_interval: int = SCAN_INTERVAL):
        self.scan_interval = scan_interval
        self.collector = NodeInfoCollector()
        self.local_node_info = self.collector.collect_all_info()
        
        # Dictionary to store discovered nodes: {ip_address: node_data}
        self.discovered_nodes: Dict[str, dict] = {}
        
        # Set to store discovered IPs (for quick lookup)
        self.discovered_ips: Set[str] = set()
        
        # Threading control
        self.running = False
        self.scanner_thread: Optional[threading.Thread] = None
        self.listener_thread: Optional[threading.Thread] = None
        
        # Callback for new node discovery
        self.on_node_discovered: Optional[Callable] = None
        
        # Get local network subnet
        self.local_subnet = self._get_local_subnet()
    
    def _get_local_subnet(self) -> str:
        """Get the local network subnet in CIDR notation"""
        try:
            ip = self.local_node_info.ip_address
            # Assume /24 subnet for most home/office networks
            network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
            return str(network)
        except Exception:
            return "192.168.1.0/24"
    
    def start(self):
        """Start the discovery service (scanner and listener)"""
        if self.running:
            print("Discovery service is already running")
            return
        
        self.running = True
        
        # Start scanner thread
        self.scanner_thread = threading.Thread(target=self._scan_network, daemon=True)
        self.scanner_thread.start()
        
        # Start listener thread for responding to requests
        self.listener_thread = threading.Thread(target=self._listen_for_requests, daemon=True)
        self.listener_thread.start()
        
        print(f"Discovery service started")
        print(f"Local node: {self.local_node_info.hostname} ({self.local_node_info.ip_address})")
        print(f"Scanning subnet: {self.local_subnet}")
    
    def stop(self):
        """Stop the discovery service"""
        self.running = False
        
        if self.scanner_thread:
            self.scanner_thread.join(timeout=2)
        
        if self.listener_thread:
            self.listener_thread.join(timeout=2)
        
        print("Discovery service stopped")
    
    def _scan_network(self):
        """Main scanning loop - tries multiple methods to find LIVE devices only"""
        print("\n🔍 Starting network scan for LIVE devices...\n")
        
        while self.running:
            try:
                # Clear previous discoveries to show only current live devices
                self.discovered_nodes.clear()
                self.discovered_ips.clear()
                
                live_ips = set()
                scan_results = {}
                
                # Method 0: Check localhost for simulated nodes (for testing)
                print("📡 Method 0: Checking localhost for simulated nodes...", end=" ", flush=True)
                localhost_ips = self._scan_localhost_nodes()
                scan_results['Localhost'] = len(localhost_ips)
                live_ips.update(localhost_ips)
                if localhost_ips:
                    print(f"✓ Found {len(localhost_ips)} simulated nodes")
                else:
                    print("⊗ No simulated nodes")
                
                # Method 1: ICMP ping sweep (most reliable for live devices)
                print("📡 Method 1/4: ICMP ping sweep (checking live devices)...", end=" ", flush=True)
                ping_ips = self._ping_sweep()
                scan_results['Ping Sweep'] = len(ping_ips)
                live_ips.update(ping_ips)
                print(f"✓ Found {len(ping_ips)} live hosts")
                
                # Method 2: Try arp-scan (if available - shows live devices)
                print("📡 Method 2/4: Running arp-scan (live scan)...", end=" ", flush=True)
                arpscan_ips = self._scan_with_arpscan()
                scan_results['arp-scan'] = len(arpscan_ips)
                live_ips.update(arpscan_ips)
                if arpscan_ips:
                    print(f"✓ Found {len(arpscan_ips)} live hosts")
                else:
                    print("⊗ Not available or no results")
                
                # Method 3: Try nmap (if available - ping scan for live devices)
                print("📡 Method 3/4: Running nmap scan (live hosts)...", end=" ", flush=True)
                nmap_ips = self._scan_with_nmap()
                scan_results['nmap'] = len(nmap_ips)
                live_ips.update(nmap_ips)
                if nmap_ips:
                    print(f"✓ Found {len(nmap_ips)} live hosts")
                else:
                    print("⊗ Not available or no results")
                
                # Method 4: Verify with ARP (only for IPs confirmed live by other methods)
                print("📡 Method 4/4: Verifying with ARP cache...", end=" ", flush=True)
                arp_ips = self._scan_arp_cache()
                # Only use ARP entries that are confirmed live by ping/scan
                verified_arp = arp_ips.intersection(live_ips) if live_ips else set()
                scan_results['ARP Verified'] = len(verified_arp)
                print(f"✓ Verified {len(verified_arp)} hosts")
                
                # Display scan summary
                print("\n" + "="*70)
                print("SCAN SUMMARY - LIVE DEVICES ONLY")
                print("="*70)
                for method, count in scan_results.items():
                    print(f"  {method:20s}: {count} hosts")
                print(f"\n  Total LIVE Hosts    : {len(live_ips)} (excluding self)")
                print("="*70 + "\n")
                
                # Request node info from each discovered IP
                if live_ips:
                    print("🔄 Gathering detailed information from live nodes...\n")
                    for ip in live_ips:
                        if ip != self.local_node_info.ip_address:
                            # Get basic info first
                            self._add_basic_node(ip)
                            # Try to get detailed info if running our service
                            self._request_node_info(ip)
                            # Get additional network details
                            self._get_network_details(ip)
                    
                    # Give some time for responses
                    time.sleep(2)
                    
                    # Display all discovered nodes
                    self.print_all_nodes()
                else:
                    print("ℹ️  No other live devices found on the network.\n")
                    print("="*70 + "\n")
                
                # Wait before next scan
                print(f"⏳ Next scan in {self.scan_interval} seconds...\n")
                time.sleep(self.scan_interval)
                
            except Exception as e:
                if self.running:
                    print(f"❌ Error in scanner: {e}")
                time.sleep(self.scan_interval)
    
    def _scan_localhost_nodes(self) -> Set[str]:
        """Check localhost for simulated nodes (for testing purposes)"""
        ips = set()
        
        # Try to contact localhost on the discovery port
        # This helps find simulated nodes running locally
        try:
            # Check if there's a node responding on localhost
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.5)
            
            # Try to send a discovery request to localhost
            try:
                sock.sendto(b"GET_NODE_INFO", ('127.0.0.1', self.DISCOVERY_PORT))
                
                # Wait for any response
                try:
                    data, addr = sock.recvfrom(4096)
                    if data:
                        # There's a simulated node on localhost
                        # Add the actual IP address (not 127.0.0.1)
                        ips.add(self.local_node_info.ip_address)
                except socket.timeout:
                    pass
            except:
                pass
            
            sock.close()
        except Exception as e:
            pass
        
        return ips
    
    def _scan_arp_cache(self) -> Set[str]:
        """Read ARP cache to find active hosts"""
        ips = set()
        try:
            # Linux: read /proc/net/arp
            try:
                with open('/proc/net/arp', 'r') as f:
                    lines = f.readlines()[1:]  # Skip header
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 1:
                            ip = parts[0]
                            if self._is_valid_ip(ip):
                                ips.add(ip)
            except FileNotFoundError:
                pass
            
            # Also try 'arp -a' command
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Parse output for IP addresses
                ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
                found_ips = re.findall(ip_pattern, result.stdout)
                for ip in found_ips:
                    if self._is_valid_ip(ip):
                        ips.add(ip)
        
        except Exception as e:
            print(f"ARP cache scan error: {e}")
        
        return ips
    
    def _scan_with_arpscan(self) -> Set[str]:
        """Use arp-scan tool if available"""
        ips = set()
        try:
            # Try arp-scan command
            result = subprocess.run(
                ['arp-scan', '--interface=auto', '--localnet'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse output for IP addresses
                ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
                found_ips = re.findall(ip_pattern, result.stdout)
                for ip in found_ips:
                    if self._is_valid_ip(ip):
                        ips.add(ip)
        
        except FileNotFoundError:
            # arp-scan not installed
            pass
        except Exception as e:
            print(f"arp-scan error: {e}")
        
        return ips
    
    def _ping_sweep(self) -> Set[str]:
        """Perform ICMP ping sweep of local subnet to find LIVE devices"""
        ips = set()
        try:
            network = ipaddress.IPv4Network(self.local_subnet, strict=False)
            
            # Get all possible hosts in subnet
            hosts = list(network.hosts())[:254]
            
            # Use fping if available (much faster and more accurate)
            try:
                result = subprocess.run(
                    ['fping', '-a', '-g', '-r', '1', self.local_subnet],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                
                if result.returncode == 0 or result.stdout:
                    for line in result.stdout.split('\n'):
                        ip = line.strip()
                        if self._is_valid_ip(ip):
                            ips.add(ip)
                    return ips
            
            except FileNotFoundError:
                pass
            
            # Fallback: parallel ping using subprocess (faster, focused scan)
            import concurrent.futures
            
            def ping_host(ip):
                try:
                    # Use -W 1 for 1 second timeout, -c 1 for single ping
                    result = subprocess.run(
                        ['ping', '-c', '1', '-W', '1', str(ip)],
                        capture_output=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2
                    )
                    if result.returncode == 0:
                        return str(ip)
                except:
                    pass
                return None
            
            # Ping all hosts in parallel (aggressive scan for speed)
            with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                results = executor.map(ping_host, hosts)
                
                for result in results:
                    if result:
                        ips.add(result)
        
        except Exception as e:
            print(f"\nPing sweep error: {e}")
        
        return ips
    
    def _scan_with_nmap(self) -> Set[str]:
        """Use nmap for network scanning if available - only live hosts"""
        ips = set()
        try:
            # Use nmap with ping scan (-sn = no port scan, just host discovery)
            # -T4 = faster timing, --min-rate = minimum packet rate
            result = subprocess.run(
                ['nmap', '-sn', '-T4', '--min-rate', '1000', self.local_subnet, '-oG', '-'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse nmap output for hosts marked as "Up"
                for line in result.stdout.split('\n'):
                    if 'Status: Up' in line:
                        match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', line)
                        if match:
                            ip = match.group()
                            if self._is_valid_ip(ip):
                                ips.add(ip)
        
        except FileNotFoundError:
            # nmap not installed
            pass
        except Exception as e:
            print(f"\nnmap scan error: {e}")
        
        return ips
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Check if IP is valid and not localhost"""
        try:
            addr = ipaddress.IPv4Address(ip)
            # Exclude localhost and multicast
            return not (addr.is_loopback or addr.is_multicast or addr.is_reserved)
        except:
            return False
    
    def _listen_for_requests(self):
        """Listen for node info requests"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.DISCOVERY_PORT))
            sock.settimeout(1.0)
            
            while self.running:
                try:
                    data, addr = sock.recvfrom(4096)
                    message = data.decode('utf-8')
                    
                    if message == "GET_NODE_INFO":
                        # Send our node info
                        self._send_node_info(addr[0])
                    
                    elif message.startswith("NODE_INFO:"):
                        # Received node info
                        node_data = json.loads(message[10:])
                        self._add_discovered_node(node_data)
                
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        pass  # Ignore minor errors
            
            sock.close()
        
        except Exception as e:
            print(f"Listener error: {e}")
    
    def _request_node_info(self, ip: str):
        """Request node info from a specific IP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2)
            sock.sendto(b"GET_NODE_INFO", (ip, self.DISCOVERY_PORT))
            
            # Wait for response
            try:
                data, addr = sock.recvfrom(4096)
                message = data.decode('utf-8')
                
                if message.startswith("NODE_INFO:"):
                    node_data = json.loads(message[10:])
                    self._add_discovered_node(node_data)
            
            except socket.timeout:
                # Node doesn't have our service running - add basic info
                self._add_basic_node(ip)
            
            sock.close()
        
        except Exception:
            pass
    
    def _send_node_info(self, target_ip: str):
        """Send our node info to a specific IP"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            message = f"NODE_INFO:{self.collector.to_json(self.local_node_info)}"
            sock.sendto(message.encode('utf-8'), (target_ip, self.DISCOVERY_PORT))
            sock.close()
        except Exception:
            pass
    
    def _add_basic_node(self, ip: str):
        """Add a node with basic info (when detailed info not available)"""
        if ip in self.discovered_ips:
            return
        
        try:
            # Try to get hostname
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except:
                hostname = f"host-{ip.split('.')[-1]}"
            
            # Get MAC address from ARP
            mac_address = self._get_mac_from_arp(ip)
            
            # Get device manufacturer/name from MAC
            device_name = self._get_device_name(mac_address, hostname)
            
            node_data = {
                'ip_address': ip,
                'hostname': hostname,
                'device_name': device_name,
                'mac_address': mac_address,
                'cpu_cores': None,
                'cpu_freq_mhz': None,
                'cpu_percent': None,
                'ram_total_gb': None,
                'ram_available_gb': None,
                'storage_total_gb': None,
                'storage_available_gb': None,
                'network_bandwidth_mbps': None,
                'os_info': 'Unknown',
                'latency_ms': None,
                'signal_strength': None,
                'open_ports': []
            }
            
            self.discovered_nodes[ip] = node_data
            self.discovered_ips.add(ip)
        
        except Exception:
            pass
    
    def _get_mac_from_arp(self, ip: str) -> str:
        """Get MAC address from ARP table"""
        try:
            # Try reading from /proc/net/arp (Linux)
            with open('/proc/net/arp', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4 and parts[0] == ip:
                        mac = parts[3]
                        if mac != '00:00:00:00:00:00':
                            return mac
        except:
            pass
        
        try:
            # Try arp command
            result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                # Parse MAC address from output
                mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', result.stdout)
                if mac_match:
                    return mac_match.group()
        except:
            pass
        
        return 'Unknown'
    
    def _get_device_name(self, mac: str, hostname: str) -> str:
        """Get device name/manufacturer from MAC address and hostname"""
        # Common MAC OUI (Organizationally Unique Identifier) prefixes
        mac_vendors = {
            '00:1A:11': 'Google',
            '00:1B:63': 'Apple',
            '00:03:93': 'Apple',
            '00:50:E4': 'Apple',
            '00:0D:93': 'Apple',
            'AC:DE:48': 'Apple',
            '3C:06:30': 'Apple',
            '00:1F:5B': 'Apple',
            '00:26:BB': 'Apple',
            '00:0A:95': 'Apple',
            '00:17:F2': 'Apple',
            '00:19:E3': 'Apple',
            '28:CF:DA': 'Apple',
            '28:E7:CF': 'Apple',
            '90:72:40': 'Apple',
            'A4:5E:60': 'Apple',
            '5C:F7:E6': 'Apple',
            '00:1C:B3': 'Apple',
            'D4:90:9C': 'Apple',
            
            '58:FB:84': 'Samsung',
            '00:12:FB': 'Samsung',
            '00:15:B9': 'Samsung',
            'E8:50:8B': 'Samsung',
            '74:45:CE': 'Samsung',
            'A0:82:1F': 'Samsung',
            '00:1D:25': 'Samsung',
            '88:36:5F': 'Samsung',
            
            '10:F9:6F': 'Xiaomi',
            '34:CE:00': 'Xiaomi',
            '64:09:80': 'Xiaomi',
            '74:51:BA': 'Xiaomi',
            '28:6C:07': 'Xiaomi',
            '58:44:98': 'Xiaomi',
            
            '00:9E:C8': 'Realme',
            '8C:C8:4B': 'Realme',
            
            'DC:85:DE': 'Oppo',
            'F8:0F:F9': 'Oppo',
            
            '00:1E:58': 'TP-Link',
            '00:27:19': 'TP-Link',
            '50:C7:BF': 'TP-Link',
            'F4:F2:6D': 'TP-Link',
            'C0:25:E9': 'TP-Link',
            '98:DE:D0': 'TP-Link',
            
            '00:1A:70': 'Netgear',
            '00:14:6C': 'Netgear',
            '00:1B:2F': 'Netgear',
            'E0:91:F5': 'Netgear',
            
            '00:26:5A': 'D-Link',
            '00:05:5D': 'D-Link',
            '00:13:46': 'D-Link',
            '00:1B:11': 'D-Link',
            
            'B8:27:EB': 'Raspberry Pi',
            'DC:A6:32': 'Raspberry Pi',
            'E4:5F:01': 'Raspberry Pi',
        }
        
        # Extract OUI (first 3 octets) from MAC
        if mac and mac != 'Unknown':
            oui = ':'.join(mac.upper().split(':')[:3])
            if oui in mac_vendors:
                vendor = mac_vendors[oui]
                
                # Combine vendor with hostname for better identification
                hostname_lower = hostname.lower()
                
                # Check for specific device types
                if vendor == 'Apple':
                    if 'iphone' in hostname_lower:
                        return 'Apple iPhone'
                    elif 'ipad' in hostname_lower:
                        return 'Apple iPad'
                    elif 'macbook' in hostname_lower:
                        return 'Apple MacBook'
                    elif 'imac' in hostname_lower:
                        return 'Apple iMac'
                    else:
                        return f'{vendor} Device'
                
                elif vendor == 'Samsung':
                    if 'galaxy' in hostname_lower:
                        return 'Samsung Galaxy'
                    else:
                        return f'{vendor} Device'
                
                elif vendor in ['Xiaomi', 'Realme', 'Oppo']:
                    return f'{vendor} Smartphone'
                
                elif vendor in ['TP-Link', 'Netgear', 'D-Link']:
                    return f'{vendor} Router'
                
                elif vendor == 'Raspberry Pi':
                    return 'Raspberry Pi'
                
                else:
                    return f'{vendor} Device'
        
        # Fall back to hostname analysis
        hostname_lower = hostname.lower()
        
        # Mobile brands
        if 'realme' in hostname_lower:
            return 'Realme Smartphone'
        elif 'samsung' in hostname_lower or 'galaxy' in hostname_lower:
            return 'Samsung Device'
        elif 'xiaomi' in hostname_lower or 'redmi' in hostname_lower or 'poco' in hostname_lower:
            return 'Xiaomi Device'
        elif 'oppo' in hostname_lower:
            return 'Oppo Device'
        elif 'vivo' in hostname_lower:
            return 'Vivo Device'
        elif 'oneplus' in hostname_lower:
            return 'OnePlus Device'
        elif 'iphone' in hostname_lower:
            return 'Apple iPhone'
        elif 'ipad' in hostname_lower:
            return 'Apple iPad'
        
        # Computer types
        elif 'kali' in hostname_lower:
            return 'Kali Linux Computer'
        elif 'ubuntu' in hostname_lower:
            return 'Ubuntu Computer'
        elif 'debian' in hostname_lower:
            return 'Debian Computer'
        elif 'windows' in hostname_lower or 'desktop' in hostname_lower:
            return 'Windows Computer'
        
        # Network devices
        elif 'router' in hostname_lower or 'gateway' in hostname_lower:
            return 'WiFi Router/Gateway'
        
        # IoT/Embedded
        elif 'raspberry' in hostname_lower or 'pi' in hostname_lower:
            return 'Raspberry Pi'
        elif 'esp' in hostname_lower:
            return 'ESP Device'
        
        # Generic
        return 'Unknown Device'
    
    def _get_network_details(self, ip: str):
        """Get additional network details for a node"""
        if ip not in self.discovered_nodes:
            return
        
        node = self.discovered_nodes[ip]
        
        # Measure latency (ping response time)
        latency = self._measure_latency(ip)
        if latency:
            node['latency_ms'] = latency
        
        # Get signal strength (if wireless)
        signal = self._get_signal_strength(ip)
        if signal:
            node['signal_strength'] = signal
        
        # Estimate bandwidth
        bandwidth = self._estimate_bandwidth(ip)
        if bandwidth:
            node['network_bandwidth_mbps'] = bandwidth
        
        # Quick port scan for common services
        open_ports = self._quick_port_scan(ip)
        if open_ports:
            node['open_ports'] = open_ports
    
    def _measure_latency(self, ip: str) -> Optional[float]:
        """Measure network latency to the node in milliseconds"""
        try:
            result = subprocess.run(
                ['ping', '-c', '3', '-W', '2', ip],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Extract average latency from ping output
                # Look for "rtt min/avg/max/mdev = X/Y/Z/W ms"
                match = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/', result.stdout)
                if match:
                    return float(match.group(1))
                
                # Alternative: look for "time=X ms" and calculate average
                times = re.findall(r'time=([\d.]+) ms', result.stdout)
                if times:
                    return sum(float(t) for t in times) / len(times)
        except:
            pass
        
        return None
    
    def _get_signal_strength(self, ip: str) -> Optional[str]:
        """Get WiFi signal strength if available"""
        try:
            # Try to get signal strength using iwconfig (Linux wireless)
            result = subprocess.run(
                ['iwconfig'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                # Parse signal level
                match = re.search(r'Signal level[=:](-?\d+)', result.stdout)
                if match:
                    level = int(match.group(1))
                    # Convert to quality description
                    if level >= -50:
                        return "Excellent"
                    elif level >= -60:
                        return "Good"
                    elif level >= -70:
                        return "Fair"
                    else:
                        return "Weak"
        except:
            pass
        
        return None
    
    def _estimate_bandwidth(self, ip: str) -> Optional[float]:
        """Estimate network bandwidth (simplified)"""
        try:
            # Check network interface speed
            result = subprocess.run(
                ['ethtool', 'wlan0'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                match = re.search(r'Speed: (\d+)Mb/s', result.stdout)
                if match:
                    return float(match.group(1))
        except:
            pass
        
        # Default estimate based on network type
        return None
    
    def _quick_port_scan(self, ip: str) -> List[int]:
        """Quick scan of common ports to identify services"""
        common_ports = [22, 80, 443, 5555]  # SSH, HTTP, HTTPS, Our service
        open_ports = []
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except:
                pass
        
        return open_ports
    
    def _add_discovered_node(self, node_data: dict):
        """Add or update a discovered node"""
        ip_address = node_data.get('ip_address')
        
        if not ip_address or ip_address == self.local_node_info.ip_address:
            return
        
        # Check if this is a new node
        is_new = ip_address not in self.discovered_ips
        
        self.discovered_nodes[ip_address] = node_data
        self.discovered_ips.add(ip_address)
        
        if is_new and self.on_node_discovered:
            self.on_node_discovered(node_data)
    
    def get_discovered_nodes(self) -> Dict[str, dict]:
        """Get all discovered nodes"""
        return self.discovered_nodes.copy()
    
    def get_node_count(self) -> int:
        """Get count of discovered nodes"""
    def print_all_nodes(self):
        """Print detailed information about all discovered nodes"""
        print(f"\n{'='*75}")
        print(f"LIVE DEVICES CONNECTED TO WIFI: {len(self.discovered_nodes)}")
        print(f"{'='*75}\n")
        
        if not self.discovered_nodes:
            print("ℹ️  No other live devices found on this network.\n")
            print(f"{'='*75}\n")
            return
        
        # Separate nodes with detailed info and basic info
        detailed_nodes = []
        basic_nodes = []
        
        for ip, node in sorted(self.discovered_nodes.items()):
            if node.get('cpu_cores'):
                detailed_nodes.append((ip, node))
            else:
                basic_nodes.append((ip, node))
        
        # Print detailed nodes first (nodes running our discovery service)
        if detailed_nodes:
            print("🖥️  NODES WITH FULL SYSTEM DETAILS (Running Discovery Service):")
            print("-" * 75)
            for idx, (ip, node) in enumerate(detailed_nodes, 1):
                device_name = node.get('device_name', 'Unknown Device')
                hostname = node.get('hostname')
                
                print(f"\n[{idx}] {device_name}")
                if hostname and hostname != device_name:
                    print(f"    Hostname: {hostname}")
                print(f"    {'─' * 65}")
                print(f"    Network Information:")
                print(f"      IP Address     : {ip}")
                print(f"      MAC Address    : {node.get('mac_address', 'Unknown')}")
                if node.get('latency_ms'):
                    print(f"      Latency        : {node.get('latency_ms'):.2f} ms")
                if node.get('signal_strength'):
                    print(f"      Signal         : {node.get('signal_strength')}")
                if node.get('network_bandwidth_mbps'):
                    print(f"      Bandwidth      : {node.get('network_bandwidth_mbps'):.0f} Mbps")
                
                print(f"\n    System Information:")
                print(f"      OS             : {node.get('os_info')}")
                print(f"      CPU            : {node.get('cpu_cores')} cores @ {node.get('cpu_freq_mhz'):.0f} MHz")
                print(f"      CPU Usage      : {node.get('cpu_percent'):.1f}%")
                print(f"      RAM Total      : {node.get('ram_total_gb'):.2f} GB")
                print(f"      RAM Available  : {node.get('ram_available_gb'):.2f} GB")
                print(f"      RAM Usage      : {((node.get('ram_total_gb', 0) - node.get('ram_available_gb', 0)) / node.get('ram_total_gb', 1) * 100):.1f}%")
                print(f"      Storage Total  : {node.get('storage_total_gb'):.2f} GB")
                print(f"      Storage Avail  : {node.get('storage_available_gb'):.2f} GB")
                
                if node.get('open_ports'):
                    ports_str = ', '.join(str(p) for p in node.get('open_ports', []))
                    print(f"\n    Open Ports       : {ports_str}")
            print()
        
        # Print basic nodes with all available details
        if basic_nodes:
            if detailed_nodes:
                print("\n" + "-" * 75)
            print("📱 DISCOVERED DEVICES (Network Details):")
            print("-" * 75 + "\n")
            
            for idx, (ip, node) in enumerate(basic_nodes, 1):
                device_name = node.get('device_name', 'Unknown Device')
                hostname = node.get('hostname', 'Unknown')
                mac = node.get('mac_address', 'Unknown')
                latency = node.get('latency_ms')
                signal = node.get('signal_strength')
                bandwidth = node.get('network_bandwidth_mbps')
                open_ports = node.get('open_ports', [])
                
                print(f"[{idx}] {device_name}")
                if hostname and hostname != device_name and not hostname.startswith('host-'):
                    print(f"    Hostname: {hostname}")
                print(f"    {'─' * 65}")
                print(f"    IP Address       : {ip}")
                print(f"    MAC Address      : {mac}")
                
                if latency:
                    print(f"    Latency          : {latency:.2f} ms")
                
                if signal:
                    print(f"    Signal Strength  : {signal}")
                
                if bandwidth:
                    print(f"    Est. Bandwidth   : {bandwidth:.0f} Mbps")
                
                if open_ports:
                    ports_str = ', '.join(str(p) for p in open_ports)
                    print(f"    Open Ports       : {ports_str}")
                    
                    # Identify services
                    services = []
                    if 22 in open_ports:
                        services.append("SSH")
                    if 80 in open_ports:
                        services.append("HTTP")
                    if 443 in open_ports:
                        services.append("HTTPS")
                    if 5555 in open_ports:
                        services.append("Discovery Service")
                    
                    if services:
                        print(f"    Services         : {', '.join(services)}")
                
                # Try to guess device type
                device_type = self._guess_device_type(hostname, mac)
                if device_type:
                    print(f"    Device Type      : {device_type}")
                
                print()
        
        print(f"{'='*75}\n")
    
    def _guess_device_type(self, hostname: str, mac: str) -> Optional[str]:
        """Guess device type from hostname and MAC"""
        hostname_lower = hostname.lower()
        
        # Router/Gateway
        if 'gateway' in hostname_lower or 'router' in hostname_lower:
            return "Router/Gateway"
        
        # Mobile devices
        if any(brand in hostname_lower for brand in ['iphone', 'ipad', 'android', 'samsung', 'xiaomi', 'realme', 'oppo', 'vivo', 'oneplus']):
            return "Mobile Device"
        
        # Computers
        if any(term in hostname_lower for term in ['pc', 'desktop', 'laptop', 'kali', 'ubuntu', 'debian']):
            return "Computer"
        
        # IoT devices
        if any(term in hostname_lower for term in ['esp', 'arduino', 'raspberry', 'pi']):
            return "IoT Device"
        
        return None


if __name__ == "__main__":
    # Test the discovery service
    service = DiscoveryService(scan_interval=10)
    
    try:
        service.start()
        print("\nDiscovery service running. Press Ctrl+C to stop.\n")
        
        # Print discovered nodes every 15 seconds
        while True:
            time.sleep(15)
            service.print_all_nodes()
            
    except KeyboardInterrupt:
        print("\n\nStopping discovery service...")
        service.stop()
        print("Goodbye!")
