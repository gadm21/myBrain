# Task Management System V2 - Complete Implementation Guide

## 🎯 Overview

This document describes the **completely redesigned** task management system with:
- ✅ Separate `daily_tasks.json` storage (not in short_term_memory)
- ✅ Natural English SMS parsing ("My tasks today are...")
- ✅ Contribution graph with color-coded task status (red/blue/mixed)
- ✅ Daily reset job that sends morning SMS
- ✅ Full debugging throughout the system

---

## 📊 Contribution Graph Color System

### Color Meanings

| Color | Level | Meaning |
|-------|-------|---------|
| **Gray** | 0 | No tasks set for this day |
| **Red** | -2 | Tasks set but **none completed** |
| **Blue/Red Gradient** | -3 | **Some tasks done, some not** (partial completion) |
| **Light Blue** | 1 | 1 task completed |
| **Medium Blue** | 2 | 2 tasks completed |
| **Blue** | 3 | 3 tasks completed |
| **Dark Blue** | 4 | 4+ tasks completed |

### Visual Examples

```
🟦 Gray    = No tasks today
🟥 Red     = Set tasks: "Write paper | Review code | Exercise" - 0/3 done
🟦🟥 Mixed  = Set tasks: "Write paper | Review code | Exercise" - 1/3 done
🟦 Blue    = Set tasks: "Write paper | Review code | Exercise" - 3/3 done ✅
```

---

## 🗄️ Storage Architecture

### New Storage: `daily_tasks.json`

**Location:** Database → `files` table → `daily_tasks.json` (for user "gad")

**Structure:**
```json
{
  "date": "2026-01-04",
  "set_at": "2026-01-04T07:15:00.000000",
  "check_ins": 0,
  "last_check_in": null,
  "proactive_set": false,
  "tasks": {
    "primary": {
      "description": "Write methodology section",
      "progress": 45,
      "completed": false,
      "completed_at": null,
      "subtasks": []
    },
    "secondary": {
      "description": "Review 3 papers",
      "progress": 0,
      "completed": false,
      "completed_at": null
    },
    "bonus": {
      "description": "Update GitHub repo",
      "progress": 0,
      "completed": false,
      "completed_at": null
    }
  }
}
```

### Key Functions

**Storage:**
- `get_daily_tasks()` - Loads from `daily_tasks.json`
- `save_daily_tasks(tasks)` - Saves to `daily_tasks.json`

**Task Management:**
- `set_todays_tasks(primary, secondary, bonus)` - Sets tasks and updates contribution graph (red)
- `update_task_progress(task_type, progress)` - Updates progress and contribution graph
- `complete_task(task_type)` - Marks complete and updates contribution graph (blue)

**Contribution Graph:**
- `update_contribution_for_tasks_set(date)` - Marks day as red (tasks not done)
- `update_contribution_for_progress(tasks)` - Updates color based on completion status
- `get_contribution_data(days)` - Returns contribution data with color levels

---

## 📱 Natural English SMS Parsing

### Supported Patterns

**Multi-task format (pipe separator):**
```
Write paper | Review code | Exercise
```

**Natural English (single or multiple tasks):**
```
My tasks today are write paper, review code, and exercise
Tasks today are finish methodology and submit grant
Today I need to write paper
Today I will work on experiments
I need to finish the paper
My goals today are coding and writing
My plan is to finish chapter 3
```

### Keyword Detection

The system recognizes these natural language patterns:
- `my tasks today are`
- `tasks today are`
- `my tasks are`
- `tasks are`
- `today i need to`
- `today i will`
- `i need to`
- `i will`
- `planning to`
- `my goals today`
- `today's goals`
- `my plan is`

### Processing Flow

1. **SMS received** → Webhook endpoint
2. **Check for pipe separator** (`|`) → Multi-task mode
3. **Check for natural language keywords** → Extract task text
4. **Clean up keywords** from task description
5. **Set tasks** → `set_todays_tasks()`
6. **Update contribution graph** → Mark as red (not done)
7. **Send confirmation SMS** with XP and stats

---

## 🤖 AI Agent Integration

### Context Injection

When Thoth responds to any query, he now has access to:

```
=== GAD'S CURRENT TASKS (Today: 2026-01-04) ===
  - PRIMARY: Write methodology section - In Progress (45%)
  - SECONDARY: Review 3 papers - In Progress (0%)
  - BONUS: Update GitHub repo - In Progress (0%)

Gamification Stats: Level Master 🔥 | 1250 XP | Streak: 7 days

IMPORTANT: When Gad asks about his tasks, YOU MUST recall and tell him these tasks.
```

### Implementation

**File:** `aiagent/handler/query.py` (lines 245-288)

