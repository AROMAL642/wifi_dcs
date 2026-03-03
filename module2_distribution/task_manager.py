"""
Task Manager Module
Handles task scheduling, load balancing, and performance tracking
"""

import time
import threading
import json
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import statistics


class SchedulingPolicy(Enum):
    """Task scheduling policies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    FASTEST_NODE = "fastest_node"
    PRIORITY_BASED = "priority_based"


class LoadBalanceStrategy(Enum):
    """Load balancing strategies"""
    EQUAL_DISTRIBUTION = "equal"
    WEIGHTED_PERFORMANCE = "weighted"
    LATENCY_AWARE = "latency_aware"
    RESOURCE_AWARE = "resource_aware"


@dataclass
class Task:
    """Represents a computational task"""
    task_id: str
    task_type: str
    priority: int = 5  # 1 (highest) to 10 (lowest)
    estimated_duration: float = 0.0  # seconds
    created_at: float = field(default_factory=time.time)
    assigned_node: Optional[str] = None
    status: str = "pending"  # pending, assigned, running, completed, failed
    result: Any = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class NodePerformance:
    """Tracks node performance metrics"""
    node_ip: str
    latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    cpu_usage: float = 0.0
    ram_available_gb: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    last_updated: float = field(default_factory=time.time)
    latency_history: List[float] = field(default_factory=list)
    load_score: float = 0.0  # Lower is better


class LatencyMonitor:
    """Real-time latency monitoring for nodes"""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.latencies: Dict[str, List[float]] = {}
        self.lock = threading.Lock()
    
    def record_latency(self, node_ip: str, latency_ms: float):
        """Record latency measurement for a node"""
        with self.lock:
            if node_ip not in self.latencies:
                self.latencies[node_ip] = []
            
            self.latencies[node_ip].append(latency_ms)
            
            # Keep only recent history
            if len(self.latencies[node_ip]) > self.max_history:
                self.latencies[node_ip].pop(0)
    
    def get_average_latency(self, node_ip: str) -> float:
        """Get average latency for a node"""
        with self.lock:
            if node_ip not in self.latencies or not self.latencies[node_ip]:
                return 0.0
            return statistics.mean(self.latencies[node_ip])
    
    def get_current_latency(self, node_ip: str) -> float:
        """Get most recent latency for a node"""
        with self.lock:
            if node_ip not in self.latencies or not self.latencies[node_ip]:
                return 0.0
            return self.latencies[node_ip][-1]
    
    def get_latency_trend(self, node_ip: str) -> str:
        """Analyze latency trend (improving/degrading/stable)"""
        with self.lock:
            if node_ip not in self.latencies or len(self.latencies[node_ip]) < 10:
                return "insufficient_data"
            
            recent = self.latencies[node_ip][-10:]
            first_half = statistics.mean(recent[:5])
            second_half = statistics.mean(recent[5:])
            
            # Avoid division by zero or None
            if first_half is None or first_half == 0:
                return "insufficient_data"
            
            change = ((second_half - first_half) / first_half) * 100
            
            if change < -10:
                return "improving"
            elif change > 10:
                return "degrading"
            else:
                return "stable"


class PerformanceTracker:
    """Track and analyze historical performance data"""
    
    def __init__(self):
        self.node_metrics: Dict[str, NodePerformance] = {}
        self.task_history: List[Task] = []
        self.lock = threading.Lock()
    
    def update_node_metrics(self, node_ip: str, **kwargs):
        """Update performance metrics for a node"""
        with self.lock:
            if node_ip not in self.node_metrics:
                self.node_metrics[node_ip] = NodePerformance(node_ip=node_ip)
            
            node = self.node_metrics[node_ip]
            
            for key, value in kwargs.items():
                if hasattr(node, key) and value is not None:
                    setattr(node, key, value)
            
            node.last_updated = time.time()
            
            # Calculate load score
            node.load_score = self._calculate_load_score(node)
    
    def _calculate_load_score(self, node: NodePerformance) -> float:
        """Calculate overall load score (lower is better)"""
        # Normalize metrics to 0-1 scale, handle None values
        avg_latency = node.avg_latency_ms if node.avg_latency_ms is not None else 0.0
        cpu_usage = node.cpu_usage if node.cpu_usage is not None else 0.0
        ram_available = node.ram_available_gb if node.ram_available_gb is not None else 8.0
        
        latency_score = min(avg_latency / 100, 1.0)  # Normalize to 100ms
        cpu_score = cpu_usage / 100.0
        ram_score = 1.0 - min(ram_available / 8.0, 1.0)  # Inverse: more available = lower score
        
        # Weighted combination
        load_score = (latency_score * 0.3 + cpu_score * 0.4 + ram_score * 0.3)
        
        return load_score
    
    def record_task_completion(self, task: Task):
        """Record completed task for analytics"""
        with self.lock:
            self.task_history.append(task)
            
            # Update node metrics
            if task.assigned_node and task.assigned_node in self.node_metrics:
                node = self.node_metrics[task.assigned_node]
                
                if task.status == "completed":
                    node.tasks_completed += 1
                    if task.start_time and task.end_time:
                        execution_time = task.end_time - task.start_time
                        node.total_execution_time += execution_time
                elif task.status == "failed":
                    node.tasks_failed += 1
    
    def get_best_nodes(self, count: int = 3) -> List[str]:
        """Get top performing nodes"""
        with self.lock:
            sorted_nodes = sorted(
                self.node_metrics.items(),
                key=lambda x: x[1].load_score
            )
            return [ip for ip, _ in sorted_nodes[:count]]
    
    def get_node_efficiency(self, node_ip: str) -> float:
        """Calculate node efficiency (0-1 scale)"""
        with self.lock:
            if node_ip not in self.node_metrics:
                return 0.0
            
            node = self.node_metrics[node_ip]
            
            # Handle None values
            tasks_completed = node.tasks_completed if node.tasks_completed is not None else 0
            tasks_failed = node.tasks_failed if node.tasks_failed is not None else 0
            total_execution_time = node.total_execution_time if node.total_execution_time is not None else 0.0
            
            total_tasks = tasks_completed + tasks_failed
            
            if total_tasks == 0:
                # No task history - return neutral efficiency
                return 0.5
            
            success_rate = tasks_completed / total_tasks
            
            # Consider speed and reliability
            avg_task_time = (total_execution_time / tasks_completed 
                           if tasks_completed > 0 else float('inf'))
            
            # Efficiency based on success rate and speed (inverse of time)
            if avg_task_time == float('inf'):
                efficiency = success_rate * 0.5  # No completed tasks yet
            else:
                efficiency = success_rate * min(1.0, 10.0 / avg_task_time)
            
            return min(efficiency, 1.0)
    
    def get_analytics_summary(self) -> Dict:
        """Get comprehensive analytics summary"""
        with self.lock:
            total_tasks = len(self.task_history)
            completed = sum(1 for t in self.task_history if t.status == "completed")
            failed = sum(1 for t in self.task_history if t.status == "failed")
            
            avg_execution_time = 0.0
            if completed > 0:
                execution_times = [
                    t.end_time - t.start_time 
                    for t in self.task_history 
                    if t.status == "completed" and t.start_time and t.end_time
                ]
                if execution_times:
                    avg_execution_time = statistics.mean(execution_times)
            
            return {
                'total_tasks': total_tasks,
                'completed': completed,
                'failed': failed,
                'success_rate': (completed / total_tasks * 100) if total_tasks > 0 else 0.0,
                'avg_execution_time': avg_execution_time,
                'active_nodes': len(self.node_metrics),
                'best_node': self.get_best_nodes(1)[0] if self.node_metrics else None
            }


class TaskScheduler:
    """Intelligent task scheduler with multiple policies"""
    
    def __init__(self, policy: SchedulingPolicy = SchedulingPolicy.LEAST_LOADED):
        self.policy = policy
        self.task_queue: List[Task] = []
        self.assigned_tasks: Dict[str, List[Task]] = {}
        self.lock = threading.Lock()
        self.round_robin_index = 0
    
    def add_task(self, task: Task):
        """Add task to queue"""
        with self.lock:
            self.task_queue.append(task)
            
            # Sort by priority if using priority-based scheduling
            if self.policy == SchedulingPolicy.PRIORITY_BASED:
                self.task_queue.sort(key=lambda t: t.priority)
    
    def assign_task(self, available_nodes: Dict[str, NodePerformance]) -> Optional[tuple]:
        """Assign next task to best node based on policy"""
        with self.lock:
            if not self.task_queue or not available_nodes:
                return None
            
            task = self.task_queue[0]
            node_ip = self._select_node(available_nodes)
            
            if node_ip:
                self.task_queue.pop(0)
                task.assigned_node = node_ip
                task.status = "assigned"
                
                if node_ip not in self.assigned_tasks:
                    self.assigned_tasks[node_ip] = []
                self.assigned_tasks[node_ip].append(task)
                
                return (task, node_ip)
            
            return None
    
    def _select_node(self, nodes: Dict[str, NodePerformance]) -> Optional[str]:
        """Select node based on scheduling policy"""
        if not nodes:
            return None
        
        node_list = list(nodes.keys())
        
        if self.policy == SchedulingPolicy.ROUND_ROBIN:
            # Round-robin selection
            selected = node_list[self.round_robin_index % len(node_list)]
            self.round_robin_index += 1
            return selected
        
        elif self.policy == SchedulingPolicy.LEAST_LOADED:
            # Select node with lowest load score
            return min(nodes.items(), key=lambda x: x[1].load_score)[0]
        
        elif self.policy == SchedulingPolicy.FASTEST_NODE:
            # Select node with lowest average latency
            return min(nodes.items(), key=lambda x: x[1].avg_latency_ms)[0]
        
        elif self.policy == SchedulingPolicy.PRIORITY_BASED:
            # High priority tasks to best nodes, low priority to any available
            if self.task_queue:
                task = self.task_queue[0]
                if task.priority <= 3:  # High priority
                    return min(nodes.items(), key=lambda x: x[1].load_score)[0]
                else:  # Low priority
                    return node_list[self.round_robin_index % len(node_list)]
        
        return node_list[0]
    
    def get_queue_size(self) -> int:
        """Get number of pending tasks"""
        with self.lock:
            return len(self.task_queue)


class LoadBalancer:
    """Dynamic load balancing with multiple strategies"""
    
    def __init__(self, strategy: LoadBalanceStrategy = LoadBalanceStrategy.RESOURCE_AWARE):
        self.strategy = strategy
        self.latency_monitor = LatencyMonitor()
        self.performance_tracker = PerformanceTracker()
        self.scheduler = TaskScheduler()
    
    def update_node_info(self, node_ip: str, node_data: Dict):
        """Update node information from discovery"""
        # Update latency
        if 'latency_ms' in node_data:
            self.latency_monitor.record_latency(node_ip, node_data['latency_ms'])
        
        # Update performance metrics
        metrics = {
            'latency_ms': node_data.get('latency_ms', 0.0),
            'avg_latency_ms': self.latency_monitor.get_average_latency(node_ip),
            'cpu_usage': node_data.get('cpu_percent', 0.0),
            'ram_available_gb': node_data.get('ram_available_gb', 0.0)
        }
        
        self.performance_tracker.update_node_metrics(node_ip, **metrics)
    
    def balance_load(self, tasks: List[Task], nodes: List[Dict]) -> Dict[str, List[Task]]:
        """Balance tasks across nodes based on strategy"""
        # Update all node info
        for node in nodes:
            self.update_node_info(node['ip_address'], node)
        
        # Get node performance data
        node_metrics = self.performance_tracker.node_metrics
        
        assignment = {}
        
        if self.strategy == LoadBalanceStrategy.EQUAL_DISTRIBUTION:
            # Distribute tasks equally
            for i, task in enumerate(tasks):
                node_ip = nodes[i % len(nodes)]['ip_address']
                if node_ip not in assignment:
                    assignment[node_ip] = []
                assignment[node_ip].append(task)
        
        elif self.strategy == LoadBalanceStrategy.WEIGHTED_PERFORMANCE:
            # Distribute based on node efficiency
            efficiencies = {
                node['ip_address']: self.performance_tracker.get_node_efficiency(node['ip_address'])
                for node in nodes
            }
            
            # Assign more tasks to efficient nodes
            for task in tasks:
                best_node = max(efficiencies.items(), key=lambda x: x[1])[0]
                if best_node not in assignment:
                    assignment[best_node] = []
                assignment[best_node].append(task)
        
        elif self.strategy == LoadBalanceStrategy.LATENCY_AWARE:
            # Prefer nodes with low latency
            for task in tasks:
                best_node = min(
                    nodes,
                    key=lambda n: self.latency_monitor.get_average_latency(n['ip_address'])
                )
                node_ip = best_node['ip_address']
                if node_ip not in assignment:
                    assignment[node_ip] = []
                assignment[node_ip].append(task)
        
        elif self.strategy == LoadBalanceStrategy.RESOURCE_AWARE:
            # Use scheduler with load-based selection
            for task in tasks:
                result = self.scheduler.assign_task(node_metrics)
                if result:
                    task_obj, node_ip = result
                    if node_ip not in assignment:
                        assignment[node_ip] = []
                    assignment[node_ip].append(task_obj)
        
        return assignment
    
    def get_status(self) -> Dict:
        """Get current load balancer status"""
        return {
            'strategy': self.strategy.value,
            'queue_size': self.scheduler.get_queue_size(),
            'active_nodes': len(self.performance_tracker.node_metrics),
            'analytics': self.performance_tracker.get_analytics_summary()
        }


if __name__ == "__main__":
    # Test the task manager
    print("="*70)
    print("Task Manager Test")
    print("="*70)
    
    # Create load balancer
    lb = LoadBalancer(strategy=LoadBalanceStrategy.RESOURCE_AWARE)
    
    # Simulate nodes
    nodes = [
        {'ip_address': '192.168.1.10', 'latency_ms': 5.0, 'cpu_percent': 30.0, 'ram_available_gb': 4.0},
        {'ip_address': '192.168.1.11', 'latency_ms': 15.0, 'cpu_percent': 60.0, 'ram_available_gb': 2.0},
        {'ip_address': '192.168.1.12', 'latency_ms': 8.0, 'cpu_percent': 20.0, 'ram_available_gb': 6.0}
    ]
    
    # Update node info
    for node in nodes:
        lb.update_node_info(node['ip_address'], node)
    
    # Create tasks
    tasks = [
        Task(task_id=f"task_{i}", task_type="compute", priority=i%3+1)
        for i in range(10)
    ]
    
    # Balance load
    assignment = lb.balance_load(tasks, nodes)
    
    print("\nTask Assignment:")
    for node_ip, node_tasks in assignment.items():
        print(f"\n  Node {node_ip}: {len(node_tasks)} tasks")
        for task in node_tasks:
            print(f"    - {task.task_id} (Priority: {task.priority})")
    
    print("\n" + "="*70)
    print("Load Balancer Status:")
    print("="*70)
    status = lb.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    print()
