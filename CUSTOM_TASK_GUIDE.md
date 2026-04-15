# Complete Guide: How to Run Custom Tasks Using the GUI

## Overview
The distributed computing system allows you to create and execute custom tasks through the GUI without modifying code. Here's a step-by-step guide with examples.

---

## Step 1: Launch the Master GUI

```bash
cd /home/aromal/Desktop/MAIN_PROJECT_FINAL/module4_ui
python3 gui_launcher.py
```

Then select **Master** mode.

---

## Step 2: Create a Custom Task

### Method 1: Using the GUI Dialog

1. Click **"Create Custom Task"** button in the left panel
2. A dialog window opens with three sections:
   - **Task Name**: Give your task a unique name
   - **Description**: Brief description of what the task does
   - **Executor Code**: Python function that runs on worker nodes
   - **Aggregator Code**: Python function that combines results

### Basic Structure

Every custom task needs:

**Executor** - Runs on worker nodes:
```python
def executor(payload, progress_cb):
    # payload: dict with task parameters
    # progress_cb: function to report progress (0.0 to 1.0)
    
    result = {"status": "success", "data": "your result"}
    progress_cb(1.0)  # Report 100% done
    return result
```

**Aggregator** - Combines results from all workers:
```python
def aggregator(results):
    # results: list of dicts returned by each executor
    
    return {"task": "custom", "total": len(results)}
```

---

## Example 1: Hash Cracking Task

### Scenario
Crack a 4-digit PIN by trying all combinations (0000-9999) against a target hash.

### Step-by-Step

1. **Click "Create Custom Task"** button

2. **Fill in Task Name:**
   ```
   hash_crack
   ```

3. **Fill in Description:**
   ```
   Crack 4-digit numerical PIN by comparing against target hash (MD5/SHA256)
   ```

4. **Paste Executor Code:**
   ```python
def executor(payload, progress_cb):
    import hashlib
    
    target_hash = payload.get("target_hash", "").lower()
    hash_type = payload.get("hash_type", "md5").lower()
    start = payload.get("start", 0)
    end = payload.get("end", 2500)
    
    if not target_hash:
        return {"status": "error", "message": "No target hash"}
    
    found = False
    result_value = None
    total_checks = end - start
    
    for idx, num in enumerate(range(start, end), start=1):
        password = str(num).zfill(4)
        
        if hash_type == "md5":
            computed_hash = hashlib.md5(password.encode()).hexdigest()
        elif hash_type == "sha256":
            computed_hash = hashlib.sha256(password.encode()).hexdigest()
        else:
            return {"status": "error", "message": f"Unsupported hash: {hash_type}"}
        
        if idx % 250 == 0 or idx == total_checks:
            progress_cb(idx / total_checks)
        
        if computed_hash == target_hash:
            found = True
            result_value = password
            progress_cb(1.0)
            break
    
    if found:
        return {
            "status": "success",
            "found": True,
            "password": result_value,
            "range": f"{start}-{end}"
        }
    else:
        return {
            "status": "success",
            "found": False,
            "range": f"{start}-{end}"
        }
   ```

5. **Paste Aggregator Code:**
   ```python
def aggregator(results):
    # Check if password was found in any range
    for result in results:
        if result.get("found"):
            return {
                "task": "hash_crack",
                "status": "success",
                "found": True,
                "password": result.get("password"),
                "message": f"PASSWORD CRACKED: {result.get('password')}",
                "found_in_range": result.get("range"),
                "total_ranges_checked": len(results)
            }
    
    # Not found in any range
    return {
        "task": "hash_crack",
        "status": "success",
        "found": False,
        "message": "PASSWORD NOT FOUND (0000-9999)",
        "total_ranges_checked": len(results)
    }
   ```

6. **Click "Register Task"** → Success message appears

---

## Step 3: Execute Your Custom Task

### Configure Worker Nodes

1. Go to **"Worker Nodes"** tab
2. Add worker nodes (default: 127.0.0.1:6000, 127.0.0.1:6001, etc.)
3. Click **"Test Connection"** to verify

### Execute the Task

1. Go to **"Logs"** tab to start fresh (optional)

2. Go back to left panel and **select your task**
   - Click on `hash_crack: Crack 4-digit PIN...`
   - Task name appears in Configuration tab

3. Go to **"Configuration"** tab
   - Update parameters if needed

4. Go to **"Execution"** tab

5. Click **"Execute Task"** button

6. Watch the progress bar and logs:
   ```
   [2026-04-08 10:30:45] Task selected: hash_crack
   [2026-04-08 10:30:46] Starting: hash_crack
   [2026-04-08 10:30:46] Sending to 3 node(s): 127.0.0.1:6000, 127.0.0.1:6001, 127.0.0.1:6002
   [2026-04-08 10:30:46] Payload: {"chunk_size": 5000, ...}
   [2026-04-08 10:30:50] ✓ Task execution completed successfully
   ```

