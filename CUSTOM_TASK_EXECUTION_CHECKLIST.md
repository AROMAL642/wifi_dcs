# Custom Task Execution Checklist

Use this checklist to ensure everything is set up correctly before executing custom tasks.

---

## ✅ Pre-Execution Checklist

### Environment Setup (Before Starting Any GUI)
- [ ] Python 3.7+ installed (`python3 --version`)
- [ ] tkinter available (`python3 -m tkinter` opens window)
- [ ] Network connectivity between machines
- [ ] Port 5000 available for master
- [ ] Ports 6000+ available for workers

### Master GUI Setup
- [ ] Master GUI started: `python3 gui_launcher.py` → Select "Master"
- [ ] GUI opens without errors
- [ ] "Logs" tab visible and working
- [ ] Left panel shows "Create Custom Task" button
- [ ] Right panel shows "Configuration", "Worker Nodes", "Execution", "Logs" tabs

### Worker GUI Setup (Need 1-4 workers)
- [ ] Worker 1 started: `python3 gui_launcher.py` → Select "Worker" (Port 6000)
- [ ] Worker 1 service started: Green "Start Service" button clicked
- [ ] Worker 1 logs show: `✓ Worker server started on 127.0.0.1:6000`
- [ ] Worker 2 started (optional): Port 6001
- [ ] Worker 2 service started: Green button clicked
- [ ] Worker 3 started (optional): Port 6002
- [ ] Worker 3 service started: Green button clicked
- [ ] All worker logs show successful startup

### Network Connectivity
- [ ] Master can see workers in "Worker Nodes" tab (auto-discovered or added)
- [ ] At least 1 worker connection shows: `127.0.0.1:6000` (or similar)
- [ ] "Test Connection" button works for each worker
- [ ] Each worker shows ✓ in connection test
- [ ] Master "Logs" tab shows discovery messages

---

## ✅ Custom Task Creation Checklist

### Before Opening Task Dialog
- [ ] Executor function code is ready (copied from examples)
- [ ] Aggregator function code is ready (copied from examples)
- [ ] Code tested locally or from example file
- [ ] No syntax errors in code (verified via CUSTOM_TASK_QUICK_REFERENCE.md)

### Open Custom Task Dialog
- [ ] Click "Create Custom Task" button in left panel
- [ ] Dialog window opens with 3 text areas
- [ ] Task Name field is empty and ready
- [ ] Description field is empty and ready
- [ ] Executor Code shows default placeholder
- [ ] Aggregator Code shows default placeholder

### Fill Task Information
- [ ] Task Name entered (lowercase, underscores): e.g., `hash_crack`
- [ ] Description entered (optional): e.g., `Crack 4-digit PIN`
- [ ] Task Name doesn't conflict with existing task names

### Add Executor Code
- [ ] Clicked in Executor Code text area
- [ ] Selected all default text (Ctrl+A)
- [ ] Deleted default text
- [ ] Pasted executor function code
- [ ] Code contains: `def executor(payload, progress_cb):`
- [ ] Code has proper indentation
- [ ] Code returns dict with `"status"` key
- [ ] Code calls `progress_cb()` at least once
- [ ] No syntax errors visible (red underlines in editor)

### Add Aggregator Code
- [ ] Clicked in Aggregator Code text area
- [ ] Selected all default text (Ctrl+A)
- [ ] Deleted default text
- [ ] Pasted aggregator function code
- [ ] Code contains: `def aggregator(results):`
- [ ] Code has proper indentation
- [ ] Code returns dict with results
- [ ] Code handles `results` list safely
- [ ] No syntax errors visible

### Register Task
- [ ] Scrolled down to see "Register Task" button
- [ ] Clicked "Register Task" button
- [ ] Success message appeared: `Task '...' registered!`
- [ ] Dialog closed automatically
- [ ] Returned to main Master GUI

### Verify Registration
- [ ] Click "Refresh Tasks" button in left panel
- [ ] New task appears in task list
- [ ] Task name matches what you created
- [ ] Task description shows in list
- [ ] Task is selectable (click on it)

---

## ✅ Task Execution Checklist

