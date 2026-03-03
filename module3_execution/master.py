#!/usr/bin/env python3
"""
Master node orchestrator.
- Discovers workers on the same WiFi network (using module1 discovery)
- Assigns tasks to workers over TCP, collects progress and results
- Aggregates partial results into a final answer
"""

import argparse
import json
import socket
import threading
import time
from typing import Dict, List, Tuple
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Add module1_discovery to path for DiscoveryService imports when run from repo root
DISCOVERY_DIR = os.path.join(BASE_DIR, "module1_discovery")
if DISCOVERY_DIR not in sys.path:
    sys.path.insert(0, DISCOVERY_DIR)

try:
    from module1_discovery.discovery_service import DiscoveryService
except Exception:
    from discovery_service import DiscoveryService

from module3_execution.tasks import (
    generate_range_sum_tasks,
    aggregate_range_sum,
    generate_array_sum_tasks,
    aggregate_array_sum,
    SUPPORTED_TASKS,
)

DEFAULT_WORKER_PORT = 6000


class MasterOrchestrator:
    def __init__(self, discover_timeout: int = 6):
        self.discover_timeout = discover_timeout

    def discover_workers(self) -> List[Dict]:
        """Run a short discovery scan and return workers that expose worker_port."""
        service = DiscoveryService(scan_interval=15)
        service.start()
        time.sleep(self.discover_timeout)
        service.stop()
        nodes = service.get_discovered_nodes()

        workers = []
        for ip, data in nodes.items():
            port = data.get("worker_port")
            if port:
                workers.append({
                    "ip": ip,
                    "port": int(port),
                    "name": data.get("device_name") or data.get("hostname") or ip,
                    "capabilities": data.get("capabilities", [])
                })
        return workers

    def run_range_sum(self, start: int, end: int, chunk_size: int, workers: List[Dict]):
        # Dynamically adjust chunk_size so there are at least as many tasks as workers
        if workers:
            total_numbers = end - start + 1
            min_chunks = max(len(workers), 1)
            # compute a chunk size that yields >= number of workers, but not too small
            chunk_size = max(1, min(chunk_size, max(1, total_numbers // min_chunks)))

        tasks = generate_range_sum_tasks(start, end, chunk_size)
        if not workers:
            print("❌ No workers available")
            return

        self._dispatch_with_retries(tasks, workers, aggregate_range_sum)

    def run_array_sum(self, numbers: List[int], chunk_size: int, workers: List[Dict]):
        tasks = generate_array_sum_tasks(numbers, chunk_size)
        if not workers:
            print("❌ No workers available")
            return

        self._dispatch_with_retries(tasks, workers, aggregate_array_sum)

    def _assign_tasks_round_robin(self, tasks: List[Dict], workers: List[Dict]) -> List[Tuple[Dict, Dict]]:
        pairs = []
        for idx, task in enumerate(tasks):
            worker = workers[idx % len(workers)]
            pairs.append((worker, task))
        return pairs

    def _dispatch_with_retries(self, tasks: List[Dict], workers: List[Dict], aggregator):
        """Dispatch tasks with retries; reassign on worker failure/disconnect."""
        max_attempts = 3
        attempts = {t["task_id"]: 0 for t in tasks}
        pending = tasks[:]
        completed = []

        while pending and workers:
            # Assign up to len(workers) tasks this round
            batch = pending[:len(workers)]
            pending = pending[len(workers):]

            assignments = self._assign_tasks_round_robin(batch, workers)
            results = []
            lock = threading.Lock()
            threads = []

            for worker, task in assignments:
                t = threading.Thread(target=self._run_task, args=(worker, task, results, lock))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            # Process results: completed vs retry
            for res in results:
                task_id = res.get("task_id")
                status = res.get("status")
                if status == "completed":
                    completed.append(res)
                else:
                    # retry if attempts left
                    attempts[task_id] += 1
                    if attempts[task_id] < max_attempts:
                        pending.append(next(t for t in tasks if t["task_id"] == task_id))
                        print(f"  ↻ Re-queuing {task_id} (attempt {attempts[task_id]} of {max_attempts})")
                    else:
                        completed.append(res)

        # Aggregate results
        if completed:
            final = aggregator([r for r in completed if r.get("status") == "completed"])
            print("\n🎉 FINAL RESULT")
            print(json.dumps(final, indent=2))
        else:
            print("❌ No successful results")

    def _run_task(self, worker: Dict, task: Dict, results: List[Dict], lock: threading.Lock):
        ip = worker["ip"]
        port = worker.get("port", DEFAULT_WORKER_PORT)
        task_id = task.get("task_id")

        print(f"➡️  Sending {task_id} to {worker['name']} ({ip}:{port})")
        try:
            with socket.create_connection((ip, port), timeout=5) as conn:
                msg = {
                    "type": "task",
                    "task_id": task_id,
                    "task_name": task["task_name"],
                    "payload": task.get("payload", {})
                }
                conn.sendall((json.dumps(msg) + "\n").encode('utf-8'))

                file = conn.makefile('r')
                task_result = {"task_id": task_id, "status": "pending", "worker": worker['name']}

                for line in file:
                    try:
                        resp = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue

                    r_type = resp.get("type")
                    if r_type == "ack":
                        print(f"  ✅ {task_id} accepted by {worker['name']}")
                    elif r_type == "progress":
                        prog = resp.get("progress")
                        print(f"  🔄 {task_id} progress {prog}%")
                    elif r_type == "result":
                        # Merge result payload to top-level for aggregation convenience
                        result_payload = resp.get("result", {})
                        task_result.update(result_payload)
                        task_result["status"] = resp.get("status", "completed")
                        task_result["duration_ms"] = resp.get("duration_ms")
                        break
                with lock:
                    results.append(task_result)
        except Exception as e:
            with lock:
                results.append({"task_id": task_id, "status": "failed", "error": str(e), "worker": worker['name']})
            print(f"  ❌ {task_id} failed on {worker['name']}: {e}")


def parse_nodes(nodes: str) -> List[Dict]:
    worker_list = []
    for item in nodes.split(','):
        if not item.strip():
            continue
        if ':' in item:
            ip, port = item.split(':', 1)
            worker_list.append({"ip": ip.strip(), "port": int(port), "name": ip.strip()})
        else:
            worker_list.append({"ip": item.strip(), "port": DEFAULT_WORKER_PORT, "name": item.strip()})
    return worker_list


def main():
    parser = argparse.ArgumentParser(description="Master orchestrator for distributed tasks")
    parser.add_argument("--task", choices=list(SUPPORTED_TASKS.keys()), default="range_sum", help="Task to run")
    parser.add_argument("--start", type=int, default=1, help="Range start (for range_sum)")
    parser.add_argument("--end", type=int, default=1_000_000, help="Range end (for range_sum)")
    parser.add_argument("--chunk-size", type=int, default=50_000, help="Chunk size for splitting tasks")
    parser.add_argument("--numbers", type=str, default=None, help="Comma-separated numbers for array_sum (e.g., 1,2,3,4)")
    parser.add_argument("--nodes", type=str, default=None, help="Comma-separated worker list (ip or ip:port). If omitted, auto-discover.")
    parser.add_argument("--discover-timeout", type=int, default=6, help="Seconds to wait for discovery")
    args = parser.parse_args()

    master = MasterOrchestrator(discover_timeout=args.discover_timeout)

    if args.nodes:
        workers = parse_nodes(args.nodes)
        print(f"Using manual worker list: {workers}")
    else:
        print("🔍 Discovering workers...")
        workers = master.discover_workers()
        if not workers:
            print("❌ No workers found. Start worker.py on remote nodes or specify --nodes")
            return
        print(f"✅ Found {len(workers)} workers: {[w['ip'] for w in workers]}")

    if args.task == "range_sum":
        master.run_range_sum(args.start, args.end, args.chunk_size, workers)
    elif args.task == "array_sum":
        if not args.numbers:
            print("❌ --numbers is required for array_sum (comma-separated list)")
            return
        try:
            nums = [int(x.strip()) for x in args.numbers.split(',') if x.strip()]
        except ValueError:
            print("❌ --numbers must be comma-separated integers")
            return
        master.run_array_sum(nums, args.chunk_size, workers)


if __name__ == "__main__":
    main()
