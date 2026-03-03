"""
Distribution Service
Integrates with Module 1 discovery and handles task distribution
"""

import sys
import os
import time
import json
from typing import List, Dict, Optional

# Add module1 to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'module1_discovery'))

from task_manager import (
    LoadBalancer, Task, SchedulingPolicy, LoadBalanceStrategy,
    LatencyMonitor, PerformanceTracker
)

try:
    from discovery_service import DiscoveryService
    from node_info import NodeInfoCollector
except ImportError:
    print("Warning: Module 1 not found. Running in standalone mode.")
    DiscoveryService = None
    NodeInfoCollector = None


class DistributionService:
    """
    Main distribution service that combines discovery and task management
    """
    
    def __init__(
        self,
        scheduling_policy: SchedulingPolicy = SchedulingPolicy.LEAST_LOADED,
        balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy.RESOURCE_AWARE
    ):
        self.scheduling_policy = scheduling_policy
        self.balance_strategy = balance_strategy
        
        # Initialize components
        self.load_balancer = LoadBalancer(strategy=balance_strategy)
        self.latency_monitor = LatencyMonitor()
        self.performance_tracker = PerformanceTracker()
        
        # Discovery service
        self.discovery_service = None
        if DiscoveryService:
            self.discovery_service = DiscoveryService(scan_interval=30)
        
        # Active nodes
        self.active_nodes: Dict[str, Dict] = {}
        
        # Statistics
        self.total_tasks_distributed = 0
        self.start_time = time.time()
    
    def start_discovery(self):
        """Start node discovery service"""
        if self.discovery_service:
            self.discovery_service.start()
            print("✓ Discovery service started")
            
            # Wait for initial scan
            time.sleep(3)
            
            # Get discovered nodes
            self._update_active_nodes()
    
    def stop_discovery(self):
        """Stop discovery service"""
        if self.discovery_service:
            self.discovery_service.stop()
            print("✓ Discovery service stopped")
    
    def _update_active_nodes(self):
        """Update active nodes from discovery"""
        if self.discovery_service:
            discovered = self.discovery_service.get_discovered_nodes()
            
            # Update active nodes and their metrics
            for ip, node_data in discovered.items():
                self.active_nodes[ip] = node_data
                
                # Update load balancer with node info
                self.load_balancer.update_node_info(ip, node_data)
                
                # Record latency
                if node_data.get('latency_ms'):
                    self.latency_monitor.record_latency(ip, node_data['latency_ms'])
    
    def create_task(self, task_id: str, task_type: str = "compute", priority: int = 5) -> Task:
        """Create a new task"""
        return Task(
            task_id=task_id,
            task_type=task_type,
            priority=priority
        )
    
    def distribute_tasks(self, tasks: List[Task]) -> Dict[str, List[Task]]:
        """Distribute tasks across available nodes"""
        # Update node information
        self._update_active_nodes()
        
        if not self.active_nodes:
            print("⚠️  No active nodes available for task distribution")
            return {}
        
        # Convert nodes to list format
        nodes = [
            {**node_data, 'ip_address': ip}
            for ip, node_data in self.active_nodes.items()
        ]
        
        # Balance load
        assignment = self.load_balancer.balance_load(tasks, nodes)
        
        self.total_tasks_distributed += len(tasks)
        
        return assignment
    
    def get_node_performance(self, node_ip: str) -> Optional[Dict]:
        """Get performance metrics for a specific node"""
        if node_ip in self.performance_tracker.node_metrics:
            node_perf = self.performance_tracker.node_metrics[node_ip]
            
            return {
                'ip': node_perf.node_ip,
                'avg_latency_ms': node_perf.avg_latency_ms,
                'latency_trend': self.latency_monitor.get_latency_trend(node_ip),
                'cpu_usage': node_perf.cpu_usage,
                'ram_available_gb': node_perf.ram_available_gb,
                'tasks_completed': node_perf.tasks_completed,
                'tasks_failed': node_perf.tasks_failed,
                'load_score': node_perf.load_score,
                'efficiency': self.performance_tracker.get_node_efficiency(node_ip)
            }
        
        return None
    
    def get_all_node_performance(self) -> List[Dict]:
        """Get performance metrics for all nodes"""
        return [
            self.get_node_performance(ip)
            for ip in self.active_nodes.keys()
        ]
    
    def get_system_status(self) -> Dict:
        """Get overall system status"""
        analytics = self.performance_tracker.get_analytics_summary()
        
        uptime = time.time() - self.start_time
        
        return {
            'uptime_seconds': uptime,
            'active_nodes': len(self.active_nodes),
            'scheduling_policy': self.scheduling_policy.value,
            'balance_strategy': self.balance_strategy.value,
            'total_tasks_distributed': self.total_tasks_distributed,
            'analytics': analytics,
            'best_nodes': self.performance_tracker.get_best_nodes(3)
        }
    
    def print_status(self):
        """Print formatted status information"""
        status = self.get_system_status()
        
        print("\n" + "="*75)
        print("DISTRIBUTION SYSTEM STATUS")
        print("="*75)
        
        print(f"\nSystem Configuration:")
        print(f"  Uptime              : {status['uptime_seconds']:.0f} seconds")
        print(f"  Scheduling Policy   : {status['scheduling_policy']}")
        print(f"  Balance Strategy    : {status['balance_strategy']}")
        
        print(f"\nActive Nodes         : {status['active_nodes']}")
        
        if status['active_nodes'] > 0:
            print(f"\nNode Performance:")
            for node_data in self.get_all_node_performance():
                if node_data:
                    print(f"\n  Node: {node_data['ip']}")
                    print(f"    Latency         : {node_data['avg_latency_ms']:.2f} ms ({node_data['latency_trend']})")
                    print(f"    CPU Usage       : {node_data['cpu_usage']:.1f}%")
                    print(f"    RAM Available   : {node_data['ram_available_gb']:.2f} GB")
                    print(f"    Load Score      : {node_data['load_score']:.3f}")
                    print(f"    Efficiency      : {node_data['efficiency']:.2%}")
                    print(f"    Tasks Completed : {node_data['tasks_completed']}")
                    print(f"    Tasks Failed    : {node_data['tasks_failed']}")
        
        print(f"\nTask Statistics:")
        print(f"  Total Distributed   : {status['total_tasks_distributed']}")
        if status['analytics']:
            print(f"  Completed           : {status['analytics']['completed']}")
            print(f"  Failed              : {status['analytics']['failed']}")
            print(f"  Success Rate        : {status['analytics']['success_rate']:.1f}%")
            if status['analytics']['avg_execution_time'] > 0:
                print(f"  Avg Execution Time  : {status['analytics']['avg_execution_time']:.2f} seconds")
        
        if status['best_nodes']:
            print(f"\nBest Performing Nodes:")
            for i, node_ip in enumerate(status['best_nodes'], 1):
                print(f"  {i}. {node_ip}")
        
        print("\n" + "="*75 + "\n")
    
    def print_task_assignment(self, assignment: Dict[str, List[Task]]):
        """Print task assignment details"""
        print("\n" + "="*75)
        print("TASK ASSIGNMENT")
        print("="*75)
        
        total_tasks = sum(len(tasks) for tasks in assignment.values())
        print(f"\nTotal Tasks: {total_tasks}")
        print(f"Distributed Across: {len(assignment)} nodes\n")
        
        for node_ip, tasks in sorted(assignment.items()):
            node_perf = self.get_node_performance(node_ip)
            
            print(f"Node: {node_ip}")
            if node_perf:
                print(f"  Latency: {node_perf['avg_latency_ms']:.2f} ms | "
                      f"Load: {node_perf['load_score']:.3f} | "
                      f"Tasks: {len(tasks)}")
            
            for task in tasks:
                print(f"    - {task.task_id} (Priority: {task.priority}, Type: {task.task_type})")
            print()
        
        print("="*75 + "\n")


