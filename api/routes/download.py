"""
Download routes
Handles file download endpoints
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import os
import json
from datetime import datetime

from api.models import JobStatus
from api.services import scraper_service
from api.core import settings

router = APIRouter(prefix="/download", tags=["Download"])


@router.get(
    "/{job_id}",
    summary="Download job results as JSON",
    description="Download the results of a scraping job as a JSON file"
)
async def download_job_results(job_id: str):
    """
    Download scraping job results as JSON file
    
    - **job_id**: The ID returned from the async endpoint
    """
    job_status = scraper_service.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if job_status.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job_status.status}"
        )
    
    try:
        # Get the results
        jobs = scraper_service.scrape_jobs(job_status.request)
        
        # Create output directory if it doesn't exist
        os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
        
        # Save to temporary file
        filename = f"jobs_{job_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(settings.OUTPUT_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type='application/json'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
