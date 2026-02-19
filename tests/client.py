"""
Reusable API client for the LinkedIn Job Scraper API.
Each method maps 1-to-1 with an endpoint, returns the parsed JSON
and the raw ``requests.Response`` so callers can inspect status codes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Response = requests.Response
JSON = Dict[str, Any]


@dataclass
class APIResponse:
    """Thin wrapper so tests can check both the HTTP layer and the body."""
    status_code: int
    data: Any                # parsed JSON, or raw text on non-JSON responses
    ok: bool                 # True when 2xx
    raw: Response = field(repr=False)

    @property
    def error(self) -> Optional[str]:
        """Return the ``detail`` field if the response is an error dict."""
        if isinstance(self.data, dict):
            return self.data.get("detail")
        return None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class LinkedInScraperClient:
    """
    Thin HTTP client for the LinkedIn Job Scraper REST API.

    Usage
    -----
    >>> client = LinkedInScraperClient("http://localhost:8000")
    >>> resp = client.health()
    >>> assert resp.ok
    >>> print(resp.data["status"])  # "healthy"
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict] = None,
        body: Optional[Dict] = None,
    ) -> APIResponse:
        url = f"{self.base_url}{path}"
        raw = self._session.request(
            method,
            url,
            params=params,
            json=body,
            timeout=self.timeout,
            allow_redirects=True,
        )
        try:
            data = raw.json()
        except Exception:
            data = raw.text

        return APIResponse(
            status_code=raw.status_code,
            data=data,
            ok=raw.ok,
            raw=raw,
        )

    def get(self, path: str, **params) -> APIResponse:
        return self._request("GET", path, params=params or None)

    def post(self, path: str, body: Optional[Dict] = None) -> APIResponse:
        return self._request("POST", path, body=body)

    def put(self, path: str, body: Optional[Dict] = None) -> APIResponse:
        return self._request("PUT", path, body=body)

    def delete(self, path: str) -> APIResponse:
        return self._request("DELETE", path)

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> APIResponse:
        """GET /health"""
        return self.get("/health")

    def root(self) -> APIResponse:
        """GET /  (returns API info; redirects from root)"""
        return self.get("/")

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------

    def scrape_jobs(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_jobs: int = 5,
        fetch_details: bool = False,
        exact_match: bool = True,
        method: str = "beautifulsoup",
    ) -> APIResponse:
        """POST /api/v1/scrape/"""
        return self.post("/api/v1/scrape/", body={
            "keywords": keywords,
            "location": location,
            "max_jobs": max_jobs,
            "fetch_details": fetch_details,
            "exact_match": exact_match,
            "method": method,
        })

    def scrape_jobs_sync(
        self,
        keywords: str,
        location: Optional[str] = None,
        max_jobs: int = 5,
        fetch_details: bool = False,
        exact_match: bool = True,
        method: str = "beautifulsoup",
    ) -> APIResponse:
        """POST /api/v1/scrape/sync  (alias endpoint)"""
        return self.post("/api/v1/scrape/sync", body={
            "keywords": keywords,
            "location": location,
            "max_jobs": max_jobs,
            "fetch_details": fetch_details,
            "exact_match": exact_match,
            "method": method,
        })

    def list_scraping_jobs(self) -> APIResponse:
        """GET /api/v1/scrape/jobs"""
        return self.get("/api/v1/scrape/jobs")

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download_job_results(self, job_id: str) -> APIResponse:
        """GET /api/v1/download/{job_id}"""
        return self.get(f"/api/v1/download/{job_id}")

    # ------------------------------------------------------------------
    # Elasticsearch
    # ------------------------------------------------------------------

    def search_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        skills: Optional[str] = None,          # comma-separated
        employment_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> APIResponse:
        """GET /api/v1/search"""
        params = {k: v for k, v in {
            "query": query,
            "location": location,
            "company": company,
            "skills": skills,
            "employment_type": employment_type,
            "page": page,
            "page_size": page_size,
        }.items() if v is not None}
        return self.get("/api/v1/search", **params)

    def get_job_by_id(self, job_id: str) -> APIResponse:
        """GET /api/v1/job/{job_id}"""
        return self.get(f"/api/v1/job/{job_id}")

    def delete_job(self, job_id: str) -> APIResponse:
        """DELETE /api/v1/job/{job_id}"""
        return self.delete(f"/api/v1/job/{job_id}")

    def analytics(self) -> APIResponse:
        """GET /api/v1/analytics"""
        return self.get("/api/v1/analytics")

    def count(self) -> APIResponse:
        """GET /api/v1/count"""
        return self.get("/api/v1/count")

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------

    def scheduler_status(self) -> APIResponse:
        """GET /api/v1/scheduler/status"""
        return self.get("/api/v1/scheduler/status")

    def scheduler_start(self) -> APIResponse:
        """POST /api/v1/scheduler/start"""
        return self.post("/api/v1/scheduler/start")

    def scheduler_stop(self) -> APIResponse:
        """POST /api/v1/scheduler/stop"""
        return self.post("/api/v1/scheduler/stop")

    def scheduler_run_now(self) -> APIResponse:
        """POST /api/v1/scheduler/run-now"""
        return self.post("/api/v1/scheduler/run-now")

    def scheduler_configuration(self) -> APIResponse:
        """GET /api/v1/scheduler/configuration"""
        return self.get("/api/v1/scheduler/configuration")

    def scheduler_update_configuration(
        self,
        day: Optional[str] = None,
        time: Optional[str] = None,
    ) -> APIResponse:
        """PUT /api/v1/scheduler/configuration"""
        body = {k: v for k, v in {"day": day, "time": time}.items() if v is not None}
        return self.put("/api/v1/scheduler/configuration", body=body)

    def scheduler_logs(self) -> APIResponse:
        """GET /api/v1/scheduler/logs"""
        return self.get("/api/v1/scheduler/logs")

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
