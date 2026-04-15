# Automatic Parameter Extraction from Custom Tasks

## Overview
The GUI framework has been modified to automatically extract required parameters from custom task executor code and dynamically populate the configuration section during task definition and execution.

## Changes Made

### 1. **module4_ui/master_gui.py**

#### New Utility Functions:
- `extract_parameters_from_code(code: str) -> List[str]`
  - Extracts parameter names from executor function signature
  - Removes standard parameters (payload, progress_cb)

- `extract_payload_keys(code: str) -> List[str]`
  - Uses regex patterns to find parameters accessed in code:
    - Pattern: `payload.get("param_name")`
    - Pattern: `payload["param_name"]`
    - Pattern: Comments with parameter names
  - Returns sorted list of unique parameter names

#### Enhanced CustomTaskDialog:
- Added **"Detected Parameters"** section
- Real-time parameter extraction on code change
- Parameters update as user types executor code
- Shows detected parameters with blue highlighting
- Added `_on_executor_change()` method for live detection

#### Modified _create_config_tab():
- Replaced static parameter fields with dynamic parameter frame
- Added scrollable canvas for unlimited parameters
- Parameters now auto-generate based on selected task
- Works for both built-in and custom tasks

#### Enhanced _on_task_select():
- Extracts parameters from executor code
- Creates dynamic input fields for each parameter
- Shows parameter list in configuration text
- Calls `_create_parameter_fields()` to build UI

#### New Helper Methods:
- `_clear_parameter_fields()` - Clears previous parameter widgets
- `_create_parameter_fields()` - Dynamically creates input entry fields

#### Updated _execute_task():
- Collects parameters from dynamic entry fields instead of hardcoded variables
- Auto-converts values to appropriate types (int, float, list, string)
- Validates that all parameters are provided
- Builds payload from all parameter entries

### 2. **custom_task_registry.py**

#### Updated save_custom_task():
```python
def save_custom_task(task_name: str, executor_code: str, aggregator_code: str, 
                     description: str = "", parameters: list = None)
```
- Now accepts and stores `parameters` list
- Parameters are persisted in `custom_tasks_registry.json`
- Format: `"parameters": ["param1", "param2", ...]`

### 3. **module3_execution/tasks.py**

#### Enhanced get_task_info():
- Now loads executor code and parameters from custom task registry
- Returns additional fields:
  - `executor_code`: Full executor function code
  - `aggregator_code`: Full aggregator function code
  - `parameters`: List of detected parameters
  - `description`: Task description

## How It Works

### Creating a Custom Task:

1. User opens "Create Custom Task" dialog
2. User writes executor code like:
```python
def executor(payload, progress_cb):
    dataset_files = payload.get("dataset_files")
    model_type = payload.get("model_type", "linear")
    epochs = payload.get("epochs", 10)
    
    # Process files...
    progress_cb(1.0)
    return {"status": "success"}
```

3. **Parameter detection happens automatically** as user types:
   - System finds `payload.get()` calls
   - Extracts: `["dataset_files", "model_type", "epochs"]`
   - Displays in green: "Parameters: dataset_files, model_type, epochs"

4. User registers task → parameters stored with task metadata

### Executing a Custom Task:

1. User selects task from task list
2. Configuration section **auto-populates with parameter input fields**:
   - `dataset_files:` [text input]
   - `model_type:` [text input]
   - `epochs:` [text input]

3. User enters values for each parameter
4. System auto-converts types (int, float, list, string)
5. Payload is built and sent to workers

## Key Features

✅ **Automatic Detection** - No manual parameter configuration needed
✅ **Real-Time Display** - Parameters shown as code is written
✅ **Type Conversion** - Auto-converts values to appropriate types
✅ **Scalable** - Works with any number of parameters
✅ **Backward Compatible** - Built-in tasks still work normally
✅ **Persistent** - Parameters stored with task metadata

## Example Usage

### Custom ML Training Task:
```python
def executor(payload, progress_cb):
    # These parameters auto-detected:
    learning_rate = payload.get("learning_rate", 0.001)
    batch_size = payload.get("batch_size", 32)
    epochs = payload.get("epochs", 10)
    dataset_file = payload.get("dataset_file")
    
    # Training logic...
    for epoch in range(epochs):
        progress_cb(epoch / epochs)
    
    return {"accuracy": 0.95, "loss": 0.05}
```

**Auto-detected parameters shown in GUI:**
```
Parameters: learning_rate, batch_size, epochs, dataset_file
```

**Configuration form generated:**
```
learning_rate: [0.001]
batch_size: [32]
epochs: [10]
dataset_file: [ ]
```

## JSON Storage Format

Custom tasks are stored in `custom_tasks_registry.json`:
```json
{
  "ml_training": {
    "executor_code": "def executor(payload, progress_cb): ...",
    "aggregator_code": "def aggregator(results): ...",
    "description": "ML model training task",
    "parameters": ["learning_rate", "batch_size", "epochs", "dataset_file"]
  }
}
```

## Parameter Extraction Patterns

Supported patterns for parameter detection:
1. `payload.get("param_name")` ✓
2. `payload["param_name"]` ✓
3. Comments like `# param_name` ✓
4. Function signature parameters (excluding standard ones) ✓

## Limitations & Notes

- Parameters must be accessed via `payload.get()` or `payload[]` to be detected
- Multi-word parameters use snake_case: `model_type`, `learning_rate`
- Type conversion is automatic but limited (int, float, list, string)
- Complex nested structures should be handled manually in executor code
- Parameters must have non-empty values before execution