**Flow:**
1. `query_openai()` is called
2. Imports `get_daily_tasks()` from `periodic_intelligence`
3. Loads tasks from `daily_tasks.json`
4. Checks if date matches today
5. Formats task information
6. Injects into system prompt
7. Thoth can now recall and remind you of tasks

---

## ⏰ Daily Reset Job

### Purpose

Automatically sends morning SMS asking for tasks if none are set.

### Implementation

**File:** `server/daily_reset_job.py`

**Schedule:** Runs at **7:00 AM daily**

**Flow:**
1. Check if tasks exist for today
2. If yes → Skip (tasks already set)
3. If no → Send morning SMS with random template
4. SMS includes current stats (level, XP, streak)

### Running the Job

**Test immediately:**
```bash
cd myBrain/server
python daily_reset_job.py
```

**Start scheduler (runs continuously):**
```python
# In daily_reset_job.py, uncomment:
start_daily_reset_scheduler()
```

**Production deployment:**
Add to your process manager (PM2, systemd, etc.):
```bash
pm2 start daily_reset_job.py --name "thoth-daily-reset"
```

---

## 🔄 Complete Task Flow

### 1. Morning (7:00 AM)
```
Daily Reset Job → Check tasks → None found → Send SMS
```

**SMS Example:**
```
🌅 Good morning, Gad.

🔥 Master | 1250 XP 🔥 7 day streak!

New day. Set your tasks:
• PRIMARY: Your #1 must-do
• SECONDARY: Nice to have (optional)
• BONUS: Stretch goal (optional)

Format: task1 | task2 | task3
Or just send one task.

-𓂀 Thoth
```

### 2. You Set Tasks via SMS
```
SMS: "My tasks today are write paper, review code, and exercise"
```

**Backend Flow:**
1. Webhook receives SMS
2. Detects natural language pattern
3. Extracts: "write paper, review code, and exercise"
4. Parses as single task (no pipe separator)
5. Calls `set_todays_tasks(primary="write paper, review code, and exercise")`
6. Saves to `daily_tasks.json`
7. Updates contribution graph → **Red** (tasks set, not done)
8. Awards +10 XP
9. Sends confirmation SMS

**Or with pipe separator:**
```
SMS: "Write paper | Review code | Exercise"
```
Parses as 3 separate tasks (primary, secondary, bonus)

### 3. During the Day - Progress Updates
```
SMS: "50"  (updates primary task to 50% progress)
SMS: "done"  (marks primary task as complete)
```

**Backend Flow:**
1. Detects number → Progress update
2. Calls `update_task_progress("primary", 50)`
3. Updates `daily_tasks.json`
4. Calls `update_contribution_for_progress(tasks)`
5. Contribution graph updates:
   - 0/3 done → **Red**
   - 1/3 done → **Mixed** (blue/red gradient)
   - 3/3 done → **Blue** (all complete)

### 4. Ask Thoth About Tasks
```
You: "What are my tasks today?"
```

**AI Agent Flow:**
1. `query_openai()` called
2. Loads `daily_tasks.json` via `get_daily_tasks()`
3. Injects task context into system prompt
4. Thoth responds: "Your tasks today are: PRIMARY: Write paper (50% done), SECONDARY: Review code (not started), BONUS: Exercise (not started)"

### 5. Next Day (7:00 AM)
```
Daily Reset Job → Check tasks → Date mismatch → Send new morning SMS
```

Old tasks remain in `daily_tasks.json` but are ignored (date check fails).

---

## 🐛 Debugging

### Backend Logs

**Look for these patterns:**

**Task Setting:**
```
[TASK DEBUG] set_todays_tasks() called - primary: 'write paper', secondary: 'review code', bonus: 'exercise'
[TASK DEBUG] Setting tasks for date: 2026-01-04
[TASK DEBUG] Tasks object created: {...}
[TASK DEBUG] save_daily_tasks() called. Tasks: {...}
[TASK DEBUG] Daily tasks saved successfully
[TASK DEBUG] Contribution updated for tasks set on 2026-01-04
```

**Task Retrieval:**
```
[TASK DEBUG] get_daily_tasks() called
[TASK DEBUG] Daily tasks loaded: {...}
[TASK DEBUG] get_todays_task() called
[TASK DEBUG] ✅ Found tasks for today: {...}
```

**AI Agent:**
```
[TASK DEBUG - AI Agent] Fetching current task context from daily_tasks.json...
[TASK DEBUG - AI Agent] Task context added from daily_tasks.json: {...}
```

**Webhook (SMS):**
```
[TASK DEBUG] Processing SMS body: 'My tasks today are write paper'
[TASK DEBUG] Current task retrieved: {...}
[TASK DEBUG] Setting single task (replacing=False): 'write paper'
[TASK DEBUG] set_todays_tasks result: {...}
[TASK DEBUG] Task set successfully
```

