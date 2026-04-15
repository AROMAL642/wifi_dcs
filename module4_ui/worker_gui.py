"""
Worker GUI for executing distributed tasks - Simple mode matching terminal behavior.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import socket
import json
import time
from pathlib import Path
from datetime import datetime
import threading
from typing import Dict, Optional, Callable

sys.path.insert(0, str(Path(__file__).parent.parent))

from module3_execution.tasks import execute_task
from module4_ui.discovery_service import NodeDiscoveryService, AdvertiseService, get_local_ip
from network_communication import WorkerServer


class WorkerGUI:
    """Worker mode GUI for task execution."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed Computing - Worker")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f0f0")
        
        self.worker_port = 6000
        self.worker_name = self._get_worker_name()
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        
        self.discovery_service = NodeDiscoveryService(
            discovery_callback=self._on_node_discovered
        )
        self.advertise_service = None
        self.worker_server = None
        
        self.logs_text = None
        
        self._create_widgets()
    
    def _get_worker_name(self) -> str:
        """Get unique worker name."""
        hostname = socket.gethostname()
        return f"worker-{hostname}"
    
    def _create_widgets(self):
        """Create main GUI widgets."""
        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=60)
        header.pack(fill="x")
        
        tk.Label(header, text=f"Worker Node - {self.worker_name}", 
                font=("Arial", 18, "bold"), fg="white", bg="#2c3e50").pack(pady=10)
        
        # Main container
        main_container = ttk.PanedWindow(self.root, orient="horizontal")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel
        left_panel = tk.Frame(self.root, bg="white")
        main_container.add(left_panel, weight=1)
        self._create_left_panel(left_panel)
        
        # Right panel
        right_panel = tk.Frame(self.root, bg="white")
        main_container.add(right_panel, weight=2)
        self._create_right_panel(right_panel)
    
    def _create_left_panel(self, parent):
        """Create left panel with connection controls."""
        tk.Label(parent, text="Worker Status / Controls", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        # Local IP and port controls (user can change port and start service)
        info_frame = tk.LabelFrame(parent, text="Connection", font=("Arial", 10, "bold"), bg="white")
        info_frame.pack(padx=10, pady=10, fill="x")
        
        local_ip = get_local_ip()
        tk.Label(info_frame, text=f"Local IP: {local_ip}", bg="white", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=5)
        
        tk.Label(info_frame, text="Port:", bg="white").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.port_var = tk.StringVar(value=str(self.worker_port))
        port_entry = tk.Entry(info_frame, textvariable=self.port_var, width=10)
        port_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        tk.Label(info_frame, text="Worker Name:", bg="white").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.name_var = tk.StringVar(value=self.worker_name)
        tk.Entry(info_frame, textvariable=self.name_var, width=25).grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        self.service_btn = tk.Button(info_frame, text="Start Service", command=self._toggle_service,
                                     bg="#4CAF50", fg="white", width=15, font=("Arial", 10, "bold"))
        self.service_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Copy connection info helper
        def _copy_address():
            addr = f"{local_ip}:{self.port_var.get()}"
            self.root.clipboard_clear()
            self.root.clipboard_append(addr)
            messagebox.showinfo("Copied", f"Address copied to clipboard:\n{addr}")
        
        tk.Button(info_frame, text="Copy IP:Port", command=_copy_address,
                 bg="#2196F3", fg="white", font=("Arial", 9)).grid(row=4, column=0, columnspan=2, pady=5, sticky="ew")
        
        # Status box and masters list follow (unchanged)
        status_frame = tk.LabelFrame(parent, text="System Information", font=("Arial", 10, "bold"), bg="white")
        status_frame.pack(padx=10, pady=10, fill="x")
        
        self.status_text = tk.Text(status_frame, height=8, width=35, bg="#f5f5f5", state="disabled")
        self.status_text.pack(padx=10, pady=10)
        
        tk.Label(parent, text="Master Nodes", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        discovery_frame = tk.LabelFrame(parent, text="Discovered Masters", font=("Arial", 10, "bold"), bg="white")
        discovery_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.masters_listbox = tk.Listbox(discovery_frame, height=10, width=35, bg="white")
        self.masters_listbox.pack(padx=10, pady=10, fill="both", expand=True)
        
        button_frame = tk.Frame(parent, bg="white")
        button_frame.pack(padx=10, pady=10, fill="x")
        
        tk.Button(button_frame, text="Refresh Masters", command=self._refresh_masters,
                 bg="#2196F3", fg="white", width=25).pack(pady=5)
    
    def _create_right_panel(self, parent):
        """Create right panel with tabs."""
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        task_frame = tk.Frame(notebook, bg="white")
        notebook.add(task_frame, text="Task Queue")
        self._create_task_tab(task_frame)
        
        log_frame = tk.Frame(notebook, bg="white")
        notebook.add(log_frame, text="Logs")
        self._create_logs_tab(log_frame)
    
    def _create_task_tab(self, parent):
        """Create task queue tab."""
        tk.Label(parent, text="Received Tasks", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        self.tasks_listbox = tk.Listbox(parent, height=15, width=100, bg="white")
        self.tasks_listbox.pack(padx=10, pady=10, fill="both", expand=True)
        
        info_frame = tk.Frame(parent, bg="white")
        info_frame.pack(padx=10, pady=10, fill="x")
        
        self.task_count_label = tk.Label(info_frame, text="Total: 0 | Completed: 0 | Failed: 0", 
                                        font=("Arial", 10, "bold"), bg="white", fg="#2196F3")
        self.task_count_label.pack(anchor="w")
    
    def _create_logs_tab(self, parent):
        """Create logs tab."""
        tk.Label(parent, text="Worker Logs", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        self.logs_text = scrolledtext.ScrolledText(parent, height=20, width=100, bg="#1e1e1e", fg="#00ff00")
        self.logs_text.pack(padx=10, pady=10, fill="both", expand=True)
        
        tk.Button(parent, text="Clear Logs", command=lambda: self.logs_text.delete("1.0", tk.END),
                 bg="#757575", fg="white").pack(padx=10, pady=5)
    
    def _start_services(self):
        """Start worker server - simple, no callbacks during execution."""
        try:
            port = int(self.port_var.get())
        except Exception:
            messagebox.showerror("Port Error", "Invalid port number")
            return
        
        self.worker_port = port
        self.worker_name = self.name_var.get() or self._get_worker_name()
        
        if self.worker_server is None:
            self.worker_server = WorkerServer(port=self.worker_port, task_callback=self._execute_task_simple)
        
        self.worker_server.start()
        self._log(f"✓ Worker server started on {get_local_ip()}:{self.worker_port}")
        
        self.discovery_service.start_discovery()
        self._log("✓ Discovery service started")
        
        self.advertise_service = AdvertiseService(self.worker_name, "worker", self.worker_port)
        self.advertise_service.start_advertising()
        self._log(f"✓ Advertising as '{self.worker_name}' on port {self.worker_port}")
        
        self.service_btn.config(text="Stop Service", bg="#f44336")
        self._update_status()
    
    def _stop_services(self):
        """Stop worker server."""
        if self.worker_server:
            self.worker_server.stop()
            self.worker_server = None
            self._log("✗ Worker server stopped")
        self.discovery_service.stop_discovery()
        self._log("✗ Discovery service stopped")
        if self.advertise_service:
            self.advertise_service.stop_advertising()
            self.advertise_service = None
        self.service_btn.config(text="Start Service", bg="#4CAF50")
    
    def _toggle_service(self):
        """Toggle worker service start/stop."""
        if self.worker_server:
            self._stop_services()
        else:
            self._start_services()
    
    def _execute_task_simple(self, task_data: Dict) -> Dict:
        """
        Execute task immediately without progress callbacks.
        Works exactly like terminal execution.
        """
        task_name = task_data.get("task_name", "unknown")
        task_id = task_data.get("task_id", f"{task_name}-{int(time.time() * 1000)}")
        payload = task_data.get("payload", {})

        try:
            self.total_tasks += 1
            start_time = time.perf_counter()
            last_progress = -1
            
            self._log(f"📥 Task received: {task_id}")
            self._log(f"   Task: {task_name}")
            self._log(f"   Payload: {self._summarize_payload(payload)}")
            self._log(f"⚙️  Executing: {task_id}")

            def progress_cb(p: float):
                nonlocal last_progress
                progress_percent = round(max(0.0, min(1.0, p)) * 100, 2)

                if progress_percent >= last_progress + 10 or progress_percent >= 100:
                    bar_length = 20
                    filled = int(bar_length * progress_percent / 100)
                    bar = "█" * filled + "░" * (bar_length - filled)
                    self._log(f"🔄 {task_id}: [{bar}] {progress_percent:.0f}%")
                    last_progress = progress_percent
            
            result = execute_task(task_name, payload, progress_cb)
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            self.completed_tasks += 1
            self._log(f"✅ Completed: {task_id}")
            self._log(f"   Duration: {duration_ms:.2f} ms")
            self._log(f"   Result: {self._summarize_result(result)}")
            self._add_task_to_queue(f"✓ {task_id} ({task_name})")
            self._update_task_count()
            
            return result
        
        except Exception as e:
            self.failed_tasks += 1
            error_msg = str(e)
            self._log(f"❌ Failed: {task_id} ({task_name})")
            self._log(f"   Error: {error_msg}")
            self._add_task_to_queue(f"✗ {task_id} ({task_name}) - {error_msg}")
            self._update_task_count()
            return {"status": "error", "message": error_msg}

    def _summarize_payload(self, payload: Dict) -> str:
        """Create compact payload summary for logs."""
        try:
            compact = {}
            for key, value in payload.items():
                if isinstance(value, list):
                    compact[key] = {
                        "type": "list",
                        "count": len(value),
                        "preview": value[:5]
                    }
                else:
                    compact[key] = value
            return json.dumps(compact, ensure_ascii=False)
        except Exception:
            return str(payload)

    def _summarize_result(self, result: Dict) -> str:
        """Create compact result summary for logs."""
        if not isinstance(result, dict):
            return str(result)

        if result.get("status") == "error":
            return f"error={result.get('message', 'unknown')}"

        keys = list(result.keys())
        parts = [f"keys={keys}"]
        for field in ["partial_sum", "count", "total_sum", "total_numbers", "task"]:
            if field in result:
                parts.append(f"{field}={result.get(field)}")

        return ", ".join(parts)
    
    def _add_task_to_queue(self, task_info: str):
        """Add task to task queue listbox."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.tasks_listbox.insert(tk.END, f"[{timestamp}] {task_info}")
        self.tasks_listbox.see(tk.END)
    
    def _update_task_count(self):
        """Update task count display."""
        self.task_count_label.config(
            text=f"Total: {self.total_tasks} | Completed: {self.completed_tasks} | Failed: {self.failed_tasks}"
        )
    
    def _update_status(self):
        """Update worker status display."""
        def update():
            while self.worker_server and getattr(self.worker_server, 'is_running', False):
                try:
                    import psutil
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    
                    info = f"""Worker: {self.worker_name}
Port: {self.worker_port}
Status: Online ✓

Tasks:
  Total: {self.total_tasks}
  Completed: {self.completed_tasks}
  Failed: {self.failed_tasks}

System:
  CPU: {cpu_percent:.1f}%
  Memory: {memory.percent:.1f}%
  Disk: {psutil.disk_usage('/').percent:.1f}%"""
                    
                    self.status_text.config(state="normal")
                    self.status_text.delete("1.0", tk.END)
                    self.status_text.insert("1.0", info)
                    self.status_text.config(state="disabled")
                    
                    threading.Event().wait(5)
                except:
                    break
        
        thread = threading.Thread(target=update, daemon=True)
        thread.start()
    
    def _on_node_discovered(self, node_addr: str, state: str):
        """Handle master node discovery."""
        if state == "discovered":
            self._log(f"Master discovered: {node_addr}")
            if node_addr not in self.masters_listbox.get(0, tk.END):
                self.masters_listbox.insert(tk.END, node_addr)
    
    def _refresh_masters(self):
        """Refresh master node list."""
        self._log("Scanning for Master nodes...")
        self.masters_listbox.delete(0, tk.END)
        self.discovery_service.stop_discovery()
        self.discovery_service.start_discovery()
    
    def _log(self, message: str):
        """Add message to logs."""
        if self.logs_text is None:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        self.logs_text.insert(tk.END, log_msg)
        self.logs_text.see(tk.END)
    
    def cleanup(self):
        """Cleanup on exit."""
        try:
            self.discovery_service.stop_discovery()
        except:
            pass
        
        try:
            if self.advertise_service:
                self.advertise_service.stop_advertising()
        except:
            pass
        
        try:
            if self.worker_server:
                self.worker_server.stop()
        except:
            pass
