#!/usr/bin/env python3
"""
Custom Task Registry Storage & Distribution
Persists custom tasks and distributes them to worker nodes
"""

import json
import socket
from pathlib import Path
from typing import Dict, List, Any

REGISTRY_FILE = Path(__file__).parent / "custom_tasks_registry.json"


def save_custom_task(task_name: str, executor_code: str, aggregator_code: str, 
                     description: str = "", parameters: list = None):
    """Save custom task with parameters."""
    registry_file = Path(__file__).parent / "custom_tasks_registry.json"
    
    # Load existing registry
    registry = {}
    if registry_file.exists():
        try:
            with open(registry_file, 'r') as f:
                registry = json.load(f)
        except:
            registry = {}
    
    # Save task with metadata
    registry[task_name] = {
        "executor_code": executor_code,
        "aggregator_code": aggregator_code,
        "description": description,
        "parameters": parameters or []
    }
    
    # Write back to file
    try:
        with open(registry_file, 'w') as f:
            json.dump(registry, f, indent=2)
    except Exception as e:
        print(f"Error saving custom task: {e}")


def load_custom_task(task_name: str) -> Dict[str, str]:
    """Load custom task from shared registry."""
    try:
        registry_file = Path(__file__).parent / "custom_tasks_registry.json"
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                registry = json.load(f)
                if task_name in registry:
                    return registry[task_name]
    except Exception as e:
        print(f"Error loading custom task: {e}")
    
    return {}


def get_all_custom_tasks() -> Dict[str, Dict]:
    """Get all registered custom tasks."""
    try:
        registry_file = Path(__file__).parent / "custom_tasks_registry.json"
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading custom tasks: {e}")
    
    return {}


def delete_custom_task(task_name: str) -> bool:
    """Delete custom task from registry."""
    try:
        registry_file = Path(__file__).parent / "custom_tasks_registry.json"
        
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                registry = json.load(f)
            
            if task_name in registry:
                del registry[task_name]
                with open(registry_file, 'w') as f:
                    json.dump(registry, f, indent=2)
                return True
    except Exception as e:
        print(f"Error deleting custom task: {e}")
    
    return False


def clear_registry() -> bool:
    """Clear all custom tasks from registry."""
    try:
        registry_file = Path(__file__).parent / "custom_tasks_registry.json"
        if registry_file.exists():
            with open(registry_file, 'w') as f:
                json.dump({}, f, indent=2)
            return True
    except Exception as e:
        print(f"Error clearing registry: {e}")
    
    return False


def distribute_task_to_workers(task_name: str, executor_code: str, aggregator_code: str, 
                               description: str, parameters: list, worker_nodes: List[str]) -> Dict[str, bool]:
    """
    Distribute custom task to all worker nodes.
    Works for both local (127.0.0.1) and remote (real IP) workers.
    
    Args:
        task_name: Name of the task
        executor_code: Executor function code
        aggregator_code: Aggregator function code
        description: Task description
        parameters: List of parameters
        worker_nodes: List of worker addresses (ip:port format)
    
    Returns:
        Dict with worker address as key and success status as value
    """
    results = {}
    
    task_data = {
        "type": "register_custom_task",
        "task_name": task_name,
        "executor_code": executor_code,
        "aggregator_code": aggregator_code,
        "description": description,
        "parameters": parameters
    }
    
    for node in worker_nodes:
        try:
            host, port = node.split(":")
            port = int(port)
            
            # Connect to worker and send task configuration
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            
            # Send task registration message
            message = json.dumps(task_data) + "\n"
            sock.sendall(message.encode('utf-8'))
            
            # Receive acknowledgment
            sock.settimeout(2)
            response = sock.recv(1024).decode('utf-8')
            sock.close()
            
            if "success" in response.lower():
                results[node] = True
                print(f"✓ Task '{task_name}' configured on {node}")
            else:
                results[node] = False
                print(f"✗ Failed to configure task '{task_name}' on {node}")
        
        except socket.timeout:
            results[node] = False
            print(f"✗ Timeout connecting to {node}")
        except ConnectionRefusedError:
            results[node] = False
            print(f"✗ Connection refused by {node}")
        except Exception as e:
            results[node] = False
            print(f"✗ Error configuring task on {node}: {str(e)}")
    
    return results


if __name__ == "__main__":
    # Test
    print(f"Registry file location: {REGISTRY_FILE}")
    print("Custom tasks:", get_all_custom_tasks())
