"""
Utility functions for web scraping
"""
import time
import random
from fake_useragent import UserAgent
from typing import Dict, List


def get_random_user_agent() -> str:
    """Generate a random user agent string"""
    ua = UserAgent()
    return ua.random


def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Add a random delay between requests"""
    time.sleep(random.uniform(min_seconds, max_seconds))


def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    return " ".join(text.split()).strip()


def get_headers() -> Dict[str, str]:
    """Get HTTP headers with random user agent"""
    return {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }


def parse_salary(salary_text: str) -> Dict[str, str]:
    """Parse salary information from text"""
    if not salary_text:
        return {"min": None, "max": None, "currency": None}
    
    # Basic parsing logic - can be enhanced
    return {
        "raw": clean_text(salary_text),
        "min": None,
        "max": None,
        "currency": "USD"
    }


def build_linkedin_search_url(keywords: str, location: str = "", 
                              experience_level: str = "", 
                              job_type: str = "",
                              date_posted: str = "") -> str:
    """Build LinkedIn job search URL with parameters"""
    base_url = "https://www.linkedin.com/jobs/search/"
    params = []
    
    if keywords:
        params.append(f"keywords={keywords.replace(' ', '%20')}")
    if location:
        params.append(f"location={location.replace(' ', '%20')}")
    if experience_level:
        params.append(f"f_E={experience_level}")
    if job_type:
        params.append(f"f_JT={job_type}")
    if date_posted:
        params.append(f"f_TPR={date_posted}")
    
    if params:
        return f"{base_url}?{'&'.join(params)}"
    return base_url


def save_to_json(data: List[Dict], filename: str):
    """Save data to JSON file"""
    import json
    import os
    
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Data saved to {filename}")


def save_to_csv(data: List[Dict], filename: str):
    """Save data to CSV file"""
    import pandas as pd
    import os
    
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8')
    
    print(f"Data saved to {filename}")


def save_to_excel(data: List[Dict], filename: str):
    """Save data to Excel file"""
    import pandas as pd
    import os
    
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False, engine='openpyxl')
    
    print(f"Data saved to {filename}")
