import re, html, hashlib
from datetime import datetime, timezone
import config

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def clean(text):
    if not text:
        return ""
    text = html.unescape(str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def parse_dt(v):
    if not v:
        return None
    try:
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v / 1000, timezone.utc).replace(tzinfo=None)
        return datetime.fromisoformat(str(v)[:19].replace("Z", ""))
    except Exception:
        return None

_ROLE_RE = [(n, re.compile(p, re.I)) for n, p in config.ROLE_PATTERNS]

def classify_role(title):
    for name, rx in _ROLE_RE:
        if rx.search(title or ""):
            return name
    return None

def normalize_city(*texts):
    t = " ".join(x for x in texts if x).lower()
    for alias, city in config.CITY_ALIASES.items():
        if alias in t:
            return city
    if ("remote" in t or "work from home" in t) and "india" in t:
        return "Remote"
    return None

def parse_experience(text):
    t = (text or "").lower()
    if re.search(r"\bfresher", t):
        return 0, None
    m = re.search(r"(\d{1,2})\s*(?:\+|-|–|to)\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)", t)
    if m and int(m.group(1)) <= int(m.group(2)) <= 30:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)", t)
    if m and int(m.group(1)) <= 30:
        return int(m.group(1)), None
    return None, None

def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def build_job(source, title, company, location, url, desc="", posted_at=None,
              salary_min=None, salary_max=None, salary_text=None):
    """Raw data -> clean job dict. Irrelevant job ho to None."""
    title = clean(title)
    if not title or not url:
        return None
    role = classify_role(title)
    city = normalize_city(location, title)
    if not role or not city:
        return None
    desc = clean(desc)
    company = clean(company) or "Unknown"
    exp_min, exp_max = parse_experience(title + " " + desc[:1500])
    h = hashlib.sha1(f"{_norm(title)}|{_norm(company)}|{city}".encode()).hexdigest()
    return {
        "job_hash": h, "title": title[:250], "company": company[:200], "city": city,
        "location_raw": clean(location)[:250], "role_category": role,
        "exp_min": exp_min, "exp_max": exp_max,
        "salary_min": salary_min, "salary_max": salary_max,
        "salary_text": (clean(salary_text)[:100] if salary_text else None),
        "source": source, "url": url[:1000], "description": desc[:5000],
        "posted_at": posted_at or utcnow(),
    }
