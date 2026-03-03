# Module 2: Task Distribution and Load Balancing

## Overview
This module provides intelligent task distribution and load balancing across discovered nodes. It integrates with Module 1 (Node Discovery) to automatically distribute computational tasks based on real-time node performance.

## Features

### 1. **Latency Monitor** - Real-time Measurement
- Continuous latency tracking for all nodes
- Historical latency data (configurable history size)
- Trend analysis (improving/degrading/stable)
- Average and current latency metrics

### 2. **Task Scheduler** - Multiple Scheduling Policies
- **Round Robin**: Equal rotation across nodes
- **Least Loaded**: Assigns to node with lowest load score
- **Fastest Node**: Prioritizes nodes with lowest latency
- **Priority Based**: High-priority tasks to best nodes

### 3. **Load Balancer** - Dynamic Balancing Strategies
- **Equal Distribution**: Tasks distributed equally
- **Weighted Performance**: More tasks to efficient nodes
- **Latency Aware**: Prefers low-latency nodes
- **Resource Aware**: Considers CPU, RAM, and latency

### 4. **Performance Tracker** - Historical Analytics
- Task completion tracking
- Success/failure rates
- Execution time analytics
- Node efficiency scoring
- Load score calculation
- Best node identification

## Files
1. **task_manager.py** - Core task management, scheduling, and performance tracking
2. **distribution_service.py** - Service integration with node discovery
3. **main.py** - Main entry point with CLI interface

## Installation

```bash
# Module 2 uses the same dependencies as Module 1
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module2_distribution
```

## Usage

### Demo Mode (Recommended for First Run)
```bash
python3 main.py --mode demo
```

### Interactive Mode
```bash
python3 main.py --mode interactive
```

Interactive commands:
- `create 5 1` - Create 5 tasks with priority 1 (high)
- `distribute` - Distribute pending tasks
- `status` - Show system status
- `nodes` - Show node performance details
- `quit` - Exit

### Custom Configuration
```bash
# Use round-robin scheduling with latency-aware balancing
python3 main.py --policy round_robin --strategy latency_aware

# Use priority-based scheduling with weighted performance
python3 main.py --policy priority_based --strategy weighted
```

### Available Options

**Scheduling Policies** (`--policy`):
- `round_robin` - Rotate through nodes equally
- `least_loaded` - Choose least loaded node (default)
- `fastest_node` - Choose node with lowest latency
- `priority_based` - Match task priority to node quality

**Load Balancing Strategies** (`--strategy`):
- `equal` - Equal distribution
- `weighted` - Performance-weighted distribution
- `latency_aware` - Latency-based distribution
- `resource_aware` - CPU/RAM/latency-based (default)

**Operating Modes** (`--mode`):
- `demo` - Automatic demonstration (default)
- `interactive` - Manual task management
- `status` - Show status and exit

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       main.py                               │
│                   (CLI Interface)                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              distribution_service.py                        │
│          (Service Orchestration)                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  - Integrates with Module 1 Discovery               │   │
│  │  - Updates node performance metrics                 │   │
│  │  - Manages task distribution                        │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  task_manager.py                            │
│              (Core Components)                              │
│                                                             │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │  LatencyMonitor    │  │  TaskScheduler     │            │
│  │  - Track latency   │  │  - Queue tasks     │            │
│  │  - Trend analysis  │  │  - Select nodes    │            │
│  └────────────────────┘  └────────────────────┘            │
│                                                             │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │  LoadBalancer      │  │ PerformanceTracker │            │
│  │  - Balance tasks   │  │  - Track metrics   │            │
│  │  - Apply strategy  │  │  - Analytics       │            │
│  └────────────────────┘  └────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## Key Metrics

### Load Score Calculation
```
Load Score = (Latency × 0.3) + (CPU Usage × 0.4) + (RAM Usage × 0.3)
```
Lower is better. Used for node selection.

### Node Efficiency
```
Efficiency = Success Rate × min(1.0, 10.0 / Avg Task Time)
```
Higher is better. Range: 0.0 to 1.0

## Example Output

```
======================================================================
DISTRIBUTION SYSTEM STATUS
======================================================================

System Configuration:
  Uptime              : 125 seconds
  Scheduling Policy   : least_loaded
  Balance Strategy    : resource_aware

Active Nodes         : 2

Node Performance:

  Node: 192.168.43.1
    Latency         : 3.27 ms (stable)
    CPU Usage       : 0.0%
    RAM Available   : 0.00 GB
    Load Score      : 0.010
    Efficiency      : 0.00%
    Tasks Completed : 0
    Tasks Failed    : 0

Task Statistics:
  Total Distributed   : 12
  Completed           : 0
  Failed              : 0

Best Performing Nodes:
  1. 192.168.43.1
  2. 192.168.43.208
```

## Integration with Module 1

Module 2 automatically integrates with Module 1 for node discovery:
- Imports discovery service from `module1_discovery`
- Receives real-time node information
- Updates performance metrics continuously
- Uses discovered nodes for task distribution

## Testing Without Discovery

```bash
# Run in standalone mode (no discovery)
python3 main.py --no-discovery --mode interactive
```

## Performance Optimization

- **Latency history size**: Default 100 measurements (configurable)
- **Discovery interval**: 30 seconds (inherited from Module 1)
- **Task queue**: Thread-safe with automatic priority sorting
- **Metrics update**: Real-time as tasks complete

## Future Enhancements (Module 3+)
- Actual task execution on remote nodes
- Result aggregation
- Fault tolerance and retry logic
- Task dependencies and workflows
- Real-time monitoring dashboard
