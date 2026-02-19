"""
Standalone test runner — no pytest required.

Usage
-----
    python tests/run_tests.py                   # all tests
    python tests/run_tests.py --fast            # skip slow scraping tests
    python tests/run_tests.py --url http://staging:8000
    python tests/run_tests.py --verbose         # print response bodies

The runner exits with code 0 if all tests pass, 1 otherwise.
"""
from __future__ import annotations

# Ensure the project root (parent of this file's directory) is on sys.path
# so that `from tests.client import ...` works regardless of how this script
# is invoked (python tests/run_tests.py  OR  python -m tests.run_tests).
import sys
import os as _os
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import argparse
import textwrap
import time
import traceback
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from tests.client import LinkedInScraperClient, APIResponse

# ---------------------------------------------------------------------------
# ANSI colours (disabled automatically when stdout is not a TTY)
# ---------------------------------------------------------------------------

_USE_COLOUR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text


PASS = _c("32", "PASS")
FAIL = _c("31", "FAIL")
SKIP = _c("33", "SKIP")
BOLD = lambda t: _c("1", t)


# ---------------------------------------------------------------------------
# Test-case dataclass
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    name: str
    fn: Callable[["Runner"], None]
    slow: bool = False  # slow = needs live LinkedIn scraping


@dataclass
class Result:
    case: TestCase
    passed: bool
    skipped: bool = False
    error: str = ""
    elapsed: float = 0.0


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class Runner:
    """Collects and executes test cases, then prints a summary."""

    def __init__(self, client: LinkedInScraperClient, verbose: bool = False, run_slow: bool = False):
        self.client = client
        self.verbose = verbose
        self.run_slow = run_slow
        self._tests: List[TestCase] = []

    # -- Registration -------------------------------------------------------

    def test(self, name: str, slow: bool = False):
        """Decorator to register a test function."""
        def decorator(fn: Callable):
            self._tests.append(TestCase(name=name, fn=fn, slow=slow))
            return fn
        return decorator

    # -- Execution ----------------------------------------------------------

    def run_all(self) -> List[Result]:
        results: List[Result] = []
        longest = max((len(t.name) for t in self._tests), default=40)

        print(f"\n{BOLD('LinkedIn Job Scraper API — Test Runner')}")
        print(f"  Base URL : {self.client.base_url}")
        print(f"  Run slow : {self.run_slow}")
        print(f"  Tests    : {len(self._tests)}\n")
        print("-" * (longest + 16))

        for case in self._tests:
            if case.slow and not self.run_slow:
                label = f"  {SKIP}  {case.name}"
                print(label)
                results.append(Result(case=case, passed=True, skipped=True))
                continue

            t0 = time.perf_counter()
            try:
                case.fn(self)
                elapsed = time.perf_counter() - t0
                label = f"  {PASS}  {case.name:<{longest}}  ({elapsed*1000:.0f} ms)"
                print(label)
                results.append(Result(case=case, passed=True, elapsed=elapsed))
            except Exception as exc:
                elapsed = time.perf_counter() - t0
                label = f"  {FAIL}  {case.name:<{longest}}  ({elapsed*1000:.0f} ms)"
                print(label)
                err = f"{type(exc).__name__}: {exc}"
                if self.verbose:
                    print(textwrap.indent(traceback.format_exc(), "        "))
                else:
                    print(f"        {_c('31', err)}")
                results.append(Result(case=case, passed=False, error=err, elapsed=elapsed))

        return results

    # -- Summary ------------------------------------------------------------

    def print_summary(self, results: List[Result]) -> bool:
        """Prints the summary table and returns True if all (non-skipped) tests passed."""
        passed  = [r for r in results if r.passed and not r.skipped]
        failed  = [r for r in results if not r.passed]
        skipped = [r for r in results if r.skipped]

        total_time = sum(r.elapsed for r in results)

        print("\n" + "-" * 60)
        print(BOLD("Summary"))
        print(f"  {_c('32', str(len(passed)))} passed   "
              f"{_c('31', str(len(failed)))} failed   "
              f"{_c('33', str(len(skipped)))} skipped   "
              f"({total_time*1000:.0f} ms)")

        if failed:
            print(f"\n{BOLD('Failed tests:')}")
            for r in failed:
                print(f"  • {r.case.name}")
                print(f"    {_c('31', r.error)}")

        print()
        return len(failed) == 0


