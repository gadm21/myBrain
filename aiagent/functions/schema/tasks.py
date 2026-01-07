from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import logging

from server.utils.functions_metadata import function_schema

logger = logging.getLogger(__name__)


class TaskStatusResponse(BaseModel):
    has_tasks: bool = Field(..., description="Whether tasks are set for today")
    tasks: Dict[str, Any] = Field(default_factory=dict, description="Task details")
    date: str = Field(..., description="Date of the tasks")
    completion_count: int = Field(0, description="Number of completed tasks")
    total_count: int = Field(0, description="Total number of tasks")


@function_schema(
    name="get_current_tasks",
    description=(
        "Retrieve Gad's current daily tasks. Use this when the user asks about their tasks, "
        "what they should be working on, or wants to know their task status. "
        "This is READ-ONLY and does NOT set or modify tasks."
    ),
    required_params=[],
)
def get_current_tasks() -> Dict[str, Any]:
    """
    AI tool: Get the current daily tasks for Gad.
    
    This function retrieves tasks WITHOUT modifying them. Use this when:
    - User asks "what is my task today?"
    - User asks "what should I be working on?"
    - User asks "what are my tasks?"
    - User wants to check task status
    
    Returns:
        A dictionary with task information including descriptions, progress, and completion status
    """
    try:
        from server.periodic_intelligence import get_daily_tasks, get_gamification_stats, get_level_info
        from datetime import datetime
        
        tasks_data = get_daily_tasks()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if not tasks_data or tasks_data.get("date") != today:
            return {
                "has_tasks": False,
                "tasks": {},
                "date": today,
                "completion_count": 0,
                "total_count": 0,
                "message": "No tasks set for today yet."
            }
        
        tasks = tasks_data.get("tasks", {})
        completed_count = sum(1 for t in tasks.values() if t.get("completed"))
        total_count = len(tasks)
        
        # Format task information for the AI
        task_list = []
        for task_type, task_info in tasks.items():
            status = "✅ COMPLETED" if task_info.get("completed") else f"⏳ {task_info.get('progress', 0)}% done"
            task_list.append({
                "type": task_type.upper(),
                "description": task_info.get("description"),
                "status": status,
                "completed": task_info.get("completed", False),
                "progress": task_info.get("progress", 0)
            })
        
        # Get gamification stats
        stats = get_gamification_stats()
        level_info = get_level_info(stats.get("total_xp", 0))
        
        return {
            "has_tasks": True,
            "tasks": task_list,
            "date": today,
            "completion_count": completed_count,
            "total_count": total_count,
            "set_at": tasks_data.get("set_at"),
            "check_ins": tasks_data.get("check_ins", 0),
            "gamification": {
                "level": level_info["level"],
                "emoji": level_info["emoji"],
                "total_xp": stats.get("total_xp", 0),
                "streak": stats.get("current_streak", 0)
            },
            "message": f"Found {total_count} task(s) for today. {completed_count} completed, {total_count - completed_count} remaining."
        }
        
    except Exception as e:
        logger.error(f"Error retrieving current tasks: {e}", exc_info=True)
        return {
            "has_tasks": False,
            "tasks": {},
            "date": datetime.now().strftime("%Y-%m-%d"),
            "completion_count": 0,
            "total_count": 0,
            "error": str(e),
            "message": "Error retrieving tasks. Please try again."
        }


@function_schema(
    name="set_daily_tasks",
    description=(
        "Set Gad's daily tasks. Use this ONLY when the user explicitly wants to SET or UPDATE tasks. "
        "Examples: 'My task is...', 'Set my task to...', 'Today I need to...', 'I will work on...'. "
        "DO NOT use this for questions like 'what is my task?' - use get_current_tasks instead."
    ),
    required_params=["primary_task"],
)
def set_daily_tasks(
    primary_task: str,
    secondary_task: Optional[str] = None,
    bonus_task: Optional[str] = None
) -> Dict[str, Any]:
    """
    AI tool: Set daily tasks for Gad.
    
    Use this when the user wants to SET tasks, not when they're asking about existing tasks.
    
    Args:
        primary_task: The main task for today (required)
        secondary_task: Optional secondary task
        bonus_task: Optional bonus task
    
    Returns:
        A dictionary with the set tasks and XP information
    """
    try:
        from server.periodic_intelligence import set_todays_tasks, get_stats_line
        
        result = set_todays_tasks(
            primary=primary_task,
            secondary=secondary_task,
            bonus=bonus_task
        )
        
        stats_line = get_stats_line()
        
        tasks_display = f"🎯 PRIMARY: {primary_task}"
        if secondary_task:
            tasks_display += f"\n📌 SECONDARY: {secondary_task}"
        if bonus_task:
            tasks_display += f"\n⭐ BONUS: {bonus_task}"
        
        xp_msg = f"+{result['xp']['xp_awarded']} XP" if result.get('xp') else ""
        
        return {
            "success": True,
            "tasks": result.get("tasks"),
            "xp_awarded": result.get("xp"),
            "stats": stats_line,
            "message": f"✅ TASKS LOCKED IN! {xp_msg}\n\n{tasks_display}\n\n{stats_line}"
        }
        
    except Exception as e:
        logger.error(f"Error setting daily tasks: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Error setting tasks: {str(e)}"
        }
