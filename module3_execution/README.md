# Module 3: Distributed Task Execution (Master/Slave)

This module adds **real task execution** on WiFi-connected nodes with a **master/slave** model.

- **Master**: discovers workers, splits tasks, sends chunks, tracks progress, aggregates results.
- **Slave (worker)**: advertises itself via UDP discovery, executes tasks over TCP, reports progress/result.

## Components
- `worker.py` — run on each worker/slave node (UDP discovery + TCP task server)
- `master.py` — run on the master to distribute tasks
- `tasks.py` — example tasks, splitters, aggregators (currently `range_sum`)

## Protocol
- **Discovery (UDP 5555)**: Master (via `DiscoveryService`) sends `GET_NODE_INFO`; worker responds `NODE_INFO:{...}` including `worker_port` and capabilities.
- **Task channel (TCP, default 6000)**: Master sends `{type:"task", task_id, task_name, payload}`. Worker replies on same socket with:
  - `{type:"ack"}` → `{type:"progress"}` → `{type:"result"}` (status `completed`/`failed`).

## Quick Start (Terminal friendly)

### On each worker node (slave)
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 module3_execution/worker.py --name WorkerA --port 6000
```
Run on every WiFi-connected node (different IPs). Keep them running.

### On master node
Auto-discover workers and run a distributed range sum:
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 module3_execution/master.py --task range_sum --start 1 --end 100000 --chunk-size 20000
```

Or specify workers manually (IP:port):
```bash
python3 module3_execution/master.py --task range_sum --start 1 --end 100000 --chunk-size 20000 --nodes 192.168.1.10:6000,192.168.1.11
```

Expected final output (example):
```
🎉 FINAL RESULT
{
  "task": "range_sum",
  "total_sum": 5000050000,
  "total_numbers": 100000,
  "ranges": [[1,20000],[20001,40000],...]
}
```

## Notes
- Uses only standard library + existing `psutil` from Module 1.
- Progress is streamed back in real time over the task socket.
- Works with real WiFi nodes; discovery uses ICMP/arp/nmap plus UDP reply.

## Next Ideas
- Add more tasks (word count, file hashing)
- Retry/timeout logic per task
- Persistent result storage
