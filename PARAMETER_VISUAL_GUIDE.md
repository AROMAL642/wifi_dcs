# Visual Guide: Parameter Auto-Extraction in Action

## Step 1: Create Custom Task Dialog Opens

```
┌─────────────────────────────────────────────────┐
│ Create Custom Task                              │
├─────────────────────────────────────────────────┤
│                                                  │
│ Task Name: [my_ml_task________________]         │
│                                                  │
│ Description: [ML model training_____]          │
│                                                  │
│ Executor Code (Python):                         │
│ ┌──────────────────────────────────────┐       │
│ │def executor(payload, progress_cb):   │       │
│ │    # Your code here                  │       │
│ │                                       │       │
│ └──────────────────────────────────────┘       │
│                                                  │
│ Detected Parameters:                            │
│ (Parameters will auto-detect from code)        │
│                                                  │
│ [Register Task] [Cancel]                       │
└─────────────────────────────────────────────────┘
```

## Step 2: User Types Executor Code

```
User writes:
```python
def executor(payload, progress_cb):
    learning_rate = payload.get("learning_rate", 0.001)
    batch_size = payload.get("batch_size", 32)
    epochs = payload.get("epochs", 10)
    dataset_file = payload["dataset_file"]
    
    # Training...
    return {"accuracy": 0.95}
```

## Step 3: Parameters Auto-Detected in Real-Time

```
┌─ Detected Parameters: ───────────────────────┐
│ Parameters: batch_size, dataset_file, epochs,│
│             learning_rate                    │
│                                              │
│ (Shown in blue as user types)               │
└──────────────────────────────────────────────┘
```

## Step 4: User Registers Task

Click "Register Task" button → Task registered with parameters

## Step 5: Task List Shows New Task

```
┌─────────────────────────────────────────────┐
│ Available Tasks                             │
├─────────────────────────────────────────────┤
│ range_sum: Sum integers in range            │
│ array_sum: Sum numbers in array             │
│ ml_training: ML model training              │ ← New!
└─────────────────────────────────────────────┘
```

## Step 6: User Selects Custom Task

Click on "ml_training" task

## Step 7: Configuration Tab Auto-Generates Input Fields

```
┌────────────────────────────────────────────────┐
│ Task Configuration                            │
├────────────────────────────────────────────────┤
│                                                 │
│ Selected Task: ml_training                     │
│ Description: ML model training task            │
│                                                 │
│ ┌─ Task Parameters (Auto-generated) ────┐    │
│ │                                        │    │
│ │ batch_size:       [32          ]      │    │
│ │ dataset_file:     [            ]      │    │
│ │ epochs:           [10          ]      │    │
│ │ learning_rate:    [0.001       ]      │    │
│ │                                        │    │
│ └────────────────────────────────────────┘    │
│                                                 │
└────────────────────────────────────────────────┘
```

## Step 8: User Fills Parameter Values

```
┌─ Task Parameters (Auto-generated) ────┐
│                                        │
│ batch_size:       [64         ]       │
│ dataset_file:     [data.csv   ]       │
│ epochs:           [20         ]       │
│ learning_rate:    [0.01       ]       │
│                                        │
└────────────────────────────────────────┘
```

## Step 9: Click Execute

System automatically:
1. ✅ Validates all parameters filled
2. ✅ Converts types (int, float, list, string)
3. ✅ Builds payload:
   ```python
   {
     "batch_size": 64,
     "dataset_file": "data.csv",
     "epochs": 20,
     "learning_rate": 0.01
   }
   ```
4. ✅ Sends to worker nodes

## Before vs After

### BEFORE (Manual):
```
┌─ Task Parameters ──────────────┐
│ Chunk Size:   [5000       ]    │
│ Start:        [1          ]    │
│ End:          [10000      ]    │
│ Numbers:      [1,2,3,4,5 ]    │
└────────────────────────────────┘

❌ Same fields for ALL tasks
❌ Manual parameter list needed
❌ No auto-detection
```

### AFTER (Automatic):
```
┌─ Task Parameters ──────────────┐
│ batch_size:    [32      ]      │
│ dataset_file:  [        ]      │
│ epochs:        [10      ]      │
│ learning_rate: [0.001   ]      │
└────────────────────────────────┘

✅ Different fields per task
✅ Auto-detected from code
✅ No manual configuration
```

## Multiple Custom Tasks

Each task has its own parameters:

### Task 1: Image Processing
```python
def executor(payload, progress_cb):
    input_image = payload.get("input_image")
    output_size = payload.get("output_size", 256)
    filter_type = payload.get("filter_type", "gaussian")
```
**Auto-detected:** `filter_type, input_image, output_size`

### Task 2: Data Analysis
```python
def executor(payload, progress_cb):
    csv_file = payload.get("csv_file")
    column_name = payload.get("column_name")
    aggregation = payload.get("aggregation", "mean")
```
**Auto-detected:** `aggregation, column_name, csv_file`

### Task 3: Text Processing
```python
def executor(payload, progress_cb):
    text_input = payload.get("text_input")
    language = payload.get("language", "en")
    output_format = payload.get("output_format", "json")
```
**Auto-detected:** `language, output_format, text_input`

## Parameter Type Conversion

Input → Detected Type:

| Input | Type | Example |
|-------|------|---------|
| `"123"` | int | batch_size = 123 |
| `"3.14"` | float | learning_rate = 3.14 |
| `"1,2,3"` | list | numbers = [1, 2, 3] |
| `"text"` | string | name = "text" |

## Error Handling

### Missing Required Parameter:
```
❌ Parameter 'dataset_file' cannot be empty
   Please fill in all parameters before execution
```

### Invalid Type Conversion:
```
Auto-detected types:
"abc" → stays as string
"123" → converts to int
"3.14" → converts to float
"[1,2,3]" → error, use "1,2,3" instead
```

## Live Detection Example

As user types:

```
# Start
Detected Parameters: (none)

# Add first parameter
def executor(payload, progress_cb):
    x = payload.get("param1"
Detected Parameters: param1 ← (still typing...)

# Add second parameter  
def executor(payload, progress_cb):
    x = payload.get("param1")
    y = payload.get("param2")
Detected Parameters: param1, param2

# Add third parameter
def executor(payload, progress_cb):
    x = payload.get("param1")
    y = payload.get("param2")
    z = payload["param3"]
Detected Parameters: param1, param2, param3
```

---

**The entire flow is automatic - no manual parameter configuration needed!**
