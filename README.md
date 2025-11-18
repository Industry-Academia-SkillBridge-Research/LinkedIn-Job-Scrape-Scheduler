# LinkedIn Job Scraper Scheduler

A comprehensive automated LinkedIn job scraping system with REST API, scheduled scraping, Elasticsearch integration, and role-based job categorization with unique identifiers.

## 🌟 Features

### Core Features
- **🤖 Automated Scheduling**: Weekly automated scraping every Monday at 9:00 AM
- **🏷️ Role-Based Categorization**: Unique job IDs with role tags (DA_001, SE_042, AIML_015, etc.)
- **🔍 Multiple Scraping Methods**: BeautifulSoup for fast scraping, Selenium for dynamic content
- **📊 Elasticsearch Integration**: Store and search job listings with powerful analytics
- **🌐 REST API**: FastAPI-based API with Swagger UI documentation
- **🎯 Smart Job Filtering**: 
  - Deduplication by company + title + location
  - Post age filtering (only last 21 days)
  - Location prioritization (Sri Lanka primary, USA/India/UK fallback)
  - Exact match job titles
  - Country-specific categorization
- **💾 Multiple Export Formats**: CSV, JSON, Excel
- **🐳 Docker Support**: Full containerization with docker-compose
- **📈 Kibana Visualization**: Optional Kibana integration for data visualization

### Advanced Features
- **400+ Skills Detection**: Comprehensive skill extraction covering Data Engineering, Cloud, DevOps, Programming, Databases, BI tools, and more
- **Top Skills Analysis**: Find most demanded skills by job role
- **Sequential Job IDs**: Unique identifiers per role per scraping run
- **Rate Limiting**: Built-in delays to avoid being blocked
- **User-Agent Rotation**: Randomized user agents to mimic real browsers

## 📋 Prerequisites

- Python 3.8+
- Docker & Docker Compose (for Elasticsearch & Kibana)
- Chrome/Chromium (for Selenium scraper)

## 🚀 Quick Start

### Docker Deployment (Recommended)

1. **Start all services**:
   ```powershell
   docker-compose up -d
   ```

   This starts:
   - **Elasticsearch** (port 9200) - Job storage and search
   - **API Server** (port 8000) - REST API with scheduler
   - **Kibana** (port 5601) - Optional visualization

2. **Access the services**:
   - **API Documentation**: http://localhost:8000/docs
   - **Health Check**: http://localhost:8000/health
   - **Kibana Dashboard**: http://localhost:5601

3. **Scheduler auto-starts**:
   - Runs every Monday at 9:00 AM
   - Scrapes 120 jobs (6 roles × 20 jobs each)
   - Approximately 18-20 minutes per run
   - Check status: `GET http://localhost:8000/api/v1/scheduler/status`

### Local Development

1. **Setup environment**:
   ```powershell
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start Elasticsearch**:
   ```powershell
   docker-compose up -d elasticsearch
   ```

3. **Run the API**:
   ```powershell
   python main.py
   ```

## 📚 API Usage

### 1. Scrape Jobs (Synchronous)

```bash
POST http://localhost:8000/api/v1/scrape/sync

{
  "keywords": "Python Developer",
  "location": "Sri Lanka",
  "max_jobs": 20,
  "save_to_elasticsearch": true,
  "fetch_details": true
}
```

### 2. Scheduled Scraping

**Start Scheduler**:
```bash
POST http://localhost:8000/api/v1/scheduler/start
```

**Get Scheduler Status**:
```bash
GET http://localhost:8000/api/v1/scheduler/status
```

**Configure Schedule**:
```bash
POST http://localhost:8000/api/v1/scheduler/config
{
  "day": "monday",
  "time": "09:00"
}
```

### 3. Elasticsearch Operations

**Search Jobs**:
```bash
GET http://localhost:8000/api/v1/elasticsearch/search?query=python&size=10
```

**Get Top Skills by Role**:
```bash
GET http://localhost:8000/api/v1/elasticsearch/top-skills/Software%20Engineer?top_n=10
```

**Get Statistics**:
```bash
GET http://localhost:8000/api/v1/elasticsearch/stats
```

## 🏗️ Project Structure

```
LinkedIn Job Scrape Sheduller/
├── api/
│   ├── main.py                      # FastAPI application entry
│   ├── core/
│   │   ├── config.py                # Application configuration
│   │   └── elasticsearch_config.py  # Elasticsearch connection
│   ├── models/
│   │   └── schemas.py               # Pydantic data models
│   ├── routes/
│   │   ├── scraping.py              # Job scraping endpoints
│   │   ├── scheduler.py             # Scheduler control endpoints
│   │   ├── elasticsearch.py         # Search & analytics endpoints
│   │   ├── download.py              # Export endpoints (CSV/JSON/Excel)
│   │   └── health.py                # Health check endpoint
│   ├── services/
│   │   ├── scraper_service.py       # Scraping business logic
│   │   ├── scheduler_service.py     # Automated scheduling (role tagging)
│   │   └── elasticsearch_service.py # Elasticsearch operations
│   └── utils/
│       └── job_filter.py            # Job filtering utilities
├── scrapers/
│   ├── beautifulsoup_scraper.py     # BeautifulSoup scraper (400+ skills)
│   ├── selenium_scraper.py          # Selenium scraper (dynamic content)
│   └── utils.py                     # Scraper utility functions
├── output/                          # Local file exports
├── docker-compose.yml               # Docker orchestration
├── Dockerfile                       # API container definition
├── main.py                          # Application launcher
├── requirements.txt                 # Python dependencies
├── SCHEDULER_QUICK_REFERENCE.md     # Scheduler usage guide
└── README.md                        # Documentation (this file)
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# API Configuration
HOST=0.0.0.0
PORT=8000
APP_VERSION=2.0.0

