"""
Job filtering utilities
Filters jobs based on exact keyword matching
"""
import re
from typing import List, Dict


def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    return text.lower().strip()


def extract_keywords(keyword_string: str) -> List[str]:
    """
    Extract individual keywords from search string
    
    Examples:
        "Data Engineer" -> ["data", "engineer", "data engineer"]
        "Senior Python Developer" -> ["senior", "python", "developer", "senior python developer"]
    """
    keywords = []
    
    # Add full phrase
    normalized_phrase = normalize_text(keyword_string)
    keywords.append(normalized_phrase)
    
    # Add individual words (for partial matching)
    words = normalized_phrase.split()
    keywords.extend(words)
    
    return keywords


def check_exact_match(job_title: str, search_keywords: str, strict: bool = True) -> bool:
    """
    Check if job title matches the search keywords exactly
    
    Args:
        job_title: The job title to check
        search_keywords: The search keywords
        strict: If True, requires all keywords to be present in order
                If False, allows any keyword to match
    
    Returns:
        True if match, False otherwise
    
    Examples:
        check_exact_match("Data Engineer", "Data Engineer") -> True
        check_exact_match("Senior Data Engineer", "Data Engineer") -> True
        check_exact_match("Software Engineer", "Data Engineer") -> False
        check_exact_match("Data Analyst", "Data Engineer", strict=False) -> True (both have "Data")
    """
    normalized_title = normalize_text(job_title)
    normalized_keywords = normalize_text(search_keywords)
    
    # Split keywords into individual words
    keyword_words = normalized_keywords.split()
    
    if strict:
        # Check if all keywords appear in the title in order (allowing other words between)
        # E.g., "Senior Data Engineer" matches "Data Engineer"
        pattern = r'\b' + r'\b.*\b'.join(re.escape(word) for word in keyword_words) + r'\b'
        return bool(re.search(pattern, normalized_title))
    else:
        # At least one keyword must match
        return any(word in normalized_title for word in keyword_words)


def filter_jobs_by_keywords(jobs: List[Dict], search_keywords: str, strict: bool = True) -> List[Dict]:
    """
    Filter jobs to only include those matching the exact keywords
    
    Args:
        jobs: List of job dictionaries
        search_keywords: The search keywords used
        strict: If True, requires all keywords to be present
    
    Returns:
        Filtered list of jobs
    
    Example:
        jobs = [
            {"title": "Data Engineer", ...},
            {"title": "Software Engineer", ...},
            {"title": "Senior Data Engineer", ...}
        ]
        filter_jobs_by_keywords(jobs, "Data Engineer") 
        # Returns only jobs 0 and 2
    """
    filtered_jobs = []
    
    for job in jobs:
        job_title = job.get('title', '')
        
        if check_exact_match(job_title, search_keywords, strict=strict):
            filtered_jobs.append(job)
    
    return filtered_jobs


def calculate_relevance_score(job_title: str, search_keywords: str) -> float:
    """
    Calculate relevance score between 0 and 1
    
    Higher score = more relevant
    
    Args:
        job_title: The job title
        search_keywords: The search keywords
    
    Returns:
        Relevance score (0.0 to 1.0)
    """
    normalized_title = normalize_text(job_title)
    normalized_keywords = normalize_text(search_keywords)
    keyword_words = set(normalized_keywords.split())
    title_words = set(normalized_title.split())
    
    # Calculate Jaccard similarity
    intersection = keyword_words.intersection(title_words)
    union = keyword_words.union(title_words)
    
    if not union:
        return 0.0
    
    base_score = len(intersection) / len(union)
    
    # Bonus for exact phrase match
    if normalized_keywords in normalized_title:
        base_score += 0.3
    
    # Bonus for word order preservation
    keyword_list = normalized_keywords.split()
    if len(keyword_list) > 1:
        pattern = r'\b' + r'\b.*\b'.join(re.escape(word) for word in keyword_list) + r'\b'
        if re.search(pattern, normalized_title):
            base_score += 0.2
    
    return min(base_score, 1.0)


def filter_and_rank_jobs(
    jobs: List[Dict], 
    search_keywords: str, 
    min_score: float = 0.5
) -> List[Dict]:
    """
    Filter jobs by relevance score and rank them
    
    Args:
        jobs: List of job dictionaries
        search_keywords: Search keywords
        min_score: Minimum relevance score (0.0 to 1.0)
    
    Returns:
        Filtered and ranked list of jobs with relevance scores
    """
    scored_jobs = []
    
    for job in jobs:
        job_title = job.get('title', '')
        score = calculate_relevance_score(job_title, search_keywords)
        
        if score >= min_score:
            job_copy = job.copy()
            job_copy['relevance_score'] = round(score, 2)
            scored_jobs.append(job_copy)
    
    # Sort by relevance score (highest first)
    scored_jobs.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    return scored_jobs


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    test_jobs = [
        {"title": "Data Engineer", "company": "Tech Corp"},
        {"title": "Senior Data Engineer", "company": "StartUp"},
        {"title": "Software Engineer", "company": "BigCo"},
        {"title": "Data Engineering Lead", "company": "Company"},
        {"title": "Software Engineer, Data Platform", "company": "Platform Inc"},
        {"title": "Lead Data Engineer - Cloud", "company": "Cloud Corp"},
    ]
    
    search_term = "Data Engineer"
    
    print(f"🔍 Searching for: '{search_term}'")
    print("=" * 60)
    
    # Test strict filtering
    print("\n✅ Strict Filtering (all keywords must match):")
    filtered = filter_jobs_by_keywords(test_jobs, search_term, strict=True)
    for job in filtered:
        print(f"  ✓ {job['title']} - {job['company']}")
    
    # Test with relevance scoring
    print("\n📊 Ranked by Relevance Score:")
    ranked = filter_and_rank_jobs(test_jobs, search_term, min_score=0.4)
    for job in ranked:
        print(f"  [{job['relevance_score']:.2f}] {job['title']} - {job['company']}")
    
    print("\n" + "=" * 60)
    print(f"Original jobs: {len(test_jobs)}")
    print(f"Filtered jobs (strict): {len(filtered)}")
    print(f"Filtered jobs (scored): {len(ranked)}")
