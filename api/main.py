"""
Main FastAPI application
LinkedIn Job Scraper API with best practices
"""
import sys
import os
from contextlib import asynccontextmanager

# Add parent directory to path to import scrapers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from api.core import settings
from api.routes import scraping, health, download, scheduler, elasticsearch


def _auto_scrape_and_import():
    """
    Run an initial scrape and optionally import results into Neo4j.
    Designed to run in a background thread on first startup.
    """
    import time
    import logging
    logger = logging.getLogger(__name__)

    # Give the server a moment to fully start
    time.sleep(5)

    logger.info("🤖 Auto-scrape: Starting initial scrape...")

    try:
        from api.models.schemas import JobSearchRequest
        from api.services.scraper_service import scraper_service

        roles = [
            ("Data Engineer",              "Remote", True,  "DE", "data_engineer"),
            ("Machine Learning Engineer",  "Remote", True,  "AIML", "ai_ml_engineer"),
            ("DevOps Engineer",            "Remote", True,  "DO", "devops_engineer"),
            ("Data Analyst",               "Remote", False, "DA", "data_analyst"),
            ("Software Engineer",          "Remote", True,  "SE", "software_engineer"),
            ("Web Developer",              "Remote", True,  "WD", "web_developer"),
        ]

        max_jobs = getattr(settings, 'AUTO_SCRAPE_MAX_JOBS', 5)
        all_jobs = []
        counter = {}

        for keywords, location, exact_match, role_tag, role_key in roles:
            try:
                logger.info(f"   Scraping: {keywords} ({location})...")
                request = JobSearchRequest(
                    keywords=keywords,
                    location=location,
                    max_jobs=max_jobs,
                    fetch_details=False,
                    exact_match=exact_match,
                )
                jobs = scraper_service.scrape_jobs(request)
                counter.setdefault(role_key, 0)
                from datetime import datetime
                date_str = datetime.utcnow().strftime("%Y%m%d")
                for j in jobs:
                    counter[role_key] += 1
                    j["role_tag"] = role_tag
                    j["role_key"] = role_key
                    j["job_role"] = keywords
                    j["job_role_id"] = f"{role_tag}_{date_str}_{counter[role_key]:03d}"
                all_jobs.extend(jobs)
                logger.info(f"   ✓ {keywords}: {len(jobs)} jobs")
                time.sleep(2)
            except Exception as e:
                logger.warning(f"   ✗ {keywords}: {e}")

        logger.info(f"🤖 Auto-scrape: {len(all_jobs)} total jobs scraped")

        # Save to Elasticsearch
        if all_jobs:
            try:
                from api.services.elasticsearch_service import elasticsearch_service
                result = elasticsearch_service.save_jobs_bulk(all_jobs)
                logger.info(f"   ✅ Elasticsearch: {result.get('success', 0)} saved")
            except Exception as e:
                logger.warning(f"   ⚠️ Elasticsearch save failed: {e}")

        # Import into Neo4j if enabled
        if getattr(settings, 'NEO4J_ENABLED', False) and all_jobs:
            logger.info("🤖 Auto-scrape: Importing jobs into Neo4j...")
            try:
                _import_jobs_to_neo4j(all_jobs)
            except Exception as e:
                logger.warning(f"   ⚠️ Neo4j import failed: {e}")

        logger.info("🤖 Auto-scrape: Initial setup complete ✓")

    except Exception as e:
        logger.error(f"🤖 Auto-scrape failed: {e}")