# Scheduler Configuration
AUTO_START_SCHEDULER=True          # Auto-start scheduler on API launch
SCHEDULER_DAY=monday                # Day of week (monday, tuesday, etc.)
SCHEDULER_TIME=09:00                # Time in 24-hour format (HH:MM)

# Job Configuration
JOBS_PER_ROLE=20                    # Jobs to scrape per role
MAX_POST_AGE_DAYS=21                # Only jobs posted within last 21 days
EXACT_MATCH=True                    # Exact job title matching
FETCH_DETAILS=True                  # Fetch full job descriptions

# Elasticsearch Configuration
ELASTICSEARCH_ENABLED=True
ELASTICSEARCH_HOST=elasticsearch    # Use 'localhost' for local dev
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=linkedin_jobs

# Location Priority (Sri Lanka primary, USA/India/UK fallback)
PRIMARY_LOCATION=Sri Lanka
PRIMARY_COUNTRY_CODE=LK
FALLBACK_LOCATIONS=United States,India,United Kingdom
FALLBACK_COUNTRY_CODES=US,IN,GB
```

### Scheduler Settings

**Supported Schedule Days**:
- `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday`
- `daily` (runs every day)

**Time Format**: 24-hour format (e.g., `09:00`, `14:30`, `23:45`)

**Default Schedule**: Every Monday at 9:00 AM

### Job Roles & Unique Identifiers

The scheduler scrapes 6 job roles with unique tagging system:

| Role | Tag | ID Format | Variations | Jobs Per Run |
|------|-----|-----------|------------|--------------|
| AI/ML Engineer | `AIML` | `AIML_001`, `AIML_002`, ... | AI/ML Engineer, Machine Learning Engineer, AI Engineer, ML Engineer | 20 |
| Data Analyst | `DA` | `DA_001`, `DA_002`, ... | Data Analyst | 20 |
| Data Engineer | `DE` | `DE_001`, `DE_002`, ... | Data Engineer | 20 |
| DevOps Engineer | `DO` | `DO_001`, `DO_002`, ... | DevOps Engineer, Dev Ops Engineer | 20 |
| Web Developer | `WD` | `WD_001`, `WD_002`, ... | Web Developer | 20 |
| Software Engineer | `SE` | `SE_001`, `SE_002`, ... | Software Engineer | 20 |

**Total**: 120 jobs per scheduled run

#### Job Metadata Fields
Each scraped job includes:
- **role_tag**: Short role identifier (`DA`, `SE`, `AIML`, etc.)
- **role_key**: Internal role category (`data_analyst`, `software_engineer`, etc.)
- **job_role_id**: Unique sequential ID per role (`DA_001`, `SE_042`, `AIML_015`)

#### ID Generation
- IDs reset with each scraping run
- Sequential numbering per role (001, 002, 003, ...)
- Format: `{TAG}_{counter:03d}`
- Example sequence for Data Analyst: `DA_001`, `DA_002`, ..., `DA_020`

## 🐳 Docker Deployment

### Services

1. **Elasticsearch**: Port 9200
   - Stores job data
   - Provides search capabilities
   - Data persisted in volume

2. **API Server**: Port 8000
   - FastAPI application
   - Auto-starts scheduler
   - Connects to Elasticsearch

3. **Kibana** (optional): Port 5601
   - Data visualization
   - Dashboard creation
   - Index management

### Docker Commands

```powershell
# Start all services
docker-compose up -d

