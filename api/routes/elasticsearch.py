"""
API routes for Elasticsearch search and analytics
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from api.services.elasticsearch_service import elasticsearch_service

router = APIRouter(tags=["Elasticsearch"])


@router.get("/search")
async def search_jobs(
    query: Optional[str] = Query(None, description="Search query for job title/description"),
    location: Optional[str] = Query(None, description="Filter by location"),
    company: Optional[str] = Query(None, description="Filter by company"),
    skills: Optional[str] = Query(None, description="Filter by skills (comma-separated)"),
    employment_type: Optional[str] = Query(None, description="Filter by employment type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page")
):
    """
    Search jobs in Elasticsearch with filters
    
    Supports:
    - Full-text search on title and description
    - Location filtering
    - Company filtering
    - Skills filtering
    - Employment type filtering
    - Pagination
    """
    # Parse skills if provided
    skills_list = None
    if skills:
        skills_list = [s.strip() for s in skills.split(',')]
    
    result = elasticsearch_service.search_jobs(
        query=query,
        location=location,
        company=company,
        skills=skills_list,
        employment_type=employment_type,
        page=page,
        page_size=page_size
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/job/{job_id}")
async def get_job(job_id: str):
    """
    Get a specific job by ID
    """
    job = elasticsearch_service.get_job_by_id(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


@router.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job by ID
    """
    result = elasticsearch_service.delete_job(job_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to delete job")
        )
    
    return {
        "message": "Job deleted successfully",
        "job_id": job_id
    }


@router.get("/analytics")
async def get_analytics():
    """
    Get aggregated analytics
    
    Returns:
    - Total job count
    - Top 10 companies
    - Top 10 locations
    - Top 20 skills
    - Employment type distribution
    - Jobs by country
    - Jobs by role
    """
    result = elasticsearch_service.get_aggregations()
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.get("/count")
async def count_jobs():
    """
    Get total job count in Elasticsearch
    """
    count = elasticsearch_service.count_jobs()
    
    return {
        "total_jobs": count,
        "index": elasticsearch_service.index
    }
