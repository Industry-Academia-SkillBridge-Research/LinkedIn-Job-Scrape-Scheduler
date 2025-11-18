"""
Scraper service layer
Handles the business logic for scraping operations
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from api.models.schemas import JobSearchRequest, JobStatus, ScrapingJobStatus, ScraperMethod
from scrapers.beautifulsoup_scraper import LinkedInScraperBS
from scrapers.selenium_scraper import LinkedInScraperSelenium
from api.utils.job_filter import filter_jobs_by_keywords, filter_and_rank_jobs
import logging

logger = logging.getLogger(__name__)


class ScraperService:
    """Service class for handling scraping operations"""
    
    def __init__(self):
        self.jobs_storage: Dict[str, ScrapingJobStatus] = {}
    
    def create_job(self, request: JobSearchRequest) -> str:
        """Create a new scraping job"""
        job_id = str(uuid.uuid4())[:8]
        
        job_status = ScrapingJobStatus(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
            request=request
        )
        
        self.jobs_storage[job_id] = job_status
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[ScrapingJobStatus]:
        """Get the status of a scraping job"""
        return self.jobs_storage.get(job_id)
    
    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        total_jobs: Optional[int] = None,
        error: Optional[str] = None
    ):
        """Update the status of a scraping job"""
        if job_id in self.jobs_storage:
            self.jobs_storage[job_id].status = status
            if total_jobs is not None:
                self.jobs_storage[job_id].total_jobs = total_jobs
            if error:
                self.jobs_storage[job_id].error = error
            if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                self.jobs_storage[job_id].completed_at = datetime.utcnow()
    
    def get_all_jobs(self) -> List[ScrapingJobStatus]:
        """Get all scraping jobs"""
        return list(self.jobs_storage.values())
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a scraping job"""
        if job_id in self.jobs_storage:
            del self.jobs_storage[job_id]
            return True
        return False
    
    def scrape_jobs(self, request: JobSearchRequest) -> List[Dict]:
        """
        Execute the scraping operation
        Returns list of scraped jobs with optional filtering
        """
        try:
            # Scrape more jobs than requested to account for filtering
            fetch_count = request.max_jobs * 2 if request.exact_match else request.max_jobs
            
            if request.method == ScraperMethod.BEAUTIFULSOUP:
                scraper = LinkedInScraperBS(
                    delay_min=2.0,
                    delay_max=4.0
                )
            else:
                scraper = LinkedInScraperSelenium(
                    headless=True,
                    delay_min=2.0,
                    delay_max=4.0
                )
            
            jobs = scraper.search_jobs(
                keywords=request.keywords,
                location=request.location or "",
                max_jobs=fetch_count,
                fetch_details=request.fetch_details
            )
            
            # Close Selenium if used
            if request.method == ScraperMethod.SELENIUM:
                try:
                    scraper.close()
                except:
                    pass
            
            # Filter jobs by exact keyword match if requested
            if request.exact_match and jobs:
                logger.info(f"📋 Before filtering: {len(jobs)} jobs")
                logger.info(f"🔍 Filtering for exact match: '{request.keywords}'")
                
                # Use strict filtering
                filtered_jobs = filter_jobs_by_keywords(
                    jobs, 
                    request.keywords, 
                    strict=True
                )
                
                logger.info(f"✅ After filtering: {len(filtered_jobs)} jobs match exactly")
                
                # Limit to requested count
                jobs = filtered_jobs[:request.max_jobs]
            
            return jobs
            
        except Exception as e:
            raise Exception(f"Scraping failed: {str(e)}")
    
    def estimate_time(self, request: JobSearchRequest) -> int:
        """Estimate scraping time in seconds"""
        base_time = 2  # Base time per job
        if request.fetch_details:
            base_time += 4  # Additional time for details
        if request.method == ScraperMethod.SELENIUM:
            base_time += 2  # Selenium is slower
        
        return base_time * request.max_jobs


# Singleton instance
scraper_service = ScraperService()
