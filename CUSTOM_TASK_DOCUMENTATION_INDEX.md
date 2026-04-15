# Custom Task Documentation - Complete Guide

Welcome! You now have comprehensive documentation for creating and running custom tasks in the Distributed Computing System.

## 📚 Documentation Files Created

### 1. **CUSTOM_TASK_GUIDE.md** - START HERE! ⭐
**Purpose:** Complete overview with examples  
**Best for:** Understanding the full workflow  
**Contains:**
- Overview of the custom task system
- Step-by-step GUI instructions
- 3 complete working examples
- Troubleshooting guide
- Best practices
- Quick reference table

**Read this first to understand the basics!**

---

### 2. **CUSTOM_TASK_VISUAL_GUIDE.md** - Diagrams & Flows
**Purpose:** Visual representations of how everything works  
**Best for:** Visual learners, understanding architecture  
**Contains:**
- GUI dialog screenshot representation
- Task execution flow diagrams
- Data flow diagrams
- Message format examples
- Error handling flows
- Task lifecycle diagram

**Read this to understand the system architecture!**

---

### 3. **CUSTOM_TASK_EXAMPLES.md** - Copy & Paste Code ⭐
**Purpose:** Ready-to-use code examples  
**Best for:** Quick implementation  
**Contains:**
- 6 complete working examples:
  1. Hash Cracking (4-digit PIN)
  2. Prime Number Checker
  3. Text Word Frequency Counter
  4. Number Sum Range Calculator
  5. Temperature Data Processor
  6. Simple Echo Task (for testing)
- Testing checklist
- Code validation instructions

**Use this when you want to copy-paste working code!**

---

### 4. **CUSTOM_TASK_QUICK_REFERENCE.md** - Cheat Sheet
**Purpose:** Quick lookup reference  
**Best for:** Quick answers while coding  
**Contains:**
- Function templates
- 5-step GUI workflow
- 6-step execution workflow
- Payload dictionary reference
- Common patterns
- Do's and Don'ts
- Debugging tips
- Test code snippets
- Progress reporting guide

**Bookmark this for quick lookups!**

---

### 5. **CUSTOM_TASK_WALKTHROUGH.md** - Step-by-Step Tutorial ⭐
**Purpose:** Detailed walkthrough of hash cracking example  
**Best for:** First-time users, learning by doing  
**Contains:**
- Part 1: Setup (5 min)
- Part 2: Create Task (10 min)
- Part 3: Execute Task (5 min)
- Part 4: Try Another Hash (Optional)
- Part 5: Understanding Results
- Part 6: Export Results
- Troubleshooting guide
- Quick checklist
- Common Q&A

**Follow this step-by-step for your first task!**

---

## 🚀 Quick Start (5 Minutes)

### For Complete Beginners:
1. Read: **CUSTOM_TASK_GUIDE.md** (10 min)
2. Follow: **CUSTOM_TASK_WALKTHROUGH.md** (30 min)
3. Reference: **CUSTOM_TASK_QUICK_REFERENCE.md** (as needed)

### For Experienced Developers:
1. Skim: **CUSTOM_TASK_GUIDE.md** (5 min)
2. Copy: Code from **CUSTOM_TASK_EXAMPLES.md** (2 min)
3. Use: **CUSTOM_TASK_QUICK_REFERENCE.md** (as needed)

---

## 📖 What to Read for Different Needs

| Your Situation | Read This | Then This |
|---|---|---|
| **First time user** | CUSTOM_TASK_WALKTHROUGH.md | CUSTOM_TASK_GUIDE.md |
| **Need working code** | CUSTOM_TASK_EXAMPLES.md | CUSTOM_TASK_QUICK_REFERENCE.md |
| **Understand how it works** | CUSTOM_TASK_VISUAL_GUIDE.md | CUSTOM_TASK_GUIDE.md |
| **Quick question** | CUSTOM_TASK_QUICK_REFERENCE.md | CUSTOM_TASK_EXAMPLES.md |
| **Stuck, need help** | CUSTOM_TASK_GUIDE.md (troubleshooting) | CUSTOM_TASK_WALKTHROUGH.md |

