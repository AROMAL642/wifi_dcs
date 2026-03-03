# Module 4: Web UI (Flask)

A minimal Flask UI to control the distributed framework.
- Choose this machine’s role: **Worker (slave)** or **Master**.
- Start a worker (UDP discovery + TCP task port) on this machine.
- Run a master task (range_sum or array_sum) against discovered or specified workers.

## Install deps
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
pip install -r module4_ui/requirements.txt
```

## Run the UI
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL
python3 module4_ui/app.py
```
Opens on http://0.0.0.0:7000

## Usage
- **Start Worker**: set name/port and launch. Worker replies to UDP 5555 and listens on TCP task port (default 6000).
- **Run Master Task**: pick `range_sum` or `array_sum`, set parameters, optionally list workers (`ip[:port]` comma-separated). If no nodes provided, it auto-discovers.
- Progress/result logs appear in the master process console.

## Notes
- Uses existing Module 3 classes (`MasterOrchestrator`, `WorkerServer`).
- Retries and dynamic chunking are handled by the master logic (already implemented).
- This is a demo UI; stop/cleanup of workers is minimal (restart process to reset).
