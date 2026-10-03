import os, time
import requests
import config
from common import build_job, parse_dt

class SkipSource(Exception):
    """Keys missing etc. - source skip hoga, fail count nahi badhega."""

def http_json(method, url, **kw):
    last = None
    for i in range(3):
        try:
            r = requests.request(method, url, timeout=25, **kw)
            if r.status_code in (400, 401, 403, 404):
                raise RuntimeError(f"HTTP {r.status_code} for {url.split('?')[0][:80]}")
            if r.status_code == 429 or r.status_code >= 500:
                last = RuntimeError(f"HTTP {r.status_code}")
                time.sleep(3 * (i + 1)); continue
            return r.json()
        except requests.RequestException as e:
            last = e; time.sleep(2 * (i + 1))
    raise last

# ---------------- Adzuna (free API key) ----------------
def fetch_adzuna():
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        raise SkipSource("Adzuna keys missing")
    jobs, errors = [], 0
    for city in config.SEARCH_CITIES:
        try:
            data = http_json("GET", "https://api.adzuna.com/v1/api/jobs/in/search/1", params={
                "app_id": app_id, "app_key": app_key, "results_per_page": 50,
                "what_or": config.ADZUNA_WHAT_OR, "where": city,
                "sort_by": "date", "max_days_old": 3, "content-type": "application/json"})
        except Exception:
            errors += 1; continue
        for r in data.get("results", []):
            j = build_job("Adzuna", r.get("title"), (r.get("company") or {}).get("display_name"),
                          (r.get("location") or {}).get("display_name"), r.get("redirect_url"),
                          r.get("description"), parse_dt(r.get("created")),
                          r.get("salary_min"), r.get("salary_max"))
            if j: jobs.append(j)
        time.sleep(1)
    if errors == len(config.SEARCH_CITIES):
        raise RuntimeError("Adzuna: saari cities fail")
    return jobs

# ---------------- Jooble (free API key) ----------------
def fetch_jooble():
    key = os.getenv("JOOBLE_API_KEY")
    if not key:
        raise SkipSource("Jooble key missing")
    jobs, errors, total = [], 0, 0
    for city in config.SEARCH_CITIES:
        for kw in config.JOOBLE_KEYWORDS:
            total += 1
            try:
                data = http_json("POST", f"https://jooble.org/api/{key}",
                                 json={"keywords": kw, "location": city, "page": 1})
            except Exception:
                errors += 1; continue
            for r in data.get("jobs", []):
                j = build_job("Jooble", r.get("title"), r.get("company"), r.get("location"),
                              r.get("link"), r.get("snippet"), parse_dt(r.get("updated")),
                              salary_text=r.get("salary"))
                if j: jobs.append(j)
            time.sleep(0.5)
    if total and errors == total:
        raise RuntimeError("Jooble: saari calls fail")
    return jobs

# ---------------- Greenhouse (company boards, free, no key) ----------------
def fetch_greenhouse():
    jobs, ok = [], 0
    for slug in config.GREENHOUSE_BOARDS:
        try:
            data = http_json("GET", f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
                             params={"content": "true"})
            ok += 1
        except Exception:
            continue
        for r in data.get("jobs", []):
            j = build_job(f"Careers:{slug}", r.get("title"), slug.title(),
                          (r.get("location") or {}).get("name"), r.get("absolute_url"),
                          r.get("content"), parse_dt(r.get("updated_at")))
            if j: jobs.append(j)
    if config.GREENHOUSE_BOARDS and ok == 0:
        raise RuntimeError("Greenhouse: koi board nahi chala")
    return jobs

# ---------------- Lever (company boards, free, no key) ----------------
def fetch_lever():
    jobs, ok = [], 0
    for slug in config.LEVER_COMPANIES:
        try:
            data = http_json("GET", f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"})
            ok += 1
        except Exception:
            continue
        for r in data if isinstance(data, list) else []:
            j = build_job(f"Careers:{slug}", r.get("text"), slug.title(),
                          (r.get("categories") or {}).get("location"), r.get("hostedUrl"),
                          r.get("descriptionPlain"), parse_dt(r.get("createdAt")))
            if j: jobs.append(j)
    if config.LEVER_COMPANIES and ok == 0:
        raise RuntimeError("Lever: koi company nahi chali")
    return jobs

# (name, function, minimum interval in minutes)
SOURCES = [
    ("greenhouse", fetch_greenhouse, 15),
    ("lever",      fetch_lever,      15),
    ("adzuna",     fetch_adzuna,     30),
    ("jooble",     fetch_jooble,     60),
]
