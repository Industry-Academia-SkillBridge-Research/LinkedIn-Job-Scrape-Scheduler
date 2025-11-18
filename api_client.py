"""
Example client code to interact with LinkedIn Job Scraper API
"""
import requests
import time
import json
from typing import List, Dict


class LinkedInJobScraperClient:
    """Client for LinkedIn Job Scraper API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the client"""
        self.base_url = base_url
        
    def scrape_sync(self, keywords: str, location: str = "", 
                   max_jobs: int = 10, fetch_details: bool = True) -> List[Dict]:
        """
        Scrape jobs synchronously (blocking)
        
        Args:
            keywords: Job search keywords
            location: Job location
            max_jobs: Maximum number of jobs
            fetch_details: Extract skills and details
            
        Returns:
            List of job dictionaries
        """
        url = f"{self.base_url}/api/v1/scrape/sync"
        
        payload = {
            "keywords": keywords,
            "location": location,
            "max_jobs": max_jobs,
            "fetch_details": fetch_details
        }
        
        print(f"Scraping {max_jobs} jobs for '{keywords}'...")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        jobs = response.json()
        print(f"✓ Got {len(jobs)} jobs")
        return jobs
    
    def scrape_async(self, keywords: str, location: str = "", 
                    max_jobs: int = 10, fetch_details: bool = True) -> str:
        """
        Start async scraping job
        
        Returns:
            Job ID
        """
        url = f"{self.base_url}/api/v1/scrape/async"
        
        payload = {
            "keywords": keywords,
            "location": location,
            "max_jobs": max_jobs,
            "fetch_details": fetch_details
        }
        
        print(f"Starting async job for '{keywords}'...")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        job_id = data["job_id"]
        print(f"✓ Job created: {job_id}")
        return job_id
    
    def get_status(self, job_id: str) -> Dict:
        """Get scraping job status"""
        url = f"{self.base_url}/api/v1/scrape/status/{job_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_results(self, job_id: str) -> List[Dict]:
        """Get scraping job results"""
        url = f"{self.base_url}/api/v1/scrape/results/{job_id}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, job_id: str, check_interval: int = 5) -> List[Dict]:
        """
        Wait for async job to complete and return results
        
        Args:
            job_id: Job ID to wait for
            check_interval: Seconds between status checks
            
        Returns:
            List of job dictionaries
        """
        print(f"Waiting for job {job_id} to complete...")
        
        while True:
            status = self.get_status(job_id)
            
            print(f"  Status: {status['status']} - Progress: {status['progress']}% - {status['scraped_jobs']}/{status['total_jobs']} jobs")
            
            if status['status'] == 'completed':
                print("✓ Job completed!")
                return self.get_results(job_id)
            elif status['status'] == 'failed':
                raise Exception(f"Job failed: {status['message']}")
            
            time.sleep(check_interval)
    
    def download_results(self, job_id: str, output_file: str):
        """Download results as JSON file"""
        url = f"{self.base_url}/api/v1/download/{job_id}"
        response = requests.get(url)
        response.raise_for_status()
        
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        print(f"✓ Downloaded to {output_file}")
    
    def list_jobs(self) -> Dict:
        """List all scraping jobs"""
        url = f"{self.base_url}/api/v1/jobs"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict:
        """Check API health"""
        url = f"{self.base_url}/api/v1/health"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()


# Example Usage
def example_1_sync_scraping():
    """Example: Synchronous scraping"""
    print("\n" + "="*70)
    print("Example 1: Synchronous Scraping")
    print("="*70)
    
    client = LinkedInJobScraperClient()
    
    jobs = client.scrape_sync(
        keywords="Data Analyst",
        location="Remote",
        max_jobs=5,
        fetch_details=True
    )
    
    print(f"\nScraped {len(jobs)} jobs:")
    for i, job in enumerate(jobs[:3], 1):
        print(f"\n{i}. {job['title']} at {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Skills: {', '.join(job.get('skills', [])[:5])}")