7. **View Results** in the "Results" box:
   ```json
   {
     "task": "hash_crack",
     "status": "success",
     "found": true,
     "password": "1234",
     "message": "PASSWORD CRACKED: 1234",
     "found_in_range": "0-2500",
     "total_ranges_checked": 4
   }
   ```

---

## Example 2: Prime Number Checker Task

### Scenario
Check if numbers are prime (distributed across workers).

### Code

**Executor:**
```python
def executor(payload, progress_cb):
    def is_prime(n):
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        for i in range(3, int(n**0.5) + 1, 2):
            if n % i == 0:
                return False
        return True
    
    numbers = payload.get("numbers", [])
    results = {}
    
    for idx, num in enumerate(numbers, start=1):
        results[str(num)] = is_prime(num)
        progress_cb(idx / len(numbers))
    
    return {"status": "success", "prime_checks": results}
```

**Aggregator:**
```python
def aggregator(results):
    all_primes = {}
    
    for result in results:
        if result.get("status") == "success":
            all_primes.update(result.get("prime_checks", {}))
    
    prime_count = sum(1 for v in all_primes.values() if v)
    
    return {
        "task": "prime_checker",
        "total_numbers": len(all_primes),
        "prime_count": prime_count,
        "primes": [k for k, v in all_primes.items() if v]
    }
```

---

## Example 3: Text Processing Task

### Scenario
Count word frequencies across distributed text chunks.

**Executor:**
```python
def executor(payload, progress_cb):
    from collections import Counter
    
    text = payload.get("text", "")
    words = text.lower().split()
    
    word_counts = Counter(words)
    
    progress_cb(1.0)
    
    return {
        "status": "success",
        "word_counts": dict(word_counts),
        "total_words": len(words)
    }
```

**Aggregator:**
```python
def aggregator(results):
    from collections import Counter
    
    combined = Counter()
    total_words = 0
    
    for result in results:
        if result.get("status") == "success":
            word_counts = result.get("word_counts", {})
            for word, count in word_counts.items():
                combined[word] += count
            total_words += result.get("total_words", 0)
    
    top_10 = combined.most_common(10)
    
    return {
        "task": "text_processor",
        "total_words": total_words,
        "unique_words": len(combined),
        "top_10_words": top_10
    }
```

---

## Exporting Results

After execution:

1. Click **"Export Results"** button
2. Choose location and filename
3. Results saved as JSON with all details

---

## Important Notes

### ✅ Do's
- ✅ Use `progress_cb(value)` where value is 0.0 to 1.0
- ✅ Return dict with at least `{"status": "success", ...}`
- ✅ Handle errors in executor (return error dict)
- ✅ Process all results in aggregator, even if some fail
- ✅ Use meaningful task names (lowercase, underscores)

### ❌ Don'ts
- ❌ Don't use blocking operations without progress reporting
- ❌ Don't return non-serializable objects (use only dict, list, str, int, float, bool, None)
- ❌ Don't forget `progress_cb(1.0)` at the end
- ❌ Don't import modules that aren't available on workers
- ❌ Don't modify executor/aggregator functions after registering

---

## Troubleshooting

### "Task execution failed"
1. Check worker nodes are running
2. Verify network connectivity
3. Check logs for error messages
4. Test connection to nodes in "Worker Nodes" tab

### "Code Error: Functions must be defined"
1. Make sure function name is exactly `executor` and `aggregator`
2. Check for syntax errors in Python code
3. Make sure indentation is correct

### "No results returned"
1. Workers might be offline
2. Check if payload is valid JSON
3. Review worker logs

### Task takes too long
1. Increase number of worker nodes
2. Reduce chunk size
3. Optimize executor code

---

## Quick Reference

| Component | Purpose | Example |
|-----------|---------|---------|
| Task Name | Unique identifier | `hash_crack`, `prime_checker` |
| Executor | Runs on workers | Processes chunk of data |
| Aggregator | Combines results | Merges all worker outputs |
| Payload | Input parameters | `{"target_hash": "abc...", "start": 0}` |
| Progress | Completion status | `progress_cb(0.5)` for 50% |
| Results | Output data | JSON dict with results |

---

## Complete Workflow

```
1. Start Master GUI → Select Master Mode
   ↓
2. Start Worker GUIs → Select Worker Mode (multiple terminals)
   ↓
3. Click "Start Service" on each worker
   ↓
4. Master auto-discovers workers (or add manually)
   ↓
5. Click "Create Custom Task" in Master GUI
   ↓
6. Paste executor and aggregator code
   ↓
7. Click "Register Task"
   ↓
8. Select task from list
   ↓
9. Configure parameters
   ↓
10. Click "Execute Task"
    ↓
11. Monitor progress in logs
    ↓
12. View results when complete
    ↓
13. Export results if needed
```

---

Enjoy distributed computing! 🚀
