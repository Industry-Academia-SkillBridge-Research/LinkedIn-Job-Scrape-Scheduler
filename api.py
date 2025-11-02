"""
FastAPI Application for LinkedIn Job Scraper
Provides REST API endpoints with automatic Swagger documentation
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
import os
import json
from datetime import datetime
import uuid

from scrapers.beautifulsoup_scraper import LinkedInScraperBS

# Initialize FastAPI app
app = FastAPI(
    title="LinkedIn Job Scraper API",
    description="API for scraping LinkedIn job postings with automatic skills extraction",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc UI
)

# Store scraping jobs in memory (use a database in production)
scraping_jobs = {}

# Enums for API validation
class ScrapingMethod(str, Enum):
    beautifulsoup = "beautifulsoup"
    selenium = "selenium"

class ExperienceLevel(str, Enum):
    internship = "1"
    entry = "2"
    associate = "3"
    mid_senior = "4"
    director = "5"
    executive = "6"

class JobType(str, Enum):
    full_time = "F"
    part_time = "P"
    contract = "C"
    temporary = "T"
    volunteer = "V"
    internship = "I"

class DatePosted(str, Enum):
    past_24h = "r86400"
    past_week = "r604800"
    past_month = "r2592000"

# Request/Response Models
class JobSearchRequest(BaseModel):
    keywords: str = Field(..., description="Job search keywords (e.g., 'Python Developer')", example="Data Analyst")
    location: Optional[str] = Field("", description="Job location (e.g., 'New York' or 'Remote')", example="Remote")
    max_jobs: int = Field(10, ge=1, le=100, description="Maximum number of jobs to scrape (1-100)")
    fetch_details: bool = Field(True, description="Extract skills and detailed information (slower but comprehensive)")
    experience_level: Optional[ExperienceLevel] = Field(None, description="Filter by experience level")
    job_type: Optional[JobType] = Field(None, description="Filter by job type")
    date_posted: Optional[DatePosted] = Field(None, description="Filter by date posted")

class JobResponse(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    posted_date: Optional[str]
    job_url: str
    skills: Optional[List[str]] = []
    criteria: Optional[Dict[str, str]] = {}
    description: Optional[str] = ""
    scraped_at: str

class ScrapingJobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int  # 0-100
    total_jobs: int
    scraped_jobs: int
    message: str
    created_at: str
    completed_at: Optional[str] = None

class ScrapingJobResponse(BaseModel):
    job_id: str
    status: str
    message: str

# Helper Functions
def create_scraping_job(request: JobSearchRequest) -> str:
    """Create a new scraping job"""
    job_id = str(uuid.uuid4())
    scraping_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0,
        "total_jobs": request.max_jobs,
        "scraped_jobs": 0,
        "message": "Job created, waiting to start...",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "request": request.dict(),
        "results": []
    }
    return job_id

def perform_scraping(job_id: str):
    """Perform the actual scraping (runs in background)"""
    job_data = scraping_jobs.get(job_id)
    if not job_data:
        return
    
    try:
        # Update status
        job_data["status"] = "running"
        job_data["message"] = "Scraping in progress..."
        
        # Get request data
        request_data = job_data["request"]
        
        # Initialize scraper
        scraper = LinkedInScraperBS(delay_min=2.0, delay_max=4.0)
        
        # Perform scraping
        jobs = scraper.search_jobs(
            keywords=request_data["keywords"],
            location=request_data["location"],
            max_jobs=request_data["max_jobs"],
            fetch_details=request_data["fetch_details"],
            experience_level=request_data.get("experience_level", ""),
            job_type=request_data.get("job_type", ""),
            date_posted=request_data.get("date_posted", "")
        )
        
        # Update job data
        job_data["results"] = jobs
        job_data["scraped_jobs"] = len(jobs)
        job_data["progress"] = 100
        job_data["status"] = "completed"
        job_data["message"] = f"Successfully scraped {len(jobs)} jobs"
        job_data["completed_at"] = datetime.now().isoformat()
        
        # Save to file
        os.makedirs("output/api", exist_ok=True)
        output_file = f"output/api/scraping_job_{job_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        
        job_data["output_file"] = output_file
        
    except Exception as e:
        job_data["status"] = "failed"
        job_data["message"] = f"Scraping failed: {str(e)}"
        job_data["progress"] = 0
        job_data["completed_at"] = datetime.now().isoformat()

# API Endpoints

@app.get("/", tags=["General"])
async def root():
    """
    Welcome endpoint with API information
    """
    return {
        "message": "LinkedIn Job Scraper API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "scrape_sync": "/api/v1/scrape/sync",
            "scrape_async": "/api/v1/scrape/async",
            "job_status": "/api/v1/scrape/status/{job_id}",
            "list_jobs": "/api/v1/jobs"
        }
    }

@app.post("/api/v1/scrape/sync", response_model=List[JobResponse], tags=["Scraping"])
async def scrape_jobs_sync(request: JobSearchRequest):
    """
    Scrape LinkedIn jobs synchronously (waits until completion)
    
    This endpoint will block until all jobs are scraped.
    Use for small batches (< 10 jobs).
    """
    try:
        # Initialize scraper
        scraper = LinkedInScraperBS(delay_min=2.0, delay_max=4.0)
        
        # Perform scraping
        jobs = scraper.search_jobs(
            keywords=request.keywords,
            location=request.location,
            max_jobs=request.max_jobs,
            fetch_details=request.fetch_details,
            experience_level=request.experience_level.value if request.experience_level else "",
            job_type=request.job_type.value if request.job_type else "",
            date_posted=request.date_posted.value if request.date_posted else ""
        )
        
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found with the specified criteria")
        
        # Save to file
        os.makedirs("output/api", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"output/api/jobs_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)
        
        return jobs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.post("/api/v1/scrape/async", response_model=ScrapingJobResponse, tags=["Scraping"])
async def scrape_jobs_async(request: JobSearchRequest, background_tasks: BackgroundTasks):
    """
    Scrape LinkedIn jobs asynchronously (returns immediately)
    
    This endpoint creates a background job and returns a job_id.
    Use the job_id to check status and retrieve results.
    Recommended for large batches (> 10 jobs).
    """
    try:
        # Create scraping job
        job_id = create_scraping_job(request)
        
        # Add to background tasks
        background_tasks.add_task(perform_scraping, job_id)
        
        return {
            "job_id": job_id,
            "status": "pending",
            "message": f"Scraping job created. Use /api/v1/scrape/status/{job_id} to check progress"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create scraping job: {str(e)}")

@app.get("/api/v1/scrape/status/{job_id}", response_model=ScrapingJobStatus, tags=["Scraping"])
async def get_scraping_status(job_id: str):
    """
    Get the status of an async scraping job
    
    Returns the current status, progress, and results (if completed)
    """
    job_data = scraping_jobs.get(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail=f"Scraping job {job_id} not found")
    
    return {
        "job_id": job_data["job_id"],
        "status": job_data["status"],
        "progress": job_data["progress"],
        "total_jobs": job_data["total_jobs"],
        "scraped_jobs": job_data["scraped_jobs"],
        "message": job_data["message"],
        "created_at": job_data["created_at"],
        "completed_at": job_data.get("completed_at")
    }

@app.get("/api/v1/scrape/results/{job_id}", response_model=List[JobResponse], tags=["Scraping"])
async def get_scraping_results(job_id: str):
    """
    Get the results of a completed scraping job
    """
    job_data = scraping_jobs.get(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail=f"Scraping job {job_id} not found")
    
    if job_data["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Job is not completed yet. Current status: {job_data['status']}"
        )
    
    return job_data["results"]

@app.get("/api/v1/jobs", tags=["Scraping Jobs"])
async def list_scraping_jobs():
    """
    List all scraping jobs
    """
    return {
        "total": len(scraping_jobs),
        "jobs": [
            {
                "job_id": job_id,
                "status": job["status"],
                "progress": job["progress"],
                "scraped_jobs": job["scraped_jobs"],
                "created_at": job["created_at"]
            }
            for job_id, job in scraping_jobs.items()
        ]
    }

@app.delete("/api/v1/jobs/{job_id}", tags=["Scraping Jobs"])
async def delete_scraping_job(job_id: str):
    """
    Delete a scraping job from memory
    """
    if job_id not in scraping_jobs:
        raise HTTPException(status_code=404, detail=f"Scraping job {job_id} not found")
    
    del scraping_jobs[job_id]
    
    return {"message": f"Job {job_id} deleted successfully"}

@app.get("/api/v1/download/{job_id}", tags=["Download"])
async def download_results(job_id: str):
    """
    Download scraping results as JSON file
    """
    job_data = scraping_jobs.get(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail=f"Scraping job {job_id} not found")
    
    if job_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    
    output_file = job_data.get("output_file")
    
    if not output_file or not os.path.exists(output_file):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    return FileResponse(
        output_file,
        media_type="application/json",
        filename=f"linkedin_jobs_{job_id}.json"
    )

@app.get("/api/v1/health", tags=["General"])
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_jobs": len([j for j in scraping_jobs.values() if j["status"] == "running"])
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    # Use import string format for reload support
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
