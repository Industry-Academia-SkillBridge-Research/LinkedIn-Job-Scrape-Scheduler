"""
LinkedIn Job Spider using Scrapy
For advanced crawling with built-in features like concurrent requests, item pipelines, etc.
"""
import scrapy
from scrapy.crawler import CrawlerProcess
from datetime import datetime
from typing import Generator
import os


class LinkedInJobSpider(scrapy.Spider):
    """
    Scrapy spider for scraping LinkedIn job listings
    
    Usage:
        scrapy crawl linkedin_jobs -a keywords="Python Developer" -a location="New York" -o output/jobs.json
    """
    
    name = "linkedin_jobs"
    allowed_domains = ["linkedin.com"]
    
    # Custom settings
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'ROBOTSTXT_OBEY': False,  # Set to True in production to respect robots.txt
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'COOKIES_ENABLED': False,
        'TELNETCONSOLE_ENABLED': False,
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }
    
    def __init__(self, keywords: str = "Software Engineer", location: str = "", 
                 max_jobs: int = 50, *args, **kwargs):
        """
        Initialize the spider
        
        Args:
            keywords: Job search keywords
            location: Job location
            max_jobs: Maximum number of jobs to scrape
        """
        super(LinkedInJobSpider, self).__init__(*args, **kwargs)
        self.keywords = keywords
        self.location = location
        self.max_jobs = int(max_jobs)
        self.jobs_scraped = 0
        
        # Build start URLs
        self.start_urls = [self._build_search_url(start=0)]
    
    def _build_search_url(self, start: int = 0) -> str:
        """Build LinkedIn job search URL"""
        base_url = "https://www.linkedin.com/jobs/search/"
        params = [
            f"keywords={self.keywords.replace(' ', '%20')}",
            f"start={start}"
        ]
        
        if self.location:
            params.append(f"location={self.location.replace(' ', '%20')}")
        
        return f"{base_url}?{'&'.join(params)}"
    
    def parse(self, response) -> Generator:
        """
        Parse job search results page
        
        Args:
            response: Scrapy response object
            
        Yields:
            Job data dictionaries or requests for next pages
        """
        # Find all job cards
        job_cards = response.css('div.base-card')
        
        if not job_cards:
            self.logger.info("No job cards found on this page")
            return
        
        for card in job_cards:
            if self.jobs_scraped >= self.max_jobs:
                return
            
            # Extract job data
            job_data = self._extract_job_data(card)
            
            if job_data:
                self.jobs_scraped += 1
                self.logger.info(f"Scraped job {self.jobs_scraped}/{self.max_jobs}: {job_data['title']}")
                yield job_data
        
        # Check if we need to scrape more jobs
        if self.jobs_scraped < self.max_jobs:
            # Get next page
            next_start = (self.jobs_scraped // 25 + 1) * 25
            next_url = self._build_search_url(start=next_start)
            
            self.logger.info(f"Moving to next page: {next_url}")
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                dont_filter=True
            )
    
    def _extract_job_data(self, card) -> dict:
        """
        Extract job data from a job card
        
        Args:
            card: Scrapy selector for job card
            
        Returns:
            Dictionary with job data
        """
        try:
            # Extract job title
            title = card.css('h3.base-search-card__title::text').get()
            title = title.strip() if title else "N/A"
            
            # Extract company name
            company = card.css('h4.base-search-card__subtitle a::text').get()
            if not company:
                company = card.css('h4.base-search-card__subtitle::text').get()
            company = company.strip() if company else "N/A"
            
            # Extract location
            location = card.css('span.job-search-card__location::text').get()
            location = location.strip() if location else "N/A"
            
            # Extract job URL
            job_url = card.css('a.base-card__full-link::attr(href)').get()
            job_url = job_url if job_url else ""
            
            # Extract job ID
            job_id = ""
            if job_url and 'jobs/view/' in job_url:
                job_id = job_url.split('jobs/view/')[-1].split('?')[0]
            
            # Extract posted date
            posted_date = card.css('time::attr(datetime)').get()
            posted_date = posted_date if posted_date else ""
            
            # Extract salary if available
            salary = card.css('span.job-search-card__salary-info::text').get()
            salary = salary.strip() if salary else "N/A"
            
            job_data = {
                'job_id': job_id,
                'title': title,
                'company': company,
                'location': location,
                'salary': salary,
                'posted_date': posted_date,
                'job_url': job_url,
                'search_keywords': self.keywords,
                'search_location': self.location,
                'scraped_at': datetime.now().isoformat()
            }
            
            return job_data
            
        except Exception as e:
            self.logger.error(f"Error extracting job data: {e}")
            return None


class LinkedInJobDetailsSpider(scrapy.Spider):
    """
    Spider for scraping detailed job information
    """
    
    name = "linkedin_job_details"
    allowed_domains = ["linkedin.com"]
    
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'ROBOTSTXT_OBEY': False,
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
    }
    
    def __init__(self, job_urls: str = "", *args, **kwargs):
        """
        Initialize the spider with job URLs
        
        Args:
            job_urls: Comma-separated list of job URLs
        """
        super(LinkedInJobDetailsSpider, self).__init__(*args, **kwargs)
        self.start_urls = job_urls.split(',') if job_urls else []
    
    def parse(self, response):
        """Parse job details page"""
        # Extract job description
        description = response.css('div.show-more-less-html__markup ::text').getall()
        description = ' '.join([text.strip() for text in description if text.strip()])
        
        # Extract criteria
        criteria = {}
        criteria_items = response.css('li.description__job-criteria-item')
        for item in criteria_items:
            header = item.css('h3::text').get()
            value = item.css('span::text').get()
            if header and value:
                criteria[header.strip()] = value.strip()
        
        # Extract company info
        company_name = response.css('a.topcard__org-name-link::text').get()
        company_name = company_name.strip() if company_name else "N/A"
        
        yield {
            'job_url': response.url,
            'company': company_name,
            'description': description,
            'seniority_level': criteria.get('Seniority level', 'N/A'),
            'employment_type': criteria.get('Employment type', 'N/A'),
            'job_function': criteria.get('Job function', 'N/A'),
            'industries': criteria.get('Industries', 'N/A'),
            'scraped_at': datetime.now().isoformat()
        }


def run_spider(spider_class, **kwargs):
    """
    Helper function to run a Scrapy spider programmatically
    
    Args:
        spider_class: The spider class to run
        **kwargs: Arguments to pass to the spider
    """
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    process.crawl(spider_class, **kwargs)
    process.start()


# Example usage
if __name__ == "__main__":
    # Run the spider
    run_spider(
        LinkedInJobSpider,
        keywords="Machine Learning Engineer",
        location="Remote",
        max_jobs=30
    )
