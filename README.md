# Job Alert System - Phase 1 (100% free)

Flow: Free APIs -> filter + dedupe -> MySQL -> Telegram instant alert -> GitHub Actions har 15 min.

## Setup (sab free, ~25 min)

### 1. MySQL (free cloud)
- **TiDB Cloud Serverless** (MySQL-compatible, free tier): tidbcloud.com par signup -> Cluster banao -> Connect -> host, port, user, password copy karo. Database name `jobs_db` banao (SQL editor me `CREATE DATABASE jobs_db;`).
- Alternative: Aiven free MySQL. Dono me free limits signup ke time khud check kar lena.
- Tables apne aap ban jayengi.

### 2. Telegram bot
1. Telegram me **@BotFather** -> `/newbot` -> naam do -> **token** milega.
2. Apne bot ko open karke `/start` bhejo.
3. Browser me kholo: `https://api.telegram.org/bot<TOKEN>/getUpdates` -> `"chat":{"id": 123456789` ye **chat id** hai.

### 3. Free job API keys
- **Adzuna**: developer.adzuna.com -> Register -> app_id + app_key
- **Jooble**: jooble.org/api/about -> API key request (free, email pe aati hai)
(Dono optional hain, jo key daali wo source chalega. Company boards bina key ke chalte hain.)

### 4. Local test
```
pip install -r requirements.txt
cp .env.example .env     # values bharo, phir:
export $(grep -v '^#' .env | xargs)
python main.py --test-telegram    # Telegram pe message aana chahiye
python main.py                    # asli run
```

### 5. Auto-run (GitHub Actions, free)
1. GitHub pe repo banao, ye saari files push karo (**.env push mat karna**).
2. Repo -> Settings -> Secrets and variables -> Actions -> in naam se secrets daalo:
   `DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID ADZUNA_APP_ID ADZUNA_APP_KEY JOOBLE_API_KEY`
3. Actions tab -> "Job Alert" -> Run workflow (pehla test).

Notes:
- **Public repo** = unlimited free minutes. **Private repo** = 2000 min/month, to cron `*/15` ko `*/30` kar dena.
- GitHub cron kabhi 5-15 min late chalta hai (free tier ki limitation).
- 60 din repo me activity na ho to GitHub scheduled runs band kar deta hai, ek commit/manual run se wapas chalu.

## Customize
Sab `config.py` me: roles, cities, company boards, alert limit.

## Phase 2: Dashboard
```
pip install -r requirements.txt
streamlit run dashboard.py
```
Phone me use: Streamlit Community Cloud pe deploy karo (free), Secrets me same .env values daalo
(optional: DASHBOARD_PASSWORD = apna password), phir phone Chrome me "Add to Home screen".
