"""Data management endpoints."""

from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter(prefix="/data", tags=["data"])


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