### Select Task
- [ ] Clicked task in left panel task list
- [ ] Task is highlighted in list
- [ ] Logs show: `[time] Task selected: <task_name>`
- [ ] Configuration tab shows selected task name
- [ ] Configuration tab shows task description

### Verify Worker Nodes
- [ ] Went to "Worker Nodes" tab
- [ ] At least 1 worker node listed (e.g., 127.0.0.1:6000)
- [ ] Node address format is correct: IP:Port
- [ ] Selected one worker node
- [ ] Clicked "Test Connection" button
- [ ] Success message or ✓ appears
- [ ] Logs show connection test result

### Prepare Execution
- [ ] Went to "Execution" tab
- [ ] Progress bar is at 0%
- [ ] "Execute Task" button is visible and enabled
- [ ] Results text box is visible and empty
- [ ] All workers still showing as connected

### Execute Task
- [ ] Clicked "Execute Task" button
- [ ] Button changed to red "Stop" button
- [ ] Progress bar started updating
- [ ] Logs show: `[time] Starting: <task_name>`
- [ ] Logs show: `[time] Sending to X node(s): ...`
- [ ] Logs show payload information

### Monitor Execution
- [ ] Watched progress bar increment
- [ ] Logs updated with status messages
- [ ] No error messages in logs (check for ✗)
- [ ] Progress reached 100%
- [ ] Execution completed in reasonable time (see CUSTOM_TASK_QUICK_REFERENCE.md)

### Check Results
- [ ] Results text box populated with output
- [ ] Results are valid JSON (formatted nicely)
- [ ] Results contain: `"status": "success"`
- [ ] Results contain expected output fields
- [ ] Logs show: `✓ Task execution completed successfully`
- [ ] "Execute Task" button is enabled again

---

## ✅ Results Validation Checklist

### Result Format
- [ ] Result is a valid JSON object
- [ ] Result has `"task"` field with task name
- [ ] Result has `"status"` field set to "success"
- [ ] Result has expected output fields
- [ ] No `"status": "error"` in final result

### Result Content
- [ ] Values make sense (e.g., sums are correct)
- [ ] Data types are correct (numbers are numbers, strings are strings)
- [ ] Arrays/lists are properly formatted
- [ ] No null or empty unexpected values
- [ ] Metadata fields present (if applicable)

### Export Results (Optional)
- [ ] Clicked "Export Results" button
- [ ] File save dialog opened
- [ ] Selected location and filename
- [ ] Clicked "Save"
- [ ] Success message appeared
- [ ] JSON file created with results
- [ ] File is readable and valid JSON

---

## ✅ Troubleshooting Checklist

### If Task Won't Register

- [ ] Check executor function name is exactly: `executor`
- [ ] Check aggregator function name is exactly: `aggregator`
- [ ] Verify no syntax errors in code (red underlines)
- [ ] Verify proper indentation (4 spaces per level)
- [ ] Verify no special characters in task name
- [ ] Try with example code from CUSTOM_TASK_EXAMPLES.md
- [ ] Clear error dialog and try again

### If Execution Fails

- [ ] Check Logs tab for error messages
- [ ] Verify all workers are still connected
- [ ] Click "Test Connection" to verify workers
- [ ] Try test with built-in task first (e.g., range_sum)
- [ ] Check if workers have required Python modules
- [ ] Verify network connectivity between master and workers
- [ ] Check if ports are open and not blocked

### If No Results Returned

- [ ] Check Logs tab for error messages
- [ ] Verify workers actually executed (check worker logs)
- [ ] Verify executor returns valid dict
- [ ] Verify aggregator processes results correctly
- [ ] Try with fewer workers first
- [ ] Check if execution timed out (check timeout settings)

### If Progress Bar Doesn't Update

- [ ] Verify executor calls `progress_cb()` inside loops
- [ ] Verify progress_cb is called with values 0.0-1.0
- [ ] Check if task is actually executing (see worker logs)
- [ ] Try with longer-running task to see updates

---

## ✅ Task-Specific Checklist: Hash Crack

