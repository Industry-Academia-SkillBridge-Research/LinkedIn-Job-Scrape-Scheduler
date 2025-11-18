"""
LinkedIn Job Scraper using BeautifulSoup
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
from datetime import datetime
from .utils import (
    get_headers, 
    clean_text, 
    random_delay, 
    build_linkedin_search_url,
    save_to_csv,
    save_to_json,
    save_to_excel
)


class LinkedInScraperBS:
    """
    LinkedIn job scraper using BeautifulSoup and requests
    Note: This works for public job listings without authentication
    """
    
    def __init__(self, delay_min: float = 2.0, delay_max: float = 5.0):
        """
        Initialize the scraper
        
        Args:
            delay_min: Minimum delay between requests in seconds
            delay_max: Maximum delay between requests in seconds
        """
        self.session = requests.Session()
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.jobs_scraped = []
        
    def search_jobs(self, keywords: str, location: str = "", 
                   max_jobs: int = 50, experience_level: str = "",
                   job_type: str = "", date_posted: str = "",
                   fetch_details: bool = False) -> List[Dict]:
        """
        Search for jobs on LinkedIn
        
        Args:
            keywords: Job search keywords (e.g., "Python Developer")
            location: Job location (e.g., "New York, NY")
            max_jobs: Maximum number of jobs to scrape
            experience_level: Experience level filter (1=Internship, 2=Entry, 3=Associate, 4=Mid-Senior, 5=Director, 6=Executive)
            job_type: Job type filter (F=Full-time, P=Part-time, C=Contract, T=Temporary, V=Volunteer, I=Internship)
            date_posted: Date posted filter (r86400=Past 24 hours, r604800=Past week, r2592000=Past month)
            fetch_details: Whether to fetch detailed information including skills for each job
            
        Returns:
            List of job dictionaries
        """
        print(f"Searching for '{keywords}' jobs in '{location}'...")
        
        jobs = []
        start = 0
        
        while len(jobs) < max_jobs:
            # Build search URL
            url = build_linkedin_search_url(
                keywords=keywords,
                location=location,
                experience_level=experience_level,
                job_type=job_type,
                date_posted=date_posted
            )
            url += f"&start={start}"
            
            print(f"Fetching page {start // 25 + 1}...")
            
            try:
                # Make request
                response = self.session.get(url, headers=get_headers(), timeout=10)
                response.raise_for_status()
                
                # Parse HTML
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Find job cards
                job_cards = soup.find_all('div', class_='base-card')
                
                if not job_cards:
                    print("No more jobs found.")
                    break
                
                # Extract job information
                for card in job_cards:
                    if len(jobs) >= max_jobs:
                        break
                    
                    job_data = self._extract_job_data(card)
                    if job_data:
                        # Fetch detailed information if requested
                        if fetch_details and job_data.get('job_url'):
                            print(f"  Fetching details for: {job_data['title']}")
                            details = self.get_job_details(job_data['job_url'])
                            if details:
                                job_data.update(details)
                            random_delay(self.delay_min, self.delay_max)
                        
                        jobs.append(job_data)
                        print(f"Scraped: {job_data['title']} at {job_data['company']}")
                
                # Move to next page
                start += 25
                
                # Add delay to avoid being blocked
                random_delay(self.delay_min, self.delay_max)
                
            except requests.exceptions.RequestException as e:
                print(f"Error fetching jobs: {e}")
                break
        
        self.jobs_scraped = jobs
        print(f"\nTotal jobs scraped: {len(jobs)}")
        return jobs
    
    def _extract_job_data(self, card) -> Optional[Dict]:
        """Extract job data from a job card"""
        try:
            # Extract job title
            title_elem = card.find('h3', class_='base-search-card__title')
            title = clean_text(title_elem.text) if title_elem else "N/A"
            
            # Extract company name
            company_elem = card.find('h4', class_='base-search-card__subtitle')
            company = clean_text(company_elem.text) if company_elem else "N/A"
            
            # Extract location
            location_elem = card.find('span', class_='job-search-card__location')
            location = clean_text(location_elem.text) if location_elem else "N/A"
            
            # Extract job link
            link_elem = card.find('a', class_='base-card__full-link')
            job_url = link_elem.get('href', '') if link_elem else ""
            
            # Extract job ID from URL
            job_id = ""
            if job_url and 'jobs/view/' in job_url:
                job_id = job_url.split('jobs/view/')[-1].split('?')[0]
            
            # Extract posted date
            date_elem = card.find('time', class_='job-search-card__listdate')
            if not date_elem:
                date_elem = card.find('time')
            posted_date = date_elem.get('datetime', '') if date_elem else ""
            
            job_data = {
                'job_id': job_id,
                'title': title,
                'company': company,
                'location': location,
                'posted_date': posted_date,
                'job_url': job_url,
                'scraped_at': datetime.now().isoformat()
            }
            
            return job_data
            
        except Exception as e:
            print(f"Error extracting job data: {e}")
            return None
    
    def get_job_details(self, job_url: str) -> Optional[Dict]:
        """
        Fetch detailed information about a specific job
        
        Args:
            job_url: URL of the job posting
            
        Returns:
            Dictionary with detailed job information including skills
        """
        try:
            response = self.session.get(job_url, headers=get_headers(), timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract description
            description_elem = soup.find('div', class_='show-more-less-html__markup')
            description = clean_text(description_elem.text) if description_elem else "N/A"
            
            # Extract criteria (seniority, employment type, etc.)
            criteria = {}
            criteria_items = soup.find_all('li', class_='description__job-criteria-item')
            for item in criteria_items:
                header = item.find('h3')
                value = item.find('span')
                if header and value:
                    criteria[clean_text(header.text)] = clean_text(value.text)
            
            # Extract skills
            skills = self._extract_skills(soup, description)
            
            return {
                'description': description,
                'criteria': criteria,
                'skills': skills
            }
            
        except Exception as e:
            print(f"Error fetching job details: {e}")
            return None
    
    def _extract_skills(self, soup, description: str) -> List[str]:
        """
        Extract required skills from job posting
        
        Args:
            soup: BeautifulSoup object
            description: Job description text
            
        Returns:
            List of skills
        """
        skills = []
        
        # Method 1: Look for skills section in the page
        skills_section = soup.find('div', class_='show-more-less-html__markup')
        if skills_section:
            # Look for skill badges or tags
            skill_spans = skills_section.find_all('span', class_='skill-badge')
            for span in skill_spans:
                skill = clean_text(span.text)
                if skill and skill not in skills:
                    skills.append(skill)
        
        # Method 2: Extract from description using common patterns
        if not skills:
            skills = self._parse_skills_from_text(description)
        
        return skills
    
    def _parse_skills_from_text(self, text: str) -> List[str]:
        """
        Parse skills from job description text using keywords and patterns
        
        Args:
            text: Job description text
            
        Returns:
            List of identified skills
        """
        import re
        
        # Common technical skills to look for
        common_skills = [
            # Programming Languages
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Ruby', 'PHP', 
            'Go', 'Rust', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'SQL',
            
            # Web Technologies
            'HTML', 'CSS', 'React', 'Angular', 'Vue.js', 'Node.js', 'Django', 'Flask',
            'Express.js', 'Spring Boot', 'ASP.NET', 'Laravel', 'Rails',
            
            # Data Science & ML
            'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Keras',
            'Scikit-learn', 'Pandas', 'NumPy', 'Data Analysis', 'Statistics',
            'NLP', 'Computer Vision', 'Neural Networks',
            
            # Databases
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server',
            'Cassandra', 'DynamoDB', 'Elasticsearch', 'Neo4j',
            
            # Cloud & DevOps
            'AWS', 'Azure', 'Google Cloud', 'GCP', 'Docker', 'Kubernetes', 'Jenkins',
            'CI/CD', 'Terraform', 'Ansible', 'Linux', 'Git', 'GitHub', 'GitLab',
            
            # Data Tools
            'Tableau', 'Power BI', 'Looker', 'Apache Spark', 'Hadoop', 'Kafka',
            'Airflow', 'ETL', 'Data Warehousing', 'Big Data',
            
            # Testing
            'Selenium', 'Jest', 'Pytest', 'JUnit', 'TestNG', 'Cypress',
            
            # Soft Skills
            'Communication', 'Leadership', 'Problem Solving', 'Teamwork',
            'Project Management', 'Agile', 'Scrum', 'Analytical Skills',
            
            # Other
            'REST API', 'GraphQL', 'Microservices', 'Blockchain', 'IoT',
            'Cybersecurity', 'UI/UX', 'Excel', 'JIRA', 'Confluence'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            # Create pattern to match skill (case insensitive, word boundary)
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                if skill not in found_skills:
                    found_skills.append(skill)
        
        return found_skills
    
    def save_to_csv(self, jobs: List[Dict] = None, filename: str = "output/jobs.csv"):
        """Save jobs to CSV file"""
        if jobs is None:
            jobs = self.jobs_scraped
        save_to_csv(jobs, filename)
    
    def save_to_json(self, jobs: List[Dict] = None, filename: str = "output/jobs.json"):
        """Save jobs to JSON file"""
        if jobs is None:
            jobs = self.jobs_scraped
        save_to_json(jobs, filename)
    
    def save_to_excel(self, jobs: List[Dict] = None, filename: str = "output/jobs.xlsx"):
        """Save jobs to Excel file"""
        if jobs is None:
            jobs = self.jobs_scraped
        save_to_excel(jobs, filename)


# Example usage
if __name__ == "__main__":
    scraper = LinkedInScraperBS()
    
    # Search for jobs
    jobs = scraper.search_jobs(
        keywords="Python Developer",
        location="United States",
        max_jobs=25
    )
    
    # Save results
    scraper.save_to_csv()
    scraper.save_to_json()
    
    print(f"\nScraped {len(jobs)} jobs successfully!")
