"""
pytest fixtures shared across all test modules.
"""
import os
import pytest
from tests.client import LinkedInScraperClient


def pytest_configure(config):
    """Register custom markers so pytest doesn't warn about unknown marks."""
    config.addinivalue_line(
        "markers", "slow: marks tests that perform live LinkedIn scraping (deselect with -m 'not slow')"
    )

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def client():
    """Session-scoped API client — one instance for the whole test run."""
    with LinkedInScraperClient(BASE_URL, timeout=60) as c:
        yield c


@pytest.fixture(scope="session")
def scraped_job_id(client):
    """
    Scrape one real job and return its job_id so ES-dependent tests
    can look it up.  Skipped entirely if the scrape returns nothing.
    """
    resp = client.scrape_jobs(
        keywords="Software Engineer",
        location="Remote",
        max_jobs=1,
        fetch_details=False,
        exact_match=False,
    )
    if not resp.ok or not resp.data.get("jobs"):
        pytest.skip("Scrape returned no jobs — skipping ID-dependent tests")
    return resp.data["jobs"][0]["job_id"]
