# Custom Task Examples - Copy & Paste Ready

Use these code snippets directly in the GUI Custom Task Dialog.

---

## Example 1: Hash Cracking (4-Digit PIN)

### Task Name:
```
hash_crack
```

### Description:
```
Crack 4-digit numerical PIN by comparing with target hash (MD5/SHA256/SHA1)
```

### Executor Code:
```python
def executor(payload, progress_cb):
    import hashlib
    
    target_hash = payload.get("target_hash", "").lower()
    hash_type = payload.get("hash_type", "md5").lower()
    start = payload.get("start", 0)
    end = payload.get("end", 2500)
    
    if not target_hash:
        return {"status": "error", "message": "No target hash provided"}
    
    found = False
    result_value = None
    total_checks = end - start
    
    try:
        for idx, num in enumerate(range(start, end), start=1):
            password = str(num).zfill(4)
            
            if hash_type == "md5":
                computed_hash = hashlib.md5(password.encode()).hexdigest()
            elif hash_type == "sha256":
                computed_hash = hashlib.sha256(password.encode()).hexdigest()
            elif hash_type == "sha1":
                computed_hash = hashlib.sha1(password.encode()).hexdigest()
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
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Aggregator Code:
```python
def aggregator(results):
    for result in results:
        if result.get("status") == "success" and result.get("found"):
            return {
                "task": "hash_crack",
                "status": "success",
                "found": True,
                "password": result.get("password"),
                "message": f"✓ PASSWORD CRACKED: {result.get('password')}",
                "found_in_range": result.get("range"),
                "total_ranges_checked": len(results)
            }
    
    return {
        "task": "hash_crack",
        "status": "success",
        "found": False,
        "message": "✗ PASSWORD NOT FOUND (0000-9999)",
        "total_ranges_checked": len(results)
    }
```

### How to Use:
1. In Configuration tab, set parameters:
   ```
   target_hash: 81dc9bdb52d04dc20036dbd8313ed055
   hash_type: md5
   start: 0
   end: 2500
   ```
2. The target hash is MD5 of "1234"
3. Workers will find it in one of the ranges
4. Aggregator returns the password

---

## Example 2: Prime Number Checker

### Task Name:
```
prime_checker
```

### Description:
```
Check if numbers are prime and return results
```

### Executor Code:
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
    if not numbers:
        return {"status": "error", "message": "No numbers provided"}
    
    prime_results = {}
    total = len(numbers)
    
    try:
        for idx, num in enumerate(numbers, start=1):
            prime_results[int(num)] = is_prime(int(num))
            progress_cb(idx / total)
        
        return {
            "status": "success",
            "prime_checks": prime_results,
            "count": len(prime_results)
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Aggregator Code:
```python
def aggregator(results):
    all_primes = {}
    total_numbers = 0
    
    for result in results:
        if result.get("status") == "success":
            checks = result.get("prime_checks", {})
            all_primes.update(checks)
            total_numbers += result.get("count", 0)
    
    prime_count = sum(1 for v in all_primes.values() if v)
    primes = sorted([k for k, v in all_primes.items() if v])
    
    return {
        "task": "prime_checker",
        "total_numbers": total_numbers,
        "prime_count": prime_count,
        "non_prime_count": total_numbers - prime_count,
        "primes": primes,
        "first_10_primes": primes[:10]
    }
