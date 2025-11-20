# Scheduler Quick Reference Guide

## 🚀 Quick Start

### Start the Scheduler
```powershell
# Via Docker (Recommended)
docker-compose up -d

# Scheduler starts automatically if AUTO_START_SCHEDULER=True
```

### Check Status
```bash
# API call
GET http://localhost:8000/api/v1/scheduler/status

# Or via curl
curl http://localhost:8000/api/v1/scheduler/status
```

---

## ⏰ How It Works

### Automatic Schedule
- **Day**: Every Monday
- **Time**: 09:00 AM (24-hour format)
- **Duration**: ~18-20 minutes
- **Jobs**: 120 total (6 roles × 20 jobs each)

### What Happens Every Monday at 9:00 AM

```
09:00:00 → Scheduler triggers
09:00:05 → Start AI/ML Engineer (AIML_001 to AIML_020)
09:03:10 → Start Data Analyst (DA_001 to DA_020)
09:06:15 → Start Data Engineer (DE_001 to DE_020)
09:09:20 → Start DevOps Engineer (DO_001 to DO_020)
09:12:25 → Start Web Developer (WD_001 to WD_020)
09:15:30 → Start Software Engineer (SE_001 to SE_020)
09:18:35 → Save 120 jobs to Elasticsearch
09:19:05 → ✅ Complete!
```

---

## 🎯 Job Roles & Tags

| Role | Tag | Example IDs (Nov 19, 2025) |
|------|-----|--------------------------|
| AI/ML Engineer | AIML | AIML_20251119_001, AIML_20251119_002, ..., AIML_20251119_020 |
| Data Analyst | DA | DA_20251119_001, DA_20251119_002, ..., DA_20251119_020 |
| Data Engineer | DE | DE_20251119_001, DE_20251119_002, ..., DE_20251119_020 |
| DevOps Engineer | DO | DO_20251119_001, DO_20251119_002, ..., DO_20251119_020 |
| Web Developer | WD | WD_20251119_001, WD_20251119_002, ..., WD_20251119_020 |
| Software Engineer | SE | SE_20251119_001, SE_20251119_002, ..., SE_20251119_020 |

---

## 📍 Location Priority

### 1. Primary Location (Sri Lanka)
- **Target**: 20 jobs per role
- **Cities**: Colombo, Kandy, Galle, etc.

### 2. Fallback Locations (if needed)
- **USA**: Up to 7 jobs
- **India**: Up to 7 jobs  
- **UK**: Up to 6 jobs

### Example Distribution
```
Data Analyst (20 jobs total):
  ✓ 12 jobs from Sri Lanka
  ✓ 5 jobs from USA
  ✓ 2 jobs from India
  ✓ 1 job from UK
```

---

## 🔍 Filtering Process

### 1. Deduplication
- Removes duplicate jobs (same company + title + location)
- Example: 70 → 65 unique jobs

### 2. Recency Filter
- Only jobs posted within last **21 days**
- Older jobs are discarded
- Example: 65 → 58 recent jobs

### 3. Location Categorization
- Groups jobs by country (LK, US, IN, GB)
- Example: LK: 12, US: 22, IN: 15, GB: 9

### 4. Priority Selection
- Takes ALL from Sri Lanka first (up to 20)
- Fills remaining slots from fallback countries
- Final: Exactly 20 jobs per role

---

## 🏷️ Job Metadata

Each job includes:

```json
{
  "job_id": "data-analyst-at-tech-corp-123",
  "title": "Data Analyst",
  "company": "Tech Corp",
  "location": "Colombo, Sri Lanka",
  
  // Role identifiers (Globally Unique)
  "role_tag": "DA",
  "role_key": "data_analyst",
  "job_role_id": "DA_20251119_001",  // Format: {TAG}_{YYYYMMDD}_{counter}
  
  // Job details
  "posted_date": "2025-11-18",
  "scraped_at": "2025-11-18T09:05:32",
  "skills": ["Python", "SQL", "Tableau"],
  "description": "...",
  "criteria": {...}
}
```

---

## 🎮 API Controls

### Start Scheduler
```bash
POST http://localhost:8000/api/v1/scheduler/start
```

### Stop Scheduler
```bash
POST http://localhost:8000/api/v1/scheduler/stop
```

### Check Status
```bash
GET http://localhost:8000/api/v1/scheduler/status
```

### Manual Trigger (Run Immediately)
```bash
POST http://localhost:8000/api/v1/scheduler/run-now
```

### Get Elasticsearch Stats
```bash
GET http://localhost:8000/api/v1/elasticsearch/stats
```

---

## 📊 Monitoring

### Real-Time Status
```json
{
  "is_running": true,
  "is_scraping": true,
  "current_scraping": {
    "current_role": "data_engineer",
    "progress": 50,
    "total_jobs_scraped": 60,
    "jobs_by_role": {
      "ai_ml_engineer": 20,
      "data_analyst": 20,
      "data_engineer": 20
    }
  },
  "next_run": "2025-11-25T09:00:00"
}
```

### View Logs (Docker)
```powershell
# Real-time logs
docker-compose logs -f scraper-api

# Or in Docker Desktop
Containers → linkedin-scraper-api → Logs tab
```

---

## 💾 Elasticsearch Storage

### Index: `linkedin_jobs`

