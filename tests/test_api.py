"""
Full pytest test suite for the LinkedIn Job Scraper API.

Run all tests:
    pytest tests/test_api.py -v

Run only fast tests (no live scraping):
    pytest tests/test_api.py -v -m "not slow"

Run against a different host:
    API_BASE_URL=http://staging:8000 pytest tests/test_api.py -v
"""
import pytest


# ===========================================================================
# Health & Root  (GET /health, GET /)
# ===========================================================================

class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.health()
        assert resp.status_code == 200

    def test_health_body_has_status_healthy(self, client):
        resp = client.health()
        assert resp.data.get("status") == "healthy"

    def test_health_body_has_version(self, client):
        resp = client.health()
        assert "version" in resp.data

    def test_health_body_has_timestamp(self, client):
        resp = client.health()
        assert "timestamp" in resp.data

    def test_root_returns_200(self, client):
        resp = client.root()
        assert resp.status_code == 200

    def test_root_body_has_name(self, client):
        resp = client.root()
        assert "name" in resp.data

    def test_root_body_has_docs_url(self, client):
        resp = client.root()
        assert resp.data.get("docs_url") == "/docs"


# ===========================================================================
# Elasticsearch — read-only  (GET /api/v1/count, /analytics, /search)
# ===========================================================================

class TestElasticsearch:
    def test_count_returns_200(self, client):
        resp = client.count()
        assert resp.status_code == 200

    def test_count_body_has_total_jobs(self, client):
        resp = client.count()
        assert "total_jobs" in resp.data
        assert isinstance(resp.data["total_jobs"], int)

    def test_count_body_has_index(self, client):
        resp = client.count()
        assert resp.data.get("index") == "linkedin_jobs"

    def test_analytics_returns_200(self, client):
        resp = client.analytics()
        assert resp.status_code == 200

    def test_analytics_body_structure(self, client):
        resp = client.analytics()
        for key in ("total_jobs", "top_companies", "top_locations", "top_skills",
                    "employment_types", "by_country", "by_role"):
            assert key in resp.data, f"Missing key: {key}"

    def test_search_no_params_returns_200(self, client):
        resp = client.search_jobs()
        assert resp.status_code == 200

    def test_search_body_has_pagination_fields(self, client):
        resp = client.search_jobs(page=1, page_size=5)
        for key in ("total", "hits", "page", "page_size", "pages"):
            assert key in resp.data, f"Missing key: {key}"

    def test_search_with_query_returns_200(self, client):
        resp = client.search_jobs(query="engineer")
        assert resp.status_code == 200
        assert isinstance(resp.data.get("hits"), list)

    def test_search_with_location_filter(self, client):
        resp = client.search_jobs(query="Data Engineer", location="Remote")
        assert resp.status_code == 200

    def test_search_with_skills_filter(self, client):
        resp = client.search_jobs(skills="Python,SQL")
        assert resp.status_code == 200

    def test_search_pagination(self, client):
        resp = client.search_jobs(page=1, page_size=3)
        assert resp.data.get("page_size") == 3

    def test_get_job_by_nonexistent_id_returns_404(self, client):
        resp = client.get_job_by_id("nonexistent-job-id-00000")
        assert resp.status_code == 404


# ===========================================================================
# Scraping — live network calls  (POST /api/v1/scrape/)
# ===========================================================================

class TestScraping:
    @pytest.mark.slow
    def test_scrape_returns_200(self, client):
        resp = client.scrape_jobs(
            keywords="Data Analyst",
            location="Remote",
            max_jobs=2,
            fetch_details=False,
            exact_match=False,
        )
        assert resp.status_code == 200

    @pytest.mark.slow
    def test_scrape_response_structure(self, client):
        resp = client.scrape_jobs(
            keywords="Data Engineer",
            max_jobs=2,
            fetch_details=False,
            exact_match=False,
        )
        assert isinstance(resp.data.get("total"), int)
        assert isinstance(resp.data.get("jobs"), list)
        assert "scraped_at" in resp.data
        assert "search_params" in resp.data

    @pytest.mark.slow
    def test_scrape_job_fields_present(self, client):
        resp = client.scrape_jobs(
            keywords="Software Engineer",
            max_jobs=1,
            fetch_details=False,
            exact_match=False,
        )
        if resp.data.get("jobs"):
            job = resp.data["jobs"][0]
            for field in ("job_id", "title", "company", "location", "job_url", "scraped_at"):
                assert field in job, f"Job missing field: {field}"

    @pytest.mark.slow
    def test_scrape_exact_match_filters_correctly(self, client):
        resp = client.scrape_jobs(
            keywords="Data Engineer",
            max_jobs=5,
            fetch_details=False,
            exact_match=True,
        )
        assert resp.ok
        for job in resp.data.get("jobs", []):
            assert "data engineer" in job["title"].lower()

    @pytest.mark.slow
    def test_scrape_sync_alias_returns_200(self, client):
        resp = client.scrape_jobs_sync(
            keywords="DevOps Engineer",
            max_jobs=2,
            fetch_details=False,
            exact_match=False,
        )
        assert resp.status_code == 200

    def test_scrape_missing_keywords_returns_422(self, client):
        """keywords is required — omitting it must return 422 Unprocessable Entity."""
        resp = client.post("/api/v1/scrape/", body={"max_jobs": 3})
        assert resp.status_code == 422

    def test_scrape_max_jobs_too_high_returns_422(self, client):
        """max_jobs > 50 must be rejected."""
        resp = client.post("/api/v1/scrape/", body={"keywords": "Engineer", "max_jobs": 999})
        assert resp.status_code == 422

    def test_scrape_max_jobs_zero_returns_422(self, client):
        """max_jobs < 1 must be rejected."""
        resp = client.post("/api/v1/scrape/", body={"keywords": "Engineer", "max_jobs": 0})
        assert resp.status_code == 422

    def test_list_scraping_jobs_returns_200(self, client):
        resp = client.list_scraping_jobs()
        assert resp.status_code == 200
        assert isinstance(resp.data, list)


