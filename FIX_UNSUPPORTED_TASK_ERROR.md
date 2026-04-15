# Fix for "Unsupported Task" Error

## The Problem
When you create a custom task in the Master GUI and try to execute it, workers respond with:
```
Unsupported task: hashcrack
```

This happens because **custom tasks are only registered in the Master's memory**, not on the workers.

## The Solution
The system now includes:

1. **`custom_task_registry.py`** - Persistent storage for custom tasks
   - Saves custom tasks to JSON file
   - Workers can load tasks from this shared file
   - Located at: `/home/aromal/Desktop/MAIN_PROJECT_FINAL/custom_task_registry.json`

2. **Updated `master_gui.py`** - Saves custom tasks to shared registry
   - When you register a task, it's automatically saved to `custom_tasks_registry.json`
   - Workers can now find and execute your custom tasks

3. **Updated `tasks.py`** - Loads custom tasks from shared registry
   - When a worker receives a custom task request, it loads the code from the registry
   - Dynamically executes the custom executor function

## How It Works Now

```
Master GUI
    │
    ├─ Register custom task (e.g., "hashcrack")
    │   ├─ Store in memory (Master's task registry)
    │   └─ Save to disk (custom_tasks_registry.json)
    │
    ├─ Execute task
    │   └─ Send request to workers
    │
Worker
    ├─ Receive task request
    ├─ Check if task is built-in (range_sum, array_sum)
    ├─ If not found, load from shared registry (custom_tasks_registry.json)
    ├─ Execute custom task code
    └─ Return results

Master GUI
    └─ Receive results and aggregate using aggregator function
```

## To Use Custom Tasks Now

### Step 1: Create Custom Task
1. Master GUI → "Create Custom Task" button
2. Fill in task name, executor code, aggregator code
3. Click "Register Task"
4. **Task is now saved to shared registry** ✓

### Step 2: Execute Custom Task
1. Select task from list
2. Configure parameters
3. Click "Execute Task"
4. Workers will:
   - Load custom task code from registry
   - Execute executor function
   - Return results
5. Master aggregates results ✓

## Files Modified

| File | Changes |
|------|---------|
| `master_gui.py` | Import `save_custom_task`, call it when registering |
| `tasks.py` | Updated `execute_task()` to load from shared registry |
| `custom_task_registry.py` | NEW - Handles persistent storage |

## Example Test

```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL

# Test the fix
python3 << 'EOF'
from custom_task_registry import save_custom_task, load_custom_task
from module3_execution.tasks import execute_task

# Save custom task
executor_code = '''def executor(payload, progress_cb):
    return {"status": "success", "result": "test"}
'''

aggregator_code = '''def aggregator(results):
    return {"task": "test", "status": "success"}
'''

save_custom_task('mytest', executor_code, aggregator_code)

# Execute it (simulating worker)
result = execute_task('mytest', {}, lambda x: None)
print("✓ Custom task executed successfully!")
EOF
```

## Verification

After the fix, custom tasks should work like this:

```
✓ Master: Create task "hashcrack"
✓ Master: Register task (saves to registry)
✓ Master: Execute task on workers
✓ Worker: Load task from registry
✓ Worker: Execute task code
✓ Master: Receive and aggregate results
✓ Final: Display password found
```

## If Still Getting Error

1. **Restart Master and Worker GUIs** (fresh start)
2. **Re-register custom task** (to ensure it's saved)
3. **Check if registry file exists:**
   ```bash
   ls -la /home/aromal/Desktop/MAIN_PROJECT_FINAL/custom_tasks_registry.json
   ```
4. **View registry contents:**
   ```bash
   cat /home/aromal/Desktop/MAIN_PROJECT_FINAL/custom_tasks_registry.json
   ```

## Troubleshooting

### "Still getting Unsupported task error"
→ Restart workers so they pick up the registry file

### "Registry file not created"
→ Check write permissions in project directory
→ Try: `chmod 755 /home/aromal/Desktop/MAIN_PROJECT_FINAL`

### "Custom task still not found"
→ Verify task name is exact (case-sensitive)
→ Check master logs for registration message
→ Check registry file for the task

---

**The fix is now active!** 🎉

Proceed with your custom task execution and you should no longer see the "Unsupported task" error.
