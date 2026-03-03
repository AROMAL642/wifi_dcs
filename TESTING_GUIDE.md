# Distributed Computing System - Testing Guide

## Overview
This guide explains how to test the distributed computing system on a single machine using multiple terminal windows, where each terminal represents a simulated node.

## Quick Start

### Option 1: Automated Demo Script (Recommended)
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL

# Generate and run the demo script
python3 test_runner.py --mode script
bash run_demo.sh
```

This will automatically open 5 terminal windows with all components running.

### Option 2: Manual Setup (Full Control)

#### Step 1: Get Instructions
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 test_runner.py --mode manual
```

#### Step 2: Open 5 Terminals

**Terminal 1 - Simulated Node 1 (Worker1):**
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 simulated_node.py --name Worker1 --offset 0
```

**Terminal 2 - Simulated Node 2 (Worker2 with varying load):**
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 simulated_node.py --name Worker2 --offset 1 --simulate-load
```

**Terminal 3 - Simulated Node 3 (Worker3):**
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 simulated_node.py --name Worker3 --offset 2
```

**Terminal 4 - Discovery Service:**
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module1_discovery
python3 main.py
```

**Terminal 5 - Distribution Service (Interactive):**
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module2_distribution
python3 main.py --mode interactive
```

#### Step 3: Use the System

In the Distribution Service terminal (Terminal 5), try these commands:

```bash
# Create 10 tasks with priority 3
>> create 10 3

# Distribute tasks to available nodes
>> distribute

# Show system status
>> status

# Show detailed node performance
>> nodes

# Create more tasks
>> create 5 1

# Distribute again
>> distribute

# Exit
>> quit
```

### Option 3: Quick Component Test
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 test_runner.py --mode quick
```

This runs quick tests on individual components.

## Files Created for Testing

### 1. `simulated_node.py`
Simulates a computational node that:
- Responds to discovery requests
- Provides system information (CPU, RAM, etc.)
- Can simulate varying load
- Tracks task execution

**Usage:**
```bash
# Basic node
python3 simulated_node.py --name MyNode --offset 0

# Node with simulated varying load
python3 simulated_node.py --name BusyNode --offset 1 --simulate-load

# Custom status interval
python3 simulated_node.py --name Worker --offset 2 --status-interval 10
```

### 2. `test_runner.py`
Orchestrates testing with different modes:
- **Manual mode**: Shows instructions for manual setup
- **Quick mode**: Runs automated component tests
- **Script mode**: Generates a bash script for automatic setup

**Usage:**
```bash
# Show manual instructions
python3 test_runner.py --mode manual

# Run quick tests
python3 test_runner.py --mode quick

# Generate demo script
python3 test_runner.py --mode script
```

### 3. `run_demo.sh` (Generated)
Automatically opens all components in separate terminals.

## Testing Scenarios

### Scenario 1: Basic Discovery Test
1. Start 2-3 simulated nodes
2. Start discovery service
3. Watch as nodes are discovered
4. Verify node details are displayed

### Scenario 2: Task Distribution Test
1. Start 3 simulated nodes
2. Start discovery service
3. Start distribution service in interactive mode
4. Create tasks with different priorities
5. Distribute tasks
6. Observe task assignment based on node performance

### Scenario 3: Load Balancing Test
1. Start nodes with varying simulated loads
2. Create multiple batches of tasks
3. Observe how tasks are distributed based on:
   - Node latency
   - CPU usage
   - RAM availability
   - Load score

### Scenario 4: Performance Tracking Test
1. Run system for extended period
2. Create and distribute multiple task batches
3. Check performance analytics:
   - Success rates
   - Execution times
   - Node efficiency scores
   - Best performing nodes

## What Each Component Shows

### Simulated Node Terminal:
```
✓ Simulated node 'Worker1' started on port 5555
  IP: 192.168.1.100
  CPU: 4 cores @ 2400 MHz
  RAM: 8.00 GB
  Listening on port 5555...
  → Responded to discovery request from 192.168.1.50
  ⚙️  Executing task: task_123 (duration: 2.0s)
  ✓ Task task_123 completed successfully
```

### Discovery Service Terminal:
```
📡 Scanning network for live devices...
✓ Found 3 live hosts

DISCOVERED DEVICES:
[1] Worker1 (Kali Linux Computer)
    IP: 192.168.1.100
    Latency: 2.5 ms
    CPU: 4 cores, 25% usage
```

### Distribution Service Terminal:
```
>> create 10 3
✓ Created 10 tasks (Priority: 3)

>> distribute
Distributing 10 tasks...

Node: 192.168.1.100 (4 tasks)
Node: 192.168.1.101 (3 tasks)
Node: 192.168.1.102 (3 tasks)
```

## Expected Behavior

1. **Node Discovery:**
   - Nodes appear within 10-30 seconds
   - Each node shows: hostname, IP, CPU, RAM, latency

2. **Task Distribution:**
   - Tasks distributed based on selected policy
   - Lower latency nodes get more tasks (in latency-aware mode)
   - Less loaded nodes get more tasks (in resource-aware mode)

3. **Performance Tracking:**
   - Real-time latency monitoring
   - Load scores calculated automatically
   - Best nodes identified for task assignment

## Troubleshooting

### Nodes Not Discovered
- Ensure all nodes are running
- Check firewall (UDP port 5555 must be open)
- Verify all terminals are on same network interface

### Tasks Not Distributing
- Ensure discovery service has found nodes
- Wait 10-15 seconds after starting nodes
- Check that nodes are responding (check node terminals)

### Port Already in Use
- Use different port offsets for each node
- Kill existing processes: `pkill -f simulated_node.py`

## Stopping the Test

1. Press `Ctrl+C` in each terminal
2. Or kill all processes:
   ```bash
   pkill -f simulated_node.py
   pkill -f "module1_discovery/main.py"
   pkill -f "module2_distribution/main.py"
   ```

## Advanced Testing

### Custom Scheduling Policies
```bash
# Round-robin scheduling
python3 main.py --mode interactive --policy round_robin

# Fastest node preference
python3 main.py --mode interactive --policy fastest_node

# Priority-based scheduling
python3 main.py --mode interactive --policy priority_based
```

### Custom Load Balancing
```bash
# Equal distribution
python3 main.py --mode interactive --strategy equal

# Weighted by performance
python3 main.py --mode interactive --strategy weighted

# Latency-aware distribution
python3 main.py --mode interactive --strategy latency_aware
```

## System Architecture During Testing

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Terminal 1 │  │  Terminal 2 │  │  Terminal 3 │
│   Worker1   │  │   Worker2   │  │   Worker3   │
│ (Sim Node)  │  │ (Sim Node)  │  │ (Sim Node)  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┴────────────────┘
                        │
                ┌───────▼────────┐
                │   Terminal 4   │
                │   Discovery    │
                │    Service     │
                └───────┬────────┘
                        │
                ┌───────▼────────┐
                │   Terminal 5   │
                │  Distribution  │
                │    Service     │
                │  (Interactive) │
                └────────────────┘
```

Each terminal represents a separate process, simulating a distributed system!
