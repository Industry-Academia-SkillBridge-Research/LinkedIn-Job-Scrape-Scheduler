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
