# Custom Task Execution Flow - Visual Guide

## GUI Custom Task Dialog

```
┌─────────────────────────────────────────────────────────────┐
│         Create Custom Task Dialog                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Task Name: ┌──────────────────────────────────────────┐   │
│             │ hash_crack                               │   │
│             └──────────────────────────────────────────┘   │
│                                                              │
│  Description: ┌──────────────────────────────────────────┐ │
│               │ Crack 4-digit PIN by hash comparison    │ │
│               └──────────────────────────────────────────┘ │
│                                                              │
│  Executor Code (Python):                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ def executor(payload, progress_cb):                │   │
│  │     import hashlib                                 │   │
│  │     target = payload.get("target_hash")           │   │
│  │     start = payload.get("start", 0)               │   │
│  │     end = payload.get("end", 2500)                │   │
│  │                                                    │   │
│  │     for num in range(start, end):                │   │
│  │         pwd = str(num).zfill(4)                  │   │
│  │         h = hashlib.md5(pwd.encode()).hexdigest()│   │
│  │         if h == target:                           │   │
│  │             return {"found": True, "pwd": pwd}   │   │
│  │         progress_cb((num-start)/(end-start))    │   │
│  │                                                    │   │
│  │     return {"found": False}                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Aggregator Code (Python):                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ def aggregator(results):                           │   │
│  │     for r in results:                             │   │
│  │         if r.get("found"):                        │   │
│  │             return {"found": True, "pwd": ...}   │   │
│  │     return {"found": False}                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Attached Files: [Add File] [Remove Selected]              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                                                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│        [Register Task]    [Cancel]                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Task Execution Flow

```
Master GUI                          Worker 1
     │                                 │
     │  1. Click "Create Custom Task"  │
     │  ────────────────────────────→  │
     │                                 │
     │  2. Fill executor code          │
     │  3. Fill aggregator code        │
     │  4. Click "Register Task"       │
     │     ✓ Task registered           │
     │                                 │
     │  5. Select task from list       │
     │  6. Configure parameters        │
     │  7. Click "Execute Task"        │
     │  ────────────────────────────→  │
     │     Task: hash_crack            │
     │     Payload: {                  │
     │       target_hash: "...",       │
     │       start: 0,                 │
     │       end: 2500                 │
     │     }                           │
     │  ────────────────────────────→  Worker processes
     │                                 ✓ Executor runs
     │                                 ✓ Returns result
     │  ←──────────────────────────    
     │     Result: {found: true, pwd}  
     │                                 
     │  8. Aggregate all results       
     │  9. Display final answer        
     │                                 
     ✓ Done                            
```

## Data Flow Diagram

```
┌──────────────────┐
│   Master GUI     │
│  (User Interface)│
└────────┬─────────┘
         │
         │ User clicks "Execute"
         │
         ▼
┌──────────────────────────────┐
│  Task Configuration          │
│  - Parse parameters          │
│  - Create payloads           │
│  - Split work across workers │
└────────┬─────────────────────┘
         │
         │ Sends Task to Worker
         │
    ┌────┴────┬───────┬────────┐
    │          │       │        │
    ▼          ▼       ▼        ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│Worker 1│ │Worker 2│ │Worker 3│ │Worker 4│
│        │ │        │ │        │ │        │
│Execute │ │Execute │ │Execute │ │Execute │
│Chunk 1 │ │Chunk 2 │ │Chunk 3 │ │Chunk 4 │
│        │ │        │ │        │ │        │
│Result 1│ │Result 2│ │Result 3│ │Result 4│
└─┬──────┘ └───┬────┘ └────┬───┘ └─┬──────┘
  │            │           │       │
  │   ┌────────┴───────────┴───────┘
  │   │ Results List:
  │   │ [{found: true, pwd: "1234"},
  │   │  {found: false},
  │   │  {found: false},
  │   │  {found: false}]
  │   │
  │   ▼
  └─►┌────────────────────┐
     │    Aggregator      │
     │  Combine Results   │
     │  Choose Best One   │
     └─────────┬──────────┘
               │
               ▼
         ┌──────────────────┐
         │  Final Result    │
         │ PASSWORD: "1234" │
         │  In Range: 0-2500│
         └──────────────────┘
