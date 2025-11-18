"""
LinkedIn Job Scraper using Selenium
This is useful for scraping dynamic content that requires JavaScript execution
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Optional
from datetime import datetime
import time
from .utils import (
    clean_text, 
    random_delay, 
    build_linkedin_search_url,
    save_to_csv,
    save_to_json,
    save_to_excel
)


class LinkedInScraperSelenium:
    """
    LinkedIn job scraper using Selenium WebDriver
    Handles dynamic content and JavaScript-rendered pages
    """
    
    def __init__(self, headless: bool = True, delay_min: float = 2.0, delay_max: float = 5.0):
        """
        Initialize the Selenium scraper
        
        Args:
            headless: Run browser in headless mode (no GUI)
            delay_min: Minimum delay between actions in seconds
            delay_max: Maximum delay between actions in seconds
        """
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.jobs_scraped = []
        
        # Set up Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Initialize WebDriver
        try:
            # Try with webdriver-manager first
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            print("Selenium WebDriver initialized successfully")
        except Exception as e:
            print(f"Error initializing Selenium with webdriver-manager: {e}")
            print("\nTrying alternative method...")
            try:
                # Try without service (uses system PATH)
                self.driver = webdriver.Chrome(options=chrome_options)
                self.wait = WebDriverWait(self.driver, 10)
                print("Selenium WebDriver initialized successfully (using system Chrome)")
            except Exception as e2:
                print(f"\nSelenium initialization failed: {e2}")
                print("\n" + "="*70)
                print("SELENIUM SETUP REQUIRED")
                print("="*70)
                print("\nSelenium requires Chrome browser and ChromeDriver.")
                print("\nOptions:")
                print("1. Use BeautifulSoup instead (simpler, no browser needed)")
                print("2. Install Chrome browser if not installed")
                print("3. Try: pip install --upgrade selenium webdriver-manager")
                print("\nFor now, please use BeautifulSoup method (option 1 in main menu)")
                print("="*70)
                raise RuntimeError("Selenium not available. Use BeautifulSoup scraper instead.")
    
    def search_jobs(self, keywords: str, location: str = "", 
                   max_jobs: int = 50, experience_level: str = "",
                   job_type: str = "", date_posted: str = "",
                   fetch_details: bool = False) -> List[Dict]:
        """
        Search for jobs on LinkedIn using Selenium
        
        Args:
            keywords: Job search keywords
            location: Job location
            max_jobs: Maximum number of jobs to scrape
            experience_level: Experience level filter
            job_type: Job type filter
            date_posted: Date posted filter
            fetch_details: Whether to fetch detailed information including skills for each job
            
        Returns:
            List of job dictionaries
        """
        print(f"Searching for '{keywords}' jobs in '{location}'...")
        
        jobs = []
        
        # Build search URL
        url = build_linkedin_search_url(
            keywords=keywords,
            location=location,
            experience_level=experience_level,
            job_type=job_type,
            date_posted=date_posted
        )
        
        try:
            # Navigate to search page
            self.driver.get(url)
            random_delay(self.delay_min, self.delay_max)
            
            # Scroll and load more jobs
            page_num = 1
            while len(jobs) < max_jobs:
                print(f"Processing page {page_num}...")
                
                # Scroll to load more jobs
                self._scroll_page()
                
                # Find job cards
                try:
                    job_cards = self.driver.find_elements(By.CSS_SELECTOR, 'div.base-card')
                    
                    if not job_cards:
                        print("No job cards found.")
                        break
                    
                    # Extract job information
                    for card in job_cards:
                        if len(jobs) >= max_jobs:
                            break
                        
                        job_data = self._extract_job_data_selenium(card)
                        if job_data and not self._is_duplicate(jobs, job_data):
                            # Fetch detailed information if requested
                            if fetch_details and job_data.get('job_url'):
                                print(f"  Fetching details for: {job_data['title']}")
                                details = self.get_job_details(job_data['job_url'])
                                if details:
                                    job_data.update(details)
                                random_delay(self.delay_min, self.delay_max)
                            
                            jobs.append(job_data)
                            print(f"Scraped: {job_data['title']} at {job_data['company']}")
                    
                    # Try to click "See more jobs" button
                    try:
                        see_more_button = self.driver.find_element(
                            By.CSS_SELECTOR, 
                            'button[aria-label="See more jobs"]'
                        )
                        see_more_button.click()
                        random_delay(self.delay_min, self.delay_max)
                        page_num += 1
                    except NoSuchElementException:
                        print("No more pages available.")
                        break
                        
                except Exception as e:
                    print(f"Error finding job cards: {e}")
                    break
            
        except Exception as e:
            print(f"Error during search: {e}")
        
        self.jobs_scraped = jobs
        print(f"\nTotal jobs scraped: {len(jobs)}")
        return jobs
    
    def _scroll_page(self):
        """Scroll the page to load dynamic content"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for _ in range(3):  # Scroll 3 times
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Calculate new scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    
    def _extract_job_data_selenium(self, card) -> Optional[Dict]:
        """Extract job data from a job card using Selenium"""
        try:
            # Extract job title
            try:
                title = clean_text(card.find_element(By.CSS_SELECTOR, 'h3.base-search-card__title').text)
            except:
                title = "N/A"
            
            # Extract company name
            try:
                company = clean_text(card.find_element(By.CSS_SELECTOR, 'h4.base-search-card__subtitle').text)
            except:
                company = "N/A"
            
            # Extract location
            try:
                location = clean_text(card.find_element(By.CSS_SELECTOR, 'span.job-search-card__location').text)
            except:
                location = "N/A"
            
            # Extract job link
            try:
                job_url = card.find_element(By.CSS_SELECTOR, 'a.base-card__full-link').get_attribute('href')
            except:
                job_url = ""
            
            # Extract job ID
            job_id = ""
            if job_url and 'jobs/view/' in job_url:
                job_id = job_url.split('jobs/view/')[-1].split('?')[0]
            
            # Extract posted date
            try:
                posted_date = card.find_element(By.CSS_SELECTOR, 'time').get_attribute('datetime')
            except:
                posted_date = ""
            
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
    
    def _is_duplicate(self, jobs: List[Dict], new_job: Dict) -> bool:
        """Check if job already exists in the list"""
        for job in jobs:
            if job.get('job_id') == new_job.get('job_id') and new_job.get('job_id'):
                return True
        return False
    
    def get_job_details(self, job_url: str) -> Optional[Dict]:
        """
        Fetch detailed information about a specific job
        
        Args:
            job_url: URL of the job posting
            
        Returns:
            Dictionary with detailed job information including skills
        """
        try:
            self.driver.get(job_url)
            random_delay(2, 4)
            
            details = {}
            
            # Extract description
            try:
                description_elem = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.show-more-less-html__markup'))
                )
                details['description'] = clean_text(description_elem.text)
            except TimeoutException:
                details['description'] = "N/A"
            
            # Extract criteria
            criteria = {}
            try:
                criteria_items = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    'li.description__job-criteria-item'
                )
                for item in criteria_items:
                    try:
                        header = item.find_element(By.TAG_NAME, 'h3').text
                        value = item.find_element(By.TAG_NAME, 'span').text
                        criteria[clean_text(header)] = clean_text(value)
                    except:
                        pass
            except:
                pass
            
            details['criteria'] = criteria
            
            # Extract skills
            details['skills'] = self._extract_skills_selenium(details.get('description', ''))
            
            return details
            
        except Exception as e:
            print(f"Error fetching job details: {e}")
            return None
    
    def _extract_skills_selenium(self, description: str) -> List[str]:
        """
        Extract required skills from job description
        
        Args:
            description: Job description text
            
        Returns:
            List of skills
        """
        import re
        
        # Comprehensive technical skills to look for (same as BeautifulSoup scraper)
        common_skills = [
            # Programming Languages
            'Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Ruby', 'PHP', 
            'Go', 'Rust', 'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'SQL', 'Perl',
            'Bash', 'PowerShell', 'VBA', 'Julia', 'Dart', 'Elixir', 'Clojure',
            'Groovy', 'Lua', 'Haskell', 'Erlang', 'F#', 'Objective-C',
            
            # Web Technologies
            'HTML', 'CSS', 'React', 'Angular', 'Vue.js', 'Node.js', 'Django', 'Flask',
            'Express.js', 'Spring Boot', 'ASP.NET', 'Laravel', 'Rails', 'Next.js',
            'Nuxt.js', 'Svelte', 'Ember.js', 'Backbone.js', 'jQuery', 'Bootstrap',
            'Tailwind CSS', 'Material UI', 'Redux', 'MobX', 'GraphQL', 'REST API',
            'WebSocket', 'gRPC', 'SOAP', 'Fastify', 'NestJS', 'Meteor',
            
            # Data Science & ML
            'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Keras',
            'Scikit-learn', 'Pandas', 'NumPy', 'Data Analysis', 'Statistics',
            'NLP', 'Computer Vision', 'Neural Networks', 'MLflow', 'Kubeflow',
            'XGBoost', 'LightGBM', 'CatBoost', 'NLTK', 'spaCy', 'Hugging Face',
            'OpenCV', 'YOLO', 'CNN', 'RNN', 'LSTM', 'Transformer', 'BERT', 'GPT',
            'Reinforcement Learning', 'Feature Engineering', 'Model Deployment',
            'A/B Testing', 'Jupyter', 'Matplotlib', 'Seaborn', 'Plotly',
            
            # Databases
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQL Server',
            'Cassandra', 'DynamoDB', 'Elasticsearch', 'Neo4j', 'MariaDB',
            'CouchDB', 'Firebase', 'Firestore', 'RocksDB', 'InfluxDB', 'TimescaleDB',
            'Snowflake', 'BigQuery', 'Redshift', 'Databricks', 'Teradata',
            'Vertica', 'Greenplum', 'ClickHouse', 'ScyllaDB', 'CockroachDB',
            'NoSQL', 'NewSQL', 'ACID', 'CAP Theorem', 'Data Modeling',
            'Database Design', 'Query Optimization', 'Indexing', 'Sharding',
            
            # Cloud Platforms & Services
            'AWS', 'Azure', 'Google Cloud', 'GCP', 'IBM Cloud', 'Oracle Cloud',
            'DigitalOcean', 'Linode', 'Heroku', 'Netlify', 'Vercel', 'Cloudflare',
            'EC2', 'S3', 'Lambda', 'RDS', 'CloudFormation', 'CloudWatch',
            'Azure DevOps', 'Azure Functions', 'Azure Storage', 'Azure AD',
            'Azure Synapse', 'Azure Data Factory', 'Data Factory', 'Azure Data Lake', 'Data Lake',
            'Microsoft Fabric', 'OneLake', 'Lakehouse', 'Delta Lake',
            'Google Kubernetes Engine', 'Cloud Run', 'Cloud Functions',
            'Cloud Storage', 'Cloud SQL', 'Cloud Pub/Sub', 'Dataflow',
            'Cloud Composer', 'Cloud Build', 'App Engine', 'Compute Engine',
            
            # DevOps & Infrastructure
            'Docker', 'Kubernetes', 'Jenkins', 'CI/CD', 'Terraform', 'Ansible',
            'Chef', 'Puppet', 'Vagrant', 'Packer', 'Consul', 'Vault',
            'Linux', 'Unix', 'Ubuntu', 'CentOS', 'Red Hat', 'Debian',
            'Git', 'GitHub', 'GitLab', 'Bitbucket', 'SVN', 'Mercurial',
            'CircleCI', 'Travis CI', 'GitHub Actions', 'GitLab CI', 'Azure Pipelines',
            'Bamboo', 'TeamCity', 'Octopus Deploy', 'Spinnaker', 'ArgoCD',
            'Helm', 'Istio', 'Prometheus', 'Grafana', 'ELK Stack', 'Datadog',
            'New Relic', 'Splunk', 'Nagios', 'Zabbix', 'PagerDuty',
            'Infrastructure as Code', 'IaC', 'GitOps', 'Container Orchestration',
            'Service Mesh', 'Load Balancing', 'Auto Scaling', 'High Availability',
            
            # Data Engineering & ETL
            'Apache Spark', 'PySpark', 'Spark SQL', 'Spark Streaming',
            'Hadoop', 'HDFS', 'MapReduce', 'Hive', 'Pig', 'HBase',
            'Kafka', 'Apache Flink', 'Apache Storm', 'Apache Beam',
            'Airflow', 'Luigi', 'Prefect', 'Dagster', 'dbt', 'Matillion',
            'Talend', 'Informatica', 'DataStage', 'SSIS', 'AWS Glue',
            'ETL', 'ELT', 'Data Pipeline', 'Data Warehousing', 'Big Data',
            'Data Integration', 'Data Migration', 'Data Transformation',
            'Data Lake', 'Data Mesh', 'Data Governance', 'Data Quality',
            'Data Catalog', 'Data Lineage', 'Master Data Management', 'MDM',
            'Stream Processing', 'Batch Processing', 'Real-time Processing',
            'Data Orchestration', 'Workflow Orchestration',
            
            # BI & Analytics
            'Tableau', 'Power BI', 'Looker', 'Qlik', 'MicroStrategy', 'SAP BI',
            'Google Data Studio', 'Metabase', 'Superset', 'Redash', 'Mode Analytics',
            'Sisense', 'Domo', 'Pentaho', 'Business Intelligence', 'Data Visualization',
            'Dashboarding', 'Reporting', 'KPI', 'Metrics', 'Analytics',
            
            # Testing & QA
            'Selenium', 'Jest', 'Pytest', 'JUnit', 'TestNG', 'Cypress',
            'Mocha', 'Chai', 'Jasmine', 'Karma', 'Protractor', 'Puppeteer',
            'Playwright', 'Appium', 'TestCafe', 'Robot Framework', 'Cucumber',
            'BDD', 'TDD', 'Unit Testing', 'Integration Testing', 'E2E Testing',
            'Performance Testing', 'Load Testing', 'JMeter', 'Gatling', 'Locust',
            'Postman', 'SoapUI', 'RestAssured', 'Test Automation', 'QA',
            
            # Mobile Development
            'iOS', 'Android', 'React Native', 'Flutter', 'Xamarin', 'Ionic',
            'SwiftUI', 'Jetpack Compose', 'Kotlin Multiplatform', 'Cordova',
            'Mobile Development', 'App Development', 'Cross-platform',
            
            # Security
            'Cybersecurity', 'Information Security', 'Application Security', 'Network Security',
            'Penetration Testing', 'Ethical Hacking', 'OWASP', 'SSL/TLS', 'OAuth',
            'JWT', 'SAML', 'IAM', 'Zero Trust', 'Vulnerability Assessment',
            'Security Auditing', 'Compliance', 'GDPR', 'SOC 2', 'ISO 27001',
            'Encryption', 'Cryptography', 'Firewalls', 'VPN', 'SIEM', 'IDS/IPS',
            
            # Methodologies & Practices
            'Agile', 'Scrum', 'Kanban', 'Lean', 'SAFe', 'DevOps', 'DataOps',
            'MLOps', 'AIOps', 'SRE', 'Site Reliability Engineering',
            'Continuous Integration', 'Continuous Deployment', 'Continuous Delivery',
            'Test Driven Development', 'Behavior Driven Development',
            'Domain Driven Design', 'Microservices', 'Monolithic Architecture',
            'Event Driven Architecture', 'Serverless', 'API First', 'Cloud Native',
            'Twelve Factor App', 'Design Patterns', 'SOLID Principles',
            'Clean Code', 'Code Review', 'Pair Programming', 'Mob Programming',
            
            # Project Management & Collaboration
            'JIRA', 'Confluence', 'Trello', 'Asana', 'Monday.com', 'Basecamp',
            'Slack', 'Microsoft Teams', 'Zoom', 'Miro', 'Figma', 'Sketch',
            'Adobe XD', 'InVision', 'Notion', 'SharePoint', 'Microsoft Project',
            'Project Management', 'Product Management', 'Requirements Gathering',
            'Stakeholder Management', 'Sprint Planning', 'Retrospective',
            
            # Soft Skills
            'Communication', 'Leadership', 'Problem Solving', 'Problem-Solving', 'Critical Thinking',
            'Teamwork', 'Collaboration', 'Time Management', 'Adaptability',
            'Analytical Skills', 'Attention to Detail', 'Creativity', 'Innovation',
            'Decision Making', 'Conflict Resolution', 'Mentoring', 'Coaching',
            'Presentation Skills', 'Technical Writing', 'Documentation',
            'Customer Service', 'Client Relations', 'Interpersonal Skills',
            
            # Other Technologies
            'Blockchain', 'Ethereum', 'Solidity', 'Smart Contracts', 'Web3',
            'IoT', 'Edge Computing', 'Embedded Systems', 'Arduino', 'Raspberry Pi',
            'Computer Networks', 'TCP/IP', 'DNS', 'HTTP/HTTPS', 'Networking',
            'Version Control', 'Code Versioning', 'Branching Strategy',
            'UI/UX', 'User Experience', 'User Interface', 'Wireframing', 'Prototyping',
            'Excel', 'Google Sheets', 'VBA', 'Macros', 'Pivot Tables',
            'SAP', 'Salesforce', 'ServiceNow', 'Workday', 'Oracle EBS',
            'ERP', 'CRM', 'HRM', 'Supply Chain Management', 'E-commerce',
            'Content Management System', 'CMS', 'WordPress', 'Drupal', 'Shopify',
            'Video Editing', 'Audio Processing', 'Image Processing', 'FFmpeg',
            'OpenGL', 'DirectX', 'Unity', 'Unreal Engine', 'Game Development',
            'AR', 'VR', 'Augmented Reality', 'Virtual Reality', 'Mixed Reality',
            'Quantum Computing', 'Edge AI', 'AutoML', 'MLaaS',
            'API Gateway', 'Service Discovery', 'Circuit Breaker', 'Message Queue',
            'RabbitMQ', 'ActiveMQ', 'ZeroMQ', 'MQTT', 'AMQP', 'WebHooks',
            'Scrapy', 'Beautiful Soup', 'Web Scraping', 'Data Mining',
            'Text Mining', 'Sentiment Analysis', 'Recommendation Systems',
            'Search Engine', 'Solr', 'Lucene', 'Algolia', 'Elasticsearch',
            'CDN', 'Content Delivery Network', 'Edge Network', 'Caching',
            'Memcached', 'Varnish', 'HAProxy', 'Nginx', 'Apache', 'IIS',
            'Serverless Computing', 'FaaS', 'Function as a Service',
            'Containerization', 'Virtualization', 'VMware', 'Hyper-V', 'KVM',
        ]
        
        found_skills = []
        text_lower = description.lower()
        
        for skill in common_skills:
            # Create pattern to match skill (case insensitive, word boundary)
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                if skill not in found_skills:
                    found_skills.append(skill)
        
        return found_skills
    
    def login(self, email: str, password: str):
        """
        Login to LinkedIn (use with caution and at your own risk)
        
        Args:
            email: LinkedIn email
            password: LinkedIn password
        """
        try:
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            
            # Enter email
            email_field = self.driver.find_element(By.ID, "username")
            email_field.send_keys(email)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, "password")
            password_field.send_keys(password)
            
            # Click login button
            login_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            login_button.click()
            
            time.sleep(5)
            print("Logged in successfully")
            
        except Exception as e:
            print(f"Error during login: {e}")
    
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
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("Browser closed")


# Example usage
if __name__ == "__main__":
    scraper = LinkedInScraperSelenium(headless=False)
    
    try:
        # Search for jobs
        jobs = scraper.search_jobs(
            keywords="Data Scientist",
            location="San Francisco",
            max_jobs=20
        )
        
        # Save results
        scraper.save_to_csv()
        scraper.save_to_json()
        
        print(f"\nScraped {len(jobs)} jobs successfully!")
        
    finally:
        scraper.close()
