"""
Scheduler service for automated weekly job scraping
Implements location-based priority scraping with Elasticsearch storage
"""
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import logging
from collections import defaultdict

from api.models.schemas import JobSearchRequest, JobStatus, ScrapingJobStatus, ScraperMethod
from api.services.scraper_service import scraper_service

# Import Elasticsearch service if available
try:
    from api.services.elasticsearch_service import elasticsearch_service
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False
    logging.warning("Elasticsearch service not available")

logger = logging.getLogger(__name__)


class SchedulerConfig:
    """Configuration for scheduled scraping jobs"""
    
    # Job roles to scrape (case-insensitive)
    # AI/ML Engineer and Machine Learning Engineer are treated as one role
    JOB_ROLES = {
        "ai_ml_engineer": ["AI/ML Engineer", "Machine Learning Engineer", "AI Engineer", "ML Engineer"],
        "data_analyst": ["Data Analyst"],
        "data_engineer": ["Data Engineer"],
        "devops_engineer": ["DevOps Engineer", "Dev Ops Engineer"],
        "web_developer": ["Web Developer"],
        "software_engineer": ["Software Engineer"]
    }
    
    # Location priority configuration
    # First priority: Sri Lanka (20 jobs target)
    # Fallback: USA, India, UK
    LOCATION_PRIORITY = {
        "primary": {
            "country": "Sri Lanka",
            "country_code": "LK",
            "target_jobs": 20
        },
        "fallback": [
            {"country": "United States", "country_code": "US", "jobs_per_country": 7},
            {"country": "India", "country_code": "IN", "jobs_per_country": 7},
            {"country": "United Kingdom", "country_code": "GB", "jobs_per_country": 6}
        ]
    }
    
    # Total jobs per role
    TOTAL_JOBS_PER_ROLE = 20
    
    # Scheduler configuration
    SCHEDULE_DAY = "monday"  # Day of week to run
    SCHEDULE_TIME = "09:00"  # Time to run (24-hour format)
    
    # Scraping settings
    FETCH_DETAILS = True
    EXACT_MATCH = True
    METHOD = ScraperMethod.BEAUTIFULSOUP
    
    # Post filtering
    MAX_POST_AGE_DAYS = 21  # Only include jobs posted within last 21 days