### Database Query

**Check daily_tasks.json:**
```sql
SELECT 
  u.username,
  f.filename,
  f.content::text
FROM files f
JOIN users u ON f."userId" = u."userId"
WHERE u.username = 'gad' 
  AND f.filename = 'daily_tasks.json';
```

### Test Commands

**Set tasks via SMS:**
```
My tasks today are write paper | review code | exercise
```

**Update progress:**
```
50
```

**Complete task:**
```
done
```

**Ask Thoth:**
```
What are my tasks today?
What should I be working on?
```

---

## 📋 API Endpoints

### Get Current Tasks
```http
GET https://api.thothcraft.com/data/tasks/current
```

**Response:**
```json
{
  "success": true,
  "tasks": {
    "date": "2026-01-04",
    "tasks": {
      "primary": {
        "description": "Write paper",
        "progress": 50,
        "completed": false
      }
    }
  },
  "has_tasks": true
}
```

### Set Tasks
```http
POST https://api.thothcraft.com/data/tasks/set
Content-Type: application/json

{
  "primary": "Write methodology section",
  "secondary": "Review 3 papers",
  "bonus": "Update GitHub"
}
```

### Get Contribution Data
```http
GET https://api.thothcraft.com/data/gamification/contributions?days=365
```

**Response includes color levels:**
```json
{
  "success": true,
  "contributions": [
    {
      "date": "2026-01-04",
      "level": -2,  // Red - tasks not done
      "tasks_set": true,
      "total_tasks": 3,
      "completed_tasks": 0
    },
    {
      "date": "2026-01-03",
      "level": 3,  // Blue - 3 tasks done
      "tasks_set": true,
      "total_tasks": 3,
      "completed_tasks": 3
    }
  ]
}
```

---

## 🎨 Frontend Integration

### Contribution Graph Component

**File:** `me/src/views/Home.vue`

**CSS Classes:**
```css
.contribution-cell.level-0   /* Gray - no tasks */
.contribution-cell.level--2  /* Red - tasks not done */
.contribution-cell.level--3  /* Mixed - partial completion */
.contribution-cell.level-1   /* Light blue - 1 task done */
.contribution-cell.level-2   /* Medium blue - 2 tasks done */
.contribution-cell.level-3   /* Blue - 3 tasks done */
.contribution-cell.level-4   /* Dark blue - 4+ tasks done */
```

**Data Fetching:**
```javascript
const fetchThothData = async () => {
  const response = await fetch('https://api.thothcraft.com/data/gamification')
  const data = await response.json()
  // Contribution data includes level for coloring
}
```

---

## 🚀 Deployment Checklist

- [ ] Backend changes deployed
- [ ] Database has `daily_tasks.json` file created
- [ ] Daily reset job running (PM2 or systemd)
- [ ] Frontend updated with new CSS classes
- [ ] Twilio webhook configured
- [ ] Test task setting via SMS
- [ ] Test natural language parsing
- [ ] Test contribution graph colors
- [ ] Test AI agent task recall
- [ ] Verify daily reset job runs at 7 AM

---

## 📝 Key Changes from V1

| Feature | V1 (Old) | V2 (New) |
|---------|----------|----------|
| **Storage** | `short_term_memory.json` → `daily_accountability` key | `daily_tasks.json` (separate file) |
| **SMS Parsing** | Basic keywords only | Natural English support |
| **Contribution Graph** | Blue gradient only | Red/Blue/Mixed based on completion |
| **Daily Reset** | Manual/periodic messages | Automated job at 7 AM |
| **AI Context** | No task context | Full task context injected |
| **Debugging** | Minimal | Comprehensive `[TASK DEBUG]` logs |

---

## 🔧 Troubleshooting

### Tasks not showing in contribution graph
1. Check if `update_contribution_for_tasks_set()` is called
2. Verify `daily_history` in gamification stats
3. Check frontend is fetching `/data/gamification/contributions`

### Thoth can't recall tasks
1. Check `[TASK DEBUG - AI Agent]` logs
2. Verify `get_daily_tasks()` returns data for today
3. Ensure date in `daily_tasks.json` matches today

### Natural language parsing not working
1. Check webhook logs for `[TASK DEBUG]`
2. Verify keyword is in the cleanup list
3. Test with pipe separator first (`task1 | task2`)

### Daily reset job not running
1. Check if job is scheduled: `pm2 list`
2. Verify Twilio credentials in environment
3. Test manually: `python daily_reset_job.py`

---

**Last Updated:** 2026-01-04  
**Version:** 2.0 (Complete Redesign)
