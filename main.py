"""
Main script to start LinkedIn Job Scraper API
FastAPI server with Swagger UI - API Only Mode
"""
import sys

# Try to load dotenv if available (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    """Start the FastAPI server"""
    try:
        from api.core import settings
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

💡 Use /api/v1/scrape/sync endpoint to scrape with parameters directly
   No job_id needed - just provide keywords, location, max_jobs!

Press CTRL+C to stop the server
""")
        
        uvicorn.run(
            "api.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.RELOAD
        )
    except ImportError as e:
        print("❌ Error: API dependencies not installed")
        print(f"   {str(e)}")
        print("\n💡 Install API dependencies with:")
        print("   pip install -r requirements-api.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting API server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)
