# Auto Parameter Extraction - Quick Reference

## What Changed?

When you define a custom task with executor code like:
```python
def executor(payload, progress_cb):
    name = payload.get("name")
    age = payload.get("age")
    city = payload.get("city")
    return {"processed": True}
```

The system **automatically detects** the parameters (`name`, `age`, `city`) and creates input fields in the Configuration section.

## How It Works

### 1. During Task Creation
```
User Types Code → System Detects Parameters → Shows in Dialog
```

**Example Dialog Output:**
```
Task Name: person_processor
Parameters: name, age, city  ← Auto-detected!
```

### 2. During Task Selection
```
Select Task → System Loads Code → Generates Input Fields
```

**Example Configuration Tab:**
```
Selected Task: person_processor
Parameters: name, age, city

Task Parameters (Auto-generated from code)
──────────────────────────────────
name: [__________]
age:  [__________]
city: [__________]
```

### 3. During Task Execution
```
User Fills Fields → System Builds Payload → Task Executes
```

**Payload sent to workers:**
```json
{
  "name": "John",
  "age": 30,
  "city": "NYC"
}
```

## Detection Methods

The system uses **regex patterns** to find parameters:

| Pattern | Example | Detects |
|---------|---------|---------|
| `payload.get("name")` | `payload.get("name")` | `name` |
| `payload["name"]` | `payload["name"]` | `name` |
| Comments | `# name, age` | `name, age` |

## Code Examples

### ✅ Good - Will Be Detected

```python
def executor(payload, progress_cb):
    # Simple get() calls
    username = payload.get("username")
    password = payload.get("password")
    
    # With defaults
    timeout = payload.get("timeout", 30)
    
    # Dictionary access
    token = payload["api_token"]
    
    return {"authenticated": True}
```

**Detected Parameters:** `username, password, timeout, api_token`

### ❌ Won't Be Detected

```python
def executor(payload, progress_cb):
    # Variable payload parameter name
    param_name = "dynamic_param"
    value = payload.get(param_name)  # Can't detect!
    
    # Indirect access
    params = payload
    result = params.get("something")  # Hard to detect!
    
    return {"done": True}
```

### 🔄 Partially Detected

```python
def executor(payload, progress_cb):
    # Multi-line expressions
    data = payload.get(
        "multiline_param"  # Will detect
    )
    
    # Commented examples
    # Important params: username, password
    actual_param = payload.get("username")  # Detects "username" but may also pick up from comment
    
    return {"done": True}
```

## Type Conversion

When you enter parameter values, the system auto-converts them:

| Input | Detected As | Python Type |
|-------|-------------|-------------|
| `123` | Integer | `int(123)` |
| `45.67` | Float | `float(45.67)` |
| `true` | String | `"true"` |
| `1,2,3` | List | `[1, 2, 3]` |
| `hello` | String | `"hello"` |

### Examples

```
Input: 100
Output: {"count": 100}

Input: 0.95
Output: {"confidence": 0.95}

Input: cat,dog,bird
Output: {"animals": ["cat", "dog", "bird"]}

Input: my_model.pkl
Output: {"model_file": "my_model.pkl"}
```

## Complete Workflow Example

### Step 1: Create Task
```python
# User enters this executor code:
def executor(payload, progress_cb):
    image_path = payload.get("image_path")
    width = payload.get("width", 800)
    height = payload.get("height", 600)
    format = payload.get("format", "jpg")
    
    progress_cb(1.0)
    return {"resized": True}

def aggregator(results):
    return {"total": len(results)}
```

**System shows:** `Parameters: image_path, width, height, format`

### Step 2: Select & Configure
```
Task List: image_resizer
↓
Configuration:
  image_path: /home/user/photo.png
  width: 1024
  height: 768
  format: png
```

### Step 3: Execute
```json
Payload sent to workers:
{
  "image_path": "/home/user/photo.png",
  "width": 1024,
  "height": 768,
  "format": "png"
}
```

## Parameter Field Behaviors

| Scenario | Behavior |
|----------|----------|
| **New task, no parameters** | Shows: "(No parameters for this task)" |
| **Task with 1-3 parameters** | All fields visible |
| **Task with 5+ parameters** | All fields visible (may need scrolling) |
| **Parameter with default** | Default value shown in field |
| **Parameter value changed** | Stays changed until task selection changes |
| **Invalid value entered** | Error shown when executing |

## Tips & Tricks

### 💡 Best Practices

1. **Use clear parameter names:**
   ```python
   ✅ payload.get("dataset_path")
   ❌ payload.get("dp")
   ```

2. **Use defaults for optional params:**
   ```python
   ✅ timeout = payload.get("timeout", 30)
   ❌ timeout = payload.get("timeout")
   ```

3. **Keep parameter names consistent:**
   ```python
   ✅ payload.get("learning_rate") everywhere
   ❌ payload.get("lr") in one place, "learning_rate" in another
   ```

### 🔧 Debugging

If parameters aren't detected:

1. **Check code syntax:**
   ```python
   ✅ payload.get("name")
   ❌ payload.get'name'  # Wrong quotes
   ```

2. **Ensure standard patterns are used:**
   ```python
   ✅ payload.get("param")
   ❌ getattr(payload, "param")  # Not detected
   ```

3. **Avoid dynamic names:**
   ```python
   ✅ payload.get("fixed_name")
   ❌ payload.get(variable_name)  # Not detected
   ```

## FAQ

**Q: Will parameters change if I edit task code?**
A: No, parameters are stored at registration time. Re-register to update.

**Q: Can I manually edit parameter fields?**
A: No, they're generated from code. Edit the executor code instead.

**Q: What if payload isn't found?**
A: Make sure your executor function takes `payload` as first argument.

**Q: Can I use nested dictionaries?**
A: Not directly. Use simple payload.get() calls.

**Q: What about list/dict parameter values?**
A: Use comma-separated values: `1,2,3` → converts to list.

## Related Files Modified

```
module4_ui/master_gui.py
├── extract_payload_keys() - Regex pattern matching
├── CustomTaskDialog - Shows detected parameters
└── MasterGUI - Generates input fields

custom_task_registry.py
└── Stores parameters metadata

module3_execution/tasks.py
└── get_task_info() - Returns executor code
```

## See Also

- `PARAMETER_AUTO_EXTRACTION_SUMMARY.md` - Detailed technical documentation
- `TESTING_AUTO_PARAMETER.md` - Test scenarios and verification
- `CUSTOM_TASK_EXAMPLES.md` - More custom task examples