# ---------------------------------------------------------------------------
# Assertion helpers (used inside test functions)
# ---------------------------------------------------------------------------

def assert_ok(resp: APIResponse, msg: str = ""):
    actual = f"  (got {resp.status_code}: {resp.error or ''})"
    assert resp.ok, f"Expected 2xx{actual}" + (f" — {msg}" if msg else "")


def assert_status(resp: APIResponse, code: int):
    assert resp.status_code == code, (
        f"Expected HTTP {code}, got {resp.status_code}: {resp.error or resp.data}"
    )


def assert_has_keys(data: dict, *keys: str):
    for k in keys:
        assert k in data, f"Missing key '{k}' in response: {list(data.keys())}"


# ---------------------------------------------------------------------------
# Test definitions
# ---------------------------------------------------------------------------

def register_tests(runner: Runner):
    client = runner.client

    # -----------------------------------------------------------------------
    # Health & Root
    # -----------------------------------------------------------------------

    @runner.test("GET /health — status 200")
    def _(r):
        assert_status(client.health(), 200)

    @runner.test("GET /health — body: status=healthy")
    def _(r):
        resp = client.health()
        assert resp.data.get("status") == "healthy", f"Got: {resp.data}"

    @runner.test("GET /health — body has version + timestamp")
    def _(r):
        assert_has_keys(client.health().data, "version", "timestamp")

    @runner.test("GET / — status 200")
    def _(r):
        assert_status(client.root(), 200)

    @runner.test("GET / — body has name, docs_url, openapi_url")
    def _(r):
        assert_has_keys(client.root().data, "name", "docs_url", "openapi_url")

    # -----------------------------------------------------------------------
    # Elasticsearch — read endpoints
    # -----------------------------------------------------------------------

    @runner.test("GET /api/v1/count — status 200")
    def _(r):
        assert_status(client.count(), 200)

    @runner.test("GET /api/v1/count — body: total_jobs (int) + index name")
    def _(r):
        data = client.count().data
        assert isinstance(data.get("total_jobs"), int), f"Got: {data}"
        assert data.get("index") == "linkedin_jobs"

    @runner.test("GET /api/v1/analytics — status 200")
    def _(r):
        assert_status(client.analytics(), 200)

    @runner.test("GET /api/v1/analytics — body has all aggregation keys")
    def _(r):
        assert_has_keys(
            client.analytics().data,
            "total_jobs", "top_companies", "top_locations",
            "top_skills", "employment_types", "by_country", "by_role",
        )

    @runner.test("GET /api/v1/search — no params, status 200")
    def _(r):
        assert_status(client.search_jobs(), 200)

    @runner.test("GET /api/v1/search — body has pagination fields")
    def _(r):
        assert_has_keys(client.search_jobs().data, "total", "hits", "page", "page_size", "pages")

    @runner.test("GET /api/v1/search?query=engineer — status 200")
    def _(r):
        assert_status(client.search_jobs(query="engineer"), 200)

    @runner.test("GET /api/v1/search — page_size param respected")
    def _(r):
        data = client.search_jobs(page_size=7).data
        assert data.get("page_size") == 7

    @runner.test("GET /api/v1/search — location filter accepted")
    def _(r):
        assert_ok(client.search_jobs(query="Data Engineer", location="Remote"))

    @runner.test("GET /api/v1/search — skills filter accepted")
    def _(r):
        assert_ok(client.search_jobs(skills="Python,SQL"))

    @runner.test("GET /api/v1/job/nonexistent — returns 404")
    def _(r):
        assert_status(client.get_job_by_id("nonexistent-job-00000"), 404)

    # -----------------------------------------------------------------------
    # Scraping — validation (no network)
    # -----------------------------------------------------------------------

    @runner.test("POST /api/v1/scrape/ — missing keywords → 422")
    def _(r):
        assert_status(client.post("/api/v1/scrape/", body={"max_jobs": 3}), 422)

    @runner.test("POST /api/v1/scrape/ — max_jobs=0 → 422")
    def _(r):
        assert_status(
            client.post("/api/v1/scrape/", body={"keywords": "Engineer", "max_jobs": 0}), 422
        )

    @runner.test("POST /api/v1/scrape/ — max_jobs=999 → 422")
    def _(r):
        assert_status(
            client.post("/api/v1/scrape/", body={"keywords": "Engineer", "max_jobs": 999}), 422
        )

    @runner.test("GET /api/v1/scrape/jobs — status 200, returns list")
    def _(r):
        resp = client.list_scraping_jobs()
        assert_status(resp, 200)
        assert isinstance(resp.data, list)

    # -----------------------------------------------------------------------
    # Scraping — live network (slow)
    # -----------------------------------------------------------------------

    @runner.test("POST /api/v1/scrape/ — live scrape, status 200", slow=True)
    def _(r):
        assert_ok(client.scrape_jobs("Data Engineer", max_jobs=2,
                                     fetch_details=False, exact_match=False))

    @runner.test("POST /api/v1/scrape/ — response structure", slow=True)
    def _(r):
        resp = client.scrape_jobs("Software Engineer", max_jobs=2,
                                  fetch_details=False, exact_match=False)
        assert_ok(resp)
        assert_has_keys(resp.data, "total", "jobs", "scraped_at", "search_params")
        assert isinstance(resp.data["jobs"], list)

    @runner.test("POST /api/v1/scrape/ — each job has required fields", slow=True)
    def _(r):
        resp = client.scrape_jobs("Data Analyst", max_jobs=2,
                                  fetch_details=False, exact_match=False)
        assert_ok(resp)
        for job in resp.data.get("jobs", []):
            assert_has_keys(job, "job_id", "title", "company", "location",
                            "job_url", "scraped_at")

    @runner.test("POST /api/v1/scrape/ — exact_match filters titles", slow=True)
    def _(r):
        resp = client.scrape_jobs("Data Engineer", max_jobs=5,
                                  fetch_details=False, exact_match=True)
        assert_ok(resp)
        for job in resp.data.get("jobs", []):
            assert "data engineer" in job["title"].lower(), (
                f"exact_match=True returned unrelated title: {job['title']}"
            )

    @runner.test("POST /api/v1/scrape/sync — alias, status 200", slow=True)
    def _(r):
        assert_ok(client.scrape_jobs_sync("DevOps Engineer", max_jobs=2,
                                          fetch_details=False, exact_match=False))

    # -----------------------------------------------------------------------
    # Download
    # -----------------------------------------------------------------------

    @runner.test("GET /api/v1/download/nonexistent — returns 404")
    def _(r):
        assert_status(client.download_job_results("nonexistent-job-id"), 404)

    # -----------------------------------------------------------------------
    # Scheduler — read
    # -----------------------------------------------------------------------

    @runner.test("GET /api/v1/scheduler/status — status 200")
    def _(r):
        assert_status(client.scheduler_status(), 200)

    @runner.test("GET /api/v1/scheduler/status — body structure")
    def _(r):
        assert_has_keys(
            client.scheduler_status().data,
            "is_running", "is_scraping", "last_run", "next_run",
            "schedule", "configuration", "current_scraping", "elasticsearch_enabled",
        )

    @runner.test("GET /api/v1/scheduler/status — schedule has day + time")
    def _(r):
        schedule = client.scheduler_status().data.get("schedule", {})
        assert_has_keys(schedule, "day", "time")

    @runner.test("GET /api/v1/scheduler/configuration — status 200")
    def _(r):
        assert_status(client.scheduler_configuration(), 200)

    @runner.test("GET /api/v1/scheduler/configuration — has job_roles dict")
    def _(r):
        data = client.scheduler_configuration().data
        assert isinstance(data.get("job_roles"), dict)
        assert len(data["job_roles"]) > 0

    @runner.test("GET /api/v1/scheduler/configuration — has location_priority")
    def _(r):
        loc = client.scheduler_configuration().data.get("location_priority", {})
        assert_has_keys(loc, "primary", "fallback")

    @runner.test("GET /api/v1/scheduler/configuration — has filters")
    def _(r):
        filters = client.scheduler_configuration().data.get("filters", {})
        assert_has_keys(filters, "max_post_age_days", "exact_match", "fetch_details")

    @runner.test("GET /api/v1/scheduler/logs — status 200")
    def _(r):
        assert_status(client.scheduler_logs(), 200)

    @runner.test("GET /api/v1/scheduler/logs — body structure")
    def _(r):
        assert_has_keys(
            client.scheduler_logs().data,
            "last_run", "last_run_statistics", "next_scheduled_run",
        )

    @runner.test("GET /api/v1/scheduler/logs — statistics structure")
    def _(r):
        stats = client.scheduler_logs().data.get("last_run_statistics", {})
        assert_has_keys(stats, "jobs_by_role", "jobs_by_country", "total_jobs")

    # -----------------------------------------------------------------------
    # Scheduler — mutations
    # -----------------------------------------------------------------------

    @runner.test("POST /api/v1/scheduler/stop — status 200")
    def _(r):
        assert_status(client.scheduler_stop(), 200)

    @runner.test("POST /api/v1/scheduler/stop — is_running=False")
    def _(r):
        assert client.scheduler_stop().data.get("is_running") is False

    @runner.test("POST /api/v1/scheduler/start — status 200")
    def _(r):
        assert_status(client.scheduler_start(), 200)

    @runner.test("POST /api/v1/scheduler/start — is_running=True")
    def _(r):
        assert client.scheduler_start().data.get("is_running") is True

    @runner.test("PUT /api/v1/scheduler/configuration — update day to tuesday")
    def _(r):
        resp = client.scheduler_update_configuration(day="tuesday")
        assert_ok(resp)
        assert "tuesday" in str(resp.data.get("new_schedule", {}).get("day", "")).lower()
        client.scheduler_update_configuration(day="monday")   # restore

    @runner.test("PUT /api/v1/scheduler/configuration — update time to 10:30")
    def _(r):
        resp = client.scheduler_update_configuration(time="10:30")
        assert_ok(resp)
        assert resp.data.get("new_schedule", {}).get("time") == "10:30"
        client.scheduler_update_configuration(time="09:00")   # restore

    @runner.test("PUT /api/v1/scheduler/configuration — invalid day → 400")
    def _(r):
        assert_status(client.scheduler_update_configuration(day="funday"), 400)

    @runner.test("PUT /api/v1/scheduler/configuration — invalid time → 400")
    def _(r):
        assert_status(client.scheduler_update_configuration(time="99:99"), 400)

    @runner.test("PUT /api/v1/scheduler/configuration — empty body → 400")
    def _(r):
        assert_status(client.put("/api/v1/scheduler/configuration", body={}), 400)

    @runner.test("POST /api/v1/scheduler/run-now — status 200", slow=True)
    def _(r):
        resp = client.scheduler_run_now()
        assert_status(resp, 200)
        assert resp.data.get("status") == "started"
        assert "started_at" in resp.data


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="LinkedIn Scraper API — test runner")
    p.add_argument("--url", default="http://localhost:8000",
                   help="API base URL (default: http://localhost:8000)")
    p.add_argument("--fast", action="store_true",
                   help="Skip slow tests that perform live LinkedIn scraping")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Print full tracebacks on failure")
    return p.parse_args()


def main():
    args = parse_args()

    with LinkedInScraperClient(args.url, timeout=60) as client:
        runner = Runner(
            client=client,
            verbose=args.verbose,
            run_slow=not args.fast,
        )
        register_tests(runner)
        results = runner.run_all()
        all_passed = runner.print_summary(results)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
