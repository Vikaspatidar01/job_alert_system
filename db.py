import os, json
from datetime import datetime, timedelta
import pymysql, certifi
from common import utcnow

def get_conn():
    kw = dict(host=os.environ["DB_HOST"], port=int(os.getenv("DB_PORT", "3306")),
              user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
              database=os.environ["DB_NAME"], charset="utf8mb4",
              autocommit=True, connect_timeout=20)
    if os.getenv("DB_SSL", "1") == "1":
        kw["ssl"] = {"ca": certifi.where()}
    return pymysql.connect(**kw)

SCHEMA = [
"""CREATE TABLE IF NOT EXISTS jobs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_hash CHAR(40) NOT NULL,
  title VARCHAR(250) NOT NULL,
  company VARCHAR(200),
  city VARCHAR(50),
  location_raw VARCHAR(250),
  role_category VARCHAR(50),
  exp_min TINYINT NULL,
  exp_max TINYINT NULL,
  salary_min DECIMAL(12,2) NULL,
  salary_max DECIMAL(12,2) NULL,
  salary_text VARCHAR(100) NULL,
  source VARCHAR(30),
  url VARCHAR(1000),
  description TEXT,
  posted_at DATETIME,
  fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  notified TINYINT DEFAULT 0,
  status VARCHAR(20) DEFAULT 'new',
  UNIQUE KEY uq_hash (job_hash),
  KEY idx_posted (posted_at),
  KEY idx_city (city),
  KEY idx_role (role_category)
) CHARACTER SET utf8mb4""",
"""CREATE TABLE IF NOT EXISTS app_settings (
  skey VARCHAR(50) PRIMARY KEY,
  svalue TEXT
) CHARACTER SET utf8mb4""",
"""CREATE TABLE IF NOT EXISTS source_state (
  source VARCHAR(30) PRIMARY KEY,
  last_run DATETIME,
  last_ok TINYINT,
  last_count INT DEFAULT 0,
  fail_count INT DEFAULT 0,
  last_error VARCHAR(500) NULL
) CHARACTER SET utf8mb4""",
]

def init_db(conn):
    with conn.cursor() as c:
        for s in SCHEMA:
            c.execute(s)

_INSERT = """INSERT IGNORE INTO jobs
 (job_hash,title,company,city,location_raw,role_category,exp_min,exp_max,salary_min,
  salary_max,salary_text,source,url,description,posted_at)
 VALUES (%(job_hash)s,%(title)s,%(company)s,%(city)s,%(location_raw)s,%(role_category)s,
  %(exp_min)s,%(exp_max)s,%(salary_min)s,%(salary_max)s,%(salary_text)s,%(source)s,
  %(url)s,%(description)s,%(posted_at)s)"""

def insert_job(conn, job):
    """True = nayi job. False = pehle se hai (duplicate)."""
    with conn.cursor() as c:
        c.execute(_INSERT, job)
        return c.rowcount == 1

def mark_notified(conn, hashes):
    if not hashes:
        return
    with conn.cursor() as c:
        c.executemany("UPDATE jobs SET notified=1 WHERE job_hash=%s", [(h,) for h in hashes])

def should_run(conn, source, interval_min):
    if interval_min <= 0:
        return True
    with conn.cursor() as c:
        c.execute("SELECT last_run FROM source_state WHERE source=%s", (source,))
        row = c.fetchone()
    return not row or not row[0] or utcnow() - row[0] >= timedelta(minutes=interval_min - 1)

def record_state(conn, source, ok, count=0, err=None):
    """Returns consecutive fail count."""
    now = utcnow()
    with conn.cursor() as c:
        if ok:
            c.execute("""INSERT INTO source_state (source,last_run,last_ok,last_count,fail_count,last_error)
              VALUES (%s,%s,1,%s,0,NULL) ON DUPLICATE KEY UPDATE last_run=VALUES(last_run),
              last_ok=1,last_count=VALUES(last_count),fail_count=0,last_error=NULL""", (source, now, count))
            return 0
        c.execute("""INSERT INTO source_state (source,last_run,last_ok,last_count,fail_count,last_error)
          VALUES (%s,%s,0,0,1,%s) ON DUPLICATE KEY UPDATE last_run=VALUES(last_run),
          last_ok=0,fail_count=fail_count+1,last_error=VALUES(last_error)""", (source, now, (err or "")[:500]))
        c.execute("SELECT fail_count FROM source_state WHERE source=%s", (source,))
        return c.fetchone()[0]


def get_alert_settings(conn):
    with conn.cursor() as c:
        c.execute("SELECT svalue FROM app_settings WHERE skey='alert_filters'")
        row = c.fetchone()
    try:
        return json.loads(row[0]) if row and row[0] else {}
    except Exception:
        return {}

def save_alert_settings(conn, settings):
    with conn.cursor() as c:
        c.execute("""INSERT INTO app_settings (skey,svalue) VALUES ('alert_filters',%s)
                     ON DUPLICATE KEY UPDATE svalue=VALUES(svalue)""", (json.dumps(settings),))

def fetch_unnotified(conn, cutoff, limit=300):
    with conn.cursor(pymysql.cursors.DictCursor) as c:
        c.execute("""SELECT job_hash,title,company,city,role_category,exp_min,exp_max,salary_min,
                     salary_max,salary_text,source,url,posted_at FROM jobs
                     WHERE notified=0 AND posted_at >= %s AND status IN ('new','saved')
                     ORDER BY posted_at DESC LIMIT %s""", (cutoff, limit))
        return c.fetchall()

def expire_old(conn, cutoff):
    with conn.cursor() as c:
        c.execute("UPDATE jobs SET notified=1 WHERE notified=0 AND posted_at < %s", (cutoff,))