# Start with Kibana
docker-compose --profile with-kibana up -d

# View logs
docker-compose logs -f scraper-api

# Stop services
docker-compose down

# Remove volumes (delete data)
docker-compose down -v
```

## 📦 Python Usage Examples

### Direct Scraper Usage

```python
from scrapers.beautifulsoup_scraper import LinkedInScraperBS

# Initialize scraper
scraper = LinkedInScraperBS()

# Scrape jobs
jobs = scraper.search_jobs(
    keywords="Python Developer",
    location="Sri Lanka",
    max_jobs=20
)

# Save to file
scraper.save_to_csv(jobs, "output/jobs.csv")
```

### API Client Usage

```python
import requests

# Scrape jobs
response = requests.post(
    "http://localhost:8000/api/v1/scrape/sync",
    json={
        "keywords": "Data Scientist",
        "location": "United States",
        "max_jobs": 30,
        "save_to_elasticsearch": True
    }
)

jobs = response.json()
print(f"Found {len(jobs['jobs'])} jobs")
```

### Elasticsearch Integration

```python
from api.core.elasticsearch_config import es_client

# Search jobs
results = es_client.search_jobs("python developer", size=10)

# Get top skills
skills = es_client.get_top_skills("Software Engineer", top_n=15)

# Get statistics
stats = es_client.get_stats()
print(f"Total jobs: {stats['total_jobs']}")
```

## 🔧 Advanced Features

### 400+ Skills Extraction

Comprehensive skill detection from job descriptions:

**Data Engineering**: PySpark, Spark SQL, Apache Kafka, Azure Synapse, Microsoft Fabric, OneLake, SSIS, Databricks, Data Factory, Informatica

**Cloud Platforms**: AWS (S3, Lambda, EC2, RDS, Redshift), Azure (Blob Storage, Data Lake, Synapse, Purview), GCP (BigQuery, Cloud Storage)

**Programming**: Python, Java, JavaScript, TypeScript, C++, C#, Go, Rust, Scala, R, SQL

**Databases**: PostgreSQL, MySQL, MongoDB, Redis, Cassandra, Elasticsearch, DynamoDB, Snowflake

**DevOps & Tools**: Docker, Kubernetes, Jenkins, GitLab CI, Terraform, Ansible, Prometheus, Grafana

**BI & Analytics**: Tableau, Power BI, Looker, Metabase, Superset

**Frameworks**: React, Angular, Vue.js, Django, Flask, FastAPI, Spring Boot, Node.js, TensorFlow, PyTorch

**Testing**: Pytest, Jest, Selenium, Cypress, JUnit

**Methodologies**: Agile, Scrum, CI/CD, DevOps, Test-Driven Development

### Top Skills Analysis

Find most demanded skills by role:
```bash
GET /api/v1/elasticsearch/top-skills/{job_role}?top_n=20
```

Returns frequency analysis across all jobs for that role.

### Smart Job Filtering

**Deduplication**: Removes duplicate jobs by company + title + location

**Recency Filter**: Only includes jobs posted within last 21 days

**Exact Match**: When enabled, "Software Engineer" won't match "Senior Software Engineer"

**Location Priority**:
1. Primary: Sri Lanka (up to 20 jobs)
2. Fallback: USA (up to 7), India (up to 7), UK (up to 6)
3. Fills to exactly 20 jobs per role

### Role-Based Tagging

Every job gets three identifiers:
- `role_tag`: Short code (DA, SE, AIML, etc.)
- `role_key`: Full category (data_analyst, software_engineer, etc.)
- `job_role_id`: Unique ID (DA_001, SE_042, AIML_015, etc.)

Sequential numbering resets with each scraping run.

## 🔍 Monitoring & Management

### Health Check

```bash
GET http://localhost:8000/health
```

### Elasticsearch Status

```bash
GET http://localhost:8000/api/v1/elasticsearch/status
```

### Scheduler Status

```bash
GET http://localhost:8000/api/v1/scheduler/status
```

### Download Results

```bash
GET http://localhost:8000/api/v1/download/{job_id}?format=csv
GET http://localhost:8000/api/v1/download/{job_id}?format=json
GET http://localhost:8000/api/v1/download/{job_id}?format=excel
```

## ⚠️ Important Notes

### Legal and Ethical Considerations
- Always review LinkedIn's Terms of Service and robots.txt
- Respect rate limits to avoid IP bans
- Use scraped data responsibly and ethically
- Consider using LinkedIn's official API for commercial applications
- This project is for educational and research purposes only

### Technical Limitations
- LinkedIn has anti-scraping measures in place
- Frequent scraping may result in temporary or permanent IP blocks
- Authentication may be required for full access to job listings
- Dynamic content loading requires Selenium

### Best Practices
- Use reasonable delays between requests (2-4 seconds)
- Limit the number of jobs per request (20-50)
- Run scheduled scrapes during off-peak hours
- Monitor Elasticsearch disk usage
- Regularly clean old job data

## 🐛 Troubleshooting

### API Won't Start
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Install dependencies
pip install -r requirements.txt
```

