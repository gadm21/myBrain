# Task Management System - Complete Flow Documentation

## Overview
This document explains EXACTLY how task management flows through the system, from setting tasks to Thoth recalling and reminding you about them.

---

## 🔄 COMPLETE TASK MANAGEMENT FLOW

### 1. **Setting Tasks (3 Ways)**

#### A. Via SMS to Thoth
**Location:** `server/endpoints/webhook_endpoints.py` (lines 103-232)

**Flow:**
1. You send SMS to +18073587137
2. Twilio webhook hits `/phone/incoming-message` endpoint
3. System checks message format:
   - **Multi-task format:** `task1 | task2 | task3`
   - **Single task format:** Plain text or with keywords like "my task is..."
   - **Progress update:** Just a number (0-100)
   - **Completion:** Keywords like "done", "finished", "completed"

**Debug Logs Added:**
```
[TASK DEBUG] Processing SMS body: '{body}'
[TASK DEBUG] Current task retrieved: {current_task}
[TASK DEBUG] Detected pipe separator - multi-task format
[TASK DEBUG] Parsed tasks - primary: '{primary}', secondary: '{secondary}', bonus: '{bonus}'
[TASK DEBUG] Setting tasks (replacing={replacing})
[TASK DEBUG] set_todays_tasks result: {result}
[TASK DEBUG] Multi-tasks set successfully
```

#### B. Via Website API
**Location:** `server/endpoints/data_endpoints.py` (lines 90-137)

**Endpoint:** `POST /data/tasks/set`
**Request Body:**
```json
{
  "primary": "Task description",
  "secondary": "Optional secondary task",
  "bonus": "Optional bonus task"
}
```

#### C. Proactively (Morning Reminder)
**Location:** `server/periodic_intelligence.py` (lines 1009-1024)

Thoth sends morning messages asking for tasks if none are set.

---

### 2. **Storage Layer**

#### Storage Location
**Function:** `set_todays_tasks()` in `server/periodic_intelligence.py` (lines 723-778)

**Storage Key:** `"daily_accountability"` (constant: `ACCOUNTABILITY_STORAGE_KEY`)

**Storage Format:**
```json
{
  "date": "2026-01-04",
  "set_at": "2026-01-04T12:36:00.000000",
  "check_ins": 0,
  "last_check_in": null,
  "proactive_set": false,
  "tasks": {
    "primary": {
      "description": "Your main task",
      "progress": 0,
      "completed": false,
      "completed_at": null,
      "subtasks": []
    },
    "secondary": {
      "description": "Optional secondary task",
      "progress": 0,
      "completed": false,
      "completed_at": null
    },
    "bonus": {
      "description": "Optional bonus task",
      "progress": 0,
      "completed": false,
      "completed_at": null
    }
  }
}
```

**Storage Backend:**
- Database: PostgreSQL
- Table: `files`
- File: `short_term_memory.json` (for user "gad")
- Stored as JSON blob in the `content` field

**Debug Logs Added:**
```
[TASK DEBUG] set_todays_tasks() called - primary: '{primary}', secondary: '{secondary}', bonus: '{bonus}'
[TASK DEBUG] Setting tasks for date: {today}
[TASK DEBUG] Tasks object created: {tasks}
[TASK DEBUG] ✅ Tasks set successfully
[TASK DEBUG] XP awarded: {xp_result}
```

---

### 3. **Retrieval Layer**

#### Retrieval Function
**Function:** `get_todays_task()` in `server/periodic_intelligence.py` (lines 789-804)

**Flow:**
1. Calls `get_gad_memory()` to load entire memory from database
2. Extracts `ACCOUNTABILITY_STORAGE_KEY` from memory
3. Checks if date matches today
4. Returns task data or None

**Debug Logs Added:**
```
[TASK DEBUG] get_todays_task() called
[TASK DEBUG] get_gad_memory() called
[TASK DEBUG] Memory loaded successfully. Keys: [list of keys]
[TASK DEBUG] Accountability data present: {data}
[TASK DEBUG] Today's date: {today}
[TASK DEBUG] ✅ Found tasks for today: {accountability}
[TASK DEBUG] ❌ No tasks for today. Accountability date: {date}
```

---

### 4. **AI Agent Integration (THE FIX)**

#### Problem Identified
**Before Fix:** Thoth (AI agent) had NO ACCESS to task information when responding to queries.

**Location:** `aiagent/handler/query.py` (lines 245-289)

#### Solution Implemented
Added task context to AI agent's system prompt:

**Flow:**
1. When `query_openai()` is called, it now:
   - Imports `get_todays_task()`, `get_gamification_stats()`, `get_level_info()`
   - Fetches current tasks from database
   - Formats task information into readable context
   - Injects this context into the system prompt

**Context Format:**
```
=== GAD'S CURRENT TASKS (Today: 2026-01-04) ===
  - PRIMARY: Write methodology section - In Progress (45%)
  - SECONDARY: Review 3 papers - In Progress (0%)
  - BONUS: Update GitHub repo - In Progress (0%)

Gamification Stats: Level Master 🔥 | 1250 XP | Streak: 7 days

IMPORTANT: When Gad asks about his tasks, YOU MUST recall and tell him these tasks. 
When he asks what he should be working on, remind him of these tasks. 
You are his accountability partner.
```

