#!/usr/bin/env python3
"""
Simulated Node - Acts as a computational node for testing
Run multiple instances of this in different terminals to simulate a distributed system
"""

import socket
import json
import threading
import time
import random
import argparse
from dataclasses import asdict
import sys
import os

# Add module1 to path
module1_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'module1_discovery')
if os.path.exists(module1_path):
    sys.path.insert(0, module1_path)

try:
    from node_info import NodeInfoCollector
except ImportError:
    print("Error: Could not import node_info. Make sure module1_discovery exists.")
    sys.exit(1)


class SimulatedNode:
    """Simulates a computational node for testing"""
    
    DISCOVERY_PORT = 5555
    
    def __init__(self, port_offset=0, node_name=None, simulate_load=False):
        self.port_offset = port_offset
        self.port = self.DISCOVERY_PORT + port_offset
        self.node_name = node_name or f"SimNode-{port_offset}"
        self.simulate_load = simulate_load
        
        # Collect actual system info
        self.collector = NodeInfoCollector()
        self.node_info = self.collector.collect_all_info()
        
        # Override hostname for simulation
        self.node_info.hostname = self.node_name
        
        # Simulated performance variations
        self.base_cpu = self.node_info.cpu_percent
        self.base_ram = self.node_info.ram_available_gb
        
        # Threading
        self.running = False
        self.listener_thread = None
        
        # Task execution tracking
        self.tasks_executed = 0
        self.tasks_failed = 0
    
    def start(self):
        """Start the simulated node"""
        self.running = True
        
        # Start listener
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()
        
        print(f"✓ Simulated node '{self.node_name}' started on port {self.port}")
        print(f"  IP: {self.node_info.ip_address}")
        print(f"  CPU: {self.node_info.cpu_cores} cores @ {self.node_info.cpu_freq_mhz:.0f} MHz")
        print(f"  RAM: {self.node_info.ram_total_gb:.2f} GB")
    
    def stop(self):
        """Stop the simulated node"""
        self.running = False
        if self.listener_thread:
            self.listener_thread.join(timeout=2)
        print(f"\n✓ Node '{self.node_name}' stopped")
        print(f"  Tasks executed: {self.tasks_executed}")
        print(f"  Tasks failed: {self.tasks_failed}")
    
    def _listen(self):
        """Listen for discovery requests"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Enable port reuse for multiple nodes on same machine
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass  # SO_REUSEPORT not available on this system
            
            sock.bind(('', self.DISCOVERY_PORT))
            sock.settimeout(1.0)
            
            print(f"  Listening on port {self.DISCOVERY_PORT}...")
            
            while self.running:
                try:
                    data, addr = sock.recvfrom(4096)
                    message = data.decode('utf-8')
                    
                    if message == "GET_NODE_INFO":
                        # Update simulated metrics
                        self._update_metrics()
                        
                        # Send response
                        self._send_node_info(addr[0])
                        
                        print(f"  → Responded to discovery request from {addr[0]}")
                    
                    elif message.startswith("EXECUTE_TASK:"):
                        # Simulate task execution
                        task_data = json.loads(message[13:])
                        self._execute_task(task_data)
                
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        pass  # Ignore minor errors
            
            sock.close()
        
        except Exception as e:
            print(f"  Error in listener: {e}")
    
    def _update_metrics(self):
        """Update simulated performance metrics"""
        if self.simulate_load:
            # Simulate varying CPU usage
            variation = random.uniform(-10, 10)
            self.node_info.cpu_percent = max(0, min(100, self.base_cpu + variation))
            
            # Simulate varying RAM availability
            ram_variation = random.uniform(-0.5, 0.5)
            self.node_info.ram_available_gb = max(0, self.base_ram + ram_variation)
        else:
            # Use actual current metrics
            current_info = self.collector.collect_all_info()
            self.node_info.cpu_percent = current_info.cpu_percent
            self.node_info.ram_available_gb = current_info.ram_available_gb
    
    def _send_node_info(self, target_ip: str):
        """Send node info to requester"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            node_data = asdict(self.node_info)
            message = f"NODE_INFO:{json.dumps(node_data)}"
            
            sock.sendto(message.encode('utf-8'), (target_ip, self.DISCOVERY_PORT))
            sock.close()
        except Exception as e:
            print(f"  Error sending node info: {e}")
    
    def _execute_task(self, task_data):
        """Simulate task execution"""
        task_id = task_data.get('task_id', 'unknown')
        duration = task_data.get('duration', 1.0)
        
        print(f"  ⚙️  Executing task: {task_id} (duration: {duration:.1f}s)")
        
        # Simulate work
        time.sleep(duration)
        
        # Random success/failure (90% success rate)
        if random.random() < 0.9:
            self.tasks_executed += 1
            print(f"  ✓ Task {task_id} completed successfully")
        else:
            self.tasks_failed += 1
            print(f"  ✗ Task {task_id} failed")
    
    def print_status(self):
        """Print current node status"""
        print(f"\n{'='*60}")
        print(f"Node: {self.node_name}")
        print(f"{'='*60}")
        print(f"  IP Address       : {self.node_info.ip_address}")
        print(f"  Port             : {self.port}")
        print(f"  CPU Usage        : {self.node_info.cpu_percent:.1f}%")
        print(f"  RAM Available    : {self.node_info.ram_available_gb:.2f} GB")
        print(f"  Tasks Executed   : {self.tasks_executed}")
        print(f"  Tasks Failed     : {self.tasks_failed}")
        print(f"  Success Rate     : {(self.tasks_executed/(self.tasks_executed+self.tasks_failed)*100) if (self.tasks_executed+self.tasks_failed) > 0 else 0:.1f}%")
        print(f"{'='*60}\n")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Simulated Node for Testing Distributed System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start node 1
  python3 simulated_node.py --name Node1 --offset 0
  
  # Start node 2 (in another terminal)
  python3 simulated_node.py --name Node2 --offset 1
  
  # Start node with simulated varying load
  python3 simulated_node.py --name Worker1 --offset 2 --simulate-load
        """
    )
    
    parser.add_argument(
        '--name',
        type=str,
        default=None,
        help='Node name (default: SimNode-X)'
    )
    
    parser.add_argument(
        '--offset',
        type=int,
        default=0,
        help='Port offset (default: 0). Use different offsets for multiple nodes'
    )
    
    parser.add_argument(
        '--simulate-load',
        action='store_true',
        help='Simulate varying CPU/RAM load'
    )
    
    parser.add_argument(
        '--status-interval',
        type=int,
        default=30,
        help='Status update interval in seconds (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Create and start node
    print("\n" + "="*60)
    print("SIMULATED NODE - Distributed Computing Test")
    print("="*60 + "\n")
    
    node = SimulatedNode(
        port_offset=args.offset,
        node_name=args.name,
        simulate_load=args.simulate_load
    )
    
    try:
        node.start()
        
        print(f"\nNode is running. Press Ctrl+C to stop.")
        print(f"Status updates every {args.status_interval} seconds.\n")
        
        # Periodic status updates
        last_status = time.time()
        
        while True:
            time.sleep(1)
            
            if time.time() - last_status >= args.status_interval:
                node.print_status()
                last_status = time.time()
    
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down node...")
        node.stop()
    
    print("\nGoodbye!\n")


if __name__ == "__main__":
    main()
