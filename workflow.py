"""
End-to-end workflow: scrape → save to Elasticsearch → query results.

This script:
  1. Health-checks the API + Elasticsearch
  2. Scrapes jobs for 4 configurable roles (no fetch_details for speed)
  3. Bulk-saves all results directly to Elasticsearch
  4. Queries Elasticsearch: count, analytics, and keyword search
  5. Prints a final summary table

Usage
-----
    python workflow.py                        # default roles, 5 jobs each
    python workflow.py --max-jobs 10          # more jobs per role
    python workflow.py --url http://host:8000 # different host
    python workflow.py --no-save              # scrape only, skip ES save
"""
from __future__ import annotations

import argparse
import json
import sys
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# path bootstrap so we can reuse the existing client
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tests.client import LinkedInScraperClient   # noqa: E402

# ---------------------------------------------------------------------------
# ANSI colours
# ---------------------------------------------------------------------------
_TTY = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def bold(t: str) -> str:  return _c("1",  t)
def green(t: str) -> str: return _c("32", t)
def yellow(t: str) -> str: return _c("33", t)
def red(t: str) -> str:   return _c("31", t)
def cyan(t: str) -> str:  return _c("36", t)
def dim(t: str) -> str:   return _c("2",  t)


def section(title: str):
    width = 64
    print(f"\n{'─' * width}")
    print(f"  {bold(title)}")
    print(f"{'─' * width}")


def ok(msg: str):   print(f"  {green('✓')} {msg}")
def warn(msg: str): print(f"  {yellow('⚠')} {msg}")
def err(msg: str):  print(f"  {red('✗')} {msg}")
def info(msg: str): print(f"  {cyan('›')} {msg}")


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
ROLES = [
    ("Data Engineer",       "Remote",    True),   # (keywords, location, exact_match)
    ("Machine Learning Engineer", "Remote", True),
    ("DevOps Engineer",     "Remote",    True),
    ("Data Analyst",        "Remote",    False),
]

ES_INDEX    = "linkedin_jobs"
ES_BASE_URL = "http://localhost:9200"


# ---------------------------------------------------------------------------
# Elasticsearch helpers (direct HTTP, no library needed)
# ---------------------------------------------------------------------------

