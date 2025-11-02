"""
Simple LinkedIn Job Scraper - BeautifulSoup Only
This version uses only BeautifulSoup (no Selenium required)
"""
import os
from scrapers.beautifulsoup_scraper import LinkedInScraperBS


def main():
    """Main function to run the scraper"""
    print("=" * 70)
    print("LinkedIn Job Scraper - BeautifulSoup Method".center(70))
    print("=" * 70)
    print()
    
    # Get user input
    keywords = input("Enter job keywords (e.g., 'Data Analyst'): ").strip()
    if not keywords:
        keywords = "Data Analyst"
        print(f"Using default: {keywords}")
    
    location = input("Enter location (e.g., 'Remote', or leave empty): ").strip()
    
    max_jobs_input = input("Enter max jobs to scrape (default: 10): ").strip()
    max_jobs = int(max_jobs_input) if max_jobs_input else 10
    
    print()
    print("⚠️  Skills Extraction:")
    print("    YES = Fetch job descriptions and extract skills (slower, ~4 sec/job)")
    print("    NO  = Fetch basic info only (faster, ~1 sec/job)")
    
    enable_skills = input("\nExtract skills and details? (Y/n): ").strip().lower()
    fetch_details = enable_skills != 'n'
    
    if fetch_details:
        est_time = max_jobs * 4
        print(f"\n⏱️  Estimated time: {est_time} seconds (~{est_time/60:.1f} minutes)")
    else:
        print(f"\n⏱️  Estimated time: {max_jobs} seconds (fast mode)")
    
    print()
    input("Press Enter to start scraping...")
    
    print("\n" + "=" * 70)
    print("Starting scraper...")
    print("-" * 70)
    
    # Create output directory
    os.makedirs("output", exist_ok=True)
    
    # Initialize scraper
    scraper = LinkedInScraperBS(delay_min=2.0, delay_max=4.0)
    
    try:
        # Search for jobs
        jobs = scraper.search_jobs(
            keywords=keywords,
            location=location,
            max_jobs=max_jobs,
            fetch_details=fetch_details
        )
        
        if jobs:
            # Save results
            scraper.save_to_csv(filename="output/jobs_beautifulsoup.csv")
            scraper.save_to_json(filename="output/jobs_beautifulsoup.json")
            
            print(f"\n✓ Successfully scraped {len(jobs)} jobs!")
            
            # Show sample
            print("\n" + "=" * 70)
            print("Sample Job (First Result)")
            print("-" * 70)
            
            sample = jobs[0]
            print(f"Title:    {sample.get('title', 'N/A')}")
            print(f"Company:  {sample.get('company', 'N/A')}")
            print(f"Location: {sample.get('location', 'N/A')}")
            print(f"Posted:   {sample.get('posted_date', 'N/A')}")
            
            if fetch_details and 'skills' in sample:
                skills = sample.get('skills', [])
                print(f"\nSkills ({len(skills)}): {', '.join(skills[:10])}")
                if len(skills) > 10:
                    print(f"           ... and {len(skills) - 10} more")
                
                criteria = sample.get('criteria', {})
                if criteria:
                    print(f"\nJob Criteria:")
                    for key, value in criteria.items():
                        print(f"  • {key}: {value}")
            
            # Summary
            print("\n" + "=" * 70)
            print("Scraping Complete!")
            print("=" * 70)
            print(f"\nResults saved to:")
            print("  ✓ output/jobs_beautifulsoup.json")
            print("  ✓ output/jobs_beautifulsoup.csv")
            
            if fetch_details:
                print(f"\n✓ Output includes:")
                print("  • Job title, company, location, posted date")
                print("  • Required skills (extracted from description)")
                print("  • Job criteria (seniority, employment type, etc.)")
                print("  • Full job description")
            else:
                print(f"\n✓ Output includes: Basic job information")
                print("  (Run again with skills extraction for detailed info)")
            
        else:
            print("\n✗ No jobs found")
            print("Tips:")
            print("  • Try different keywords")
            print("  • Try broader location (or leave empty)")
            print("  • Check your internet connection")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("Thank you for using LinkedIn Job Scraper!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user.")
    except Exception as e:
        print(f"\n\n✗ Unexpected error: {e}")
