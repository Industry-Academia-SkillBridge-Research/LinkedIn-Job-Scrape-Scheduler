"""
Scraping routes
Handles all scraping-related endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from datetime import datetime
import json

from api.models import (
    JobSearchRequest,
    JobResponse,
    JobListResponse,
    ScrapingJobResponse,
    ScrapingJobStatus,
    JobStatus
)
from api.services import scraper_service
from api.core import settings

router = APIRouter(prefix="/scrape", tags=["Scraping"])


def background_scrape_task(job_id: str, request: JobSearchRequest):
    """Background task to perform scraping"""
    try:
        scraper_service.update_job_status(job_id, JobStatus.IN_PROGRESS)
        
        jobs = scraper_service.scrape_jobs(request)
        
        scraper_service.update_job_status(
            job_id,
            JobStatus.COMPLETED,
            total_jobs=len(jobs)
        )
        
    except Exception as e:
        scraper_service.update_job_status(
            job_id,
            JobStatus.FAILED,
            error=str(e)
        )


@router.post(
    "/",
    response_model=JobListResponse,
    summary="Scrape jobs with search parameters",
    description="Scrape LinkedIn jobs directly with keywords, location, and exact keyword filtering"
)
async def scrape_jobs(request: JobSearchRequest):
    """
    Scrape LinkedIn jobs with search parameters
    
    - **keywords**: Job search keywords (required) - e.g., "Data Engineer"
    - **location**: Job location (optional) - e.g., "Remote", "New York"
    - **max_jobs**: Maximum number of jobs to scrape (1-50)
    - **fetch_details**: Whether to fetch detailed job information including skills
    - **method**: Scraping method (beautifulsoup or selenium)
    - **exact_match**: Filter to only include jobs matching exact keywords (RECOMMENDED)
    
    **Example:**
    If you search for "Data Engineer" with exact_match=true:
    - ✅ "Data Engineer" - Included
    - ✅ "Senior Data Engineer" - Included
    - ✅ "Lead Data Engineer - Cloud" - Included
    - ❌ "Software Engineer" - Excluded
    - ❌ "Software Engineer, Data Platform" - Excluded (doesn't match pattern)
    
    Returns immediately with all scraped and filtered jobs.
    """
    try:
        jobs = scraper_service.scrape_jobs(request)
        
        response = JobListResponse(
            total=len(jobs),
            jobs=[JobResponse(**job) for job in jobs],
            scraped_at=datetime.utcnow().isoformat(),
            search_params=request
        )
        
        # Add filtering info if exact match was used
        if request.exact_match:
            response.filtered = len(jobs)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/sync",
    response_model=JobListResponse,
    summary="Scrape jobs synchronously (alias)",
    description="Same as POST / - Scrape LinkedIn jobs and return results immediately"
)
async def scrape_jobs_sync(request: JobSearchRequest):
    """Alias for POST / endpoint"""
    return await scrape_jobs(request)


@router.get(
    "/jobs",
    response_model=List[ScrapingJobStatus],
    summary="List all scraping job history",
    description="Get a list of all scraping jobs (for async operations tracking)"
)
async def list_all_jobs():
    """Get all scraping jobs history"""
    return scraper_service.get_all_jobs()
