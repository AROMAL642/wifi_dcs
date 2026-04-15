# Code Changes Summary - Auto Parameter Extraction

## Files Modified

### 1. module4_ui/master_gui.py

#### Added Imports
```python
import inspect  # For function signature inspection
```

#### New Functions Added

**Function 1: extract_parameters_from_code()**
```python
def extract_parameters_from_code(code: str) -> List[str]:
    """Extract parameter names from executor function code."""
    try:
        namespace = {}
        exec(code, namespace)
        executor_func = namespace.get("executor")
        
        if not executor_func:
            return []
        
        # Get function signature
        sig = inspect.signature(executor_func)
        params = list(sig.parameters.keys())
        
        # Remove 'payload' and 'progress_cb' (these are standard)
        required_params = [p for p in params if p not in ['payload', 'progress_cb']]
        
        # Try to extract from payload keys in docstring or code
        extracted_from_code = extract_payload_keys(code)
        return extracted_from_code if extracted_from_code else required_params
    except Exception as e:
        return []
```

**Function 2: extract_payload_keys()**
```python
def extract_payload_keys(code: str) -> List[str]:
    """Extract payload parameter keys from executor code."""
    import re
    keys = set()
    
    # Pattern 1: payload.get("key_name")
    pattern1 = r'payload\.get\(["\']([^"\']+)["\']\)'
    matches = re.findall(pattern1, code)
    keys.update(matches)
    
    # Pattern 2: payload["key_name"]
    pattern2 = r'payload\[["\']([^"\']+)["\']\]'
    matches = re.findall(pattern2, code)
    keys.update(matches)
    
    # Pattern 3: In comments like # dataset_files, numbers, etc.
    pattern3 = r'#.*?([a-z_][a-z0-9_]*)'
    matches = re.findall(pattern3, code.lower())
    # Filter to reasonable looking parameter names
    keys.update([m for m in matches if len(m) > 2 and not m.isdigit()])
    
    return sorted(list(keys))
```

#### Modified Classes

**CustomTaskDialog Changes:**

1. **Increased window size:** `700x600` → `900x700`

2. **Added executor code event binding:**
   ```python
   self.executor_text.bind("<<Change>>", self._on_executor_change)
   self.executor_text.bind("<KeyRelease>", self._on_executor_change)
   ```

3. **Added parameter display section:**
   ```python
   tk.Label(self, text="Detected Parameters:", font=("Arial", 10, "bold")).grid(...)
   self.params_frame = tk.Frame(self)
   self.params_label = tk.Label(self.params_frame, text="(Parameters will auto-detect...)")
   ```

4. **New method: _on_executor_change()**
   ```python
   def _on_executor_change(self, event=None):
       """Auto-extract parameters when executor code changes."""
       executor_code = self.executor_text.get("1.0", tk.END).strip()
       params = extract_payload_keys(executor_code)
       if params:
           self.params_label.config(text=f"Parameters: {', '.join(params)}", fg="#2196F3")
       else:
           self.params_label.config(text="(No parameters detected in code)", fg="#666666")
   ```

5. **Updated _register_task():**
   ```python
   # Extract parameters for storage
   params = extract_payload_keys(executor_code)
   
   # Save to shared registry with parameters
   save_custom_task(task_name, executor_code, aggregator_code, description, params)
   ```

**MasterGUI Configuration Tab Changes:**

1. **Replaced _create_config_tab():**
   - Removed static parameter fields
   - Added dynamic parameter frame with scrolling support
   - Added placeholder label

2. **New method: _clear_parameter_fields()**
   ```python
   def _clear_parameter_fields(self):
       """Clear previously created parameter fields."""
       if hasattr(self, 'param_entries'):
           for widget in self.param_entries.values():
               if widget:
                   widget.destroy()
           self.param_entries.clear()
   ```

3. **New method: _create_parameter_fields()**
   ```python
   def _create_parameter_fields(self, params: List[str], defaults: Dict):
       """Dynamically create input fields for task parameters."""
       # Clears all existing widgets
       for child in self.param_frame_wrapper.winfo_children():
           child.destroy()
       
       # Creates labeled entry fields for each parameter
       for param_name in params:
           frame = tk.Frame(self.param_frame_wrapper, bg="white")
           frame.pack(fill="x", padx=5, pady=3)
           
           label = tk.Label(frame, text=f"{param_name}:", width=20, ...)
           label.pack(side="left", padx=5)
           
           entry = tk.Entry(frame, width=40, ...)
           entry.pack(side="left", padx=5, fill="x", expand=True)
           
           self.param_entries[param_name] = entry
   ```

