"""
Network communication module for Master-Worker interaction.
Simple, fast, reliable - matches terminal behavior.
"""

import socket
import json
import threading
import time
import base64
import io
import os
import tempfile
import zipfile
from typing import Dict, Callable, Optional, List, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class WorkerServer:
    """TCP server running on worker to receive and execute tasks."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 6000, 
                 task_callback: Optional[Callable] = None):
        self.host = host
        self.port = port
        self.task_callback = task_callback
        self.server_socket = None
        self.is_running = False
        self.server_thread = None
    
    def start(self):
        """Start the worker server."""
        self.is_running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
    
    def stop(self):
        """Stop the worker server."""
        self.is_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
    
    def _run_server(self):
        """Run the server listening for tasks."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            while self.is_running:
                try:
                    self.server_socket.settimeout(1.0)
                    client_socket, client_addr = self.server_socket.accept()
                    threading.Thread(target=self._handle_client, 
                                   args=(client_socket, client_addr), daemon=True).start()
                except socket.timeout:
                    continue
                except:
                    if self.is_running:
                        break
        except Exception as e:
            print(f"Server error: {e}")
    
    def _handle_client(self, client_socket: socket.socket, client_addr: tuple):
        """Handle incoming task - simple and direct."""
        try:
            # Receive task data with length prefix
            length_data = client_socket.recv(4)
            if not length_data or len(length_data) < 4:
                return
            
            data_length = int.from_bytes(length_data, 'big')
            task_data_bytes = self._recv_all(client_socket, data_length, timeout=60)
            
            if not task_data_bytes:
                return
            
            task_data = json.loads(task_data_bytes.decode('utf-8'))

            # Unpack any dataset attachments and update payload paths
            task_data = _unpack_task_attachments(task_data)
            
            # Execute task callback (does actual work)
            if self.task_callback:
                result = self.task_callback(task_data)
            else:
                result = {"status": "error", "message": "No callback"}
            
            # Send result with length prefix
            result_json = json.dumps(result).encode('utf-8')
            result_length = len(result_json).to_bytes(4, 'big')
            client_socket.sendall(result_length + result_json)
        
        except Exception as e:
            try:
                error_result = {"status": "error", "message": str(e)}
                error_json = json.dumps(error_result).encode('utf-8')
                error_length = len(error_json).to_bytes(4, 'big')
                client_socket.sendall(error_length + error_json)
            except:
                pass
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    @staticmethod
    def _recv_all(sock: socket.socket, num_bytes: int, timeout: int = 60) -> bytes:
        """Receive exactly num_bytes with timeout."""
        sock.settimeout(timeout)
        data = b""
        while len(data) < num_bytes:
            chunk = sock.recv(min(4096, num_bytes - len(data)))
            if not chunk:
                return None
            data += chunk
        return data


class MasterClient:
    """Client on master to send tasks to workers."""
    
    @staticmethod
    def send_task(host: str, port: int, task_data: Dict) -> Dict:
        """Send task to worker and get result. Auto-timeout based on payload size."""
        try:
            task_data = _pack_task_attachments(task_data)
            # Calculate timeout: 5s base + 10s per MB
            payload_size = len(json.dumps(task_data)) / (1024 * 1024)
            timeout = max(30, int(5 + (payload_size * 10)))
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # Connect
            sock.settimeout(10)
            sock.connect((host, port))
            
            # Send task with length prefix
            task_json = json.dumps(task_data).encode('utf-8')
            task_length = len(task_json).to_bytes(4, 'big')
            sock.sendall(task_length + task_json)
            
            # Receive result with timeout
            sock.settimeout(timeout)
            length_data = sock.recv(4)
            if not length_data:
                sock.close()
                return {"status": "error", "message": f"No response from {host}:{port}"}
            
            result_length = int.from_bytes(length_data, 'big')
            result_data = MasterClient._recv_all(sock, result_length, timeout)
            sock.close()
            
            if result_data:
                return json.loads(result_data.decode('utf-8'))
            else:
                return {"status": "error", "message": f"Incomplete response from {host}:{port}"}
        
        except socket.timeout:
            return {"status": "error", "message": f"Timeout (>{timeout}s) - worker busy or unreachable"}
        except ConnectionRefusedError:
            return {"status": "error", "message": f"Worker {host}:{port} not running"}
        except Exception as e:
            return {"status": "error", "message": f"Error: {str(e)}"}
    
    @staticmethod
    def _recv_all(sock: socket.socket, num_bytes: int, timeout: int) -> bytes:
        """Receive exactly num_bytes."""
        sock.settimeout(timeout)
        data = b""
        while len(data) < num_bytes:
            chunk = sock.recv(min(4096, num_bytes - len(data)))
            if not chunk:
                return None
            data += chunk
        return data


def _collect_attachment_paths(payload: Dict[str, Any]) -> Dict[str, List[str]]:
    """Collect dataset/file attachments from payload (keys containing dataset/file)."""
    attachments: Dict[str, List[str]] = {}
    for key, value in payload.items():
        if "file" in key.lower() or "dataset" in key.lower():
            if isinstance(value, list):
                attachments[key] = [str(v) for v in value]
            elif isinstance(value, str) and value:
                attachments[key] = [v for v in value.split(",") if v]
    return attachments


def _pack_task_attachments(task_data: Dict) -> Dict:
    """Zip and base64-encode dataset/file attachments into task_data."""
    payload = task_data.get("payload") or {}
    attachments = _collect_attachment_paths(payload)

    if not attachments:
        return task_data

    all_files: List[str] = []
    for paths in attachments.values():
        all_files.extend(paths)

    # Remove empty/invalid entries
    all_files = [p for p in all_files if p]
    if not all_files:
        return task_data

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in all_files:
            if not os.path.exists(file_path):
                continue
            arcname = Path(file_path).name
            zf.write(file_path, arcname=arcname)

    archive_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    attachment_manifest = []
    for key, paths in attachments.items():
        names = [Path(p).name for p in paths]
        attachment_manifest.append({"key": key, "names": names})

    task_data = dict(task_data)
    task_data["attachments"] = {
        "archive_b64": archive_b64,
        "files": attachment_manifest
    }

    # Replace payload entries with just filenames (will be resolved on worker)
    payload = dict(payload)
    for item in attachment_manifest:
        payload[item["key"]] = item["names"]
    task_data["payload"] = payload

    return task_data


def _unpack_task_attachments(task_data: Dict) -> Dict:
    """Extract attachments and update payload with local file paths."""
    attachments = task_data.get("attachments")
    if not attachments:
        return task_data

    archive_b64 = attachments.get("archive_b64")
    files_meta = attachments.get("files", [])
    if not archive_b64:
        return task_data

    payload = task_data.get("payload") or {}

    try:
        temp_dir = tempfile.mkdtemp(prefix="dataset_")
        archive_bytes = base64.b64decode(archive_b64)
        buffer = io.BytesIO(archive_bytes)

        with zipfile.ZipFile(buffer, "r") as zf:
            zf.extractall(temp_dir)

        for item in files_meta:
            key = item.get("key")
            names = item.get("names", [])
            if key:
                payload[key] = [str(Path(temp_dir) / name) for name in names]

        payload["dataset_dir"] = temp_dir
        task_data["payload"] = payload
    except Exception:
        # If unpacking fails, return original task_data (worker can error appropriately)
        return task_data

    return task_data
