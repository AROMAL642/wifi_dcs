# Module 1: WiFi Node Discovery

## Overview
This module performs automatic discovery of nodes (devices) on the local WiFi network and collects their system information including:
- CPU cores, frequency, and usage
- RAM capacity and availability
- Storage capacity and availability
- Network bandwidth
- IP and MAC addresses
- Operating system information

## Files
1. **node_info.py** - Collects system information from the local node
2. **discovery_service.py** - UDP broadcast-based discovery service
3. **main.py** - Main entry point with CLI interface

## Installation

```bash
# Install required dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
# Start discovery service with default settings
python main.py
```

### Show Local Node Info Only
```bash
# Display information about this node and exit
python main.py --info-only
```

### Custom Broadcast Interval
```bash
# Set broadcast interval to 10 seconds
python main.py -i 10
```

### Quiet Mode
```bash
# Run in quiet mode (minimal output)
python main.py -q
```

## How It Works

1. **Node Information Collection**: The `NodeInfoCollector` class gathers comprehensive system information using the `psutil` library

2. **UDP Broadcasting**: The discovery service broadcasts a discovery message on port 5555 every 5 seconds (configurable)

3. **Discovery Protocol**:
   - Nodes send "DISCOVER_NODE" broadcasts
   - Nodes respond with "NODE_INFO:{json_data}" containing their system information
   - Each node maintains a registry of discovered nodes

4. **Real-time Updates**: Discovered nodes are printed to console with detailed information

## Architecture

```
┌─────────────────┐
│   main.py       │ ← Entry point, CLI interface
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  discovery_service.py   │ ← UDP broadcast discovery
│  - Listener Thread      │
│  - Broadcaster Thread   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────┐
│  node_info.py   │ ← System info collection
└─────────────────┘
```

## Network Requirements

- All nodes must be on the same local network (WiFi/LAN)
- UDP port 5555 must be accessible
- Firewall must allow UDP broadcast traffic

## Example Output

```
Local Node Information:
----------------------------------------------------------------------
Hostname:      node1
IP Address:    192.168.1.100
MAC Address:   aa:bb:cc:dd:ee:ff
OS:            Linux 5.15.0 (x86_64)
CPU:           8 cores @ 2400 MHz (Usage: 15.2%)
RAM:           12.50 GB / 16.00 GB available
Storage:       450.25 GB / 500.00 GB available
Network:       1000 Mbps
----------------------------------------------------------------------

✓ New node discovered: node2 (192.168.1.101)
  CPU: 4 cores @ 2200 MHz
  RAM: 3.75/8.00 GB available
  Storage: 120.50/250.00 GB available
```

## Future Enhancements (Module 2+)
- Task distribution
- Load balancing
- Secure communication
- Performance monitoring
- Fault tolerance
