"""Data management endpoints."""

from fastapi import APIRouter
from typing import Dict, Any, List
from pydantic import BaseModel

router = APIRouter(prefix="/data", tags=["data"])


class TaskSetRequest(BaseModel):
    primary: str
    secondary: str = None
    bonus: str = None


class TaskProgressRequest(BaseModel):
    task_type: str  # "primary", "secondary", or "bonus"
    progress: int   # 0-100


class TaskCompleteRequest(BaseModel):
    task_type: str  # "primary", "secondary", or "bonus"


@router.get(
    "/gamification",
    summary="Get gamification stats and contribution data",
    description="Returns XP, level, streak, and daily contribution history for the accountability system"
)
async def get_gamification_data() -> Dict[str, Any]:
    """Get gamification stats for display on the website."""
    try:
        from server.periodic_intelligence import (
            get_gamification_stats, get_level_info, get_contribution_data, get_daily_summary
        )
        
        stats = get_gamification_stats()
        level_info = get_level_info(stats["total_xp"])
        contributions = get_contribution_data(365)  # Last year
        summary = get_daily_summary()
        
        return {
            "success": True,
            "data": {
                "level": level_info,
                "stats": {
                    "total_xp": stats["total_xp"],
                    "current_streak": stats["current_streak"],
                    "longest_streak": stats["longest_streak"],
                    "tasks_completed": stats["tasks_completed"],
                    "perfect_days": stats["perfect_days"],
                    "badges": stats.get("badges", [])
                },
                "contributions": contributions,
                "today": summary
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


@router.get(
    "/gamification/contributions",
    summary="Get contribution grid data",
    description="Returns daily XP data for GitHub-style contribution grid"
)
async def get_contributions(days: int = 365) -> Dict[str, Any]:
    """Get contribution data for the grid visualization."""
    try:
        from server.periodic_intelligence import get_contribution_data
        
        contributions = get_contribution_data(min(days, 365))
        
        return {
            "success": True,
            "contributions": contributions
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "contributions": []
        }


@router.post(
    "/tasks/set",
    summary="Set today's tasks proactively",
    description="Allows setting primary, secondary, and bonus tasks before Thoth asks"
)
async def set_tasks_proactively(task_request: TaskSetRequest) -> Dict[str, Any]:
    """Set today's tasks proactively through the website."""
    try:
        from server.periodic_intelligence import (
            set_todays_tasks_proactively, get_todays_task, get_stats_line
        )
        
        # Check if tasks are already set for today
        current_task = get_todays_task()
        if current_task:
            return {
                "success": False,
                "error": "Tasks already set for today. Update progress or complete existing tasks.",
                "current_tasks": current_task
            }
        
        # Set the new tasks
        result = set_todays_tasks_proactively(
            primary=task_request.primary,
            secondary=task_request.secondary,
            bonus=task_request.bonus
        )
        
        if result:
            stats_line = get_stats_line()
            return {
                "success": True,
                "message": "Tasks set successfully!",
                "tasks": result["tasks"],
                "xp_awarded": result.get("xp", {}).get("xp_awarded", 0),
                "stats_line": stats_line
            }
        else:
            return {
                "success": False,
                "error": "Failed to set tasks"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get(
    "/tasks/current",
    summary="Get today's current tasks",
    description="Returns the tasks set for today, if any"
)
async def get_current_tasks() -> Dict[str, Any]:
    """Get today's current task status."""
    try:
        from server.periodic_intelligence import get_todays_task
        
        current_task = get_todays_task()
        
        if current_task:
            return {
                "success": True,
                "tasks": current_task,
                "has_tasks": True
            }
        else:
            return {
                "success": True,
                "tasks": None,
                "has_tasks": False,
                "message": "No tasks set for today yet"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tasks": None
        }


@router.post(
    "/tasks/progress",
    summary="Update task progress",
    description="Update progress on a specific task (0-100)"
)
async def update_task_progress(request: TaskProgressRequest) -> Dict[str, Any]:
    """Update progress on a specific task."""
    try:
        from server.periodic_intelligence import (
            update_task_progress, get_todays_task, get_stats_line
        )
        
        # Validate task type
        if request.task_type not in ["primary", "secondary", "bonus"]:
            return {
                "success": False,
                "error": "Invalid task type. Must be 'primary', 'secondary', or 'bonus'"
            }
        
        # Validate progress
        if not (0 <= request.progress <= 100):
            return {
                "success": False,
                "error": "Progress must be between 0 and 100"
            }
        
        result = update_task_progress(request.task_type, request.progress)
        
        if "error" not in result:
            stats_line = get_stats_line()
            return {
                "success": True,
                "message": f"Progress updated to {request.progress}%",
                "task_type": result["task_type"],
                "old_progress": result["old_progress"],
                "new_progress": result["new_progress"],
                "xp_awarded": result.get("xp", {}).get("xp_awarded", 0),
                "stats_line": stats_line
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post(
    "/tasks/complete",
    summary="Mark task as completed",
    description="Mark a task as completed and award XP"
)
async def complete_task(request: TaskCompleteRequest) -> Dict[str, Any]:
    """Mark a task as completed."""
    try:
        from server.periodic_intelligence import (
            complete_task, get_todays_task, get_stats_line
        )
        
        # Validate task type
        if request.task_type not in ["primary", "secondary", "bonus"]:
            return {
                "success": False,
                "error": "Invalid task type. Must be 'primary', 'secondary', or 'bonus'"
            }
        
        result = complete_task(request.task_type)
        
        if "error" not in result:
            stats_line = get_stats_line()
            xp_info = result.get("xp", {})
            xp_total = xp_info.get("xp_awarded", 0)
            
            return {
                "success": True,
                "message": f"🎉 {request.task_type.upper()} TASK COMPLETE!",
                "task_type": result["task_type"],
                "task_description": result["task_description"],
                "xp_awarded": xp_total,
                "leveled_up": xp_info.get("leveled_up", False),
                "stats_line": stats_line
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post(
    "/tasks/modify",
    summary="Modify existing task",
    description="Update the description of an existing task"
)
async def modify_task(request: TaskSetRequest) -> Dict[str, Any]:
    """Modify an existing task's description."""
    try:
        from server.periodic_intelligence import get_todays_task
        
        current_task = get_todays_task()
        if not current_task:
            return {
                "success": False,
                "error": "No tasks set for today. Create tasks first."
            }
        
        # Update task descriptions
        tasks = current_task.get("tasks", {})
        
        if request.primary and "primary" in tasks:
            tasks["primary"]["description"] = request.primary
        
        if request.secondary and "secondary" in tasks:
            tasks["secondary"]["description"] = request.secondary
        elif request.secondary and "secondary" not in tasks:
            # Add new secondary task
            tasks["secondary"] = {
                "description": request.secondary,
                "progress": 0,
                "completed": False,
                "completed_at": None
            }
        
        if request.bonus and "bonus" in tasks:
            tasks["bonus"]["description"] = request.bonus
        elif request.bonus and "bonus" not in tasks:
            # Add new bonus task
            tasks["bonus"] = {
                "description": request.bonus,
                "progress": 0,
                "completed": False,
                "completed_at": None
            }
        
        # Save updated tasks
        from server.periodic_intelligence import save_gad_memory, get_gad_memory, ACCOUNTABILITY_STORAGE_KEY
        memory = get_gad_memory()
        memory[ACCOUNTABILITY_STORAGE_KEY] = current_task
        save_gad_memory(memory)
        
        return {
            "success": True,
            "message": "Tasks updated successfully",
            "tasks": current_task
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