### Sample Query - Get All Data Analyst Jobs
```bash
GET http://localhost:9200/linkedin_jobs/_search
{
  "query": {
    "term": {
      "role_tag": "DA"
    }
  }
}
```

### Count Jobs by Role
```bash
GET http://localhost:9200/linkedin_jobs/_search
{
  "size": 0,
  "aggs": {
    "by_role": {
      "terms": {
        "field": "role_tag.keyword"
      }
    }
  }
}
```

### Get Specific Job by ID
```bash
GET http://localhost:9200/linkedin_jobs/_search
{
  "query": {
    "term": {
      "job_role_id": "DA_001"
    }
  }
}
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Scheduler
AUTO_START_SCHEDULER=True
SCHEDULER_DAY=monday
SCHEDULER_TIME=09:00

# Jobs
JOBS_PER_ROLE=20
MAX_POST_AGE_DAYS=21
EXACT_MATCH=True
FETCH_DETAILS=True

# Elasticsearch
ELASTICSEARCH_ENABLED=True
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=linkedin_jobs
```

### Change Schedule
```env
# Daily at 2:00 AM
SCHEDULER_DAY=daily
SCHEDULER_TIME=02:00

# Wednesday at 3:30 PM
SCHEDULER_DAY=wednesday
SCHEDULER_TIME=15:30
```

---

## 🔧 Troubleshooting

### Scheduler Not Running
```bash
# Check status
GET http://localhost:8000/api/v1/scheduler/status

# Start manually
POST http://localhost:8000/api/v1/scheduler/start
```

### No Jobs in Elasticsearch
```bash
# Trigger manual run
POST http://localhost:8000/api/v1/scheduler/run-now

# Wait 20 minutes, then check
GET http://localhost:8000/api/v1/elasticsearch/stats
```

### View Errors
```powershell
# Check Docker logs
docker-compose logs scraper-api | Select-String "ERROR"

# Or get status from API
GET http://localhost:8000/api/v1/scheduler/status
# Check "errors" field in response
```

### Reset Everything
```powershell
# Stop containers
docker-compose down

# Remove old data
docker-compose down -v

# Start fresh
docker-compose up -d
```

---

## 📈 Expected Results

### After First Run (Monday 9:00 AM)

**Total Jobs**: 120
- AI/ML Engineer: 20 jobs
- Data Analyst: 20 jobs
- Data Engineer: 20 jobs
- DevOps Engineer: 20 jobs
- Web Developer: 20 jobs
- Software Engineer: 20 jobs

**By Country** (approximate):
- Sri Lanka: 45 jobs
- USA: 35 jobs
- India: 30 jobs
- UK: 10 jobs

**Elasticsearch**:
- Index: linkedin_jobs
- Total docs: 120
- All jobs searchable

---

## 🎯 Best Practices

### 1. Let It Run Automatically
- Don't manually trigger unless testing
- Scheduler will run every Monday at 9:00 AM

### 2. Monitor Regularly
- Check status weekly after run
- Review logs for any errors

### 3. Clean Old Data Periodically
```bash
# Delete jobs older than 3 months
POST http://localhost:9200/linkedin_jobs/_delete_by_query
{
  "query": {
    "range": {
      "scraped_at": {
        "lt": "now-90d"
      }
    }
  }
}
```

### 4. Backup Data
```powershell
# Export jobs to JSON
GET http://localhost:8000/api/v1/elasticsearch/search?size=1000

# Save response to file
```

---

## 📚 Related Files

- **Configuration**: `api/services/scheduler_service.py`
- **Documentation**: `ROLE_TAG_IMPLEMENTATION.md`
- **Test Scripts**: 
  - `test_role_tags.py` - Test role tagging
  - `test_scheduler_workflow.py` - This workflow demo
- **README**: `README.md` - Full documentation

---

## 🆘 Quick Help

### I want to...

**Change the schedule**:
- Edit `.env` file: `SCHEDULER_DAY` and `SCHEDULER_TIME`
- Restart: `docker-compose restart scraper-api`

**Add more roles**:
- Edit `api/services/scheduler_service.py`
- Add to `JOB_ROLES` and `ROLE_TAGS` dicts
- Restart containers

**Change location priority**:
- Edit `LOCATION_PRIORITY` in `scheduler_service.py`
- Restart containers

**Increase jobs per role**:
- Edit `.env`: `JOBS_PER_ROLE=30`
- Or edit `TOTAL_JOBS_PER_ROLE` in `scheduler_service.py`

**Run manually now**:
- `POST http://localhost:8000/api/v1/scheduler/run-now`

**Stop scheduler**:
- `POST http://localhost:8000/api/v1/scheduler/stop`

---

## ✅ Summary

✓ Runs automatically every Monday at 9:00 AM  
✓ Scrapes 6 roles, 20 jobs each = 120 total  
✓ Prioritizes Sri Lanka, falls back to USA/India/UK  
✓ Filters duplicates and old jobs (>21 days)  
✓ Assigns globally unique IDs: DA_20251119_001, SE_20251119_042, AIML_20251119_015  
✓ Saves to Elasticsearch for searching  
✓ Takes ~18-20 minutes to complete  
✓ Provides real-time progress via API  

**Set it and forget it!** 🚀

---

For detailed documentation, see:
- `ROLE_TAG_IMPLEMENTATION.md` - Complete implementation guide
- `README.md` - Full project documentation
- Swagger UI: http://localhost:8000/docs
