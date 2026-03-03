#!/usr/bin/env python3
"""
Test Runner - Orchestrates testing of the distributed computing system
Runs discovery and distribution with simulated nodes
"""

import subprocess
import time
import sys
import os
import argparse
from typing import List


class TestOrchestrator:
    """Orchestrates testing of the distributed system"""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
    
    def print_banner(self):
        """Print test banner"""
        print("\n" + "="*75)
        print("DISTRIBUTED COMPUTING SYSTEM - INTEGRATED TEST")
        print("="*75 + "\n")
    
    def print_instructions(self):
        """Print testing instructions"""
        print("📋 TEST SETUP INSTRUCTIONS")
        print("="*75)
        print("\nThis test requires multiple terminals. Follow these steps:\n")
        
        print("TERMINAL 1 - Simulated Node 1:")
        print("  cd /home/aromal/Desktop/MAIN_PROJECT_FINAL")
        print("  python3 simulated_node.py --name Worker1 --offset 0\n")
        
        print("TERMINAL 2 - Simulated Node 2:")
        print("  cd /home/aromal/Desktop/MAIN_PROJECT_FINAL")
        print("  python3 simulated_node.py --name Worker2 --offset 1 --simulate-load\n")
        
        print("TERMINAL 3 - Simulated Node 3 (Optional):")
        print("  cd /home/aromal/Desktop/MAIN_PROJECT_FINAL")
        print("  python3 simulated_node.py --name Worker3 --offset 2\n")
        
        print("TERMINAL 4 - Discovery Service:")
        print("  cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module1_discovery")
        print("  python3 main.py\n")
        
        print("TERMINAL 5 - Distribution Service:")
        print("  cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module2_distribution")
        print("  python3 main.py --mode interactive\n")
        
        print("="*75)
        print("\nOnce all terminals are running, use the distribution service")
        print("to create and distribute tasks:\n")
        print("  >> create 10 3     # Create 10 tasks with priority 3")
        print("  >> distribute      # Distribute tasks to nodes")
        print("  >> status          # Show system status")
        print("  >> nodes           # Show node performance")
        print("="*75 + "\n")
    
    def quick_test(self):
        """Run a quick automated test"""
        print("🚀 QUICK TEST MODE")
        print("="*75)
        print("\nThis will test the components individually.\n")
        
        # Test 1: Node Info Collection
        print("Test 1: Node Information Collection")
        print("-" * 75)
        try:
            result = subprocess.run(
                ['python3', os.path.join(self.base_dir, 'module1_discovery/node_info.py')],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("✓ Node info collection: PASSED")
                print(result.stdout[:500] + "...\n" if len(result.stdout) > 500 else result.stdout + "\n")
            else:
                print("✗ Node info collection: FAILED\n")
        except Exception as e:
            print(f"✗ Error: {e}\n")
        
        # Test 2: Task Manager
        print("Test 2: Task Manager and Load Balancing")
        print("-" * 75)
        try:
            result = subprocess.run(
                ['python3', os.path.join(self.base_dir, 'module2_distribution/task_manager.py')],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("✓ Task manager: PASSED")
                print(result.stdout + "\n")
            else:
                print("✗ Task manager: FAILED\n")
        except Exception as e:
            print(f"✗ Error: {e}\n")
        
        print("="*75)
        print("Quick test completed!")
        print("For full system test, run with --mode manual")
        print("="*75 + "\n")
    
    def demo_script(self):
        """Generate a demo shell script"""
        script_path = os.path.join(self.base_dir, 'run_demo.sh')
        
        script_content = """#!/bin/bash
# Distributed Computing System Demo Script
# This script helps you run all components in separate terminal windows

echo "======================================================================="
echo "Distributed Computing System - Multi-Terminal Demo"
echo "======================================================================="
echo ""
echo "This script will open multiple terminal windows."
echo "Press Ctrl+C in each terminal to stop that component."
echo ""

# Function to run command in new terminal
run_in_terminal() {
    local title=$1
    local command=$2
    
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="$title" -- bash -c "$command; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -title "$title" -e "$command; bash" &
    elif command -v konsole &> /dev/null; then
        konsole --title "$title" -e bash -c "$command; exec bash" &
    else
        echo "No suitable terminal emulator found. Please run commands manually."
        echo "$title: $command"
        return 1
    fi
    
    sleep 1
}

cd "$(dirname "$0")"

echo "Starting simulated nodes..."
run_in_terminal "Node 1 - Worker1" "python3 simulated_node.py --name Worker1 --offset 0"
run_in_terminal "Node 2 - Worker2" "python3 simulated_node.py --name Worker2 --offset 1 --simulate-load"
run_in_terminal "Node 3 - Worker3" "python3 simulated_node.py --name Worker3 --offset 2"

echo "Waiting for nodes to initialize..."
sleep 3

echo "Starting discovery service..."
run_in_terminal "Discovery Service" "cd module1_discovery && python3 main.py"

echo "Waiting for discovery to start..."
sleep 3

echo "Starting distribution service..."
run_in_terminal "Distribution Service" "cd module2_distribution && python3 main.py --mode interactive"

echo ""
echo "======================================================================="
echo "All components started!"
echo "======================================================================="
echo ""
echo "Terminals opened:"
echo "  1. Worker1 (Simulated Node)"
echo "  2. Worker2 (Simulated Node with varying load)"
echo "  3. Worker3 (Simulated Node)"
echo "  4. Discovery Service (Finding nodes)"
echo "  5. Distribution Service (Interactive task management)"
echo ""
echo "In the Distribution Service terminal, try these commands:"
echo "  >> create 10 3     # Create 10 tasks"
echo "  >> distribute      # Distribute to nodes"
echo "  >> status          # Show system status"
echo "  >> nodes           # Show node details"
echo ""
"""
        
        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make executable
            os.chmod(script_path, 0o755)
            
            print(f"✓ Demo script created: {script_path}")
            print(f"\nTo run the demo:")
            print(f"  bash {script_path}")
            print(f"\nOr make it executable and run:")
            print(f"  chmod +x {script_path}")
            print(f"  ./{script_path}\n")
            
            return script_path
        
        except Exception as e:
            print(f"✗ Error creating demo script: {e}")
            return None
    
    def cleanup(self):
        """Cleanup running processes"""
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Test Runner for Distributed Computing System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--mode',
        choices=['manual', 'quick', 'script'],
        default='manual',
        help='Test mode: manual (instructions), quick (automated), script (generate demo script)'
    )
    
    args = parser.parse_args()
    
    orchestrator = TestOrchestrator()
    orchestrator.print_banner()
    
    try:
        if args.mode == 'manual':
            orchestrator.print_instructions()
        
        elif args.mode == 'quick':
            orchestrator.quick_test()
        
        elif args.mode == 'script':
            orchestrator.demo_script()
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
    
    finally:
        orchestrator.cleanup()


if __name__ == "__main__":
    main()
