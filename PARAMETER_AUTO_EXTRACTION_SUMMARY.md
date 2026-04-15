# Framework GUI Auto Parameter Extraction - Implementation Summary

## Overview
Modified the framework GUI to **automatically extract required parameters from custom task executor code** and dynamically generate input fields in the Configuration section.

## Changes Made

### 1. **module4_ui/master_gui.py** - Main GUI Module
#### Added Imports
```python
import inspect  # For function signature inspection
```

#### New Utility Functions

**`extract_parameters_from_code(code: str) -> List[str]`**
- Extracts parameter names from executor function code
- Removes standard parameters (`payload`, `progress_cb`)
- Falls back to extracting from payload.get() calls

**`extract_payload_keys(code: str) -> List[str]`**
- Uses regex patterns to find payload parameter keys
- Patterns:
  - `payload.get("key_name")`
  - `payload["key_name"]`
  - Comments mentioning parameter names

#### Enhanced CustomTaskDialog Class
**New Features:**
- Real-time parameter detection as user types executor code
- `_on_executor_change()` method triggers on every keystroke
- Shows detected parameters in the dialog
- Parameters are saved with task registration via `save_custom_task()`

**Updated `_register_task()` method:**
```python
# Extract parameters and save with task
params = extract_payload_keys(executor_code)
save_custom_task(task_name, executor_code, aggregator_code, description, params)
```

#### Enhanced MasterGUI Configuration Tab
**`_create_config_tab(parent)`:**
- Simplified parameter frame (removed complex canvas structure)
- Placeholder label: "(Select a task to see parameters)"
- Dynamic parameter fields generated on task selection

**`_on_task_select(event)`:**
- Extracts task info including executor code
- Calls `extract_payload_keys()` to get parameters
- Dynamically creates parameter input fields
- Shows parameters in config text area

**`_create_parameter_fields(params, defaults)`:**
- Clears previous parameter widgets
- Creates labeled input fields for each parameter
- Sets default values if available
- Stores references in `self.param_entries` dict

#### Updated Task Execution
**`_execute_task()` method:**
- Collects values from dynamically created parameter entries
- Auto-converts types: int, float, comma-separated lists
- Builds payload from parameter entries
- Error handling for missing/invalid parameters

### 2. **custom_task_registry.py** - Task Registry
#### Updated Function
**`save_custom_task()`:**
```python
def save_custom_task(task_name: str, executor_code: str, aggregator_code: str, 
                     description: str = "", parameters: list = None)
```
- Now accepts and stores `parameters` list
- Stores in JSON: `"parameters": [list of param names]`

### 3. **module3_execution/tasks.py** - Task Management
#### Enhanced Function
**`get_task_info(task_name: str) -> Optional[Dict]`:**
- Loads executor code from custom task registry
- Returns task metadata including:
  - `executor_code`: Full Python code
  - `aggregator_code`: Full Python code
  - `description`: Task description
  - `parameters`: List of required parameters

## Workflow

### Creating a Custom Task
1. **User opens "Create Custom Task" dialog**
2. **Types executor code with payload parameters:**
   ```python
   def executor(payload, progress_cb):
       dataset_files = payload.get("dataset_files")
       model_type = payload.get("model_type")
       epochs = payload.get("epochs", 10)
       # ...
   ```
3. **Dialog detects and displays parameters:**
   - "Parameters: dataset_files, model_type, epochs"
4. **User clicks "Register Task"**
5. **Task saved with parameter metadata:**
   ```json
   {
     "task_name": {
       "executor_code": "...",
       "aggregator_code": "...",
       "description": "...",
       "parameters": ["dataset_files", "model_type", "epochs"]
     }
   }
   ```

### Executing a Custom Task
1. **User selects custom task from task list**
2. **System extracts parameters from executor code:**
   - Loads code from registry
   - Runs regex patterns to find payload.get() calls
   - Generates input fields
3. **Configuration tab shows:**
   ```
   Selected Task: ml_training
   Description: ML model training with datasets
   Parameters: dataset_files, model_type, epochs
   ```
4. **Parameter input fields appear:**
   ```
   dataset_files: [____________]
   model_type:    [____________]
   epochs:        [____________]
   ```
5. **User enters values and executes**
6. **System builds payload and sends to workers**

## Parameter Detection Methods

### Method 1: Regex Pattern Matching
Searches for common payload access patterns:
```python
payload.get("param_name")
payload["param_name"]
```

### Method 2: Code Comments
Extracts parameter names from comments (fallback):
```python
# dataset_files, numbers, model_type
```

### Method 3: Function Signature
Inspects executor function parameters (last resort):
```python
def executor(payload, progress_cb):  # Only "payload" and "progress_cb" expected
```

## Example: Custom Task with Auto-Detection

### Input Code
```python
def executor(payload, progress_cb):
    dataset = payload.get("dataset_path")
    batch_size = payload.get("batch_size", 32)
    learning_rate = payload.get("learning_rate", 0.001)
    
    result = {"status": "success"}
    progress_cb(1.0)
    return result
```

### Auto-Detected Parameters
```
Parameters: dataset_path, batch_size, learning_rate
```

### Generated UI
```
Configuration Tab:
─────────────────────────────────────
Selected Task: ml_training

Parameters: dataset_path, batch_size, learning_rate

Task Parameters (Auto-generated from code)
─────────────────────────────────────
dataset_path:   [__________]
batch_size:     [32________]
learning_rate:  [0.001_____]
```

## Type Conversion

Parameter values are automatically converted based on format:
- **Integer**: `"123"` → `123`
- **Float**: `"0.5"` → `0.5`
- **List**: `"1,2,3"` → `[1, 2, 3]`
- **String**: `"text"` → `"text"` (default)

## Files Modified

| File | Changes |
|------|---------|
| `module4_ui/master_gui.py` | Added parameter extraction utilities, enhanced dialogs, dynamic UI generation |
| `custom_task_registry.py` | Updated to store parameter metadata |
| `module3_execution/tasks.py` | Enhanced get_task_info() to return executor code and parameters |

## Benefits

✅ **Automatic Parameter Detection** - No manual configuration needed  
✅ **User-Friendly UI** - Intuitive input fields appear automatically  
✅ **Type Conversion** - Values converted to appropriate Python types  
✅ **Built-in & Custom Tasks** - Works with both task types  
✅ **Flexible Detection** - Multiple fallback methods for robustness  
✅ **Real-time Feedback** - Shows detected parameters as user types code  

## Testing

To test the feature:

1. **Create a custom task:**
   - Click "Create Custom Task"
   - Enter executor code with payload.get() calls
   - Observe parameters detected automatically

2. **Execute custom task:**
   - Select task from list
   - Verify parameter fields appear
   - Fill in values and execute

3. **Try different parameter formats:**
   - Single values: `100`
   - Floating point: `0.5`
   - Lists: `1,2,3,4,5`
   - Text: `model_v1.pkl`