```

## Message Format

### Request (Master → Worker)
```json
{
  "task_name": "hash_crack",
  "payload": {
    "target_hash": "81dc9bdb52d04dc20036dbd8313ed055",
    "hash_type": "md5",
    "start": 0,
    "end": 2500
  }
}
```

### Response (Worker → Master)
```json
{
  "status": "success",
  "found": true,
  "password": "1234",
  "range": "0-2500"
}
```

### Aggregated Result
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

## Step-by-Step Execution Timeline

```
Time │ Master GUI              │ Worker Nodes
─────┼────────────────────────┼─────────────────────────────
  0s │ User clicks "Execute"  │ (waiting)
  1s │ Create task payloads   │ (waiting)
  2s │ Send task to all       │ ◄─── Receive Task 1
     │ workers               │ ◄─── Receive Task 2
     │                        │ ◄─── Receive Task 3
     │ Progress: 0%           │ ◄─── Receive Task 4
  3s │ Waiting for results    │ ─────► Start Executor 1
     │                        │ ─────► Start Executor 2
     │                        │ ─────► Start Executor 3
  5s │ Progress: 25%          │ ─────► Start Executor 4
     │                        │
  7s │ Progress: 50%          │ Processing...
     │                        │
 10s │ Progress: 75%          │ Processing...
     │                        │
 12s │                        │ ─────► Result 1
     │ Receive Result 1       │ ─────► Result 2
     │                        │ ─────► Result 3
 13s │ Receive Result 2       │ ─────► Result 4
     │ Receive Result 3       │
     │ Receive Result 4       │
 14s │ Aggregate Results      │ (done)
     │ Display Answer ✓       │
     │ Progress: 100%         │
```

## Parameters for Different Task Types

### Hash Cracking
```
Payload: {
  target_hash: "81dc9bdb52d04dc20036dbd8313ed055",
  hash_type: "md5",
  start: 0,
  end: 2500
}
```

### Prime Checking
```
Payload: {
  numbers: [2, 3, 5, 7, 11, 13, 17, 19],
  algorithm: "standard"
}
```

### Text Processing
```
Payload: {
  text: "the quick brown fox jumps over the lazy dog",
  operation: "word_count"
}
```

### Range Sum
```
Payload: {
  start: 1,
  end: 10000,
  chunk_size: 2500
}
```

## Error Handling Flow

```
┌─────────────────────────────────────────┐
│  Execute Task on Worker                 │
└────────┬────────────────────────────────┘
         │
    ┌────┴────┐
    │          │
    ▼          ▼
  SUCCESS    ERROR
    │          │
    │    ┌─────┴─────────────────┐
    │    │                       │
    │    ▼                       ▼
    │  Network Error      Execution Error
    │    (No response)     (Exception)
    │                      
    ▼                      
  Return Result       Return {
  {                     "status": "error",
    "status":           "message": "..."
    "success",        }
    "data": ...
  }

Master aggregates:
- Count successful results
- Add errors array if any failed
- Still return valid final result
```

## Success/Failure Scenarios

### ✅ Perfect Execution
```
All workers respond → Aggregator finds result → Success ✓
```

### ⚠️ Partial Failure
```
3 workers succeed, 1 fails → 
Aggregator uses 3 good results → 
Still returns valid answer ✓
```

### ❌ Total Failure
```
All workers fail or timeout →
Master reports errors →
User sees failure message ✗
```

## Custom Task Lifecycle

```
1. REGISTRATION PHASE
   ┌────────────────────────────────────┐
   │ User clicks "Create Custom Task"   │
   │ Fills in executor & aggregator     │
   │ Clicks "Register Task"             │
   │ Code validated & stored in memory  │
   └────────────────┬───────────────────┘
                    │ Task now available
                    ▼
2. DISCOVERY PHASE
   ┌────────────────────────────────────┐
   │ Task appears in available tasks    │
   │ User can see it in the list        │
   │ User can select it                 │
   └────────────────┬───────────────────┘
                    │
                    ▼
3. CONFIGURATION PHASE
   ┌────────────────────────────────────┐
   │ User selects task                  │
   │ Sets up parameters                 │
   │ Chooses worker nodes               │
   └────────────────┬───────────────────┘
                    │
                    ▼
4. EXECUTION PHASE
   ┌────────────────────────────────────┐
   │ User clicks "Execute Task"         │
   │ Task distributed to workers        │
   │ Executors run in parallel          │
   │ Progress tracked                   │
   └────────────────┬───────────────────┘
                    │
                    ▼
5. AGGREGATION PHASE
   ┌────────────────────────────────────┐
   │ All results collected              │
   │ Aggregator function called         │
   │ Final result computed              │
   │ User sees answer                   │
   └────────────────────────────────────┘
```