def example_2_async_scraping():
    """Example: Asynchronous scraping"""
    print("\n" + "="*70)
    print("Example 2: Asynchronous Scraping")
    print("="*70)
    
    client = LinkedInJobScraperClient()
    
    # Start async job
    job_id = client.scrape_async(
        keywords="Python Developer",
        location="United States",
        max_jobs=15,
        fetch_details=True
    )
    
    # Wait for completion
    jobs = client.wait_for_completion(job_id)
    
    print(f"\nScraped {len(jobs)} jobs:")
    for i, job in enumerate(jobs[:3], 1):
        print(f"\n{i}. {job['title']} at {job['company']}")
        print(f"   Skills: {', '.join(job.get('skills', [])[:5])}")
    
    # Download results
    client.download_results(job_id, f"output/client_download_{job_id}.json")


def example_3_multiple_searches():
    """Example: Multiple parallel searches"""
    print("\n" + "="*70)
    print("Example 3: Multiple Parallel Searches")
    print("="*70)
    
    client = LinkedInJobScraperClient()
    
    searches = [
        ("Data Scientist", "Remote"),
        ("Machine Learning Engineer", "San Francisco"),
        ("DevOps Engineer", "New York")
    ]
    
    job_ids = []
    
    # Start all jobs
    for keywords, location in searches:
        job_id = client.scrape_async(
            keywords=keywords,
            location=location,
            max_jobs=5,
            fetch_details=True
        )
        job_ids.append((job_id, keywords))
    
    # Wait for all to complete
    all_jobs = {}
    for job_id, keywords in job_ids:
        jobs = client.wait_for_completion(job_id, check_interval=3)
        all_jobs[keywords] = jobs
    
    # Summary
    print("\n" + "="*70)
    print("Summary:")
    for keywords, jobs in all_jobs.items():
        print(f"  {keywords}: {len(jobs)} jobs")


def example_4_health_and_status():
    """Example: Check API health and list jobs"""
    print("\n" + "="*70)
    print("Example 4: Health Check and Job Listing")
    print("="*70)
    
    client = LinkedInJobScraperClient()
    
    # Health check
    health = client.health_check()
    print(f"\nAPI Status: {health['status']}")
    print(f"Active Jobs: {health['active_jobs']}")
    print(f"Timestamp: {health['timestamp']}")
    
    # List all jobs
    jobs_list = client.list_jobs()
    print(f"\nTotal Jobs: {jobs_list['total']}")
    
    if jobs_list['jobs']:
        print("\nRecent Jobs:")
        for job in jobs_list['jobs'][:5]:
            print(f"  • {job['job_id'][:8]}... - {job['status']} ({job['scraped_jobs']} jobs)")


def main():
    """Run examples"""
    print("\n" + "="*70)
    print("LinkedIn Job Scraper API - Client Examples")
    print("="*70)
    print("\nMake sure the API server is running: python api.py")
    print()
    
    examples = {
        '1': ("Synchronous scraping (5 jobs)", example_1_sync_scraping),
        '2': ("Asynchronous scraping (15 jobs)", example_2_async_scraping),
        '3': ("Multiple parallel searches", example_3_multiple_searches),
        '4': ("Health check and job listing", example_4_health_and_status),
    }
    
    print("Select example to run:")
    for key, (desc, _) in examples.items():
        print(f"  {key}. {desc}")
    print("  5. Run all examples")
    print("  6. Exit")
    
    choice = input("\nEnter choice (1-6): ").strip()
    
    if choice == '6':
        return
    elif choice == '5':
        for _, example_func in examples.values():
            try:
                example_func()
                time.sleep(2)
            except Exception as e:
                print(f"\n✗ Error: {e}")
    elif choice in examples:
        try:
            _, example_func = examples[choice]
            example_func()
        except Exception as e:
            print(f"\n✗ Error: {e}")
            print("\nMake sure API server is running: python api.py")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure API server is running: python api.py")