class JobScheduler:
    """Scheduler for automated job scraping with location priority"""
    
    def __init__(self):
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.scraping_status: Dict = {
            "is_scraping": False,
            "current_role": None,
            "current_location": None,
            "progress": 0,
            "total_jobs_scraped": 0,
            "jobs_by_role": {},
            "jobs_by_country": {},
            "errors": []
        }
        self.seen_job_ids: Set[str] = set()  # For deduplication
    
    def normalize_job_id(self, job: Dict) -> str:
        """
        Create a stable, normalized job ID for deduplication
        Format: {company}_{title}_{location}
        """
        company = job.get('company', '').strip().lower()
        title = job.get('title', '').strip().lower()
        location = job.get('location', '').strip().lower()
        
        # Remove extra whitespace and special characters
        import re
        company = re.sub(r'\s+', '_', company)
        title = re.sub(r'\s+', '_', title)
        location = re.sub(r'\s+', '_', location)
        
        # Create unique ID
        unique_id = f"{company}_{title}_{location}"
        
        # Also use job_id if available
        if job.get('job_id'):
            unique_id = f"{job['job_id']}_{unique_id}"
        
        return unique_id
    
    def is_job_recent(self, job: Dict) -> bool:
        """Check if job was posted within the last 21 days"""
        posted_date_str = job.get('posted_date')
        if not posted_date_str:
            return True  # Include if no date available
        
        try:
            # Parse date
            from dateutil import parser
            posted_date = parser.parse(posted_date_str)
            
            # Check if within last 21 days
            days_old = (datetime.now() - posted_date).days
            return days_old <= SchedulerConfig.MAX_POST_AGE_DAYS
            
        except Exception as e:
            logger.warning(f"Could not parse date '{posted_date_str}': {e}")
            return True  # Include if parsing fails
    
    def extract_country_from_location(self, location: str) -> Optional[str]:
        """
        Extract country from location string
        Maps to country codes (LK, US, IN, GB)
        """
        location_lower = location.lower()
        
        # Country mappings
        country_mapping = {
            'LK': ['sri lanka', 'colombo', 'kandy', 'galle', 'jaffna'],
            'US': ['united states', 'usa', 'new york', 'california', 'texas', 'remote', 'us'],
            'IN': ['india', 'bangalore', 'mumbai', 'delhi', 'hyderabad', 'pune'],
            'GB': ['united kingdom', 'uk', 'london', 'manchester', 'birmingham', 'england']
        }
        
        for country_code, keywords in country_mapping.items():
            if any(keyword in location_lower for keyword in keywords):
                return country_code
        
        return None
    
    def filter_and_prioritize_jobs(self, jobs: List[Dict], role_key: str) -> List[Dict]:
        """
        Filter and prioritize jobs based on:
        1. Deduplication
        2. Recency (21 days)
        3. Location priority (Sri Lanka first, then USA, India, UK)
        4. Limit to 20 jobs total per role
        """
        # Step 1: Deduplicate
        unique_jobs = []
        for job in jobs:
            job_id = self.normalize_job_id(job)
            if job_id not in self.seen_job_ids:
                self.seen_job_ids.add(job_id)
                unique_jobs.append(job)
        
        logger.info(f"   After deduplication: {len(unique_jobs)} unique jobs")
        
        # Step 2: Filter by recency
        recent_jobs = [job for job in unique_jobs if self.is_job_recent(job)]
        logger.info(f"   After recency filter (<=21 days): {len(recent_jobs)} jobs")
        
        # Step 3: Categorize by country
        jobs_by_country = {
            'LK': [],
            'US': [],
            'IN': [],
            'GB': [],
            'OTHER': []
        }
        
        for job in recent_jobs:
            location = job.get('location', '')
            country_code = self.extract_country_from_location(location)
            
            if country_code:
                jobs_by_country[country_code].append(job)
            else:
                jobs_by_country['OTHER'].append(job)
        
        # Log distribution
        logger.info(f"   Distribution by country:")
        for country, job_list in jobs_by_country.items():
            if job_list:
                logger.info(f"      {country}: {len(job_list)} jobs")
        
        # Step 4: Select 20 jobs with priority
        selected_jobs = []
        target = SchedulerConfig.TOTAL_JOBS_PER_ROLE
        
        # First: Take all from Sri Lanka (up to 20)
        lk_jobs = jobs_by_country['LK'][:target]
        selected_jobs.extend(lk_jobs)
        remaining = target - len(selected_jobs)
        
        logger.info(f"   Selected {len(lk_jobs)} jobs from Sri Lanka")
        
        # If we need more, fill from fallback countries in priority order
        if remaining > 0:
            priority_order = ['US', 'IN', 'GB', 'OTHER']
            
            for country_code in priority_order:
                if remaining <= 0:
                    break
                
                country_jobs = jobs_by_country[country_code]
                jobs_to_add = country_jobs[:remaining]
                selected_jobs.extend(jobs_to_add)
                remaining -= len(jobs_to_add)
                
                if jobs_to_add:
                    logger.info(f"   Added {len(jobs_to_add)} jobs from {country_code}")
        
        logger.info(f"   ✅ Final selection: {len(selected_jobs)} jobs for {role_key}")
        
        return selected_jobs
    
    def scrape_role_all_locations(self, role_key: str, role_variations: List[str]) -> List[Dict]:
        """
        Scrape a role from multiple locations and apply priority filtering
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 Scraping Role: {role_key}")
        logger.info(f"   Variations: {', '.join(role_variations)}")
        logger.info(f"{'='*60}")
        
        all_jobs = []
        
        # Scrape from primary location (Sri Lanka)
        primary = SchedulerConfig.LOCATION_PRIORITY["primary"]
        logger.info(f"\n📍 Primary Location: {primary['country']}")
        
        for variation in role_variations:
            try:
                request = JobSearchRequest(
                    keywords=variation,
                    location=primary['country'],
                    max_jobs=30,  # Scrape more to account for filtering
                    fetch_details=SchedulerConfig.FETCH_DETAILS,
                    exact_match=SchedulerConfig.EXACT_MATCH,
                    method=SchedulerConfig.METHOD
                )
                
                jobs = scraper_service.scrape_jobs(request)
                logger.info(f"   ✓ '{variation}': {len(jobs)} jobs found")
                all_jobs.extend(jobs)
                
                time.sleep(2)  # Delay between variations
                
            except Exception as e:
                logger.error(f"   ✗ Error scraping '{variation}' in {primary['country']}: {e}")
                self.scraping_status["errors"].append({
                    "role": variation,
                    "location": primary['country'],
                    "error": str(e)
                })
        
        # Scrape from fallback locations
        for fallback in SchedulerConfig.LOCATION_PRIORITY["fallback"]:
            logger.info(f"\n📍 Fallback Location: {fallback['country']}")
            
            for variation in role_variations:
                try:
                    request = JobSearchRequest(
                        keywords=variation,
                        location=fallback['country'],
                        max_jobs=10,  # Fewer from fallback
                        fetch_details=SchedulerConfig.FETCH_DETAILS,
                        exact_match=SchedulerConfig.EXACT_MATCH,
                        method=SchedulerConfig.METHOD
                    )
                    
                    jobs = scraper_service.scrape_jobs(request)
                    logger.info(f"   ✓ '{variation}': {len(jobs)} jobs found")
                    all_jobs.extend(jobs)
                    
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"   ✗ Error scraping '{variation}' in {fallback['country']}: {e}")
        
        logger.info(f"\n📊 Raw jobs collected: {len(all_jobs)}")
        
        # Apply filtering and prioritization
        filtered_jobs = self.filter_and_prioritize_jobs(all_jobs, role_key)
        
        return filtered_jobs
    
    def scrape_all_roles(self) -> Dict:
        """Scrape all configured job roles with location priority"""
        self.scraping_status = {
            "is_scraping": True,
            "current_role": None,
            "current_location": None,
            "progress": 0,
            "total_jobs_scraped": 0,
            "jobs_by_role": {},
            "jobs_by_country": defaultdict(int),
            "errors": [],
            "started_at": datetime.utcnow().isoformat()
        }
        
        self.seen_job_ids.clear()  # Reset deduplication
        all_jobs = []
        total_roles = len(SchedulerConfig.JOB_ROLES)
        
        try:
            for idx, (role_key, role_variations) in enumerate(SchedulerConfig.JOB_ROLES.items()):
                self.scraping_status["current_role"] = role_key
                self.scraping_status["progress"] = int((idx / total_roles) * 100)
                
                # Scrape this role from all locations
                role_jobs = self.scrape_role_all_locations(role_key, role_variations)
                
                # Track statistics
                self.scraping_status["jobs_by_role"][role_key] = len(role_jobs)
                
                for job in role_jobs:
                    location = job.get('location', '')
                    country = self.extract_country_from_location(location)
                    if country:
                        self.scraping_status["jobs_by_country"][country] += 1
                
                all_jobs.extend(role_jobs)
                self.scraping_status["total_jobs_scraped"] = len(all_jobs)
                
                logger.info(f"\n✅ Completed {role_key}: {len(role_jobs)} jobs")
                
                # Delay between roles
                time.sleep(5)
            
            # Save to Elasticsearch if available
            if ES_AVAILABLE and elasticsearch_service.client and all_jobs:
                logger.info(f"\n💾 Saving {len(all_jobs)} jobs to Elasticsearch...")
                result = elasticsearch_service.save_jobs_bulk(all_jobs)
                logger.info(f"   ✅ Elasticsearch: {result['success']} saved, {result['failed']} failed")
            
            self.last_run = datetime.utcnow()
            
            summary = {
                "status": "completed",
                "total_jobs": len(all_jobs),
                "roles_scraped": len(SchedulerConfig.JOB_ROLES),
                "jobs_by_role": dict(self.scraping_status["jobs_by_role"]),
                "jobs_by_country": dict(self.scraping_status["jobs_by_country"]),
                "completed_at": datetime.utcnow().isoformat(),
                "errors": self.scraping_status["errors"],
                "elasticsearch_saved": ES_AVAILABLE
            }
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🎉 Scheduled Scraping Completed!")
            logger.info(f"   Total Jobs: {len(all_jobs)}")
            logger.info(f"   Roles: {len(SchedulerConfig.JOB_ROLES)}")
            logger.info(f"   By Role: {summary['jobs_by_role']}")
            logger.info(f"   By Country: {summary['jobs_by_country']}")
            logger.info(f"   Errors: {len(self.scraping_status['errors'])}")
            logger.info(f"{'='*60}\n")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Scheduled scraping failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat()
            }
        finally:
            self.scraping_status["is_scraping"] = False
            self.scraping_status["progress"] = 100
    
    def scheduled_job(self):
        """Job to be run on schedule"""
        logger.info(f"⏰ Scheduled job triggered at {datetime.utcnow()}")
        self.scrape_all_roles()
    
    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("⚠️  Scheduler is already running")
            return
        
        logger.info(f"🚀 Starting scheduler...")
        logger.info(f"   Schedule: Every {SchedulerConfig.SCHEDULE_DAY} at {SchedulerConfig.SCHEDULE_TIME}")
        logger.info(f"   Job Roles: {list(SchedulerConfig.JOB_ROLES.keys())}")
        logger.info(f"   Jobs per role: {SchedulerConfig.TOTAL_JOBS_PER_ROLE}")
        logger.info(f"   Primary location: {SchedulerConfig.LOCATION_PRIORITY['primary']['country']}")
        
        # Schedule the job
        schedule_func = getattr(schedule.every(), SchedulerConfig.SCHEDULE_DAY.lower())
        schedule_func.at(SchedulerConfig.SCHEDULE_TIME).do(self.scheduled_job)
        
        # Calculate next run time
        self.next_run = schedule.next_run()
        
        # Start scheduler in background thread
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info(f"✅ Scheduler started successfully!")
        logger.info(f"   Next run: {self.next_run}")
    
    def _run_scheduler(self):
        """Run scheduler loop in background thread"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            logger.warning("⚠️  Scheduler is not running")
            return
        
        logger.info("🛑 Stopping scheduler...")
        self.is_running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        logger.info("✅ Scheduler stopped")
    
    def get_status(self) -> Dict:
        """Get current scheduler status"""
        return {
            "is_running": self.is_running,
            "is_scraping": self.scraping_status.get("is_scraping", False),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "schedule": {
                "day": SchedulerConfig.SCHEDULE_DAY,
                "time": SchedulerConfig.SCHEDULE_TIME
            },
            "configuration": {
                "job_roles": {k: v for k, v in SchedulerConfig.JOB_ROLES.items()},
                "total_jobs_per_role": SchedulerConfig.TOTAL_JOBS_PER_ROLE,
                "primary_location": SchedulerConfig.LOCATION_PRIORITY["primary"],
                "fallback_locations": SchedulerConfig.LOCATION_PRIORITY["fallback"],
                "max_post_age_days": SchedulerConfig.MAX_POST_AGE_DAYS
            },
            "current_scraping": {
                "current_role": self.scraping_status.get("current_role"),
                "progress": self.scraping_status.get("progress", 0),
                "total_jobs_scraped": self.scraping_status.get("total_jobs_scraped", 0),
                "jobs_by_role": self.scraping_status.get("jobs_by_role", {}),
                "jobs_by_country": dict(self.scraping_status.get("jobs_by_country", {}))
            },
            "elasticsearch_enabled": ES_AVAILABLE
        }
    
    def run_now(self) -> Dict:
        """Manually trigger a scraping run"""
        if self.scraping_status.get("is_scraping", False):
            return {
                "status": "error",
                "message": "Scraping is already in progress"
            }
        
        logger.info("🚀 Manual scraping triggered")
        
        # Run in background thread to not block API
        thread = threading.Thread(target=self.scrape_all_roles, daemon=True)
        thread.start()
        
        return {
            "status": "started",
            "message": "Scraping started in background",
            "started_at": datetime.utcnow().isoformat()
        }


# Singleton instance
job_scheduler = JobScheduler()