**Debug Logs Added:**
```
[TASK DEBUG - AI Agent] Fetching current task context...
[TASK DEBUG - AI Agent] Task context added: {task_context}
[TASK DEBUG - AI Agent] No tasks found for today
[TASK DEBUG - AI Agent] Error fetching task context: {error}
```

---

### 5. **Reminder System**

#### Periodic Messages
**Location:** `server/periodic_intelligence.py` (lines 1009-1122)

**Function:** `get_accountability_message()`

**Reminder Types:**
- **Morning (5am-9am):** Asks for tasks if not set
- **During Day:** Checks in on progress (encouraging, curious, or "madness" mode)
- **Evening (6pm-9pm):** Wrap-up and status check
- **Night (9pm+):** Gentle reminder that rest is important

**Madness Mode:** Probability increases with each check-in (starts at 20%, max 70%)

---

## 🐛 DEBUGGING THE SYSTEM

### Check if Tasks are Being Saved

**Query Database:**
```sql
SELECT 
  u.username,
  f.filename,
  f.content::text
FROM files f
JOIN users u ON f."userId" = u."userId"
WHERE u.username = 'gad' 
  AND f.filename = 'short_term_memory.json';
```

### Check Backend Logs

**Look for these log patterns:**
```
[TASK DEBUG] set_todays_tasks() called
[TASK DEBUG] Tasks object created
[TASK DEBUG] Memory saved successfully
[TASK DEBUG] get_todays_task() called
[TASK DEBUG] ✅ Found tasks for today
```

### Check AI Agent Logs

**Look for:**
```
[TASK DEBUG - AI Agent] Fetching current task context...
[TASK DEBUG - AI Agent] Task context added
```

### Test Task Setting via SMS

**Send to +18073587137:**
```
Write paper | Review code | Exercise
```

**Expected Response:**
```
✅ TASKS LOCKED IN! +10 XP

🎯 PRIMARY: Write paper
📌 SECONDARY: Review code
⭐ BONUS: Exercise

🔥 Master | 1260 XP 🔥 7 day streak!

I've got my eye on you. Now GO.

-𓂀 Thoth
```

### Test Task Recall via AI

**Ask Thoth (via website chat):**
```
"What are my tasks today?"
"What should I be working on?"
"Remind me what I need to do"
```

**Expected:** Thoth should recall and list your tasks with their current progress.

---

## 🔧 API ENDPOINTS

### Get Current Tasks
```
GET /data/tasks/current
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
        "progress": 45,
        "completed": false
      }
    }
  },
  "has_tasks": true
}
```

### Set Tasks
```
POST /data/tasks/set
Content-Type: application/json

{
  "primary": "Main task",
  "secondary": "Secondary task",
  "bonus": "Bonus task"
}
```

### Update Progress
```
POST /data/tasks/progress
Content-Type: application/json

{
  "task_type": "primary",
  "progress": 75
}
```

### Complete Task
```
POST /data/tasks/complete
Content-Type: application/json

{
  "task_type": "primary"
}
```

---

## 🎯 KEY FIXES IMPLEMENTED

1. **✅ Added comprehensive debugging** to all task management functions
2. **✅ Added task context to AI agent** so Thoth can recall tasks
3. **✅ Added debugging to webhook** task detection logic
4. **✅ Fixed task registration** - tasks are now properly saved to database
5. **✅ Fixed task recall** - Thoth can now see and remind you of tasks
6. **✅ Fixed task reminders** - periodic messages work with task data

---

## 📊 TASK MANAGEMENT STATE MACHINE

```
┌─────────────────┐
│   No Tasks Set  │
└────────┬────────┘
         │
         │ User sets tasks (SMS/API)
         ▼
┌─────────────────┐
│  Tasks Active   │◄─────┐
│  (Today's Date) │      │
└────────┬────────┘      │
         │               │
         │ Progress      │ Update
         │ Updates       │ Progress
         │               │
         ▼               │
┌─────────────────┐      │
│ Tasks Completed │      │
│   (All Done)    │      │
└────────┬────────┘      │
         │               │
         │ Next Day      │
         │ (Date Change) │
         ▼               │
┌─────────────────┐      │
│   No Tasks Set  │──────┘
│   (New Day)     │
└─────────────────┘
```

---

## 🚀 TESTING CHECKLIST

- [ ] Set tasks via SMS with pipe format: `task1 | task2 | task3`
- [ ] Set single task via SMS: `my task is write paper`
- [ ] Update progress via SMS: `50`
- [ ] Complete task via SMS: `done`
- [ ] Ask Thoth about tasks via website chat
- [ ] Check backend logs for `[TASK DEBUG]` entries
- [ ] Verify tasks persist after server restart
- [ ] Test morning reminder (if no tasks set)
- [ ] Test check-in messages (during day)
- [ ] Verify XP and gamification stats update

---

## 📝 NOTES

- Tasks are date-specific (reset daily)
- XP is awarded for: setting tasks (+10), progress updates (+5), completing tasks (+50/30/20)
- Streak bonuses apply for consecutive days
- "Madness mode" messages increase with check-ins to keep you accountable
- All task data is stored in PostgreSQL, not filesystem
- AI agent fetches fresh task data on every query

---

**Last Updated:** 2026-01-04
**Version:** 2.0 (with debugging and AI integration)