---

## 🎯 Common Tasks

### Task: Create Hash Cracking Task
**Time:** ~20 minutes  
**Files to use:**
1. CUSTOM_TASK_EXAMPLES.md → Copy executor & aggregator (5 min)
2. CUSTOM_TASK_WALKTHROUGH.md → Follow Part 2: Create Task (10 min)
3. CUSTOM_TASK_WALKTHROUGH.md → Follow Part 3: Execute Task (5 min)

### Task: Create Prime Number Checker
**Time:** ~25 minutes  
1. CUSTOM_TASK_EXAMPLES.md → Copy "Prime Number Checker" code (5 min)
2. CUSTOM_TASK_QUICK_REFERENCE.md → Check patterns (2 min)
3. CUSTOM_TASK_GUIDE.md → Follow "Create Custom Task" section (10 min)
4. Execute and test (8 min)

### Task: Create Your Own Custom Task
**Time:** ~1 hour  
1. CUSTOM_TASK_QUICK_REFERENCE.md → Review executor/aggregator templates (10 min)
2. CUSTOM_TASK_GUIDE.md → Review best practices (10 min)
3. CUSTOM_TASK_EXAMPLES.md → Study patterns in examples (15 min)
4. Create and test your task (25 min)

### Task: Debug Why Task Isn't Working
**Time:** ~15 minutes  
1. CUSTOM_TASK_QUICK_REFERENCE.md → Debugging tips section
2. CUSTOM_TASK_GUIDE.md → Troubleshooting section
3. CUSTOM_TASK_EXAMPLES.md → Testing checklist

---

## 📋 Complete Workflow Summary

```
1. START MASTER GUI
   └─ Select "Master" mode

2. START WORKER GUIs (3 terminals)
   └─ Each selects "Worker" mode
   └─ Each clicks "Start Service"

3. MASTER GUI: Create Custom Task
   └─ Click "Create Custom Task" button
   └─ Fill in task name
   └─ Paste executor code
   └─ Paste aggregator code
   └─ Click "Register Task"

4. MASTER GUI: Execute Task
   └─ Select task from list
   └─ Go to "Execution" tab
   └─ Click "Execute Task"
   └─ Monitor progress in logs
   └─ View results when done

5. EXPORT RESULTS
   └─ Click "Export Results" button
   └─ Save to JSON file
```

---

## 🔑 Key Concepts

### Executor
- Runs on worker nodes
- Processes chunk of data
- Reports progress with `progress_cb(0-1)`
- Returns dict with `"status": "success"` or `"error"`

### Aggregator
- Runs on master after all workers finish
- Combines results from all workers
- Returns final answer as dict
- Handles both success and error cases

### Payload
- Input parameters passed to executor
- Contains: chunk_size, start, end, numbers, or custom params
- Accessed via: `payload.get("key", default)`

### Progress Callback
- Function to report completion %
- Call as: `progress_cb(0.5)` for 50%
- Must call `progress_cb(1.0)` when done
- Keeps UI responsive

---

## 📚 File Organization

```
/home/aromal/Desktop/MAIN_PROJECT_FINAL/
│
├── CUSTOM_TASK_GUIDE.md               ⭐ START HERE
├── CUSTOM_TASK_VISUAL_GUIDE.md        Diagrams & flows
├── CUSTOM_TASK_EXAMPLES.md            ⭐ Copy-paste code
├── CUSTOM_TASK_QUICK_REFERENCE.md     Cheat sheet
├── CUSTOM_TASK_WALKTHROUGH.md         ⭐ Step-by-step
│
├── module3_execution/
│   └── tasks.py                        Task registration
├── module4_ui/
│   ├── master_gui.py                   Master interface
│   ├── worker_gui.py                   Worker interface
│   └── gui_launcher.py                 GUI entry point
```

---

## ✅ Before You Start

