import os
from datetime import timedelta
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Job Radar", page_icon="📡", layout="wide")

# ---------- config / secrets ----------
def _load_env():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8-sig"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.split(" #")[0].strip().strip('"').strip("'"))
    try:  # Streamlit Cloud secrets
        for k in st.secrets:
            if isinstance(st.secrets[k], str):
                os.environ.setdefault(k, st.secrets[k])
    except Exception:
        pass
_load_env()

import db
from common import utcnow

# ---------- optional password gate ----------
pw = os.getenv("DASHBOARD_PASSWORD")
if pw and st.session_state.get("ok") != True:
    entered = st.text_input("🔒 Password", type="password")
    if entered == pw:
        st.session_state["ok"] = True
        st.rerun()
    st.stop()

# ---------- styling ----------
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; max-width: 1250px;}
.kpi {background: linear-gradient(135deg,#1c2333,#222b42); border:1px solid #2d3750;
      border-radius:14px; padding:14px 18px;}
.kpi .v {font-size:1.9rem; font-weight:700; color:#fff; line-height:1.1;}
.kpi .l {font-size:.8rem; color:#9aa7c7; text-transform:uppercase; letter-spacing:.06em;}
.chip {display:inline-block; padding:2px 10px; margin:2px 6px 2px 0; border-radius:999px;
       background:#26304a; color:#cfd8f3; font-size:.78rem;}
.chip.new {background:#1f6f43; color:#d6ffe8;}
.jt {font-size:1.08rem; font-weight:650; color:#fff;}
.jc {color:#9aa7c7; font-size:.92rem;}
</style>""", unsafe_allow_html=True)

# ---------- data ----------
@st.cache_data(ttl=60, show_spinner=False)
def load_jobs():
    conn = db.get_conn()
    try:
        with conn.cursor(db.pymysql.cursors.DictCursor) as c:
            c.execute("""SELECT id,title,company,city,role_category,exp_min,exp_max,salary_min,
                         salary_max,salary_text,source,url,posted_at,status FROM jobs
                         WHERE posted_at >= %s ORDER BY posted_at DESC LIMIT 5000""",
                      (utcnow() - timedelta(days=30),))
            rows = c.fetchall()
    finally:
        conn.close()
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    for col in ["exp_min", "exp_max", "salary_min", "salary_max"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["posted_at"] = pd.to_datetime(df["posted_at"])
    df["age_h"] = (pd.Timestamp(utcnow()) - df["posted_at"]).dt.total_seconds() / 3600
    return df

@st.cache_data(ttl=60, show_spinner=False)
def load_health():
    conn = db.get_conn()
    try:
        with conn.cursor(db.pymysql.cursors.DictCursor) as c:
            c.execute("SELECT source,last_run,last_ok,last_count,fail_count,last_error FROM source_state")
            return pd.DataFrame(c.fetchall())
    finally:
        conn.close()

def set_status(job_id, status):
    conn = db.get_conn()
    try:
        with conn.cursor() as c:
            c.execute("UPDATE jobs SET status=%s WHERE id=%s", (status, job_id))
    finally:
        conn.close()
    load_jobs.clear()

def exp_bucket(v):
    if pd.isna(v): return "Not mentioned"
    if v <= 1: return "0-1 yrs"
    if v <= 3: return "2-3 yrs"
    if v <= 5: return "4-5 yrs"
    return "6+ yrs"

def ago(h):
    m = int(h * 60)
    if m < 60: return f"{max(m,0)} min ago"
    if h < 24: return f"{int(h)} hr ago"
    return f"{int(h // 24)} day ago"

# ---------- header ----------
h1, h2 = st.columns([5, 1])
h1.markdown("## 📡 Job Radar &nbsp;<span style='font-size:.9rem;color:#9aa7c7'>MIS · Data Analyst · Power BI · SQL</span>", unsafe_allow_html=True)
if h2.button("🔄 Refresh", use_container_width=True):
    load_jobs.clear(); load_health.clear(); st.rerun()

try:
    df = load_jobs()
except Exception as e:
    st.error(f"Database connect nahi hua: {e}")
    st.stop()
if df.empty:
    st.info("Abhi koi job nahi mili. Pehle `python main.py` chalao.")
    st.stop()
df["exp_bucket"] = df["exp_min"].apply(exp_bucket)

# ---------- sidebar slicers ----------
sb = st.sidebar
sb.header("🎛️ Filters")
q = sb.text_input("🔍 Search (title / company)")
roles = sb.multiselect("Job role", sorted(df["role_category"].dropna().unique()))
exps = sb.multiselect("Experience", ["0-1 yrs", "2-3 yrs", "4-5 yrs", "6+ yrs", "Not mentioned"])
cities = sb.multiselect("Location", sorted(df["city"].dropna().unique()))
srcs = sb.multiselect("Source", sorted(df["source"].dropna().unique()))
posted = sb.select_slider("Posted", options=["Last 1 hr", "Last 6 hr", "Last 24 hr", "Last 3 days", "Last 7 days", "Last 30 days"],
                          value="Last 7 days")
only_sal = sb.checkbox("Sirf salary wali jobs")
status_f = sb.radio("Status", ["Active (new + saved)", "Saved", "Applied", "Hidden", "All"])

hours = {"Last 1 hr": 1, "Last 6 hr": 6, "Last 24 hr": 24, "Last 3 days": 72,
         "Last 7 days": 168, "Last 30 days": 720}[posted]
f = df[df["age_h"] <= hours]
if q: f = f[f["title"].str.contains(q, case=False, na=False) | f["company"].str.contains(q, case=False, na=False)]
if roles: f = f[f["role_category"].isin(roles)]
if exps: f = f[f["exp_bucket"].isin(exps)]
if cities: f = f[f["city"].isin(cities)]
if srcs: f = f[f["source"].isin(srcs)]
if only_sal: f = f[f["salary_min"].notna() | f["salary_text"].notna()]
f = {"Active (new + saved)": f[f["status"].isin(["new", "saved"])], "Saved": f[f["status"] == "saved"],
     "Applied": f[f["status"] == "applied"], "Hidden": f[f["status"] == "hidden"], "All": f}[status_f]

# ---------- KPIs ----------
k = st.columns(5)
def kpi(col, v, l): col.markdown(f"<div class='kpi'><div class='v'>{v}</div><div class='l'>{l}</div></div>", unsafe_allow_html=True)
kpi(k[0], len(f), "Matching jobs")
kpi(k[1], int((df["age_h"] <= 1).sum()), "Last 1 hour")
kpi(k[2], int((df["age_h"] <= 24).sum()), "Last 24 hours")
kpi(k[3], int((df["status"] == "applied").sum()), "Applied")
kpi(k[4], f["city"].nunique(), "Cities")
st.write("")

# ---------- charts ----------
t1, t2 = st.tabs(["📋 Jobs", "📊 Insights"])
with t2:
    if f.empty:
        st.info("Filter ke hisaab se data nahi hai.")
    else:
        c1, c2 = st.columns(2)
        c1.subheader("City-wise jobs"); c1.bar_chart(f["city"].value_counts())
        c2.subheader("Role-wise jobs"); c2.bar_chart(f["role_category"].value_counts())
        c3, c4 = st.columns(2)
        c3.subheader("Source-wise jobs"); c3.bar_chart(f["source"].value_counts())
        c4.subheader("Top hiring companies"); c4.bar_chart(f["company"].value_counts().head(10))
        st.subheader("Jobs per day")
        st.line_chart(f.groupby(f["posted_at"].dt.date).size())
    with st.expander("🩺 Source health"):
        try: st.dataframe(load_health(), use_container_width=True)
        except Exception as e: st.write(e)

# ---------- job cards ----------
with t1:
    st.caption(f"{len(f)} jobs mili. Latest pehle.")
    PAGE = 40
    for _, r in f.head(PAGE).iterrows():
        with st.container(border=True):
            a, b = st.columns([5, 2])
            fresh = "<span class='chip new'>NEW</span>" if r["age_h"] <= 6 and r["status"] == "new" else ""
            exp = ("Not mentioned" if pd.isna(r["exp_min"]) else
                   f"{int(r['exp_min'])}-{int(r['exp_max'])} yrs" if pd.notna(r["exp_max"]) else f"{int(r['exp_min'])}+ yrs")
            sal = r["salary_text"] if r["salary_text"] else (f"₹{int(r['salary_min']):,}" if pd.notna(r["salary_min"]) else "Salary n/a")
            a.markdown(f"<div class='jt'>{r['title']} {fresh}</div><div class='jc'>🏢 {r['company']}</div>"
                       f"<span class='chip'>📍 {r['city']}</span><span class='chip'>💼 {r['role_category']}</span>"
                       f"<span class='chip'>🧑‍💻 {exp}</span><span class='chip'>💰 {sal}</span>"
                       f"<span class='chip'>🕒 {ago(r['age_h'])}</span><span class='chip'>🔎 {r['source']}</span>",
                       unsafe_allow_html=True)
            b.link_button("✅ Apply Now", r["url"], use_container_width=True)
            s1, s2, s3 = b.columns(3)
            jid = int(r["id"])
            if s1.button("⭐", key=f"s{jid}", help="Save"): set_status(jid, "saved"); st.rerun()
            if s2.button("📨", key=f"a{jid}", help="Applied mark karo"): set_status(jid, "applied"); st.rerun()
            if s3.button("🙈", key=f"h{jid}", help="Hide"): set_status(jid, "hidden"); st.rerun()
    if len(f) > PAGE:
        st.info(f"Top {PAGE} dikh rahi hain. Filters se list chhoti karo.")