def _import_jobs_to_neo4j(jobs):
    """Import scraped jobs into Neo4j knowledge graph."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        from py2neo import Graph, Node, Relationship
    except ImportError:
        logger.warning("   py2neo not installed — skipping Neo4j import")
        return

    uri = settings.NEO4J_URI
    user = settings.NEO4J_USER
    password = settings.NEO4J_PASSWORD

    graph = Graph(uri, auth=(user, password))
    logger.info(f"   Connected to Neo4j at {uri}")

    role_names = {
        'ai_ml_engineer': 'AI / ML Engineer',
        'data_analyst': 'Data Analyst',
        'data_engineer': 'Data Engineer',
        'devops_engineer': 'DevOps Engineer',
        'software_engineer': 'Software Engineer',
        'web_developer': 'Web Developer',
    }

    added = 0
    for job in jobs:
        job_id = job.get('job_id', '')
        # Skip if already exists
        existing = graph.run(
            "MATCH (j:Job {job_id: $jid}) RETURN count(j) as c",
            jid=job_id
        ).data()[0]['c']
        if existing > 0:
            continue

        criteria = job.get('criteria') or {}
        job_node = Node("Job", "Vacancy",
            job_id=job_id,
            title=job.get('title', ''),
            company_name=job.get('company', ''),
            location=job.get('location', ''),
            posted_date=job.get('posted_date', ''),
            job_url=job.get('job_url', ''),
            scraped_at=job.get('scraped_at', ''),
            description=job.get('description', ''),
            role_tag=job.get('role_tag', ''),
            role_key=job.get('role_key', ''),
            job_role_id=job.get('job_role_id', ''),
            seniority_level=criteria.get('Seniority level', ''),
            employment_type=criteria.get('Employment type', ''),
            job_function=criteria.get('Job function', ''),
            industries=criteria.get('Industries', ''),
        )
        graph.merge(job_node, "Job", "job_id")

        # Company
        company = job.get('company', '')
        if company:
            co_node = Node("Company", name=company)
            graph.merge(co_node, "Company", "name")
            graph.merge(Relationship(job_node, "AT_COMPANY", co_node))

        # Role
        role_key = job.get('role_key', '')
        role_tag = job.get('role_tag', '')
        if role_key and role_tag:
            role_name = role_names.get(role_key, role_key.replace('_', ' ').title())
            role_node = Node("Role", role_key=role_key, name=role_name, tag=role_tag)
            graph.merge(role_node, "Role", "role_key")
            graph.merge(Relationship(job_node, "BELONGS_TO_ROLE", role_node))

        # Skills
        for skill in (job.get('skills') or []):
            if skill and skill.strip():
                sk_node = Node("Skill", name=skill)
                graph.merge(sk_node, "Skill", "name")
                graph.merge(Relationship(job_node, "REQUIRES_SKILL", sk_node))

        added += 1

    logger.info(f"   ✅ Neo4j: {added} jobs imported, "
                f"{len(jobs) - added} skipped (duplicates)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    print("\n🚀 Application starting up...")
    
    # Check Elasticsearch connection
    print("\n🔍 Checking Elasticsearch connection...")
    try:
        from api.core.elasticsearch_config import es_client
        
        if settings.ELASTICSEARCH_ENABLED:
            if es_client.is_connected:
                info = es_client.client.info()
                print(f"✅ Elasticsearch CONNECTED")
                print(f"   └─ Cluster: {info['cluster_name']}")
                print(f"   └─ Version: {info['version']['number']}")
                print(f"   └─ Host: {settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}")
                print(f"   └─ Index: {settings.ELASTICSEARCH_INDEX}")
                
                # Check if index exists
                index_exists = es_client.client.indices.exists(index=settings.ELASTICSEARCH_INDEX)
                if index_exists:
                    doc_count = es_client.client.count(index=settings.ELASTICSEARCH_INDEX)
                    print(f"   └─ Documents: {doc_count['count']}")
                else:
                    print(f"   └─ Index will be auto-created on first save")
            else:
                print(f"⚠️  Elasticsearch NOT CONNECTED")
                print(f"   └─ Host: {settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}")
                print(f"   └─ Make sure Elasticsearch is running: docker-compose up -d")
        else:
            print(f"ℹ️  Elasticsearch is DISABLED (ELASTICSEARCH_ENABLED=False)")
    except Exception as e:
        print(f"⚠️  Elasticsearch connection error: {e}")
    
    # Auto-start scheduler if configured
    if getattr(settings, 'AUTO_START_SCHEDULER', False):
        print("\n⏰ Auto-starting job scheduler...")
        try:
            from api.services.scheduler_service import job_scheduler
            job_scheduler.start()
            print(f"✅ Scheduler started: Next run at {job_scheduler.next_run}")
        except Exception as e:
            print(f"⚠️  Failed to auto-start scheduler: {e}")
    
    # Auto-scrape on startup if index is empty
    if getattr(settings, 'AUTO_SCRAPE_ON_STARTUP', False):
        print("\n🔄 Checking if initial scrape is needed...")
        try:
            from api.core.elasticsearch_config import es_client
            doc_count = 0
            if es_client.is_connected:
                try:
                    index_exists = es_client.client.indices.exists(index=settings.ELASTICSEARCH_INDEX)
                    if index_exists:
                        count_resp = es_client.client.count(index=settings.ELASTICSEARCH_INDEX)
                        doc_count = count_resp.get('count', 0)
                except Exception:
                    pass
            
            if doc_count == 0:
                print("📭 Elasticsearch index is empty — running initial scrape...")
                import threading
                thread = threading.Thread(
                    target=_auto_scrape_and_import,
                    daemon=True
                )
                thread.start()
            else:
                print(f"✅ Elasticsearch already has {doc_count} documents — skipping initial scrape")
        except Exception as e:
            print(f"⚠️  Auto-scrape check failed: {e}")
    
    print("\n✅ Application ready!\n")
    
    yield
    
    # Shutdown
    print("\n🛑 Application shutting down...")
    
    # Close Elasticsearch connection
    try:
        from api.core.elasticsearch_config import es_client
        if es_client.is_connected:
            print("🔍 Closing Elasticsearch connection...")
            es_client.close()
            print("✅ Elasticsearch connection closed")
    except Exception as e:
        print(f"⚠️  Error closing Elasticsearch: {e}")
    
    # Stop scheduler if running
    try:
        from api.services.scheduler_service import job_scheduler
        if job_scheduler.is_running:
            print("⏰ Stopping job scheduler...")
            job_scheduler.stop()
            print("✅ Scheduler stopped")
    except Exception as e:
        print(f"⚠️  Error stopping scheduler: {e}")
    
    print("✅ Application shutdown complete\n")


def create_application() -> FastAPI:
    """Application factory"""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router)
    app.include_router(scraping.router, prefix=settings.API_V1_PREFIX)
    app.include_router(download.router, prefix=settings.API_V1_PREFIX)
    app.include_router(elasticsearch.router, prefix=settings.API_V1_PREFIX, tags=["Elasticsearch"])
    app.include_router(scheduler.router, prefix=f"{settings.API_V1_PREFIX}/scheduler", tags=["Scheduler"])
    
    return app


# Create the application instance
app = create_application()


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    """Redirect root to API docs"""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║           LinkedIn Job Scraper API                            ║
║           Version: {settings.APP_VERSION}                                    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

🚀 Starting server...
📝 Swagger UI: http://{settings.HOST}:{settings.PORT}/docs
📘 ReDoc: http://{settings.HOST}:{settings.PORT}/redoc
🔗 OpenAPI: http://{settings.HOST}:{settings.PORT}/openapi.json

Press CTRL+C to stop the server
""")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD
    )
