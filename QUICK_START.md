# 🚀 Quick Start Guide

## NEW: Real WiFi Master/Slave Execution (Module 3)

### Run on each worker/slave (real WiFi node)
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 module3_execution/worker.py --name WorkerA --port 6000
```

### Run on the master
Auto-discover workers on the WiFi and distribute a range-sum task:
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 module3_execution/master.py --task range_sum --start 1 --end 100000 --chunk-size 20000
```

Or specify workers manually (ip[:port]):
```bash
python3 module3_execution/master.py --task range_sum --start 1 --end 100000 --chunk-size 20000 --nodes 192.168.1.10:6000,192.168.1.11
```

Progress and final aggregated result will stream in the master terminal.

---

## Problem Fixed: No Active Nodes (Simulated Test Harness)

The system now properly discovers simulated nodes running on localhost!

### ✅ What Was Fixed:

1. **Added localhost scanning** - Discovery service now checks for simulated nodes on the same machine
2. **Enable SO_REUSEPORT** - Multiple simulated nodes can now share port 5555
3. **Fixed all division errors** - Handles None/missing metrics gracefully

---

## 📋 How to Test (5 Terminals Required)

### Terminal 1: Simulated Worker 1
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 simulated_node.py --name Worker1 --offset 0
```

### Terminal 2: Simulated Worker 2
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 simulated_node.py --name Worker2 --offset 1 --simulate-load
```

### Terminal 3: Simulated Worker 3
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 simulated_node.py --name Worker3 --offset 2
```

### Terminal 4: Discovery Service (Module 1)
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module1_discovery
python3 main.py
```

**Wait for the scan to complete - you should see:**
```
📡 Method 0: Checking localhost for simulated nodes... ✓ Found 3 simulated nodes
```

### Terminal 5: Distribution Service (Module 2)
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module2_distribution
python3 main.py --mode interactive
```

**Now run these commands:**
```
>> create 10 3      ← Create 10 tasks with priority 3
>> distribute       ← Distribute to discovered nodes
>> status           ← View system status
>> nodes            ← View node performance
>> quit             ← Exit
```

---

## 🎯 Expected Output

### In Terminal 4 (Discovery):
```
📡 Method 0: Checking localhost for simulated nodes... ✓ Found 3 simulated nodes
📡 Method 1/4: ICMP ping sweep... ✓ Found X live hosts
...
╔════════════════════════════════════════════════════════════════════╗
║                    DISCOVERED NODE #1                              ║
╚════════════════════════════════════════════════════════════════════╝
  IP Address    : 10.253.140.190
  MAC Address   : XX:XX:XX:XX:XX:XX
  Hostname      : SimNode-0 / Worker1
  ...
```

### In Terminal 5 (Distribution):
```
>> distribute
Distributing 10 tasks...
✓ Distributed 10 tasks across 3 nodes

>> status
╔════════════════════════════════════════════════════════════════════╗
║                    DISTRIBUTION SYSTEM STATUS                      ║
╚════════════════════════════════════════════════════════════════════╝
  Strategy      : resource_aware
  Active Nodes  : 3
  Tasks Pending : 0
  ...
```

---

## 🔧 Troubleshooting

### "No active nodes available"
**Solution**: Make sure:
1. All 3 simulated nodes are running (Terminals 1-3)
2. Discovery service is running (Terminal 4)
3. Wait 5-10 seconds for discovery to complete before distributing tasks

### "Address already in use"
**Solution**: 
- Kill existing processes: `pkill -f simulated_node`
- Or use different port offsets

### Simulated nodes don't respond
**Solution**:
- Check SO_REUSEPORT is supported: `python3 -c "import socket; print(hasattr(socket, 'SO_REUSEPORT'))"`
- If False, you can only run 1 simulated node at a time

---

## 📊 Features Working

✅ **Module 1 - Discovery**:
- Multi-method network scanning (ICMP, nmap, arp-scan, ARP)
- Localhost simulated node detection
- Detailed metrics (latency, bandwidth, signal strength, device name)

✅ **Module 2 - Distribution**:
- 4 Scheduling Policies: Round Robin, Least Loaded, Fastest Node, Priority Based
- 4 Load Balance Strategies: Equal, Weighted Performance, Latency Aware, Resource Aware
- Real-time latency monitoring
- Performance tracking and analytics

✅ **Testing Framework**:
- Simulated nodes with realistic behavior
- Multiple nodes on single machine
- Task execution simulation with success/failure rates

---

## 🎉 Next Steps

Once testing is successful, you can:

1. **Add more scheduling policies** - Custom algorithms
2. **Implement actual task execution** - Run real Python code on nodes
3. **Add result aggregation** - Collect and merge results from all nodes
4. **Create monitoring dashboard** - Real-time visualization
5. **Add fault tolerance** - Retry failed tasks, handle node failures
6. **Deploy to real network** - Test with actual distributed devices

---

**Project Status**: ✅ **Core framework complete and tested!**
