"""
Comprehensive GUI for WiFi-based Distributed Computing System.
Supports built-in tasks, custom task creation, file attachments, and real-time monitoring.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from module3_execution.tasks import (
    execute_task, aggregate_range_sum, aggregate_array_sum,
    register_custom_task, get_all_tasks, generate_range_sum_tasks,
    generate_array_sum_tasks, validate_file_attachments
)


class TaskExecutionWorker:
    """Background worker for task execution."""
    
    def __init__(self, task_name: str, payload: Dict, nodes: List[str], 
                 progress_callback: Callable, completion_callback: Callable):
        self.task_name = task_name
        self.payload = payload
        self.nodes = nodes
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.thread = None
        self.is_running = False
    
    def start(self):
        """Start execution in background thread."""
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop execution."""
        self.is_running = False
    
    def _run(self):
        """Execute task and aggregate results."""
        try:
            results = []
            for idx, node in enumerate(self.nodes):
                if not self.is_running:
                    break
                
                # Simulate task execution (in real scenario, send to worker node)
                def progress_cb(progress):
                    overall_progress = (idx + progress) / len(self.nodes)
                    self.progress_callback(overall_progress)
                
                result = execute_task(self.task_name, self.payload, progress_cb)
                results.append(result)
            
            # Aggregate results
            if self.task_name == "range_sum":
                final_result = aggregate_range_sum(results)
            elif self.task_name == "array_sum":
                final_result = aggregate_array_sum(results)
            else:
                final_result = {"task": self.task_name, "results": results}
            
            self.completion_callback(True, final_result)
        except Exception as e:
            self.completion_callback(False, str(e))


