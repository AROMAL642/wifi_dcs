# Testing Guide - Auto Parameter Extraction Feature

## Quick Test Scenario

### Test 1: Create Custom Task with Auto-Detection

**Steps:**
1. Open Master GUI
2. Click "Create Custom Task" button
3. Enter task details:
   - **Task Name:** `image_processor`
   - **Description:** `Process images with filters`
   - **Executor Code:**
     ```python
     def executor(payload, progress_cb):
         image_path = payload.get("image_path")
         filter_type = payload.get("filter_type", "blur")
         intensity = payload.get("intensity", 5)
         
         # Simulate processing
         for i in range(1, 11):
             progress_cb(i / 10)
         
         return {"status": "success", "result": f"{filter_type} applied"}
     ```
   - **Aggregator Code:**
     ```python
     def aggregator(results):
         return {"total_processed": len(results), "all_results": results}
     ```

**Expected Result:**
- Dialog shows: **"Parameters: image_path, filter_type, intensity"**
- Task registers successfully
- Parameters stored in registry

### Test 2: Execute Custom Task with Generated Fields

**Steps:**
1. Select the custom task from the task list
2. Observe the Configuration tab

**Expected Output:**
```
Selected Task: image_processor
Description: Process images with filters

Parameters: image_path, filter_type, intensity

Task Parameters (Auto-generated from code)
─────────────────────────────────────
image_path:  [__________]
filter_type: [blur______]
intensity:   [5_________]
```

3. Fill in parameter values:
   - `image_path`: `/path/to/image.jpg`
   - `filter_type`: `sharpen`
   - `intensity`: `8`
4. Click "Execute Task"

**Expected Result:**
- Task executes with correct parameters
- Logs show: `Payload: {"image_path": "/path/to/image.jpg", "filter_type": "sharpen", "intensity": 8}`

### Test 3: Different Parameter Patterns

**Create task with various payload access patterns:**

```python
def executor(payload, progress_cb):
    # Pattern 1: payload.get() with defaults
    param1 = payload.get("param1", "default")
    
    # Pattern 2: payload.get() without defaults
    param2 = payload.get("param2")
    
    # Pattern 3: Direct dictionary access
    param3 = payload["param3"]
    
    progress_cb(1.0)
    return {"done": True}
```

**Expected Detection:**
- Parameters: `param1, param2, param3` (all detected)

### Test 4: Type Conversion

**Create task and test different input types:**

```python
def executor(payload, progress_cb):
    count = payload.get("count", 0)          # Should be int
    ratio = payload.get("ratio", 1.0)        # Should be float
    items = payload.get("items", [])         # Should be list
    name = payload.get("name", "default")    # Should be string
    
    return {"done": True}
```

**Fill inputs:**
1. `count`: `100`
2. `ratio`: `0.75`
3. `items`: `1,2,3,4,5`
4. `name`: `test_run`

**Expected Payload:**
```json
{
  "count": 100,           # int
  "ratio": 0.75,          # float
  "items": [1, 2, 3, 4, 5],  # list of ints
  "name": "test_run"      # string
}
```

### Test 5: Built-in Tasks Still Work

**Test that built-in tasks still show parameters:**

1. Select `range_sum` task
2. Verify parameter fields appear: `start`, `end`, `chunk_size`
3. Select `array_sum` task
4. Verify parameter fields appear: `numbers`, `chunk_size`

### Test 6: Edge Cases

**Test 1: Task with no parameters**
```python
def executor(payload, progress_cb):
    result = {"data": "static result"}
    progress_cb(1.0)
    return result
```

**Expected:** Shows "(No parameters for this task)"

**Test 2: Task with many parameters (5+)**
```python
def executor(payload, progress_cb):
    p1 = payload.get("param1")
    p2 = payload.get("param2")
    p3 = payload.get("param3")
    p4 = payload.get("param4")
    p5 = payload.get("param5")
    p6 = payload.get("param6")
    return {"done": True}
```

**Expected:** All 6 parameter fields visible

**Test 3: Task with special characters**
```python
def executor(payload, progress_cb):
    data_file = payload.get("data_file")
    output_dir = payload.get("output_dir")
    config_json = payload.get("config_json")
    return {"done": True}
```

**Expected:** All detected with underscores preserved

## Verification Checklist

- [ ] Custom task dialog shows detected parameters while typing
- [ ] Parameters field appears empty if no parameters detected
- [ ] Parameter input fields appear when task is selected
- [ ] Parameter labels are clear and readable
- [ ] Type conversion works (int, float, list, string)
- [ ] Task executes with correct payload
- [ ] Built-in tasks still work normally
- [ ] Error handling for missing required parameters
- [ ] Registry file stores parameters correctly
- [ ] Multiple custom tasks with different parameters work
- [ ] Parameter values persist in entry fields until task changes
- [ ] Logs show correct parameter values

## Example Custom Tasks to Test

### Data Processing Task
```python
def executor(payload, progress_cb):
    input_file = payload.get("input_file")
    output_file = payload.get("output_file")
    chunk_size = payload.get("chunk_size", 1000)
    
    for i in range(10):
        progress_cb((i + 1) / 10)
    
    return {
        "input": input_file,
        "output": output_file,
        "chunk_size": chunk_size,
        "status": "completed"
    }

def aggregator(results):
    return {"total_tasks": len(results), "all_results": results}
```

### Machine Learning Task
```python
def executor(payload, progress_cb):
    dataset_path = payload.get("dataset_path")
    model_type = payload.get("model_type")
    epochs = payload.get("epochs", 10)
    batch_size = payload.get("batch_size", 32)
    
    for epoch in range(1, epochs + 1):
        progress_cb(epoch / epochs)
    
    return {
        "model": model_type,
        "epochs": epochs,
        "accuracy": 0.95
    }

def aggregator(results):
    avg_acc = sum(r.get("accuracy", 0) for r in results) / len(results)
    return {"avg_accuracy": avg_acc, "tasks": len(results)}
```

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Parameter fields don't appear | Make sure payload.get() is used in executor code |
| Fields show but empty | Parameter names not detected - check regex patterns |
| Type conversion fails | Check input format (numbers with commas for lists) |
| Old parameters shown | Clear cache and reload task list |
| Executor code syntax error | Check Python syntax before registering |

## Performance Testing

Test with various parameter counts:
- **0 parameters:** Should show placeholder message
- **3-5 parameters:** Normal case, should display nicely
- **10+ parameters:** Verify scrolling/layout works
- **Very long parameter names:** Verify UI doesn't break

