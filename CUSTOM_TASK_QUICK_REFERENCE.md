# Custom Task Quick Reference Card

## Executor Function Template

```python
def executor(payload, progress_cb):
    """
    Runs on each worker node.
    
    Args:
        payload: dict with input parameters
        progress_cb: function(float 0-1) to report progress
    
    Returns:
        dict with "status" key and results
    """
    
    # Extract parameters from payload
    param1 = payload.get("param1", default_value)
    param2 = payload.get("param2", default_value)
    
    try:
        # Do some work
        progress_cb(0.5)  # 50% done
        
        result = compute_something(param1, param2)
        
        # Return success
        progress_cb(1.0)  # 100% done
        return {
            "status": "success",
            "data": result
        }
    
    except Exception as e:
        # Return error
        return {
            "status": "error",
            "message": str(e)
        }
```

## Aggregator Function Template

```python
def aggregator(results):
    """
    Combines results from all workers.
    
    Args:
        results: list of dicts returned by each executor
    
    Returns:
        dict with final aggregated result
    """
    
    aggregated = []
    
    for result in results:
        if result.get("status") == "success":
            # Use successful results
            data = result.get("data")
            aggregated.append(data)
    
    # Combine all results
    final_answer = combine_results(aggregated)
    
    return {
        "task": "task_name",
        "status": "success",
        "final_result": final_answer,
        "processed": len(aggregated)
    }
```

---

## GUI Workflow - 5 Steps

### Step 1: Click "Create Custom Task"
Button location: Left panel, below "Refresh Tasks"

### Step 2: Fill Task Information
| Field | Example | Notes |
|-------|---------|-------|
| Task Name | `hash_crack` | Lowercase, underscores only |
| Description | `Crack 4-digit PIN` | Optional but helpful |

### Step 3: Paste Executor Code
- Copy executor function
- Paste into "Executor Code" box
- Function MUST be named `executor`

### Step 4: Paste Aggregator Code
- Copy aggregator function
- Paste into "Aggregator Code" box
- Function MUST be named `aggregator`

### Step 5: Click "Register Task"
- Code is validated
- Success message appears
- Task now available to execute

---

## Execution Workflow - 6 Steps

### Step 1: Select Task
- Left panel → Click task in list
- Task name appears in Configuration tab

### Step 2: Configure Workers
- "Worker Nodes" tab
- Add nodes or use defaults
- Click "Test Connection" to verify

### Step 3: Set Parameters
- "Configuration" tab
- Update payload values
- These values sent to executor as `payload` dict

### Step 4: Click "Execute Task"
- "Execution" tab
- Button turns red (Stop available)
- Progress bar updates

### Step 5: Monitor Progress
- Watch "Logs" tab for status
- Progress bar shows completion %
- System shows which nodes are running

### Step 6: View Results
- "Results" box shows final answer
- JSON formatted
- Can export to file

---

## Payload Dictionary

The `payload` dict passed to executor contains:

```python
{
    "chunk_size": 5000,              # Default from GUI
    "start": 0,                      # If range_sum task
    "end": 10000,                    # If range_sum task
    "numbers": [1,2,3,4,5],          # If array_sum task
    # Your custom parameters here
}
```

**Custom Parameters Example:**
```python
# In executor:
target_hash = payload.get("target_hash", "")
start_range = payload.get("start", 0)
# etc.
```

---

## Common Patterns

### Pattern 1: Loop with Progress
```python
total = len(items)
for idx, item in enumerate(items, start=1):
    result = process(item)
    progress_cb(idx / total)  # Update progress
```

### Pattern 2: Early Exit on Success
```python
for item in items:
    if found_match(item):
        return {"status": "success", "result": item}

return {"status": "success", "found": False}
```

### Pattern 3: Error Handling
```python
try:
    result = risky_operation()
    progress_cb(1.0)
    return {"status": "success", "data": result}
except Exception as e:
    return {"status": "error", "message": str(e)}
```

### Pattern 4: Batch Processing
```python
batch_size = 100
for i in range(0, len(items), batch_size):
    batch = items[i:i+batch_size]
    process_batch(batch)
    progress_cb(i / len(items))
```

---

## Return Value Format

### Success (Always Required)
```python
{
    "status": "success",
    "any_key": any_value,
    "another_key": another_value
}
```

### Error (Alternative)
```python
{
    "status": "error",
    "message": "description of error"
}
```

---

