"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class ScraperMethod(str, Enum):
    """Supported scraper methods"""
    BEAUTIFULSOUP = "beautifulsoup"
    SELENIUM = "selenium"


class JobStatus(str, Enum):
    """Job scraping status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class JobSearchRequest(BaseModel):
    """Request model for job search"""
    keywords: str = Field(..., description="Job search keywords", min_length=1)
    location: Optional[str] = Field(None, description="Job location")
    max_jobs: int = Field(10, description="Maximum number of jobs to scrape", ge=1, le=50)
    fetch_details: bool = Field(True, description="Fetch detailed job information including skills")
    method: ScraperMethod = Field(ScraperMethod.BEAUTIFULSOUP, description="Scraping method to use")
    exact_match: bool = Field(True, description="Filter jobs to match exact keywords (recommended to avoid irrelevant results)")
    
    @validator('keywords')
    def keywords_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Keywords cannot be empty')
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "keywords": "Data Engineer",
                "location": "Remote",
                "max_jobs": 5,
                "fetch_details": True,
                "method": "beautifulsoup",
                "exact_match": True
            }
        }


class JobCriteria(BaseModel):
    """Job criteria information"""
    seniority_level: Optional[str] = Field(None, alias="Seniority level")
    employment_type: Optional[str] = Field(None, alias="Employment type")
    job_function: Optional[str] = Field(None, alias="Job function")
    industries: Optional[str] = Field(None, alias="Industries")
    
    class Config:
        populate_by_name = True


class JobResponse(BaseModel):
    """Response model for a single job"""
    job_id: str
    title: str
    company: str
    location: str
    posted_date: Optional[str] = None
    job_url: str
    scraped_at: str
    description: Optional[str] = None
    criteria: Optional[Dict[str, str]] = None
    skills: Optional[List[str]] = None
    role_tag: Optional[str] = Field(None, description="Role tag identifier (e.g., DA, SE, AIML)")
    role_key: Optional[str] = Field(None, description="Role category key (e.g., data_analyst, software_engineer)")
    job_role_id: Optional[str] = Field(None, description="Unique job role identifier (e.g., DA_001, SE_042)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "data-analyst-at-company-123456",
                "title": "Data Analyst",
                "company": "Tech Company",
                "location": "Remote",
                "posted_date": "2025-10-20",
                "job_url": "https://linkedin.com/jobs/view/...",
                "scraped_at": "2025-10-31T12:00:00",
                "description": "We are looking for a talented Data Analyst...",
                "criteria": {
                    "Seniority level": "Mid-Senior level",
                    "Employment type": "Full-time"
                },
                "skills": ["Python", "SQL", "Tableau"],
                "role_tag": "DA",
                "role_key": "data_analyst",
                "job_role_id": "DA_001"
            }
        }


class ScrapingJobStatus(BaseModel):
    """Status of a scraping job"""
    job_id: str
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    total_jobs: Optional[int] = None
    error: Optional[str] = None
    request: JobSearchRequest


class ScrapingJobResponse(BaseModel):
    """Response for async scraping job creation"""
    job_id: str
    status: JobStatus
    message: str
    estimated_time_seconds: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "abc123",
                "status": "pending",
                "message": "Scraping job created successfully",
                "estimated_time_seconds": 40
            }
        }


class JobListResponse(BaseModel):
    """Response model for list of jobs"""
    total: int
    filtered: Optional[int] = Field(None, description="Number of jobs after filtering (if exact_match=true)")
    jobs: List[JobResponse]
    scraped_at: str
    search_params: JobSearchRequest


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
