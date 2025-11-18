@echo off
echo ========================================
echo LinkedIn Job Scraper API
echo ========================================
echo.
echo Starting FastAPI server...
echo.

cd /d "%~dp0"
python api\main.py

pause
