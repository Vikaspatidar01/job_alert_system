import os, time, html
import requests
from common import utcnow

def _api(method, payload):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or not os.getenv("TELEGRAM_CHAT_ID"):
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID set nahi hai")
    r = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=payload, timeout=20)
    if r.status_code == 429:
        time.sleep(int(r.json().get("parameters", {}).get("retry_after", 5)) + 1)
        r = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=payload, timeout=20)
    r.raise_for_status()

def send_text(text):
    _api("sendMessage", {"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text,
                         "parse_mode": "HTML", "disable_web_page_preview": True})

def _ago(dt):
    m = max(0, int((utcnow() - dt).total_seconds() // 60))
    if m < 60: return f"{m} min pehle"
    if m < 1440: return f"{m // 60} ghante pehle"
    return f"{m // 1440} din pehle"

def _exp(j):
    if j["exp_min"] is None: return "Not mentioned"
    if j["exp_max"]: return f'{j["exp_min"]}-{j["exp_max"]} yrs'
    return "Fresher" if j["exp_min"] == 0 else f'{j["exp_min"]}+ yrs'

def _salary(j):
    if j.get("salary_text"): return j["salary_text"]
    if j.get("salary_min"):
        lo = f'₹{int(j["salary_min"]):,}'
        return lo if not j.get("salary_max") else f'{lo} - ₹{int(j["salary_max"]):,}'
    return "Not mentioned"

def send_job(j):
    e = html.escape
    text = (f"🆕 <b>{e(j['title'])}</b>\n"
            f"🏢 {e(j['company'])}\n📍 {e(j['city'])}   💼 {e(j['role_category'])}\n"
            f"🧑‍💻 Exp: {_exp(j)}\n💰 {e(_salary(j))}\n"
            f"🕒 {_ago(j['posted_at'])}   🔎 {e(j['source'])}")
    _api("sendMessage", {"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": [[{"text": "✅ Apply Now", "url": j["url"]}]]}})