def es_bulk_save(jobs: List[Dict], es_url: str, index: str) -> Dict[str, int]:
    """Bulk-index a list of job dicts into Elasticsearch."""
    if not jobs:
        return {"saved": 0, "failed": 0}

    lines: List[str] = []
    for job in jobs:
        job_copy = dict(job)
        job_copy.setdefault("scraped_at", datetime.now(timezone.utc).isoformat())
        doc_id = job_copy.get("job_id", "")
        action = {"index": {"_index": index}}
        if doc_id:
            action["index"]["_id"] = doc_id
        lines.append(json.dumps(action))
        lines.append(json.dumps(job_copy))

    body = "\n".join(lines) + "\n"
    resp = requests.post(
        f"{es_url}/_bulk",
        data=body,
        headers={"Content-Type": "application/x-ndjson"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    saved  = sum(1 for item in data.get("items", []) if item.get("index", {}).get("result") in ("created", "updated"))
    failed = sum(1 for item in data.get("items", []) if item.get("index", {}).get("error"))
    return {"saved": saved, "failed": failed}


def es_count(es_url: str, index: str) -> int:
    try:
        r = requests.get(f"{es_url}/{index}/_count", timeout=10)
        return r.json().get("count", 0)
    except Exception:
        return -1


def es_refresh(es_url: str, index: str):
    """Force ES to make writes visible immediately."""
    requests.post(f"{es_url}/{index}/_refresh", timeout=10)


# ---------------------------------------------------------------------------
# Main workflow
# ---------------------------------------------------------------------------

def run_workflow(
    api_url: str,
    es_url: str,
    roles: List[tuple],
    max_jobs: int,
    save: bool,
):
    start_time = time.perf_counter()

    # ── 0. Banner ──────────────────────────────────────────────────────────
    print(f"""
{bold('═' * 64)}
{bold('  LinkedIn Job Scraper — End-to-End Workflow')}
{bold('═' * 64)}
  API  : {cyan(api_url)}
  ES   : {cyan(es_url)}
  Roles: {len(roles)}  ·  Max jobs/role: {max_jobs}
  Save : {'Elasticsearch' if save else 'Disabled (dry-run)'}
  Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")

    # ── 1. Health check ────────────────────────────────────────────────────
    section("Step 1 — Health Checks")

    with LinkedInScraperClient(api_url) as client:
        resp = client.health()
        if resp.ok:
            ok(f"API healthy — v{resp.data.get('version', '?')}")
        else:
            err(f"API not healthy: {resp.status_code}")
            sys.exit(1)

    try:
        es_resp = requests.get(f"{es_url}/_cluster/health", timeout=5)
        es_data = es_resp.json()
        status_colour = green if es_data["status"] == "green" else yellow
        ok(f"Elasticsearch {status_colour(es_data['status'].upper())} — "
           f"cluster: {es_data['cluster_name']}")
        initial_count = es_count(es_url, ES_INDEX)
        info(f"Index '{ES_INDEX}' — documents before run: {bold(str(initial_count))}")
    except Exception as e:
        err(f"Cannot reach Elasticsearch at {es_url}: {e}")
        save = False
        warn("Continuing without ES save")

    # ── 2. Scrape all roles ────────────────────────────────────────────────
    section("Step 2 — Scraping Jobs from LinkedIn")

    all_jobs: List[Dict] = []
    role_summary: List[Dict] = []

    with LinkedInScraperClient(api_url, timeout=90) as client:
        for i, (keywords, location, exact_match) in enumerate(roles, 1):
            label = f"[{i}/{len(roles)}] {bold(keywords)}"
            print(f"\n  {label}  ({location}, exact={exact_match})")
            t0 = time.perf_counter()

            resp = client.scrape_jobs(
                keywords=keywords,
                location=location,
                max_jobs=max_jobs,
                fetch_details=False,
                exact_match=exact_match,
            )

            elapsed = time.perf_counter() - t0

            if not resp.ok:
                err(f"  Scrape failed: {resp.status_code} — {resp.error}")
                role_summary.append({"role": keywords, "scraped": 0, "saved": 0, "error": resp.error})
                continue

            jobs = resp.data.get("jobs", [])
            for j in jobs:
                j["job_role"] = keywords          # tag each job with role
            all_jobs.extend(jobs)

            ok(f"  {green(str(len(jobs)))} jobs scraped  "
               f"{dim(f'({elapsed:.1f}s)')}")

            for job in jobs:
                print(f"      {dim('·')} {job['title']:<45} @ {dim(job['company'][:30])}")

            role_summary.append({
                "role":    keywords,
                "scraped": len(jobs),
                "saved":   0,
                "error":   None,
            })

    info(f"\n  Total jobs scraped: {bold(str(len(all_jobs)))}")

    # ── 3. Save to Elasticsearch ───────────────────────────────────────────
    if save and all_jobs:
        section("Step 3 — Saving to Elasticsearch")

        info(f"Bulk-indexing {len(all_jobs)} documents into '{ES_INDEX}' …")
        t0 = time.perf_counter()

        try:
            result = es_bulk_save(all_jobs, es_url, ES_INDEX)
            es_refresh(es_url, ES_INDEX)
            elapsed = time.perf_counter() - t0

            ok(f"{green(str(result['saved']))} documents saved   "
               f"{dim(f'({elapsed:.1f}s)')}")
            if result["failed"]:
                warn(f"{result['failed']} documents failed to index "
                     f"(likely duplicates or field mapping errors)")

            # update role_summary with save counts (approximate equal split)
            for entry in role_summary:
                entry["saved"] = result["saved"] // max(len(roles), 1)

        except Exception as e:
            err(f"Bulk save failed: {e}")
    elif not save:
        section("Step 3 — Elasticsearch Save (skipped — dry-run)")
        warn("Pass without --no-save to persist data")

    # ── 4. Query Elasticsearch ─────────────────────────────────────────────
    if save:
        section("Step 4 — Querying Elasticsearch")

        # 4a. Count
        count_after = es_count(es_url, ES_INDEX)
        info(f"Total documents in index: {bold(str(count_after))}")

        # 4b. Analytics via API
        try:
            with LinkedInScraperClient(api_url) as client:
                analytics = client.analytics().data
            print()
            info(f"Top companies:")
            for c in analytics.get("top_companies", [])[:5]:
                print(f"      {dim('·')} {c.get('name', '?'):<40} "
                      f"({c.get('count', '?')} jobs)")

            print()
            info(f"Top locations:")
            for l in analytics.get("top_locations", [])[:5]:
                print(f"      {dim('·')} {l.get('location', '?'):<40} "
                      f"({l.get('count', '?')} jobs)")

            print()
            info(f"Jobs by role:")
            for r in analytics.get("by_role", [])[:8]:
                role_name = r.get("role", "?")
                role_cnt  = r.get("count", "?")
                print(f"      {dim('·')} {role_name:<40} {role_cnt}")

        except Exception as e:
            warn(f"Could not fetch analytics: {e}")

        # 4c. Sample search
        print()
        sample_query = "Engineer"
        info(f"Sample search: '{sample_query}' (top 5 hits)")
        try:
            with LinkedInScraperClient(api_url) as client:
                search_resp = client.search_jobs(query=sample_query, page_size=5)
            hits = search_resp.data.get("hits", [])
            total = search_resp.data.get("total", 0)
            info(f"  {total} total matches — showing first {len(hits)}:")
            for h in hits:
                print(f"      {dim('·')} {h.get('title','?'):<45} @ {h.get('company','?')[:25]}")
                print(f"        {dim(h.get('location',''))}")
        except Exception as e:
            warn(f"Could not fetch search results: {e}")

    # ── 5. Summary table ───────────────────────────────────────────────────
    section("Step 5 — Workflow Summary")

    col_w = [38, 10, 10]
    header = (
        f"  {'Role':<{col_w[0]}} {'Scraped':>{col_w[1]}} {'Saved':>{col_w[2]}}"
    )
    print(header)
    print(f"  {'─'*col_w[0]} {'─'*col_w[1]} {'─'*col_w[2]}")
    for entry in role_summary:
        status = "" if entry["error"] else ""
        print(
            f"  {status} {entry['role']:<{col_w[0]-2}} "
            f"{green(str(entry['scraped'])):>{col_w[1]+9}} "
            f"{(green(str(entry['saved'])) if save else dim('—')):>{col_w[2]+9}}"
        )

    total_scraped = sum(e["scraped"] for e in role_summary)
    total_saved   = sum(e["saved"]   for e in role_summary) if save else 0

    print(f"  {'─'*col_w[0]} {'─'*col_w[1]} {'─'*col_w[2]}")
    print(
        f"  {'TOTAL':<{col_w[0]}} "
        f"{bold(str(total_scraped)):>{col_w[1]+8}} "
        f"{(bold(str(total_saved)) if save else dim('—')):>{col_w[2]+8}}"
    )

    elapsed_total = time.perf_counter() - start_time
    print(f"\n  {green('✓')} Workflow complete in {bold(f'{elapsed_total:.1f}s')}")
    if save and all_jobs:
        print(f"  {cyan('›')} View http://{api_url.split('://')[-1]}/docs to query via Swagger")
        print(f"  {cyan('›')} Elasticsearch: {es_url}/{ES_INDEX}/_search")
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="LinkedIn Scraper — end-to-end workflow demo")
    p.add_argument("--url",       default="http://localhost:8000", help="API base URL")
    p.add_argument("--es-url",    default="http://localhost:9200", help="Elasticsearch URL")
    p.add_argument("--max-jobs",  type=int, default=5,            help="Max jobs per role (1-50)")
    p.add_argument("--no-save",   action="store_true",            help="Skip Elasticsearch save")
    args = p.parse_args()

    run_workflow(
        api_url  = args.url,
        es_url   = args.es_url,
        roles    = ROLES,
        max_jobs = min(max(args.max_jobs, 1), 50),
        save     = not args.no_save,
    )


if __name__ == "__main__":
    main()
