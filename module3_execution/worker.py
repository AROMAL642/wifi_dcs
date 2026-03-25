#!/usr/bin/env python3
"""
Worker/Slave node service.
- Responds to discovery GET_NODE_INFO on UDP port 5555
- Accepts task execution requests over TCP (default port 6000)
- Reports progress, status, and results back to the master on the same connection
"""

import socket
import threading
import json
import time
from typing import Dict
import sys
import os

# Allow importing discovery module
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from module1_discovery.node_info import NodeInfoCollector
except Exception:
    from node_info import NodeInfoCollector  # fallback if run inside module1_discovery

from module3_execution.tasks import execute_task, SUPPORTED_TASKS

DISCOVERY_PORT = 5555
DEFAULT_WORKER_PORT = 6000


class WorkerServer:
    def __init__(self, worker_port: int = DEFAULT_WORKER_PORT, node_name: str = None):
        self.worker_port = worker_port
        self.node_name = node_name
        self.running = False
        self.udp_thread = None
        self.tcp_thread = None
        self.collector = NodeInfoCollector()
        self.node_info = self.collector.collect_all_info()
        if not self.node_name:
            self.node_name = self.node_info.hostname

    def start(self):
        self.running = True
        self.udp_thread = threading.Thread(target=self._udp_responder, daemon=True)
        self.udp_thread.start()

        self.tcp_thread = threading.Thread(target=self._tcp_server, daemon=True)
        self.tcp_thread.start()

        print(f"✓ Worker '{self.node_name}' ready")
        print(f"  Discovery port : {DISCOVERY_PORT}")
        print(f"  Worker port    : {self.worker_port}")
        print(f"  IP             : {self.node_info.ip_address}")
        print(f"  Listening for tasks...\n")

    def stop(self):
        self.running = False
        print("Stopping worker...")

    def _udp_responder(self):
        """Respond to GET_NODE_INFO discovery requests."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except Exception:
                pass
            sock.bind(('', DISCOVERY_PORT))
            sock.settimeout(1.0)

            while self.running:
                try:
                    data, addr = sock.recvfrom(4096)
                    message = data.decode('utf-8')
                    if message == "GET_NODE_INFO":
                        payload = self._build_node_info()
                        response = "NODE_INFO:" + json.dumps(payload)
                        sock.sendto(response.encode('utf-8'), addr)
                except socket.timeout:
                    continue
                except Exception:
                    if self.running:
                        continue
        except Exception as e:
            print(f"UDP responder error: {e}")

    def _tcp_server(self):
        """Listen for task execution requests over TCP."""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('', self.worker_port))
            server.listen(5)
            server.settimeout(1.0)
            
            while self.running:
                try:
                    conn, addr = server.accept()
                    t = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                    t.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"TCP accept error: {e}")
            server.close()
        except Exception as e:
            print(f"TCP server error: {e}")

    def _handle_client(self, conn: socket.socket, addr):
        """Handle a master connection and run a single task."""
        file = conn.makefile('r')
        try:
            line = file.readline()
            if not line:
                return
            try:
                msg = json.loads(line.strip())
            except json.JSONDecodeError:
                self._send(conn, {"type": "error", "message": "invalid json"})
                return

            if msg.get("type") != "task":
                self._send(conn, {"type": "error", "message": "invalid message type"})
                return

            task_id = msg.get("task_id") or f"task-{int(time.time())}"
            task_name = msg.get("task_name")
            payload = msg.get("payload", {})

            if task_name not in SUPPORTED_TASKS:
                self._send(conn, {"type": "error", "task_id": task_id, "message": "unsupported task"})
                return

            # Print task received on worker terminal
            self._print_task_status(task_id, "received", task_name, payload)
            
            self._send(conn, {"type": "ack", "task_id": task_id, "status": "accepted", "worker": self.node_name})

            start_time = time.time()
            last_progress = 0

            def progress_cb(p: float):
                """Callback for task progress - sends to master and logs locally"""
                nonlocal last_progress
                progress_percent = round(p * 100, 2)
                
                # Only send/print if progress changed significantly
                if progress_percent >= last_progress + 10 or progress_percent >= 100:
                    # Send to master
                    self._send(conn, {
                        "type": "progress",
                        "task_id": task_id,
                        "progress": progress_percent,
                        "status": "running"
                    })
                    
                    # Print on worker terminal
                    self._print_task_progress(task_id, progress_percent)
                    last_progress = progress_percent

            try:
                # Execute task with progress callback
                self._print_task_status(task_id, "executing", task_name, payload)
                result = execute_task(task_name, payload, progress_cb)
                duration = (time.time() - start_time) * 1000
                
                # Print completion on worker terminal
                self._print_task_status(task_id, "completed", task_name, None, duration_ms=duration)
                
                # Send result to master
                self._send(conn, {
                    "type": "result",
                    "task_id": task_id,
                    "status": "completed",
                    "worker": self.node_name,
                    "result": result,
                    "duration_ms": round(duration, 2)
                })
            except Exception as e:
                # Print error on worker terminal
                self._print_task_status(task_id, "failed", task_name, None, error=str(e))
                
                # Send error to master
                self._send(conn, {
                    "type": "result",
                    "task_id": task_id,
                    "status": "failed",
                    "worker": self.node_name,
                    "error": str(e)
                })
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _send(self, conn: socket.socket, obj: Dict):
        """Send JSON object to master"""
        try:
            data = json.dumps(obj) + "\n"
            conn.sendall(data.encode('utf-8'))
        except Exception:
            pass

    def _print_task_status(self, task_id: str, status: str, task_name: str = None, payload: Dict = None, duration_ms: float = None, error: str = None):
        """Print task status on worker terminal"""
        timestamp = time.strftime("%H:%M:%S")
        
        if status == "received":
            print(f"[{timestamp}] 📥 Task received: {task_id}")
            print(f"           Task: {task_name}")
            if payload:
                if task_name == "range_sum":
                    start = payload.get("start")
                    end = payload.get("end")
                    print(f"           Range: {start} to {end}")
                elif task_name == "array_sum":
                    count = len(payload.get("numbers", []))
                    print(f"           Count: {count} numbers")
        
        elif status == "executing":
            print(f"[{timestamp}] ⚙️  Executing: {task_id}")
        
        elif status == "completed":
            print(f"[{timestamp}] ✅ Completed: {task_id}")
            if duration_ms is not None:
                print(f"           Duration: {duration_ms:.2f} ms")
        
        elif status == "failed":
            print(f"[{timestamp}] ❌ Failed: {task_id}")
            if error:
                print(f"           Error: {error}")

    def _print_task_progress(self, task_id: str, progress_percent: float):
        """Print task progress on worker terminal"""
        timestamp = time.strftime("%H:%M:%S")
        bar_length = 20
        filled = int(bar_length * progress_percent / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"[{timestamp}] 🔄 {task_id}: [{bar}] {progress_percent:.0f}%")

    def _build_node_info(self) -> Dict:
        """Build node info dict for discovery response"""
        info = self.collector.to_dict(self.node_info)
        info.update({
            "worker_port": self.worker_port,
            "supports_tasks": True,
            "capabilities": list(SUPPORTED_TASKS.keys()),
            "device_name": self.node_name,
        })
        return info


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Worker/Slave node service")
    parser.add_argument("--port", type=int, default=DEFAULT_WORKER_PORT, help="TCP port to listen for tasks (default 6000)")
    parser.add_argument("--name", type=str, default=None, help="Name of this worker")
    args = parser.parse_args()

    server = WorkerServer(worker_port=args.port, node_name=args.name)
    server.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