class CustomTaskDialog(tk.Toplevel):
    """Dialog for creating custom tasks with file attachments."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create Custom Task")
        self.geometry("700x600")
        self.task_result = None
        self.attached_files = []
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create dialog widgets."""
        # Task Name
        tk.Label(self, text="Task Name:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        self.task_name_var = tk.StringVar()
        tk.Entry(self, textvariable=self.task_name_var, width=40).grid(row=0, column=1, columnspan=2, padx=10, pady=10)
        
        # Description
        tk.Label(self, text="Description:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=10, pady=10)
        self.desc_var = tk.StringVar()
        tk.Entry(self, textvariable=self.desc_var, width=40).grid(row=1, column=1, columnspan=2, padx=10, pady=10)
        
        # Executor Code
        tk.Label(self, text="Executor Code (Python):", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="nw", padx=10, pady=10)
        self.executor_text = scrolledtext.ScrolledText(self, height=10, width=70)
        self.executor_text.grid(row=2, column=1, columnspan=2, padx=10, pady=10)
        
        self.executor_text.insert("1.0", """def executor(payload, progress_cb):
    # Your custom task logic here
    # payload: Dict with task parameters
    # progress_cb: Callable[[float], None] for progress updates
    
    result = {
        "status": "success",
        "data": "your result here"
    }
    progress_cb(1.0)
    return result""")
        
        # Aggregator Code
        tk.Label(self, text="Aggregator Code (Python):", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="nw", padx=10, pady=10)
        self.aggregator_text = scrolledtext.ScrolledText(self, height=8, width=70)
        self.aggregator_text.grid(row=3, column=1, columnspan=2, padx=10, pady=10)
        
        self.aggregator_text.insert("1.0", """def aggregator(results):
    # Aggregate partial results
    combined = {
        "task": "custom_task",
        "total_results": len(results),
        "data": results
    }
    return combined""")
        
        # File Attachments Section
        tk.Label(self, text="Attached Files:", font=("Arial", 10, "bold")).grid(row=4, column=0, sticky="w", padx=10, pady=10)
        
        button_frame = tk.Frame(self)
        button_frame.grid(row=4, column=1, sticky="w", padx=10, pady=10)
        tk.Button(button_frame, text="Add File", command=self._add_file, bg="#4CAF50", fg="white").pack(side="left", padx=5)
        tk.Button(button_frame, text="Remove Selected", command=self._remove_file, bg="#f44336", fg="white").pack(side="left", padx=5)
        
        # File List
        self.file_listbox = tk.Listbox(self, height=4, width=70)
        self.file_listbox.grid(row=5, column=1, columnspan=2, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.file_listbox.yview)
        scrollbar.grid(row=5, column=3, sticky="ns", pady=10)
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        
        # Buttons
        button_frame_bottom = tk.Frame(self)
        button_frame_bottom.grid(row=6, column=0, columnspan=4, pady=20)
        
        tk.Button(button_frame_bottom, text="Register Task", command=self._register_task, 
                 bg="#2196F3", fg="white", width=15).pack(side="left", padx=10)
        tk.Button(button_frame_bottom, text="Cancel", command=self.destroy, 
                 bg="#757575", fg="white", width=15).pack(side="left", padx=10)
    
    def _add_file(self):
        """Add file to attachments."""
        file_path = filedialog.askopenfilename(title="Select File to Attach")
        if file_path:
            try:
                validate_file_attachments(file_path)
                self.attached_files.append(file_path)
                self.file_listbox.insert(tk.END, Path(file_path).name)
            except Exception as e:
                messagebox.showerror("File Error", str(e))
    
    def _remove_file(self):
        """Remove selected file from attachments."""
        selection = self.file_listbox.curselection()
        if selection:
            idx = selection[0]
            self.file_listbox.delete(idx)
            self.attached_files.pop(idx)
    
    def _register_task(self):
        """Register custom task."""
        task_name = self.task_name_var.get().strip()
        description = self.desc_var.get().strip()
        executor_code = self.executor_text.get("1.0", tk.END).strip()
        aggregator_code = self.aggregator_text.get("1.0", tk.END).strip()
        
        if not all([task_name, executor_code, aggregator_code]):
            messagebox.showerror("Validation Error", "Task name and code are required!")
            return
        
        try:
            # Create namespace for code execution
            namespace = {}
            exec(executor_code, namespace)
            executor_func = namespace.get("executor")
            
            namespace = {}
            exec(aggregator_code, namespace)
            aggregator_func = namespace.get("aggregator")
            
            if not executor_func or not aggregator_func:
                messagebox.showerror("Code Error", "Executor and aggregator functions must be defined!")
                return
            
            # Register the task
            register_custom_task(
                task_name=task_name,
                executor=executor_func,
                aggregator=aggregator_func,
                description=description or f"Custom task: {task_name}"
            )
            
            self.task_result = {
                "task_name": task_name,
                "files": self.attached_files
            }
            
            messagebox.showinfo("Success", f"Task '{task_name}' registered successfully!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Registration Error", f"Failed to register task:\n{str(e)}")


class DistributedComputingGUI:
    """Main GUI application for distributed computing framework."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("WiFi-Based Distributed Computing System")
        self.root.geometry("1200x800")
        self.root.configure(bg="#f0f0f0")
        
        self.current_task = None
        self.current_worker = None
        self.execution_results = None
        
        self._create_widgets()
        self._update_task_list()
    
    def _create_widgets(self):
        """Create main GUI widgets."""
        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=60)
        header.pack(fill="x")
        
        tk.Label(header, text="WiFi Distributed Computing System", 
                font=("Arial", 18, "bold"), fg="white", bg="#2c3e50").pack(pady=15)
        
        # Main container
        main_container = ttk.PanedWindow(self.root, orient="horizontal")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel - Task selection
        left_panel = tk.Frame(self.root, bg="white")
        main_container.add(left_panel, weight=1)
        
        self._create_left_panel(left_panel)
        
        # Right panel - Configuration & Execution
        right_panel = tk.Frame(self.root, bg="white")
        main_container.add(right_panel, weight=2)
        
        self._create_right_panel(right_panel)
    
    def _create_left_panel(self, parent):
        """Create left panel with task selection."""
        tk.Label(parent, text="Available Tasks", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        # Task Listbox
        self.task_listbox = tk.Listbox(parent, height=20, width=30, bg="white", fg="black")
        self.task_listbox.pack(padx=10, pady=10, fill="both", expand=True)
        self.task_listbox.bind("<<ListboxSelect>>", self._on_task_select)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.task_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.task_listbox.config(yscrollcommand=scrollbar.set)
        
        # Buttons
        button_frame = tk.Frame(parent, bg="white")
        button_frame.pack(padx=10, pady=10, fill="x")
        
        tk.Button(button_frame, text="Create Custom Task", command=self._open_custom_task_dialog,
                 bg="#4CAF50", fg="white", width=25).pack(pady=5)
        tk.Button(button_frame, text="Refresh Tasks", command=self._update_task_list,
                 bg="#2196F3", fg="white", width=25).pack(pady=5)
    
    def _create_right_panel(self, parent):
        """Create right panel with configuration and execution."""
        # Notebook for tabs
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab 1: Task Configuration
        config_frame = tk.Frame(notebook, bg="white")
        notebook.add(config_frame, text="Configuration")
        self._create_config_tab(config_frame)
        
        # Tab 2: Node Configuration
        node_frame = tk.Frame(notebook, bg="white")
        notebook.add(node_frame, text="Nodes")
        self._create_nodes_tab(node_frame)
        
        # Tab 3: Execution & Results
        exec_frame = tk.Frame(notebook, bg="white")
        notebook.add(exec_frame, text="Execution")
        self._create_execution_tab(exec_frame)
        
        # Tab 4: Logs
        log_frame = tk.Frame(notebook, bg="white")
        notebook.add(log_frame, text="Logs")
        self._create_logs_tab(log_frame)
    
    def _create_config_tab(self, parent):
        """Create task configuration tab."""
        tk.Label(parent, text="Task Configuration", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        # Task info display
        self.config_text = scrolledtext.ScrolledText(parent, height=15, width=80, bg="#f5f5f5")
        self.config_text.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Parameter input
        param_frame = tk.LabelFrame(parent, text="Task Parameters", font=("Arial", 10, "bold"), bg="white")
        param_frame.pack(padx=10, pady=10, fill="x")
        
        # Dynamic parameter fields
        self.param_entries = {}
        
        tk.Label(param_frame, text="Chunk Size:", bg="white").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.chunk_size_var = tk.StringVar(value="5000")
        tk.Entry(param_frame, textvariable=self.chunk_size_var, width=20).grid(row=0, column=1, padx=5, pady=5)
        
        # Range Sum specific
        tk.Label(param_frame, text="Start (Range):", bg="white").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.range_start_var = tk.StringVar(value="1")
        tk.Entry(param_frame, textvariable=self.range_start_var, width=20).grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(param_frame, text="End (Range):", bg="white").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.range_end_var = tk.StringVar(value="10000")
        tk.Entry(param_frame, textvariable=self.range_end_var, width=20).grid(row=2, column=1, padx=5, pady=5)
        
        # Array Sum specific
        tk.Label(param_frame, text="Numbers (Array):", bg="white").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.array_numbers_var = tk.StringVar(value="1,2,3,4,5")
        tk.Entry(param_frame, textvariable=self.array_numbers_var, width=20).grid(row=3, column=1, padx=5, pady=5)
    
    def _create_nodes_tab(self, parent):
        """Create worker nodes configuration tab."""
        tk.Label(parent, text="Worker Nodes Configuration", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        # Node input
        input_frame = tk.LabelFrame(parent, text="Add Node", font=("Arial", 10, "bold"), bg="white")
        input_frame.pack(padx=10, pady=10, fill="x")
        
        tk.Label(input_frame, text="Node Address (IP:Port):", bg="white").pack(side="left", padx=5, pady=5)
        self.node_input_var = tk.StringVar(value="127.0.0.1:6000")
        tk.Entry(input_frame, textvariable=self.node_input_var, width=30).pack(side="left", padx=5)
        tk.Button(input_frame, text="Add", command=self._add_node, bg="#4CAF50", fg="white").pack(side="left", padx=5)
        
        # Nodes listbox
        list_frame = tk.LabelFrame(parent, text="Active Nodes", font=("Arial", 10, "bold"), bg="white")
        list_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.nodes_listbox = tk.Listbox(list_frame, height=15, width=50, bg="white")
        self.nodes_listbox.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Default nodes
        default_nodes = ["127.0.0.1:6000", "127.0.0.1:6001", "127.0.0.1:6002"]
        for node in default_nodes:
            self.nodes_listbox.insert(tk.END, node)
        
        # Remove button
        tk.Button(list_frame, text="Remove Selected", command=self._remove_node, 
                 bg="#f44336", fg="white").pack(padx=10, pady=5)
    
    def _create_execution_tab(self, parent):
        """Create execution and results tab."""
        # Progress bar
        progress_frame = tk.Frame(parent, bg="white")
        progress_frame.pack(padx=10, pady=10, fill="x")
        
        tk.Label(progress_frame, text="Execution Progress:", bg="white").pack(side="left", padx=5)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5)
        
        self.progress_label = tk.Label(progress_frame, text="0%", bg="white", width=5)
        self.progress_label.pack(side="left", padx=5)
        
        # Execute button
        button_frame = tk.Frame(parent, bg="white")
        button_frame.pack(padx=10, pady=10, fill="x")
        
        self.execute_btn = tk.Button(button_frame, text="Execute Task", command=self._execute_task,
                                     bg="#2196F3", fg="white", width=20, font=("Arial", 11, "bold"))
        self.execute_btn.pack(side="left", padx=5)
        
        self.stop_btn = tk.Button(button_frame, text="Stop", command=self._stop_execution,
                                  bg="#f44336", fg="white", width=20, font=("Arial", 11, "bold"), state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        tk.Button(button_frame, text="Export Results", command=self._export_results,
                 bg="#FF9800", fg="white", width=20).pack(side="left", padx=5)
        
        # Results display
        tk.Label(parent, text="Results:", font=("Arial", 10, "bold"), bg="white").pack(padx=10, pady=(10, 5), anchor="w")
        
        self.results_text = scrolledtext.ScrolledText(parent, height=20, width=100, bg="#f5f5f5")
        self.results_text.pack(padx=10, pady=10, fill="both", expand=True)
    
    def _create_logs_tab(self, parent):
        """Create logs tab."""
        tk.Label(parent, text="System Logs", font=("Arial", 12, "bold"), bg="white").pack(padx=10, pady=10)
        
        self.logs_text = scrolledtext.ScrolledText(parent, height=25, width=100, bg="#1e1e1e", fg="#00ff00")
        self.logs_text.pack(padx=10, pady=10, fill="both", expand=True)
        
        tk.Button(parent, text="Clear Logs", command=lambda: self.logs_text.delete("1.0", tk.END),
                 bg="#757575", fg="white").pack(padx=10, pady=5)
    
    def _log(self, message: str):
        """Add message to logs."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        self.logs_text.insert(tk.END, log_msg)
        self.logs_text.see(tk.END)
    
    def _update_task_list(self):
        """Update available tasks in listbox."""
        self.task_listbox.delete(0, tk.END)
        all_tasks = get_all_tasks()
        
        for task_name, description in all_tasks.items():
            self.task_listbox.insert(tk.END, f"{task_name}: {description}")
        
        self._log("Task list updated")
    
    def _on_task_select(self, event):
        """Handle task selection."""
        selection = self.task_listbox.curselection()
        if selection:
            task_str = self.task_listbox.get(selection[0])
            self.current_task = task_str.split(":")[0].strip()
            
            self.config_text.delete("1.0", tk.END)
            self.config_text.insert("1.0", f"Selected Task: {self.current_task}\n\n")
            
            all_tasks = get_all_tasks()
            if self.current_task in all_tasks:
                self.config_text.insert(tk.END, f"Description: {all_tasks[self.current_task]}\n\n")
                self.config_text.insert(tk.END, "Configure parameters in the fields below and click Execute.")
            
            self._log(f"Task selected: {self.current_task}")
    
    def _add_node(self):
        """Add worker node."""
        node = self.node_input_var.get().strip()
        if node:
            self.nodes_listbox.insert(tk.END, node)
            self._log(f"Node added: {node}")
            self.node_input_var.set("127.0.0.1:6000")
        else:
            messagebox.showwarning("Input Error", "Please enter a valid node address")
    
    def _remove_node(self):
        """Remove selected node."""
        selection = self.nodes_listbox.curselection()
        if selection:
            node = self.nodes_listbox.get(selection[0])
            self.nodes_listbox.delete(selection[0])
            self._log(f"Node removed: {node}")
    
    def _open_custom_task_dialog(self):
        """Open custom task creation dialog."""
        dialog = CustomTaskDialog(self.root)
        self.root.wait_window(dialog)
        
        if dialog.task_result:
            self._update_task_list()
            messagebox.showinfo("Success", f"Custom task '{dialog.task_result['task_name']}' created!")
            self._log(f"Custom task registered: {dialog.task_result['task_name']}")
    
    def _execute_task(self):
        """Execute selected task."""
        if not self.current_task:
            messagebox.showerror("Selection Error", "Please select a task first")
            return
        
        nodes = list(self.nodes_listbox.get(0, tk.END))
        if not nodes:
            messagebox.showerror("Configuration Error", "No worker nodes configured")
            return
        
        # Build payload
        payload = {"chunk_size": int(self.chunk_size_var.get())}
        
        if self.current_task == "range_sum":
            payload["start"] = int(self.range_start_var.get())
            payload["end"] = int(self.range_end_var.get())
        elif self.current_task == "array_sum":
            numbers_str = self.array_numbers_var.get()
            payload["numbers"] = [int(x.strip()) for x in numbers_str.split(",")]
        
        # Disable execute button
        self.execute_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress_var.set(0)
        self.results_text.delete("1.0", tk.END)
        
        self._log(f"Starting execution of task: {self.current_task}")
        self._log(f"Nodes: {', '.join(nodes)}")
        self._log(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Create worker
        self.current_worker = TaskExecutionWorker(
            self.current_task, payload, nodes,
            self._update_progress, self._execution_complete
        )
        self.current_worker.start()
    
    def _stop_execution(self):
        """Stop task execution."""
        if self.current_worker:
            self.current_worker.stop()
            self._log("Execution stopped by user")
            self.execute_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
    
    def _update_progress(self, progress: float):
        """Update progress bar."""
        self.progress_var.set(progress * 100)
        self.progress_label.config(text=f"{int(progress * 100)}%")
        self.root.update_idletasks()
    
    def _execution_complete(self, success: bool, result):
        """Handle task execution completion."""
        self.execute_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        
        if success:
            self._log("Task execution completed successfully")
            self.results_text.insert("1.0", json.dumps(result, indent=2))
            self.execution_results = result
            messagebox.showinfo("Success", "Task execution completed!")
        else:
            self._log(f"Task execution failed: {result}")
            messagebox.showerror("Execution Error", f"Task failed:\n{result}")
        
        self.progress_var.set(100)
    
    def _export_results(self):
        """Export results to JSON file."""
        if not self.execution_results:
            messagebox.showwarning("Export Error", "No results to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, "w") as f:
                    json.dump(self.execution_results, f, indent=2)
                messagebox.showinfo("Success", f"Results exported to {file_path}")
                self._log(f"Results exported to: {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {str(e)}")


def main():
    """Main entry point."""
    root = tk.Tk()
    gui = DistributedComputingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