### Elasticsearch Connection Failed
```powershell
# Check if Elasticsearch is running
docker-compose ps

# View Elasticsearch logs
docker-compose logs elasticsearch

# Restart Elasticsearch
docker-compose restart elasticsearch
```

### Scraping Errors
- **Blocked by LinkedIn**: Increase delays, use proxies
- **No results found**: Check keywords and location
- **Timeout errors**: Increase timeout in scraper settings

### Docker Issues
```powershell
# Remove all containers and volumes
docker-compose down -v

# Rebuild containers
docker-compose build --no-cache

# View all logs
docker-compose logs
```

## 📊 Scheduler Workflow

### What Happens Every Monday at 9:00 AM?

1. **Initialize**: Scheduler triggers, resets job counters
2. **Scrape 6 Roles**: Each with variations (AI/ML Engineer, Data Analyst, etc.)
3. **Multi-Location Scraping**:
   - Primary: Sri Lanka (~30 jobs per role)
   - Fallback: USA, India, UK (~10 jobs each per role)
4. **Filter & Prioritize**:
   - Remove duplicates (company + title + location)
   - Keep only recent jobs (≤21 days old)
   - Prioritize Sri Lanka jobs
   - Select exactly 20 jobs per role
5. **Tag & Identify**: Assign role_tag and job_role_id
6. **Save to Elasticsearch**: Store all 120 jobs with metadata
7. **Complete**: ~18-20 minutes total

### Expected Results Per Run

- **Total Jobs**: 120
- **By Role**: 20 each (AIML, DA, DE, DO, WD, SE)
- **By Country** (approx): LK: 45, US: 35, IN: 30, GB: 10

See **SCHEDULER_QUICK_REFERENCE.md** for detailed scheduler guide.

## 📄 API Documentation

**Interactive Documentation**:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

**Key Endpoints**:
- `GET /health` - Health check
- `POST /api/v1/scrape/sync` - Scrape jobs immediately
- `GET /api/v1/scheduler/status` - Check scheduler status
- `POST /api/v1/scheduler/run-now` - Trigger manual run
- `GET /api/v1/elasticsearch/search` - Search jobs
- `GET /api/v1/elasticsearch/top-skills/{role}` - Get top skills

## 🚀 Deployment Options

### Cloud Deployment (24/7 Operation)

1. **Railway.app** (Easiest):
   - Connect GitHub repository
   - Auto-deploys on push
   - Free tier available

2. **AWS EC2** (Production):
   - Deploy Docker containers
   - Use managed Elasticsearch service
   - Set up auto-scaling

3. **DigitalOcean/Azure/GCP**: Similar Docker deployment

### Local Deployment

Keep laptop running with Docker or deploy to home server.

## 🤝 Contributing

This is a research project under Industry-Academia-SkillBridge-Research organization.

## 📝 License

Educational and research use only. Respect LinkedIn's Terms of Service and robots.txt.

## 📧 Support

**Documentation**:
- `README.md` - This file
- `SCHEDULER_QUICK_REFERENCE.md` - Scheduler usage guide
- API Docs - http://localhost:8000/docs

**Troubleshooting**:
1. Check API logs: `docker-compose logs scraper-api`
2. Check Elasticsearch: `GET /api/v1/elasticsearch/status`
3. Check scheduler: `GET /api/v1/scheduler/status`

---

**Version**: 2.0.0  
**Repository**: [LinkedIn-Job-Scrape-Scheduler](https://github.com/Industry-Academia-SkillBridge-Research/LinkedIn-Job-Scrape-Scheduler)  
**Last Updated**: November 2025
