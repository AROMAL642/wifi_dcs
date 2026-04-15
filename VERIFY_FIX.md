# Verify the Fix Works - Quick Test

## What Was Fixed

**Error:** `✗ Execution failed: Unsupported task: hashcrack`

**Cause:** Workers couldn't find custom tasks registered in Master GUI

**Fix:** Created shared task registry so workers can load custom tasks

---

## Quick Verification (2 minutes)

### Step 1: Check Files Were Created
```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL

# Should exist:
ls -la custom_task_registry.py      # NEW FILE
# custom_task_registry.py                  1.5K

echo "✓ Registry file exists"
```

### Step 2: Test Registry Storage
```bash
python3 << 'EOF'
from custom_task_registry import save_custom_task, load_custom_task

# Save test task
executor = 'def executor(payload, progress_cb):\n    return {"status": "success"}'
aggregator = 'def aggregator(results):\n    return {"status": "success"}'

save_custom_task("test", executor, aggregator)
print("✓ Task saved to registry")

# Load it back
task = load_custom_task("test")
if task and "executor_code" in task:
    print("✓ Task loaded from registry")
else:
    print("✗ Failed to load task")
EOF
```

### Step 3: Full System Test
```bash
python3 << 'EOF'
from module3_execution.tasks import execute_task
from custom_task_registry import save_custom_task

# Save a working custom task
executor_code = '''def executor(payload, progress_cb):
    import hashlib
    target = payload.get("target_hash", "81dc9bdb52d04dc20036dbd8313ed055")
    start = payload.get("start", 0)
    end = payload.get("end", 2500)
    
    for idx, num in enumerate(range(start, end)):
        pwd = str(num).zfill(4)
        h = hashlib.md5(pwd.encode()).hexdigest()
        progress_cb(idx / (end - start))
        if h == target:
            return {"status": "success", "found": True, "password": pwd}
    
    return {"status": "success", "found": False}
'''

aggregator_code = '''def aggregator(results):
    for r in results:
        if r.get("found"):
            return {"status": "success", "found": True, "password": r.get("password")}
    return {"status": "success", "found": False}
'''

# Register task
save_custom_task("hashcrack", executor_code, aggregator_code)
print("✓ Hash crack task saved to registry")

# Execute it
result = execute_task("hashcrack", {
    "target_hash": "81dc9bdb52d04dc20036dbd8313ed055",
    "start": 0,
    "end": 2500
}, lambda x: None)

if result.get("status") == "success":
    print("✓ Custom task executed successfully!")
    print(f"✓ Result: {result}")
else:
    print("✗ Task execution failed")
    print(f"Error: {result}")
EOF
```

---

## Now Test with GUI

### Prerequisites
- All workers stopped (close windows)
- All masters stopped (close windows)

### Test Steps

1. **Start Master GUI**
   ```bash
   cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module4_ui
   python3 gui_launcher.py
   # Select "Master"
   ```

2. **Start 2 Worker GUIs** (in separate terminals)
   ```bash
   cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module4_ui
   python3 gui_launcher.py
   # Select "Worker" (port 6000 for first, 6001 for second)
   ```

3. **Start Services on Workers**
   - Each worker: Click "Start Service" (green button)
   - Wait for logs: `✓ Worker server started`

4. **Create Custom Task in Master**
   - Click "Create Custom Task" button
   - Task Name: `hashcrack`
   - Description: `Crack 4-digit PIN`
   - Paste Executor Code (from CUSTOM_TASK_EXAMPLES.md)
   - Paste Aggregator Code (from CUSTOM_TASK_EXAMPLES.md)
   - Click "Register Task"
   - **Should see:** `Task 'hashcrack' registered!` ✓

5. **Verify Task in Registry**
   ```bash
   cat /home/aromal/Desktop/MAIN_PROJECT_FINAL/custom_tasks_registry.json
   # Should show your "hashcrack" task
   ```

6. **Execute Task in Master**
   - Select `hashcrack` from task list
   - Go to "Execution" tab
   - Click "Execute Task"
   - **Check logs:**
     ```
     [time] Starting: hashcrack
     [time] Sending to 2 node(s): 127.0.0.1:6000, 127.0.0.1:6001
     ✓ Task execution completed successfully
     ```
   - **Expected:** NO MORE `Unsupported task: hashcrack` error! ✓

7. **View Results**
   - Results should show:
     ```json
     {
       "task": "hashcrack",
       "status": "success",
       "found": true,
       "password": "1234",
       "message": "✓ PASSWORD CRACKED: 1234",
       ...
     }
     ```

---

## Success Checklist

- [ ] Registry file exists: `custom_task_registry.py`
- [ ] Can save custom tasks to registry
- [ ] Can load custom tasks from registry
- [ ] Custom task executes without "Unsupported task" error
- [ ] Results are returned and displayed
- [ ] Master aggregates results correctly
- [ ] Can export results to JSON

---

## If Still Getting Error

### Check 1: Registry File Exists
```bash
ls -la /home/aromal/Desktop/MAIN_PROJECT_FINAL/custom_tasks_registry.json
```

### Check 2: Task Saved to Registry
```bash
python3 -c "
from custom_task_registry import load_custom_task
task = load_custom_task('hashcrack')
print('Found:', task is not None and 'executor_code' in task)
"
```

### Check 3: Worker Can Load Task
```bash
python3 << 'EOF'
from module3_execution.tasks import execute_task

# Try executing custom task
try:
    result = execute_task('hashcrack', {"target_hash": "test"}, lambda x: None)
    print("✓ Task executed (or returned error)")
    print("Result:", result)
except ValueError as e:
    print("✗ Task not found:", e)
except Exception as e:
    print("Error:", e)
EOF
```

### Check 4: Restart Everything
```bash
# Kill all GUI processes
pkill -f "gui_launcher.py"
pkill -f "python3"

# Wait 2 seconds
sleep 2

# Start fresh
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module4_ui
python3 gui_launcher.py
```

---

## Verification Success Indicators

✓ Registry file created  
✓ Custom tasks persist in JSON file  
✓ Workers load tasks from registry  
✓ Executor code runs on workers  
✓ Aggregator runs on master  
✓ Results display correctly  
✓ **NO MORE "Unsupported task" error**

---

**The fix is working when you can execute custom tasks without getting "Unsupported task" error!** ✓
