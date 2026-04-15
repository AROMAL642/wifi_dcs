# Quick Reference: Parameter Extraction Feature

## What Changed?

The GUI now **automatically detects parameters** from custom task code and creates input fields.

## For Users

### Creating a Custom Task
```python
def executor(payload, progress_cb):
    # Parameters auto-detected from these patterns:
    learning_rate = payload.get("learning_rate", 0.001)
    batch_size = payload.get("batch_size", 32)
    epochs = payload.get("epochs", 10)
    
    # Do work...
    progress_cb(1.0)
    return {"status": "success"}
```

**Result:** GUI automatically shows:
```
Parameters: batch_size, epochs, learning_rate
```

### Executing a Custom Task
1. Select task from task list
2. **Configuration section auto-generates input fields**
3. Fill in parameter values
4. Click Execute

## For Developers

### Modified Functions

| File | Function | Change |
|------|----------|--------|
| `master_gui.py` | `extract_payload_keys()` | NEW - Regex extraction |
| `master_gui.py` | `CustomTaskDialog._on_executor_change()` | NEW - Live parameter detection |
| `master_gui.py` | `_create_config_tab()` | Modified - Dynamic fields |
| `master_gui.py` | `_on_task_select()` | Modified - Parameter extraction |
| `master_gui.py` | `_execute_task()` | Modified - Dynamic payload building |
| `master_gui.py` | `_create_parameter_fields()` | NEW - Field generation |
| `master_gui.py` | `_clear_parameter_fields()` | NEW - Cleanup |
| `tasks.py` | `get_task_info()` | Modified - Returns executor_code |
| `custom_task_registry.py` | `save_custom_task()` | Modified - Stores parameters |

### Code Examples

#### Extract parameters from code:
```python
from module4_ui.master_gui import extract_payload_keys

code = """
def executor(payload, progress_cb):
    x = payload.get("param1")
    y = payload["param2"]
    return {}
"""

params = extract_payload_keys(code)
# Result: ['param1', 'param2']
```

#### Get task info with parameters:
```python
from module3_execution.tasks import get_task_info

info = get_task_info("custom_task_name")
# Returns:
# {
#   "executor": <function>,
#   "aggregator": <function>,
#   "executor_code": "...",
#   "parameters": ["param1", "param2"],
#   "description": "..."
# }
```

#### Save custom task with parameters:
```python
from custom_task_registry import save_custom_task

save_custom_task(
    task_name="my_task",
    executor_code="...",
    aggregator_code="...",
    description="My task",
    parameters=["param1", "param2"]
)
```

## Detection Patterns

✅ Works:
- `payload.get("name")`
- `payload.get('name')`
- `payload["name"]`
- `payload['name']`
- `payload .get( "name" )`
- `# Parameters: name1, name2`

❌ Doesn't work:
- `p = payload; p.get("name")`
- `d = {"data": payload}; d["data"].get("name")`
- Complex variable references

## Parameter Types

Auto-converts based on input:
- `"123"` → `123` (int)
- `"3.14"` → `3.14` (float)
- `"1,2,3"` → `[1, 2, 3]` (list)
- `"text"` → `"text"` (string)

## Testing

```bash
python3 test_param_extraction.py
```

Tests extraction patterns:
1. Basic `payload.get()` calls
2. Array access `payload[]`
3. Mixed patterns
4. Complete ML task example

## Files to Check

- ✅ `module4_ui/master_gui.py` - Main GUI implementation
- ✅ `custom_task_registry.py` - Parameter persistence
- ✅ `module3_execution/tasks.py` - Parameter retrieval
- ✅ `test_param_extraction.py` - Test suite
- ✅ Documentation files created

## Syntax Check

All modified files compile without errors:
```bash
python3 -m py_compile \
  module4_ui/master_gui.py \
  custom_task_registry.py \
  module3_execution/tasks.py
```

Result: ✅ All files compile successfully

---

**No need to manually configure parameters!** Just write code with `payload.get()` and the GUI does the rest.
