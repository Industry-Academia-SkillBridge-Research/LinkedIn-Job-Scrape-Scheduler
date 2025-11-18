"""
API routes for scheduler control
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
from pydantic import BaseModel

from api.services.scheduler_service import job_scheduler

router = APIRouter()


class ScheduleConfigUpdate(BaseModel):
    """Model for updating scheduler configuration"""
    day: Optional[str] = None  # monday, tuesday, etc.
    time: Optional[str] = None  # HH:MM format


@router.get("/status")
async def get_scheduler_status() -> Dict:
    """
    Get current scheduler status including:
    - Is running/scraping
    - Last run time
    - Next scheduled run
    - Configuration
    - Current progress (if scraping)
    
    Returns:
        Dict: Comprehensive scheduler status
    """
    return job_scheduler.get_status()


@router.post("/start")
async def start_scheduler() -> Dict:
    """
    Start the automatic scheduler
    
    The scheduler will run weekly according to configured schedule
    
    Returns:
        Dict: Success message and next run time
    """
    try:
        job_scheduler.start()
        
        return {
            "status": "success",
            "message": "Scheduler started successfully",
            "is_running": job_scheduler.is_running,
            "next_run": job_scheduler.next_run.isoformat() if job_scheduler.next_run else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@router.post("/stop")
async def stop_scheduler() -> Dict:
    """
    Stop the automatic scheduler
    
    Note: This will not stop currently running scraping job
    
    Returns:
        Dict: Success message
    """
    try:
        job_scheduler.stop()
        
        return {
            "status": "success",
            "message": "Scheduler stopped successfully",
            "is_running": job_scheduler.is_running
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")


@router.post("/run-now")
async def run_now() -> Dict:
    """
    Manually trigger a scraping run immediately
    
    This will:
    1. Scrape all configured job roles
    2. Apply location priority (Sri Lanka first, then USA/India/UK)
    3. Filter by recency (<=21 days)
    4. Deduplicate results
    5. Save to Elasticsearch (if enabled)
    
    The job runs in background and doesn't block the API
    
    Returns:
        Dict: Status and tracking information
    """
    try:
        result = job_scheduler.run_now()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger manual run: {str(e)}")


@router.get("/configuration")
async def get_configuration() -> Dict:
    """
    Get current scheduler configuration
    
    Returns:
        Dict: Job roles, locations, schedule settings, etc.
    """
    from api.services.scheduler_service import SchedulerConfig
    
    return {
        "job_roles": {k: v for k, v in SchedulerConfig.JOB_ROLES.items()},
        "total_jobs_per_role": SchedulerConfig.TOTAL_JOBS_PER_ROLE,
        "location_priority": SchedulerConfig.LOCATION_PRIORITY,
        "schedule": {
            "day": SchedulerConfig.SCHEDULE_DAY,
            "time": SchedulerConfig.SCHEDULE_TIME
        },
        "filters": {
            "max_post_age_days": SchedulerConfig.MAX_POST_AGE_DAYS,
            "exact_match": SchedulerConfig.EXACT_MATCH,
            "fetch_details": SchedulerConfig.FETCH_DETAILS
        },
        "method": SchedulerConfig.METHOD.value
    }


@router.put("/configuration")
async def update_configuration(config: ScheduleConfigUpdate) -> Dict:
    """
    Update scheduler configuration
    
    Note: Changes will take effect after next restart
    
    Args:
        config: New schedule day and/or time
    
    Returns:
        Dict: Updated configuration
    """
    from api.services.scheduler_service import SchedulerConfig
    
    updated_fields = []
    
    if config.day:
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        if config.day.lower() not in valid_days:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid day. Must be one of: {', '.join(valid_days)}"
            )
        SchedulerConfig.SCHEDULE_DAY = config.day.lower()
        updated_fields.append("day")
    
    if config.time:
        # Validate time format (HH:MM)
        import re
        if not re.match(r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$", config.time):
            raise HTTPException(
                status_code=400,
                detail="Invalid time format. Must be HH:MM (24-hour format)"
            )
        SchedulerConfig.SCHEDULE_TIME = config.time
        updated_fields.append("time")
    
    if not updated_fields:
        raise HTTPException(
            status_code=400,
            detail="No valid fields to update"
        )
    
    # Restart scheduler if it's running
    was_running = job_scheduler.is_running
    if was_running:
        job_scheduler.stop()
        job_scheduler.start()
    
    return {
        "status": "success",
        "message": f"Configuration updated: {', '.join(updated_fields)}",
        "updated_fields": updated_fields,
        "scheduler_restarted": was_running,
        "new_schedule": {
            "day": SchedulerConfig.SCHEDULE_DAY,
            "time": SchedulerConfig.SCHEDULE_TIME
        },
        "next_run": job_scheduler.next_run.isoformat() if job_scheduler.next_run else None
    }


@router.get("/logs")
async def get_scraping_logs() -> Dict:
    """
    Get recent scraping activity logs
    
    Returns:
        Dict: Last run summary with statistics
    """
    status = job_scheduler.get_status()
    
    return {
        "last_run": status["last_run"],
        "last_run_statistics": {
            "jobs_by_role": status["current_scraping"]["jobs_by_role"],
            "jobs_by_country": status["current_scraping"]["jobs_by_country"],
            "total_jobs": status["current_scraping"]["total_jobs_scraped"]
        },
        "next_scheduled_run": status["next_run"]
    }