Make sure you have:
- [ ] Python 3.7+
- [ ] tkinter installed (`apt-get install python3-tk`)
- [ ] Network accessible between master and workers
- [ ] At least 1 worker node running
- [ ] Basic Python knowledge

---

## 💡 Pro Tips

1. **Test Locally First**
   - Run executor code locally in terminal
   - Verify it works before pasting in GUI

2. **Start Simple**
   - Use simple tasks first (echo, sum, etc.)
   - Progress to complex tasks

3. **Monitor Logs**
   - Always watch Logs tab during execution
   - Errors show up there first

4. **Test Connections**
   - Click "Test Connection" before executing
   - Verify all workers respond

5. **Use Progress Callbacks**
   - Report progress every 10% of work
   - Helps UI stay responsive

6. **Handle Errors**
   - Always return error dict if something fails
   - Aggregator should handle mixed success/error

---

## 🆘 Quick Help

### Where is the executor code in GUI?
→ CUSTOM_TASK_EXAMPLES.md

### How do I debug code errors?
→ CUSTOM_TASK_QUICK_REFERENCE.md (Debugging Tips section)

### Workers not showing up?
→ CUSTOM_TASK_GUIDE.md (Troubleshooting section)

### What should progress_cb be?
→ CUSTOM_TASK_QUICK_REFERENCE.md (Progress Reporting Convention)

### Can I attach files?
→ CUSTOM_TASK_GUIDE.md (Step 2 section)

### How do I export results?
→ CUSTOM_TASK_WALKTHROUGH.md (Part 6)

---

## 🎓 Learning Path

### Beginner Path (90 minutes)
1. Read CUSTOM_TASK_GUIDE.md (15 min)
2. Follow CUSTOM_TASK_WALKTHROUGH.md (45 min)
3. Try Example 2 from CUSTOM_TASK_EXAMPLES.md (30 min)

### Intermediate Path (2 hours)
1. Skim CUSTOM_TASK_VISUAL_GUIDE.md (15 min)
2. Study CUSTOM_TASK_EXAMPLES.md all examples (30 min)
3. Understand patterns in CUSTOM_TASK_QUICK_REFERENCE.md (15 min)
4. Create 2 custom tasks (60 min)

### Advanced Path (3+ hours)
1. Deep dive CUSTOM_TASK_GUIDE.md best practices (30 min)
2. Analyze CUSTOM_TASK_EXAMPLES.md code patterns (30 min)
3. Create complex custom tasks (90+ min)
4. Experiment with scaling (60+ min)

---

## 📞 Support Resources

| Issue | Resource |
|-------|----------|
| Code examples | CUSTOM_TASK_EXAMPLES.md |
| Syntax errors | CUSTOM_TASK_QUICK_REFERENCE.md |
| Workflow issues | CUSTOM_TASK_WALKTHROUGH.md |
| Architecture questions | CUSTOM_TASK_VISUAL_GUIDE.md |
| General questions | CUSTOM_TASK_GUIDE.md |

---

## 🎉 Success Indicators

You've successfully mastered custom tasks when you can:
- [ ] Create and register a custom task in under 5 minutes
- [ ] Execute a task without consulting documentation
- [ ] Debug task issues by reading logs
- [ ] Write executor/aggregator code from scratch
- [ ] Scale tasks across multiple workers effectively

---

## 🚀 Next Steps

1. ✅ **Done reading?** Start with CUSTOM_TASK_WALKTHROUGH.md
2. ✅ **Task created?** Try creating another task
3. ✅ **Comfortable?** Build something useful with your data
4. ✅ **Scaling?** Add more workers and test performance
5. ✅ **Mastering?** Share your custom tasks with others!

---

**Happy distributed computing! 🚀**

---

## Version Info
- Created: 2026-04-08
- Last Updated: 2026-04-08
- Examples Tested: ✅ Hash Crack, Prime Check, Text Processing
- Compatibility: Python 3.7+, Linux/Mac/Windows

---

**Questions?** Check the relevant documentation file above!
