#!/usr/bin/env python3
"""
Simple web UI (Flask) to control the distributed framework.
- Choose role: master or worker (slave)
- Start a worker on this machine (exposes UDP 5555 + TCP task port)
- Run a master task (range_sum or array_sum) using existing Module 3 logic

Note: This UI is a thin wrapper over the existing master/worker classes and is
intended for lab/demo use. It runs tasks in background threads; stop/cleanup is
minimal.
"""

import threading
import os
import sys
import json
from typing import List, Optional
from flask import Flask, request, render_template_string, redirect, url_for, flash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Add discovery path
DISCOVERY_DIR = os.path.join(BASE_DIR, "module1_discovery")
if DISCOVERY_DIR not in sys.path:
    sys.path.insert(0, DISCOVERY_DIR)

from module3_execution.worker import WorkerServer
from module3_execution.master import MasterOrchestrator, parse_nodes
from module3_execution.tasks import SUPPORTED_TASKS

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # for flash messages

# Global state (simple demo; not for production)
running_worker = {"server": None, "thread": None}


HOME_TEMPLATE = """
<!doctype html>
<title>Distributed Framework UI</title>
<h2>Distributed Framework UI</h2>
<p>Select role for this machine:</p>
<ul>
  <li><a href="{{ url_for('worker_form') }}">Start as Worker (Slave)</a></li>
  <li><a href="{{ url_for('master_form') }}">Run a Master Task</a></li>
</ul>
"""

WORKER_TEMPLATE = """
<!doctype html>
<title>Start Worker</title>
<h3>Start Worker (Slave)</h3>
<form method="post">
  Name: <input name="name" value="{{ default_name }}"/><br/>
  TCP Task Port: <input name="port" type="number" value="6000"/><br/>
  <button type="submit">Start Worker</button>
</form>
<p><a href="{{ url_for('home') }}">Back</a></p>
"""

MASTER_TEMPLATE = """
<!doctype html>
<title>Run Master Task</title>
<h3>Run Master Task</h3>
<form method="post">
  Task:
  <select name="task">
    {% for t in tasks %}
    <option value="{{t}}">{{t}}</option>
    {% endfor %}
  </select><br/>
  Range start (for range_sum): <input name="start" type="number" value="1"/><br/>
  Range end (for range_sum): <input name="end" type="number" value="100000"/><br/>
  Chunk size: <input name="chunk_size" type="number" value="50000"/><br/>
  Numbers (for array_sum, comma-separated): <input name="numbers"/><br/>
  Nodes (comma-separated ip[:port], leave blank to auto-discover):<br/>
  <input name="nodes" style="width:320px"/><br/>
  Discover timeout (sec): <input name="discover_timeout" type="number" value="6"/><br/>
  <button type="submit">Run</button>
</form>
<p><a href="{{ url_for('home') }}">Back</a></p>
"""

RESULT_TEMPLATE = """
<!doctype html>
<title>Task Launched</title>
<h3>Task launched in background</h3>
<p>{{ message }}</p>
<p>Check master console logs for progress/result.</p>
<p><a href="{{ url_for('home') }}">Back</a></p>
"""


@app.route("/")
def home():
    return render_template_string(HOME_TEMPLATE)


@app.route("/worker", methods=["GET", "POST"])
def worker_form():
    if request.method == "POST":
        name = request.form.get("name") or None
        port = int(request.form.get("port") or 6000)

        # stop existing worker if any
        if running_worker["server"]:
            flash("A worker is already running; restart the server to change config.")
            return redirect(url_for("home"))

        server = WorkerServer(worker_port=port, node_name=name)
        t = threading.Thread(target=server.start, daemon=True)
        t.start()
        running_worker["server"] = server
        running_worker["thread"] = t
        flash(f"Worker started on port {port} with name {server.node_name}")
        return redirect(url_for("home"))

    default_name = os.uname().nodename
    return render_template_string(WORKER_TEMPLATE, default_name=default_name)


@app.route("/master", methods=["GET", "POST"])
def master_form():
    if request.method == "POST":
        task = request.form.get("task", "range_sum")
        start = int(request.form.get("start") or 1)
        end = int(request.form.get("end") or 100000)
        chunk_size = int(request.form.get("chunk_size") or 50000)
        numbers_raw = request.form.get("numbers") or ""
        nodes_raw = request.form.get("nodes") or ""
        discover_timeout = int(request.form.get("discover_timeout") or 6)

        master = MasterOrchestrator(discover_timeout=discover_timeout)

        if nodes_raw.strip():
            workers = parse_nodes(nodes_raw.strip())
            message = f"Using manual workers: {workers}"
        else:
            print("🔍 Discovering workers...")
            workers = master.discover_workers()
            message = f"Discovered {len(workers)} workers"

        # Run in background thread to avoid blocking Flask
        def run_task():
            if task == "range_sum":
                master.run_range_sum(start, end, chunk_size, workers)
            elif task == "array_sum":
                try:
                    nums = [int(x.strip()) for x in numbers_raw.split(',') if x.strip()]
                except ValueError:
                    print("Invalid numbers input")
                    return
                master.run_array_sum(nums, chunk_size, workers)

        threading.Thread(target=run_task, daemon=True).start()

        return render_template_string(RESULT_TEMPLATE, message=message)

    return render_template_string(MASTER_TEMPLATE, tasks=SUPPORTED_TASKS.keys())


if __name__ == "__main__":
    # For quick local run
    app.run(host="0.0.0.0", port=7000, debug=False)