4. **Updated _on_task_select():**
   ```python
   def _on_task_select(self, event):
       # ... existing code ...
       
       # NEW: Clear and recreate parameter fields
       self._clear_parameter_fields()
       
       task_info = get_task_info(self.current_task)
       if task_info and task_info.get("executor_code"):
           executor_code = task_info["executor_code"]
           params = extract_payload_keys(executor_code)
           if params:
               self.config_text.insert(tk.END, f"Parameters: {', '.join(params)}\n\n")
               self._create_parameter_fields(params, task_info.get("parameters", {}))
       elif self.current_task == "range_sum":
           self._create_parameter_fields(["start", "end", "chunk_size"], {})
       elif self.current_task == "array_sum":
           self._create_parameter_fields(["numbers", "chunk_size"], {})
   ```

5. **Completely rewrote _execute_task():**
   ```python
   def _execute_task(self):
       # ... validation ...
       
       # NEW: Build payload from dynamic parameter entries
       payload = {}
       for param_name, entry_widget in self.param_entries.items():
           value = entry_widget.get().strip()
           
           # NEW: Type conversion
           if value.isdigit():
               payload[param_name] = int(value)
           elif '.' in value:
               payload[param_name] = float(value)
           elif ',' in value:
               try:
                   payload[param_name] = [int(x.strip()) for x in value.split(",")]
               except ValueError:
                   payload[param_name] = [x.strip() for x in value.split(",")]
           else:
               payload[param_name] = value
       
       # ... rest of execution ...
   ```

---

### 2. custom_task_registry.py

#### Function Signature Change

**Before:**
```python
def save_custom_task(task_name: str, executor_code: str, 
                     aggregator_code: str, description: str = ""):
```

**After:**
```python
def save_custom_task(task_name: str, executor_code: str, 
                     aggregator_code: str, description: str = "", 
                     parameters: list = None):
```

#### Implementation Change

**Before:**
```python
registry[task_name] = {
    "executor_code": executor_code,
    "aggregator_code": aggregator_code,
    "description": description
}
```

**After:**
```python
registry[task_name] = {
    "executor_code": executor_code,
    "aggregator_code": aggregator_code,
    "description": description,
    "parameters": parameters or []
}
```

---

### 3. module3_execution/tasks.py

#### Enhanced get_task_info() Function

**Before:**
```python
def get_task_info(task_name: str) -> Optional[Dict]:
    """Get information about a specific task."""
    if task_name in SUPPORTED_TASKS:
        return SUPPORTED_TASKS[task_name]
    
    task_info = {
        "executor": _custom_registry.get_executor(task_name),
        "aggregator": _custom_registry.get_aggregator(task_name),
    }
    return task_info if task_info["executor"] else None
```

**After:**
```python
def get_task_info(task_name: str) -> Optional[Dict]:
    """Get information about a specific task, including executor code for custom tasks."""
    if task_name in SUPPORTED_TASKS:
        return SUPPORTED_TASKS[task_name]
    
    # For custom tasks, try to load from registry
    try:
        from pathlib import Path
        import json
        
        registry_file = Path(__file__).parent.parent / "custom_tasks_registry.json"
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                registry = json.load(f)
                if task_name in registry:
                    task_data = registry[task_name]
                    return {
                        "executor": _custom_registry.get_executor(task_name),
                        "aggregator": _custom_registry.get_aggregator(task_name),
                        "executor_code": task_data.get("executor_code", ""),
                        "aggregator_code": task_data.get("aggregator_code", ""),
                        "description": task_data.get("description", ""),
                        "parameters": task_data.get("parameters", [])
                    }
    except Exception as e:
        pass
    
    task_info = {
        "executor": _custom_registry.get_executor(task_name),
        "aggregator": _custom_registry.get_aggregator(task_name),
    }
    return task_info if task_info["executor"] else None
```

---

## Data Structure Changes

### Custom Task Registry JSON

**Before:**
```json
{
  "task_name": {
    "executor_code": "...",
    "aggregator_code": "...",
    "description": "..."
  }
}
```

**After:**
```json
{
  "task_name": {
    "executor_code": "...",
    "aggregator_code": "...",
    "description": "...",
    "parameters": ["param1", "param2", "param3"]
  }
}
```

---

## Summary of Changes

| Component | Change Type | Impact |
|-----------|-------------|--------|
| **Imports** | Added | `inspect` module for function signatures |
| **Functions** | Added 2 | `extract_parameters_from_code()`, `extract_payload_keys()` |
| **CustomTaskDialog** | Enhanced | Real-time parameter detection |
| **MasterGUI** | Enhanced | Dynamic parameter field generation |
| **Registry** | Enhanced | Stores parameter metadata |
| **Task Info** | Enhanced | Returns executor code and parameters |
| **Payload Building** | Rewritten | Builds from dynamic entries with type conversion |

---

## Backward Compatibility

✅ **Fully backward compatible:**
- Old tasks without parameters still work
- Optional `parameters` argument defaults to `None`
- `get_task_info()` handles missing fields gracefully
- Built-in tasks (range_sum, array_sum) unaffected

---

## Total Lines Changed

- **master_gui.py**: ~100 lines added/modified
- **custom_task_registry.py**: 5 lines modified
- **tasks.py**: 15 lines modified

**Total**: ~120 lines of code changes
