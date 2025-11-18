# LinkedIn Job Scraper Scheduler

A comprehensive automated LinkedIn job scraping system with REST API, scheduled scraping, Elasticsearch integration, and advanced job filtering capabilities.

## 🌟 Features

### Core Features
- **🤖 Automated Scheduling**: Schedule recurring job scrapes (weekly, daily) with customizable timing
- **🔍 Multiple Scraping Methods**: BeautifulSoup for fast scraping, Selenium for dynamic content
- **📊 Elasticsearch Integration**: Store and search job listings with powerful analytics
- **🌐 REST API**: FastAPI-based API with Swagger UI for easy interaction
- **🎯 Smart Job Filtering**: 
  - Exact match job titles
  - Post age filtering (e.g., only jobs from last 21 days)
  - Location prioritization (primary + fallback locations)
  - Country-specific search
- **💾 Multiple Export Formats**: CSV, JSON, Excel
- **🐳 Docker Support**: Full containerization with docker-compose
- **📈 Kibana Visualization**: Optional Kibana integration for data visualization

### Advanced Features
- **Skills Extraction**: Automatically extract and analyze skills from job descriptions
- **Top Skills Analysis**: Find most demanded skills by job role
- **Rate Limiting**: Built-in delays to avoid being blocked
- **User-Agent Rotation**: Randomized user agents to mimic real browsers
- **Job Quality Control**: Filter jobs by post date, exact match, and more

## 📋 Prerequisites

- Python 3.8+
- Docker & Docker Compose (for Elasticsearch & Kibana)
- Chrome/Chromium (for Selenium scraper)

## 🚀 Quick Start

### Option 1: Docker Deployment (Recommended)

1. **Start all services**:
   ```powershell
   docker-compose up -d
   ```

   This will start:
   - Elasticsearch (port 9200)
   - API Server (port 8000)
   - Kibana (port 5601) - optional

2. **Access the API**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Kibana: http://localhost:5601 (if enabled)

3. **Start with Kibana** (optional):
   ```powershell
   docker-compose --profile with-kibana up -d
   ```

### Option 2: Local Development

1. **Clone and setup**:
   ```powershell
   cd "c:\Users\Chamika\Desktop\Research\LinkedIn Job Scrape Sheduller"
   python -m venv venv

   pip install -r requirements.txt
   ```

2. **Start Elasticsearch** (using Docker):
   ```powershell
   docker-compose up -d elasticsearch
   ```

3. **Start the API server**:
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
│   ├── main.py                    # FastAPI application
│   ├── core/
│   │   ├── config.py             # Configuration settings
│   │   └── elasticsearch_config.py
│   ├── models/
│   │   └── schemas.py            # Pydantic models
│   ├── routes/
│   │   ├── scraping.py           # Scraping endpoints
│   │   ├── scheduler.py          # Scheduler endpoints
│   │   ├── elasticsearch.py      # Elasticsearch endpoints
│   │   ├── download.py           # File download endpoints
│   │   └── health.py             # Health check
│   ├── services/
│   │   ├── scraper_service.py    # Scraping logic
│   │   ├── scheduler_service.py  # Scheduling logic
│   │   └── elasticsearch_service.py
│   └── utils/
│       └── job_filter.py         # Job filtering utilities
├── scrapers/
│   ├── beautifulsoup_scraper.py  # BeautifulSoup implementation
│   ├── selenium_scraper.py       # Selenium implementation
│   └── utils.py                  # Utility functions
├── output/                       # Scraped data output
├── docker-compose.yml            # Docker services configuration
├── Dockerfile                    # API container
├── main.py                       # Application entry point
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```env
# API Configuration
HOST=0.0.0.0
PORT=8000
APP_VERSION=2.0.0

# Scheduler Configuration
AUTO_START_SCHEDULER=True
SCHEDULER_DAY=monday
SCHEDULER_TIME=09:00

# Job Configuration
JOBS_PER_ROLE=20
MAX_POST_AGE_DAYS=21
EXACT_MATCH=True
FETCH_DETAILS=True

# Elasticsearch Configuration
ELASTICSEARCH_ENABLED=True
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=linkedin_jobs

# Location Priority
PRIMARY_LOCATION=Sri Lanka
PRIMARY_COUNTRY_CODE=LK
FALLBACK_LOCATIONS=United States,India,United Kingdom
FALLBACK_COUNTRY_CODES=US,IN,GB
```

### Scheduler Configuration

The scheduler supports:
- **Days**: monday, tuesday, wednesday, thursday, friday, saturday, sunday
- **Time**: 24-hour format (HH:MM), e.g., "09:00", "14:30"

### Job Roles

Default job roles scraped by scheduler:
- Software Engineer
- DevOps Engineer
- Data Scientist
- ML Engineer
- Frontend Developer
- Backend Developer
- Full Stack Developer
- QA Engineer

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

### Skills Extraction

Automatically extracts skills from job descriptions:
- Programming languages (Python, Java, JavaScript, etc.)
- Frameworks (React, Django, TensorFlow, etc.)
- Tools (Docker, Kubernetes, Git, etc.)
- Databases (PostgreSQL, MongoDB, Redis, etc.)
- Cloud platforms (AWS, Azure, GCP)

### Top Skills Analysis

Find most demanded skills by job role:
```bash
GET /api/v1/elasticsearch/top-skills/{job_role}?top_n=20
```

### Exact Match Filtering

Enable `EXACT_MATCH=True` to only include jobs with exact title matches (e.g., "Software Engineer" won't match "Senior Software Engineer").

### Location Priority

Configure primary and fallback locations:
- Primary location searched first
- Fallback locations used if insufficient results
- Separate country codes for better targeting

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

## 📄 API Documentation

Full API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🤝 Contributing

This is a research project. Feel free to fork and modify for your needs.

## 📝 License

This project is for educational and research purposes only. Use responsibly and ensure compliance with LinkedIn's Terms of Service.

## 📧 Support

For issues or questions, please check:
1. API documentation at `/docs`
2. Docker logs: `docker-compose logs`
3. Elasticsearch status: `/api/v1/elasticsearch/status`

---

**Version**: 2.0.0  
**Last Updated**: November 2025