### Before Execution
- [ ] Target hash is valid (32 char MD5, 64 char SHA256, etc.)
- [ ] Hash is lowercase (will be converted, but verify)
- [ ] Hash type is supported: "md5", "sha256", or "sha1"
- [ ] Range is valid: start < end, both 0-9999 for 4-digit PIN

### During Execution
- [ ] Progress updates every 250-500 checks
- [ ] Logs show task progressing
- [ ] Execution time is reasonable (under 5 seconds)

### After Execution
- [ ] Result shows `"found": true` or `"found": false`
- [ ] If found, result shows `"password": "xxxx"` (4 digits)
- [ ] Result shows which range found the password
- [ ] Result shows total ranges checked

---

## ✅ Task-Specific Checklist: Prime Checker

### Before Execution
- [ ] Numbers array is populated with integers
- [ ] Numbers are reasonable (not too large, under 1,000,000)
- [ ] Array has at least 1 number

### During Execution
- [ ] Progress updates regularly
- [ ] No timeout errors

### After Execution
- [ ] Result shows count of primes found
- [ ] Result shows list of prime numbers
- [ ] Result shows total numbers checked
- [ ] Prime numbers are actually prime (optional: verify manually)

---

## ✅ Post-Execution Checklist

### Clean Up
- [ ] Exported results if needed
- [ ] Closed results dialog if popup appeared
- [ ] Master GUI still responsive
- [ ] Workers still connected (if continuing with more tasks)

### For Next Execution
- [ ] Reset progress bar: Optional, happens automatically
- [ ] Clear results box: Optional, happens automatically
- [ ] Select new task or same task again
- [ ] Verify workers still connected
- [ ] Ready for next execution

### Shut Down (When Done)
- [ ] Click "Stop Service" on all worker GUIs
- [ ] Close all worker GUI windows
- [ ] Close master GUI window
- [ ] Verify all processes ended (check terminal)

---

## 🎯 Quick Success Verification

### In ~2 minutes:
- [ ] Executor code runs without Python errors
- [ ] Aggregator code returns a dict
- [ ] Master and workers communicate successfully
- [ ] Task executes and returns results

### In ~5 minutes:
- [ ] Custom task is created in under 5 minutes
- [ ] Execution completes without errors
- [ ] Results can be exported to JSON
- [ ] Process repeatable for different tasks

### In ~30 minutes:
- [ ] Can create task, execute, and analyze results
- [ ] Understand executor and aggregator roles
- [ ] Can troubleshoot basic issues
- [ ] Ready to create custom tasks for real use cases

---

## 📊 Success Criteria Summary

| Criterion | Status |
|-----------|--------|
| Master GUI opens | ✓ / ✗ |
| Workers connect | ✓ / ✗ |
| Task registers | ✓ / ✗ |
| Task executes | ✓ / ✗ |
| Results returned | ✓ / ✗ |
| Results valid | ✓ / ✗ |
| Can export | ✓ / ✗ |

**Success = All ✓**

---

## 🚨 Red Flags to Watch

| Flag | Meaning | Solution |
|------|---------|----------|
| ✗ No workers listed | Workers not running | Start workers, click "Scan" |
| ✗ Test Connection fails | Network issue | Verify ports, restart worker |
| ✗ "Code Error" message | Syntax error in code | Check function names, indentation |
| ✗ Blank results box | Task failed silently | Check logs, test connection |
| ✗ Progress stuck at 0% | Executor not calling progress_cb | Add progress_cb() calls |
| ✗ Timeout error | Task taking too long | Optimize code, add more workers |
| ✗ Worker crashes | Code error on worker | Test executor locally first |

---

## ✨ Final Check Before Declaring Success

```
[ ] Master GUI launched
[ ] 1+ workers launched and services started
[ ] Workers discovered by master
[ ] Custom task created and registered
[ ] Task selected from list
[ ] Workers tested and connected
[ ] Task executed without errors
[ ] Results displayed in GUI
[ ] Results exported to file
[ ] All checklist items marked ✓
```

**When all items are ✓, you're ready to use custom tasks!** 🎉

---

**Print this checklist or bookmark it for quick reference during execution!**