## Aggregator Patterns

### Pattern 1: Find in Results
```python
for result in results:
    if result.get("status") == "success" and result.get("found"):
        return {"status": "success", "answer": result.get("answer")}
return {"status": "success", "found": False}
```

### Pattern 2: Sum/Combine All
```python
total = 0
for result in results:
    if result.get("status") == "success":
        total += result.get("value", 0)
return {"status": "success", "total": total}
```

### Pattern 3: Count & Collect
```python
collected = []
for result in results:
    if result.get("status") == "success":
        collected.extend(result.get("data", []))
return {"status": "success", "items": collected}
```

---

## Do's and Don'ts

### ✅ DO
- ✅ Always call `progress_cb(1.0)` when done
- ✅ Handle exceptions and return error dict
- ✅ Return dict (JSON serializable)
- ✅ Use lowercase function names
- ✅ Import modules inside function
- ✅ Test locally first
- ✅ Add error checks in aggregator

### ❌ DON'T
- ❌ Forget `progress_cb()` call
- ❌ Return non-dict objects
- ❌ Use function names other than `executor`/`aggregator`
- ❌ Assume all workers succeed
- ❌ Use complex Python objects (classes, etc.)
- ❌ Modify global variables
- ❌ Do infinite loops without progress

---

## Debugging Tips

### Issue: "Code Error: Functions must be defined"
**Solution:** Make sure function name is exactly `executor` or `aggregator`

### Issue: "Task execution failed" with no details
**Solution:** 
1. Check "Logs" tab
2. Test connection to workers first
3. Verify payload is valid

### Issue: Progress doesn't update
**Solution:** Call `progress_cb()` inside loop
```python
for i in range(100):
    progress_cb(i / 100)  # Add this
```

### Issue: Results are empty
**Solution:** Check aggregator processes failed results too
```python
for result in results:
    if result.get("status") == "error":
        continue  # Skip errors
    # Process success
```

---

## Test Your Code

### Before Pasting in GUI:
1. Copy your executor code
2. Open terminal
3. Run:
```bash
python3 << 'EOF'
# PASTE YOUR CODE HERE
def executor(payload, progress_cb):
    ...

# Test
try:
    r = executor({"test": "value"}, lambda x: print(f"Progress: {x*100}%"))
    print("Result:", r)
    print("✓ Valid!")
except Exception as e:
    print("✗ Error:", e)
EOF
```

---

## Example Payload Strings

### For Hash Crack:
```
target_hash: 81dc9bdb52d04dc20036dbd8313ed055
hash_type: md5
start: 0
end: 2500
```

### For Range Sum:
```
start: 1
end: 10000
chunk_size: 2500
```

### For Array Sum:
```
numbers: 1,2,3,4,5,6,7,8,9,10
chunk_size: 5
```

---

## Progress Reporting Convention

| Value | Meaning |
|-------|---------|
| 0.0 | Just started |
| 0.25 | 25% complete |
| 0.5 | Halfway |
| 0.75 | 75% complete |
| 1.0 | Finished |

**Best Practice:**
```python
total_items = 1000
for idx, item in enumerate(items, start=1):
    process(item)
    # Report every 10%
    if idx % 100 == 0 or idx == total_items:
        progress_cb(idx / total_items)
```

---

## Response Time Expectations

| Task Type | Typical Time |
|-----------|--------------|
| Hash crack (0-2500) | 1-3 seconds |
| Prime check (10 numbers) | <1 second |
| Text processing | 1-2 seconds |
| Range sum (2500 numbers) | 1-2 seconds |
| Network latency | 0.5-1 second |

**Total = Task Time + Network Latency + Aggregation**

---

## File Attachments (Optional)

If you need to attach files:
1. Click "Add File" button in Custom Task dialog
2. Select file
3. File path shown in list
4. In executor, access via:
```python
# Files would need to be manually included
# Usually for reference/lookup tables
```

---

## Success Checklist

Before clicking "Execute Task":
- [ ] Task registered successfully (no errors)
- [ ] Task visible in available tasks list
- [ ] At least 1 worker node connected
- [ ] Worker connection test shows ✓
- [ ] Executor code uses `progress_cb()`
- [ ] Aggregator handles error cases
- [ ] Payload parameters set correctly
- [ ] Ready to Execute button available

---

Quick Reference: Use `progress_cb(0.0 to 1.0)` to keep UI responsive! 🚀
