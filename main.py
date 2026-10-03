import sys, logging
from datetime import timedelta
import config, db, notifier
from common import utcnow
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
    fresh = sorted([j for j in new_jobs if j["posted_at"] >= cutoff],
                   key=lambda j: j["posted_at"], reverse=True)
    stale = [j for j in new_jobs if j["posted_at"] < cutoff]
    db.mark_notified(conn, [j["job_hash"] for j in stale])  # purani jobs ka alert nahi

    to_send, rest = fresh[:config.MAX_ALERTS_PER_RUN], fresh[config.MAX_ALERTS_PER_RUN:]
    sent = []
    for j in to_send:
        try:
            notifier.send_job(j); sent.append(j["job_hash"])
            import time; time.sleep(1)
        except Exception as e:
            log.error("Telegram fail: %s", e); break
    db.mark_notified(conn, sent)
    if rest and len(sent) == len(to_send):
        try:
            notifier.send_text(f"📋 Aur <b>{len(rest)}</b> nayi jobs mili hain. Dashboard me dekho.")
            db.mark_notified(conn, [j["job_hash"] for j in rest])
        except Exception as e:
            log.error("Summary fail: %s", e)
    log.info("Done. nayi=%s alerts=%s", len(new_jobs), len(sent))

if __name__ == "__main__":
    if "--test-telegram" in sys.argv:
        notifier.send_text("✅ Job Alert Bot connected! Telegram setup sahi hai.")
        print("Test message bhej diya")
    else:
        run()
