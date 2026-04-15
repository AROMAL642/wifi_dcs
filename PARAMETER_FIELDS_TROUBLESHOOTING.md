# Troubleshooting: Parameter Input Fields Not Showing

## Issue Description
When selecting a custom task, the Configuration section doesn't show input textboxes for parameters.

## Root Cause
The parameter fields need to be explicitly created when a task is selected. The issue was likely:
1. Placeholder label not being cleared
2. Parameter frame not properly initialized
3. Task info not returning executor code

## Solution Implemented

### 1. Fixed Parameter Frame Initialization
The `_create_config_tab()` was simplified:

**Before (Complex with canvas):**
```python
canvas = tk.Canvas(self.param_frame_wrapper, ...)
scrollbar = ttk.Scrollbar(...)
scrollable_frame = tk.Frame(canvas, ...)
# ... complex setup ...
self.param_frame_wrapper = scrollable_frame
```

**After (Simple direct frame):**
```python
self.param_frame_wrapper = tk.LabelFrame(parent, text="Task Parameters...", bg="white")
self.param_frame_wrapper.pack(padx=10, pady=10, fill="both", expand=True)

self.param_placeholder = tk.Label(self.param_frame_wrapper, text="(Select a task...)")
self.param_placeholder.pack()

self.param_entries = {}
```

### 2. Added Placeholder Clearing
The `_create_parameter_fields()` now clears ALL widgets:

```python
def _create_parameter_fields(self, params: List[str], defaults: Dict):
    # Clear all existing widgets including placeholder
    for child in self.param_frame_wrapper.winfo_children():
        child.destroy()  # ← This removes the "(Select a task...)" label
    
    self.param_entries = {}
    
    if not params:
        tk.Label(..., text="(No parameters for this task)").pack()
        return
    
    # Create fresh parameter fields
    for param_name in params:
        frame = tk.Frame(self.param_frame_wrapper, bg="white")
        frame.pack(fill="x", padx=5, pady=3)
        
        label = tk.Label(frame, text=f"{param_name}:", width=20, ...)
        label.pack(side="left", padx=5)
        
        entry = tk.Entry(frame, width=40, ...)  # ← Textbox created here
        entry.pack(side="left", padx=5, fill="x", expand=True)
        
        self.param_entries[param_name] = entry
```

### 3. Enhanced Task Info Retrieval
The `get_task_info()` now loads executor code:

```python
def get_task_info(task_name: str) -> Optional[Dict]:
    # ... load custom task from registry ...
    return {
        "executor": ...,
        "aggregator": ...,
        "executor_code": task_data.get("executor_code", ""),  # ← Now returns this
        "aggregator_code": ...,
        "description": ...,
        "parameters": task_data.get("parameters", [])
    }
```

## Verification Steps

### Step 1: Create a Custom Task
```
1. Click "Create Custom Task"
2. Enter code:
   def executor(payload, progress_cb):
       name = payload.get("name")
       age = payload.get("age")
       return {"done": True}
   
   def aggregator(results):
       return {"total": len(results)}

3. Dialog shows: "Parameters: name, age" ✓
4. Click "Register Task"
```

### Step 2: Select the Task
```
1. Select task from list: "my_task"
2. Configuration tab shows:
   
   Selected Task: my_task
   Parameters: name, age
   
   Task Parameters (Auto-generated from code)
   ──────────────────────────────────
   name: [____________]  ← Textbox shows here
   age:  [____________]  ← Textbox shows here
```

### Step 3: Fill and Execute
```
1. Enter values:
   name: [John]
   age:  [30]

2. Click "Execute Task"
3. Logs show: 
   Payload: {"name": "John", "age": 30}
```

## If Fields Still Don't Show

### Debug Step 1: Check Registry File
```bash
cat /home/aromal/Desktop/MAIN_PROJECT_FINAL/custom_tasks_registry.json
```

Should show:
```json
{
  "my_task": {
    "executor_code": "def executor(payload, progress_cb):\n    ...",
    "aggregator_code": "...",
    "description": "...",
    "parameters": ["name", "age"]
  }
}
```

### Debug Step 2: Check Parameter Extraction
Run test in Python:
```python
import sys
sys.path.insert(0, '/home/aromal/Desktop/MAIN_PROJECT_FINAL')

from module4_ui.master_gui import extract_payload_keys

code = """
def executor(payload, progress_cb):
    name = payload.get("name")
    age = payload.get("age")
    return {"done": True}
"""

params = extract_payload_keys(code)
print("Detected parameters:", params)
# Should print: Detected parameters: ['age', 'name']
```

### Debug Step 3: Check Executor Code Loading
```python
from module3_execution.tasks import get_task_info

info = get_task_info("my_task")
print("Task info:", info)
print("Has executor_code:", "executor_code" in info)
print("Parameters:", info.get("parameters", []))
```

### Debug Step 4: Check Frame Creation
Open `module4_ui/master_gui.py` and verify:
1. `_create_config_tab()` creates `param_frame_wrapper`
2. `_on_task_select()` calls `_create_parameter_fields()`
3. `_create_parameter_fields()` destroys old widgets and creates entries

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Placeholder text shows, no fields | Parameters not detected | Check executor code has `payload.get()` |
| Old fields don't disappear | Widgets not destroyed | Verify `destroy()` loop in `_create_parameter_fields()` |
| Fields appear but empty | Entry widgets created but not filled | Verify `entry.insert()` is called |
| No entry fields at all | `param_entries` dict not populated | Check `entry` creation loop |
| Fields visible but wrong size | Layout not configured | Verify `pack(fill="x", expand=True)` |

## Testing Checklist

- [ ] Create custom task with `payload.get("param")` code
- [ ] See "Parameters: param" in dialog
- [ ] Register task successfully
- [ ] Select task from list
- [ ] Textboxes appear with parameter labels
- [ ] Can type into textboxes
- [ ] Default values show (if specified)
- [ ] Execute task with filled values
- [ ] Logs show correct payload

## What Fields Should Look Like

### Good ✅
```
Configuration Tab:
────────────────────────────────────
Selected Task: image_processor
Description: Process images with filters

Parameters: image_path, width, height

Task Parameters (Auto-generated from code)
────────────────────────────────────────────
image_path: [/path/to/image.jpg________]
width:      [1920_____________________]
height:     [1080_____________________]
```

### Bad ❌
```
Configuration Tab:
────────────────────────────────────
Selected Task: image_processor

Task Parameters (Auto-generated from code)
(Select a task to see parameters)  ← Placeholder still showing
← No textboxes visible!
```

## Force Clear & Reset

If fields are stuck, try:

1. **Restart GUI:**
   ```bash
   pkill -f master_gui.py
   python3 -m module4_ui.master_gui
   ```

2. **Clear cache:**
   ```bash
   rm -rf /home/aromal/Desktop/MAIN_PROJECT_FINAL/__pycache__/
   rm -rf /home/aromal/Desktop/MAIN_PROJECT_FINAL/module4_ui/__pycache__/
   ```

3. **Verify registry:**
   ```bash
   cat /home/aromal/Desktop/MAIN_PROJECT_FINAL/custom_tasks_registry.json
   ```

## Support

If textboxes still don't appear after these steps:

1. Check syntax: `python3 -m py_compile module4_ui/master_gui.py`
2. Check imports: Verify all modules load correctly
3. Check logs: Run GUI in terminal to see error messages
4. Check registry: Verify custom tasks are saved properly