# ===========================================================================
# Download  (GET /api/v1/download/{job_id})
# ===========================================================================

class TestDownload:
    def test_download_nonexistent_job_returns_404(self, client):
        resp = client.download_job_results("nonexistent-job-id")
        assert resp.status_code == 404


# ===========================================================================
# Scheduler  (GET/POST /api/v1/scheduler/*)
# ===========================================================================

class TestScheduler:
    # --- status ---
    def test_status_returns_200(self, client):
        resp = client.scheduler_status()
        assert resp.status_code == 200

    def test_status_body_structure(self, client):
        resp = client.scheduler_status()
        for key in ("is_running", "is_scraping", "last_run", "next_run",
                    "schedule", "configuration", "current_scraping", "elasticsearch_enabled"):
            assert key in resp.data, f"Missing key in scheduler status: {key}"

    def test_status_schedule_fields(self, client):
        schedule = client.scheduler_status().data.get("schedule", {})
        assert "day" in schedule
        assert "time" in schedule

    # --- configuration ---
    def test_configuration_returns_200(self, client):
        resp = client.scheduler_configuration()
        assert resp.status_code == 200

    def test_configuration_has_job_roles(self, client):
        resp = client.scheduler_configuration()
        assert isinstance(resp.data.get("job_roles"), dict)
        assert len(resp.data["job_roles"]) > 0

    def test_configuration_has_location_priority(self, client):
        resp = client.scheduler_configuration()
        loc = resp.data.get("location_priority", {})
        assert "primary" in loc
        assert "fallback" in loc

    def test_configuration_has_schedule(self, client):
        resp = client.scheduler_configuration()
        sched = resp.data.get("schedule", {})
        assert "day" in sched
        assert "time" in sched

    def test_configuration_has_filters(self, client):
        resp = client.scheduler_configuration()
        filters = resp.data.get("filters", {})
        assert "max_post_age_days" in filters
        assert "exact_match" in filters

    # --- update configuration ---
    def test_update_configuration_valid_day(self, client):
        resp = client.scheduler_update_configuration(day="tuesday")
        assert resp.status_code == 200
        assert "tuesday" in str(resp.data.get("new_schedule", {}).get("day", "")).lower()
        # restore original
        client.scheduler_update_configuration(day="monday")

    def test_update_configuration_valid_time(self, client):
        resp = client.scheduler_update_configuration(time="10:00")
        assert resp.status_code == 200
        assert resp.data.get("new_schedule", {}).get("time") == "10:00"
        # restore original
        client.scheduler_update_configuration(time="09:00")

    def test_update_configuration_invalid_day_returns_400(self, client):
        resp = client.scheduler_update_configuration(day="funday")
        assert resp.status_code == 400

    def test_update_configuration_invalid_time_returns_400(self, client):
        resp = client.scheduler_update_configuration(time="99:99")
        assert resp.status_code == 400

    def test_update_configuration_empty_body_returns_400(self, client):
        resp = client.put("/api/v1/scheduler/configuration", body={})
        assert resp.status_code == 400

    # --- start / stop ---
    def test_start_returns_200(self, client):
        resp = client.scheduler_start()
        assert resp.status_code == 200

    def test_start_response_has_is_running_true(self, client):
        resp = client.scheduler_start()
        assert resp.data.get("is_running") is True

    def test_stop_returns_200(self, client):
        resp = client.scheduler_stop()
        assert resp.status_code == 200

    def test_stop_response_has_is_running_false(self, client):
        resp = client.scheduler_stop()
        assert resp.data.get("is_running") is False

    def test_start_after_stop(self, client):
        client.scheduler_stop()
        resp = client.scheduler_start()
        assert resp.ok
        assert resp.data.get("is_running") is True

    # --- logs ---
    def test_logs_returns_200(self, client):
        resp = client.scheduler_logs()
        assert resp.status_code == 200

    def test_logs_body_structure(self, client):
        resp = client.scheduler_logs()
        for key in ("last_run", "last_run_statistics", "next_scheduled_run"):
            assert key in resp.data, f"Missing key in logs: {key}"

    def test_logs_statistics_structure(self, client):
        stats = client.scheduler_logs().data.get("last_run_statistics", {})
        assert "jobs_by_role" in stats
        assert "jobs_by_country" in stats
        assert "total_jobs" in stats

    # --- run-now (slow — triggers background scraping) ---
    @pytest.mark.slow
    def test_run_now_returns_200(self, client):
        resp = client.scheduler_run_now()
        assert resp.status_code == 200

    @pytest.mark.slow
    def test_run_now_response_structure(self, client):
        resp = client.scheduler_run_now()
        assert resp.data.get("status") == "started"
        assert "started_at" in resp.data