```

### How to Use:
1. In Configuration tab, modify array_numbers:
   ```
   100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120
   ```
2. Click Execute
3. See which numbers are prime

---

## Example 3: Text Word Frequency Counter

### Task Name:
```
text_processor
```

### Description:
```
Count word frequencies in text and find most common words
```

### Executor Code:
```python
def executor(payload, progress_cb):
    from collections import Counter
    
    text = payload.get("text", "")
    if not text:
        return {"status": "error", "message": "No text provided"}
    
    try:
        words = text.lower().split()
        word_counts = Counter(words)
        
        progress_cb(0.5)
        
        total_words = len(words)
        unique_words = len(word_counts)
        
        progress_cb(1.0)
        
        return {
            "status": "success",
            "word_counts": dict(word_counts),
            "total_words": total_words,
            "unique_words": unique_words
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Aggregator Code:
```python
def aggregator(results):
    from collections import Counter
    
    combined = Counter()
    total_words = 0
    total_unique = 0
    
    for result in results:
        if result.get("status") == "success":
            word_counts = result.get("word_counts", {})
            for word, count in word_counts.items():
                combined[word] += count
            total_words += result.get("total_words", 0)
            total_unique += result.get("unique_words", 0)
    
    top_20 = combined.most_common(20)
    
    return {
        "task": "text_processor",
        "total_words": total_words,
        "unique_words": len(combined),
        "top_20_words": top_20,
        "results_from": len(results)
    }
```

### How to Use:
1. Create payload in Configuration tab:
   ```json
   {
     "text": "the quick brown fox jumps over the lazy dog the fox is quick"
   }
   ```
2. Execute
3. See word frequencies

---

## Example 4: Number Sum Range Calculator

### Task Name:
```
range_sum
```

### Description:
```
Sum all numbers in a range [start, end]
```

### Executor Code:
```python
def executor(payload, progress_cb):
    start = int(payload.get("start", 0))
    end = int(payload.get("end", 100))
    
    if end < start:
        return {"status": "error", "message": "End must be >= start"}
    
    try:
        total = 0
        count = end - start + 1
        report_every = max(1, count // 10)
        
        for idx, value in enumerate(range(start, end + 1), start=1):
            total += value
            if idx % report_every == 0 or idx == count:
                progress_cb(idx / count)
        
        return {
            "status": "success",
            "partial_sum": total,
            "count": count,
            "range": [start, end]
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Aggregator Code:
```python
def aggregator(results):
    total_sum = 0
    total_count = 0
    ranges = []
    
    for result in results:
        if result.get("status") == "success":
            total_sum += result.get("partial_sum", 0)
            total_count += result.get("count", 0)
            if "range" in result:
                ranges.append(result["range"])
    
    return {
        "task": "range_sum",
        "total_sum": total_sum,
        "total_numbers": total_count,
        "ranges": ranges,
        "average": total_sum / total_count if total_count > 0 else 0
    }
```

### How to Use:
1. In Configuration tab:
   ```
   Range Start: 1
   Range End: 10000
   Chunk Size: 2500
   ```
2. Click Execute
3. Get sum of 1+2+3+...+10000 = 50,005,000

---

## Example 5: Temperature Data Processor

### Task Name:
```
temperature_stats
```

### Description:
```
Calculate statistics (min, max, average) for temperature data
```

### Executor Code:
```python
def executor(payload, progress_cb):
    temperatures = payload.get("temperatures", [])
    if not temperatures:
        return {"status": "error", "message": "No temperature data"}
    
    try:
        temps = [float(t) for t in temperatures]
        
        progress_cb(0.3)
        
        min_temp = min(temps)
        max_temp = max(temps)
        avg_temp = sum(temps) / len(temps)
        
        progress_cb(0.7)
        
        above_25 = sum(1 for t in temps if t > 25)
        below_10 = sum(1 for t in temps if t < 10)
        
        progress_cb(1.0)
        
        return {
            "status": "success",
            "min": min_temp,
            "max": max_temp,
            "avg": avg_temp,
            "count": len(temps),
            "above_25": above_25,
            "below_10": below_10
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Aggregator Code:
```python
def aggregator(results):
    all_temps = []
    
    for result in results:
        if result.get("status") == "success":
            all_temps.append({
                "min": result.get("min"),
                "max": result.get("max"),
                "avg": result.get("avg"),
                "count": result.get("count")
            })
    
    if not all_temps:
        return {"status": "error", "message": "No valid data"}
    
    overall_min = min(t["min"] for t in all_temps)
    overall_max = max(t["max"] for t in all_temps)
    total_temps = sum(t["count"] for t in all_temps)
    overall_avg = sum(t["avg"] * t["count"] for t in all_temps) / total_temps
    
    return {
        "task": "temperature_stats",
        "min_temperature": overall_min,
        "max_temperature": overall_max,
        "average_temperature": round(overall_avg, 2),
        "total_readings": total_temps,
        "batches_processed": len(all_temps)
    }
```

### How to Use:
```
temperatures: 15.2,16.5,18.3,22.1,25.6,28.9,30.2,29.1,26.3,21.5,18.2,15.8
```

---

## Example 6: Simple Echo Task

### Task Name:
```
echo_task
```

### Description:
```
Echo back the input message (useful for testing)
```

### Executor Code:
```python
def executor(payload, progress_cb):
    message = payload.get("message", "")
    worker_id = payload.get("worker_id", "unknown")
    
    try:
        progress_cb(0.5)
        
        result = {
            "status": "success",
            "original_message": message,
            "worker_id": worker_id,
            "echoed": f"Worker {worker_id} echoes: {message}"
        }
        
        progress_cb(1.0)
        return result
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### Aggregator Code:
```python
def aggregator(results):
    echoes = []
    
    for result in results:
        if result.get("status") == "success":
            echoes.append(result.get("echoed", ""))
    
    return {
        "task": "echo_task",
        "total_workers": len(results),
        "successful": len(echoes),
        "all_echoes": echoes,
        "message": f"Received {len(echoes)} echoes from {len(results)} workers"
    }
```

### How to Use:
```
message: Hello from Master!
worker_id: test-1
```

---

## Testing Checklist

Before executing any custom task:

- [ ] Task name is lowercase with underscores only
- [ ] Executor function is named exactly `executor`
- [ ] Aggregator function is named exactly `aggregator`
- [ ] Both functions have correct parameter names
- [ ] Executor returns a dict with `"status"` key
- [ ] Progress callback called: `progress_cb(value)` where 0 ≤ value ≤ 1
- [ ] No import errors in the code
- [ ] No syntax errors (try pasting in Python IDE first)
- [ ] All required imports are in the functions
- [ ] Worker nodes are running and connected
- [ ] Test connection to at least one worker first

---

## Quick Test Command

To verify executor code is valid Python:

```bash
python3 << 'EOF'
# Paste your executor code here
def executor(payload, progress_cb):
    ...

# Test it
try:
    result = executor({"test": "data"}, lambda x: None)
    print("✓ Valid code:", result)
except Exception as e:
    print("✗ Error:", e)
EOF
```

---

Good luck with your custom tasks! 🚀