if __name__ == "__main__":
    # Test distribution service
    print("="*75)
    print("Distribution Service Test")
    print("="*75)
    
    # Create service
    service = DistributionService(
        scheduling_policy=SchedulingPolicy.LEAST_LOADED,
        balance_strategy=LoadBalanceStrategy.RESOURCE_AWARE
    )
    
    # Start discovery (if available)
    if service.discovery_service:
        print("\nStarting node discovery...")
        service.start_discovery()
        time.sleep(5)
    else:
        print("\nRunning in standalone mode (no discovery)")
        # Add mock nodes for testing
        service.active_nodes = {
            '192.168.1.10': {'latency_ms': 5.0, 'cpu_percent': 30.0, 'ram_available_gb': 4.0},
            '192.168.1.11': {'latency_ms': 15.0, 'cpu_percent': 60.0, 'ram_available_gb': 2.0}
        }
    
    # Create and distribute tasks
    print("\nCreating tasks...")
    tasks = [
        service.create_task(f"compute_task_{i}", task_type="compute", priority=(i % 3) + 1)
        for i in range(10)
    ]
    
    print(f"Distributing {len(tasks)} tasks...\n")
    assignment = service.distribute_tasks(tasks)
    
    # Display results
    service.print_task_assignment(assignment)
    service.print_status()
    
    # Cleanup
    if service.discovery_service:
        service.stop_discovery()
    
    print("Test completed successfully!")
