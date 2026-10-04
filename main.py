import os

def load_env(path=".env"):
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if not os.path.exists(p):
        return
    for line in open(p, encoding="utf-8-sig"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split(" #")[0].strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)

load_env()

import sys, logging, time
from datetime import timedelta
import config, db, notifier
from common import utcnow, matches
from sources import SOURCES, SkipSource

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("jobalert")

def run():
    conn = db.get_conn()
    db.init_db(conn)
    new_jobs = []

    for name, fn, interval in SOURCES:
        if not db.should_run(conn, name, interval):
            log.info("%s: abhi due nahi, skip", name); continue
        try:
            jobs = fn()
        except SkipSource as e:
            log.warning("%s skipped: %s", name, e); continue
        except Exception as e:
            fails = db.record_state(conn, name, False, err=str(e))
            log.error("%s FAILED (%s) fail_count=%s", name, e, fails)
            if fails == 3:
                try: notifier.send_text(f"⚠️ <b>Source down:</b> {name} lagatar 3 baar fail hua.\n{str(e)[:200]}")
                except Exception: pass
            continue
        added = 0
        for j in jobs:
            if db.insert_job(conn, j):
                new_jobs.append(j); added += 1
        db.record_state(conn, name, True, len(jobs))
        log.info("%s: %s relevant, %s nayi", name, len(jobs), added)

    cutoff = utcnow() - timedelta(hours=config.MAX_AGE_HOURS)
    db.expire_old(conn, cutoff)
    settings = db.get_alert_settings(conn)
    sent = []
    if settings.get("enabled", True):
        cand = [j for j in db.fetch_unnotified(conn, cutoff) if matches(j, settings)]
        limit = int(settings.get("max_per_run", config.MAX_ALERTS_PER_RUN))
        log.info("Alert filter: %s matching jobs, max %s bhejunga", len(cand), limit)
        for j in cand[:limit]:
            try:
                notifier.send_job(j); sent.append(j["job_hash"]); time.sleep(1)
            except Exception as e:
                log.error("Telegram fail: %s", e); break
        db.mark_notified(conn, sent)
    else:
        log.info("Alerts paused (dashboard se band kiye gaye)")
    log.info("Done. nayi=%s alerts=%s", len(new_jobs), len(sent))

if __name__ == "__main__":
    if "--test-telegram" in sys.argv:
        notifier.send_text("✅ Job Alert Bot connected! Telegram setup sahi hai.")
        print("Test message bhej diya")
    else:
        run()
