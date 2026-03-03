#!/usr/bin/env python3
"""
Module 2: Task Distribution and Load Balancing
Main entry point for the distribution module
"""

import sys
import os
import time
import argparse

# Add module1 to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'module1_discovery'))

from distribution_service import DistributionService
from task_manager import SchedulingPolicy, LoadBalanceStrategy, Task


def display_banner():
    """Display application banner"""
    print("\n" + "="*75)
    print(" WiFi Distributed Computing - Module 2: Task Distribution")
    print("="*75 + "\n")


def interactive_mode(service: DistributionService):
    """Interactive mode for task management"""
    print("\nInteractive Task Distribution Mode")
    print("Commands:")
    print("  create <count> <priority>  - Create tasks")
    print("  distribute                 - Distribute pending tasks")
    print("  status                     - Show system status")
    print("  nodes                      - Show node performance")
    print("  help                       - Show this help")
    print("  quit                       - Exit\n")
    
    pending_tasks = []
    
    while True:
        try:
            cmd = input(">> ").strip().lower().split()
            
            if not cmd:
                continue
            
            if cmd[0] == 'quit' or cmd[0] == 'exit':
                break
            
            elif cmd[0] == 'create':
                count = int(cmd[1]) if len(cmd) > 1 else 1
                priority = int(cmd[2]) if len(cmd) > 2 else 5
                
                for i in range(count):
                    task = service.create_task(
                        f"task_{int(time.time())}_{i}",
                        task_type="compute",
                        priority=priority
                    )
                    pending_tasks.append(task)
                
                print(f"✓ Created {count} tasks (Priority: {priority})")
                print(f"  Total pending: {len(pending_tasks)}")
            
            elif cmd[0] == 'distribute':
                if not pending_tasks:
                    print("⚠️  No pending tasks to distribute")
                    continue
                
                print(f"\nDistributing {len(pending_tasks)} tasks...")
                assignment = service.distribute_tasks(pending_tasks)
                
                if assignment:
                    service.print_task_assignment(assignment)
                    pending_tasks.clear()
                else:
                    print("⚠️  No active nodes available")
            
            elif cmd[0] == 'status':
                service.print_status()
            
            elif cmd[0] == 'nodes':
                print("\n" + "="*75)
                print("NODE PERFORMANCE DETAILS")
                print("="*75 + "\n")
                
                nodes = service.get_all_node_performance()
                
                if not nodes:
                    print("No active nodes found.\n")
                else:
                    for node in nodes:
                        if node:
                            print(f"Node: {node['ip']}")
                            print(f"  Latency Trend    : {node['latency_trend']}")
                            print(f"  Avg Latency      : {node['avg_latency_ms']:.2f} ms")
                            print(f"  CPU Usage        : {node['cpu_usage']:.1f}%")
                            print(f"  RAM Available    : {node['ram_available_gb']:.2f} GB")
                            print(f"  Load Score       : {node['load_score']:.3f}")
                            print(f"  Efficiency       : {node['efficiency']:.2%}")
                            print(f"  Tasks Completed  : {node['tasks_completed']}")
                            print(f"  Tasks Failed     : {node['tasks_failed']}")
                            print()
            
            elif cmd[0] == 'help':
                print("\nCommands:")
                print("  create <count> <priority>  - Create tasks (priority: 1-10)")
                print("  distribute                 - Distribute pending tasks")
                print("  status                     - Show system status")
                print("  nodes                      - Show node performance")
                print("  help                       - Show this help")
                print("  quit                       - Exit")
            
            else:
                print(f"Unknown command: {cmd[0]}. Type 'help' for commands.")
        
        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"Error: {e}")


def demo_mode(service: DistributionService):
    """Demo mode with automatic task distribution"""
    print("Running demonstration mode...\n")
    
    # Wait for node discovery
    print("Discovering nodes...")
    time.sleep(8)
    
    # Show initial status
    service.print_status()
    
    # Create sample tasks
    print("Creating sample tasks...")
    tasks = []
    
    # High priority tasks
    for i in range(3):
        tasks.append(service.create_task(f"critical_task_{i}", priority=1))
    
    # Medium priority tasks
    for i in range(5):
        tasks.append(service.create_task(f"normal_task_{i}", priority=5))
    
    # Low priority tasks
    for i in range(4):
        tasks.append(service.create_task(f"background_task_{i}", priority=8))
    
    print(f"✓ Created {len(tasks)} tasks\n")
    
    # Distribute tasks
    print("Distributing tasks across nodes...\n")
    assignment = service.distribute_tasks(tasks)
    
    if assignment:
        service.print_task_assignment(assignment)
    else:
        print("⚠️  No active nodes available for task distribution\n")
    
    # Show final status
    service.print_status()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Task Distribution and Load Balancing Service',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-p', '--policy',
        choices=['round_robin', 'least_loaded', 'fastest_node', 'priority_based'],
        default='least_loaded',
        help='Scheduling policy (default: least_loaded)'
    )
    
    parser.add_argument(
        '-s', '--strategy',
        choices=['equal', 'weighted', 'latency_aware', 'resource_aware'],
        default='resource_aware',
        help='Load balancing strategy (default: resource_aware)'
    )
    
    parser.add_argument(
        '-m', '--mode',
        choices=['interactive', 'demo', 'status'],
        default='demo',
        help='Operating mode (default: demo)'
    )
    
    parser.add_argument(
        '--no-discovery',
        action='store_true',
        help='Run without node discovery (testing mode)'
    )
    
    args = parser.parse_args()
    
    # Display banner
    display_banner()
    
    # Map string arguments to enums
    policy_map = {
        'round_robin': SchedulingPolicy.ROUND_ROBIN,
        'least_loaded': SchedulingPolicy.LEAST_LOADED,
        'fastest_node': SchedulingPolicy.FASTEST_NODE,
        'priority_based': SchedulingPolicy.PRIORITY_BASED
    }
    
    strategy_map = {
        'equal': LoadBalanceStrategy.EQUAL_DISTRIBUTION,
        'weighted': LoadBalanceStrategy.WEIGHTED_PERFORMANCE,
        'latency_aware': LoadBalanceStrategy.LATENCY_AWARE,
        'resource_aware': LoadBalanceStrategy.RESOURCE_AWARE
    }
    
    # Create service
    print(f"Initializing distribution service...")
    print(f"  Scheduling Policy  : {args.policy}")
    print(f"  Balance Strategy   : {args.strategy}\n")
    
    service = DistributionService(
        scheduling_policy=policy_map[args.policy],
        balance_strategy=strategy_map[args.strategy]
    )
    
    try:
        # Start discovery
        if not args.no_discovery and service.discovery_service:
            service.start_discovery()
        
        # Run selected mode
        if args.mode == 'interactive':
            interactive_mode(service)
        
        elif args.mode == 'demo':
            demo_mode(service)
        
        elif args.mode == 'status':
            time.sleep(5)  # Wait for discovery
            service.print_status()
    
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
    
    finally:
        # Cleanup
        if service.discovery_service:
            service.stop_discovery()
        
        print("✓ Distribution service stopped. Goodbye!\n")


if __name__ == "__main__":
    exit(main() or 0)
