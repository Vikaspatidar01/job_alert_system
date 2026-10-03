"""Saari settings yahin hain. Roles / cities / companies yahan se badlo."""

# Alert aur dashboard me sirf ye cities aayengi
CITY_ALIASES = {
    "indore": "Indore", "noida": "Noida", "gurgaon": "Gurgaon", "gurugram": "Gurgaon",
    "mumbai": "Mumbai", "navi mumbai": "Mumbai", "thane": "Mumbai",
    "pune": "Pune", "bengaluru": "Bengaluru", "bangalore": "Bengaluru",
    "hyderabad": "Hyderabad", "chennai": "Chennai", "delhi": "Delhi",
    "ahmedabad": "Ahmedabad", "kolkata": "Kolkata", "jaipur": "Jaipur",
    "bhopal": "Bhopal", "chandigarh": "Chandigarh", "kochi": "Kochi",
}

# API search ke liye cities (Adzuna / Jooble)
SEARCH_CITIES = ["Indore", "Noida", "Gurgaon", "Mumbai", "Pune",
                 "Bengaluru", "Hyderabad", "Chennai", "Delhi"]

# Job title is regex se match hua tabhi job rakhi jayegi (order important hai)
ROLE_PATTERNS = [
    ("Power BI Developer",   r"\bpower\s?-?bi\b"),
    ("MIS Executive",        r"\bmis\b|management information"),
    ("BI / Reporting",       r"business intelligence|\bbi\b|reporting analyst|\breporting\b"),
    ("Data Analyst",         r"\bdata\s+analy|\banalytics\b"),
    ("SQL / Database",       r"\bsql\b|\bdatabase\b|\bdba\b"),
]

# Adzuna: ek call per city. what_or = in me se koi bhi word
ADZUNA_WHAT_OR = "analyst MIS powerbi SQL BI reporting database"
# Jooble: keyword x city
JOOBLE_KEYWORDS = ["data analyst", "MIS executive", "power bi", "sql developer"]

# Company career boards (public JSON, free, no key).
# NOTE: ye sirf examples hain. Galat slug ho to 404 pe auto skip ho jata hai.
# Slug kaise nikale: careers page ka URL dekho
#   boards.greenhouse.io/<slug>   ya   jobs.lever.co/<slug>
GREENHOUSE_BOARDS = ["razorpay", "postman", "browserstack", "druva"]
LEVER_COMPANIES = ["cred", "meesho"]

MAX_AGE_HOURS = 72          # isse purani job alert nahi hogi
MAX_ALERTS_PER_RUN = 15     # ek run me max itne Telegram alerts (flood se bachne ke liye)
