"""
CareerPath Pro – Flask Application
Complete career guidance and job portal backend
Works both locally and on Vercel (serverless).
"""

import os
import json
import shutil
from datetime import datetime, timedelta
import logging
import threading
from supabase import create_client, Client
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from flask import Flask, render_template, jsonify, request, abort, session, redirect, url_for, flash, send_from_directory
from flask_cors import CORS

# ── Vercel detection ───────────────────────────────────────────────────
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))

# ── App Configuration ──────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-careerpath-key")
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# On Vercel the filesystem is read-only except /tmp
if IS_VERCEL:
    DATA_DIR = "/tmp/data"
else:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

JOBS_FILE = os.path.join(DATA_DIR, "jobs.json")
TN_JOBS_FILE = os.path.join(DATA_DIR, "tn_jobs.json")
INDIA_JOBS_FILE = os.path.join(DATA_DIR, "india_jobs.json")

# Seed file shipped with the repo (used as fallback on Vercel cold-start)
SEED_FILE = os.path.join(os.path.dirname(__file__), "data", "jobs.json")
TN_SEED_FILE = os.path.join(os.path.dirname(__file__), "data", "tn_jobs.json")
INDIA_SEED_FILE = os.path.join(os.path.dirname(__file__), "data", "india_jobs.json")

# Upload folder for resumes
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database Setup - Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yerecpvwemiuexucboee.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_eGUWBISpXTHlHQHO2LYhSA_E1bQB4ou")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Supabase Jobs Persistence (for Vercel – /tmp is ephemeral) ────────
def _supabase_save_jobs(kind: str, data: dict):
    """
    Upsert scraped jobs JSON into Supabase `scraped_data` table.
    Table schema:  kind TEXT PRIMARY KEY, data JSONB, updated_at TIMESTAMPTZ
    """
    try:
        supabase.table("scraped_data").upsert({
            "kind": kind,
            "data": data,
            "updated_at": datetime.now().isoformat(),
        }).execute()
        logger.info(f"☁️  Saved {kind} to Supabase ({len(data.get('jobs', []))} jobs)")
    except Exception as e:
        logger.warning(f"⚠️  Supabase save ({kind}) failed: {e}")


def _supabase_load_jobs(kind: str):
    """Load scraped jobs JSON from Supabase `scraped_data` table."""
    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", kind).execute()
        if resp.data:
            return resp.data[0]["data"]
    except Exception as e:
        logger.warning(f"⚠️  Supabase load ({kind}) failed: {e}")
    return None


# ── Authentication Helper ──────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ── Helpers ────────────────────────────────────────────────────────────

def load_jobs():
    """Load cached jobs from JSON file, falling back to Supabase then seed on Vercel."""
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE, "r") as f:
            return json.load(f)
    # On Vercel: try Supabase first (persisted from last scrape)
    if IS_VERCEL:
        sb_data = _supabase_load_jobs("jobs")
        if sb_data:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(JOBS_FILE, "w") as f:
                json.dump(sb_data, f)
            logger.info("☁️  Loaded jobs from Supabase → /tmp")
            return sb_data
        # Fallback to seed file
        if os.path.exists(SEED_FILE):
            os.makedirs(DATA_DIR, exist_ok=True)
            shutil.copy2(SEED_FILE, JOBS_FILE)
            logger.info("📦 Copied seed jobs.json to /tmp for Vercel cold-start")
            with open(JOBS_FILE, "r") as f:
                return json.load(f)
    return {"jobs": [], "last_updated": None}


def load_tn_jobs():
    """Load Tamil Nadu & Pondicherry specific jobs."""
    if os.path.exists(TN_JOBS_FILE):
        with open(TN_JOBS_FILE, "r") as f:
            return json.load(f)
    if IS_VERCEL:
        sb_data = _supabase_load_jobs("tn_jobs")
        if sb_data:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(TN_JOBS_FILE, "w") as f:
                json.dump(sb_data, f)
            logger.info("☁️  Loaded TN jobs from Supabase → /tmp")
            return sb_data
        if os.path.exists(TN_SEED_FILE):
            os.makedirs(DATA_DIR, exist_ok=True)
            shutil.copy2(TN_SEED_FILE, TN_JOBS_FILE)
            logger.info("📦 Copied TN seed to /tmp")
            with open(TN_JOBS_FILE, "r") as f:
                return json.load(f)
    return {"jobs": [], "last_updated": None, "region": "Tamil Nadu & Pondicherry"}


def save_tn_jobs(data):
    """Persist Tamil Nadu jobs to JSON file (+ Supabase on Vercel)."""
    with open(TN_JOBS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    if IS_VERCEL:
        _supabase_save_jobs("tn_jobs", data)


def load_india_jobs():
    """Load All-India jobs from JSON file."""
    if os.path.exists(INDIA_JOBS_FILE):
        with open(INDIA_JOBS_FILE, "r") as f:
            return json.load(f)
    if IS_VERCEL:
        sb_data = _supabase_load_jobs("india_jobs")
        if sb_data:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(INDIA_JOBS_FILE, "w") as f:
                json.dump(sb_data, f)
            logger.info("☁️  Loaded India jobs from Supabase → /tmp")
            return sb_data
        if os.path.exists(INDIA_SEED_FILE):
            os.makedirs(DATA_DIR, exist_ok=True)
            shutil.copy2(INDIA_SEED_FILE, INDIA_JOBS_FILE)
            logger.info("📦 Copied India seed to /tmp")
            with open(INDIA_JOBS_FILE, "r") as f:
                return json.load(f)
    return {"jobs": [], "last_updated": None, "region": "India"}


def save_india_jobs(data):
    """Persist All-India jobs to JSON file (+ Supabase on Vercel)."""
    with open(INDIA_JOBS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    if IS_VERCEL:
        _supabase_save_jobs("india_jobs", data)


def save_jobs(data):
    """Persist jobs to JSON file (+ Supabase on Vercel)."""
    with open(JOBS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    if IS_VERCEL:
        _supabase_save_jobs("jobs", data)


def refresh_jobs():
    """Run the scraper and save new results (lazy-imports scraper)."""
    logger.info("🔄 Refreshing job listings …")
    try:
        from scraper.job_scraper import JobScraper  # lazy import
        scraper = JobScraper()

        # On Vercel: use fast API-only scraper to stay within timeout
        if IS_VERCEL:
            jobs = scraper.scrape_fast()
            logger.info(f"⚡ Vercel fast-scrape: {len(jobs)} jobs")
        else:
            jobs = scraper.scrape_all()

        data = {
            "jobs": jobs,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_jobs(data)
        logger.info(f"✅ Saved {len(jobs)} jobs at {data['last_updated']}")

        # On Vercel, TN/India scrapers run via separate cron endpoints
        if not IS_VERCEL:
            # Run Tamil Nadu specific scraper
            try:
                tn_count = refresh_tn_jobs()
                logger.info(f"✅ TN scraper: {tn_count} jobs")
            except Exception as e:
                logger.warning(f"⚠️  TN scraper skipped: {e}")

            # Run All-India mega scraper
            try:
                india_count = refresh_india_jobs()
                logger.info(f"✅ India scraper: {india_count} jobs")
            except Exception as e:
                logger.warning(f"⚠️  India scraper skipped: {e}")

        # Merge TN jobs into main jobs list (avoid duplicates)
        if not IS_VERCEL:
            try:
                tn_data = load_tn_jobs()
                tn_jobs = tn_data.get("jobs", [])
                existing_keys = set()
                for j in jobs:
                    key = f"{j.get('title','')}-{j.get('company','')}-{j.get('location','')}".lower()
                    existing_keys.add(key)
                new_tn = []
                for j in tn_jobs:
                    key = f"{j.get('title','')}-{j.get('company','')}-{j.get('location','')}".lower()
                    if key not in existing_keys:
                        existing_keys.add(key)
                        new_tn.append(j)
                if new_tn:
                    # Re-assign IDs for merged list
                    merged = jobs + new_tn
                    for i, j in enumerate(merged):
                        j["id"] = i + 1
                    data["jobs"] = merged
                    data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    save_jobs(data)
                    logger.info(f"✅ Merged {len(new_tn)} TN jobs → total {len(merged)}")
            except Exception as e:
                logger.warning(f"⚠️  TN merge skipped: {e}")

        # Run trend analysis after scrape (skip on Vercel – too slow)
        if not IS_VERCEL:
            try:
                from scraper.trend_analyzer import TrendAnalyzer
                analyzer = TrendAnalyzer(DATA_DIR)
                analyzer.analyze(data.get("jobs", jobs))
                logger.info("📊 Trend analysis complete")
            except Exception as e:
                logger.warning(f"⚠️  Trend analysis skipped: {e}")

        return len(data.get("jobs", jobs))
    except Exception as e:
        logger.error(f"❌ Scraper error: {e}")
        return 0


def refresh_tn_jobs():
    """Run the Tamil Nadu & Pondicherry dedicated scraper."""
    logger.info("🔄 Refreshing Tamil Nadu & Pondicherry jobs …")
    try:
        from scraper.tamilnadu_scraper import TamilNaduJobScraper
        tn_scraper = TamilNaduJobScraper()
        tn_jobs = tn_scraper.scrape_all()
        # Assign IDs
        for i, j in enumerate(tn_jobs):
            j["id"] = i + 1
        tn_data = {
            "jobs": tn_jobs,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "region": "Tamil Nadu & Pondicherry",
            "total": len(tn_jobs),
        }
        save_tn_jobs(tn_data)
        logger.info(f"✅ Saved {len(tn_jobs)} TN jobs")
        return len(tn_jobs)
    except Exception as e:
        logger.error(f"❌ TN Scraper error: {e}")
        return 0


def refresh_india_jobs():
    """Run the All-India mega scraper with AI organization."""
    logger.info("🇮🇳 Refreshing All-India job listings …")
    try:
        from scraper.india_scraper import IndiaJobScraper, CAREER_URLS
        import urllib.parse as _urlparse
        india_scraper = IndiaJobScraper()
        india_jobs = india_scraper.scrape_all(min_jobs=500)
        # Assign IDs & fix any generic career page URLs → use real portals
        for i, j in enumerate(india_jobs):
            j["id"] = i + 1
            url = j.get("apply_url", "")
            company = j.get("company", "")
            if url and (url.endswith("/jobs") or url.endswith("/careers")):
                # Use real career portal if available, else Naukri search
                if company in CAREER_URLS:
                    j["apply_url"] = CAREER_URLS[company]
                else:
                    title = j.get("title", "")
                    city = j.get("location_city", "")
                    q = _urlparse.quote_plus(f"{title} {company}")
                    loc = city.lower().replace(" ", "-") if city else "india"
                    j["apply_url"] = f"https://www.naukri.com/{_urlparse.quote(title.lower().replace(' ', '-'))}-jobs-in-{_urlparse.quote(loc)}?k={q}"
        india_data = {
            "jobs": india_jobs,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "region": "India",
            "total": len(india_jobs),
            "states_covered": len(set(j.get("location_state", "") for j in india_jobs if j.get("location_state"))),
            "cities_covered": len(set(j.get("location_city", "") for j in india_jobs if j.get("location_city"))),
        }
        save_india_jobs(india_data)
        logger.info(f"✅ Saved {len(india_jobs)} All-India jobs")
        return len(india_jobs)
    except Exception as e:
        logger.error(f"❌ India Scraper error: {e}")
        return 0


# ── Scheduler state tracking ───────────────────────────────────────────
scheduler_info = {
    "active": False,
    "type": None,           # "apscheduler" or "threading"
    "last_refresh": None,
    "last_refresh_count": 0,
    "next_run": None,
    "refresh_history": [],   # last 10 refreshes
    "errors": [],            # last 5 errors
    "started_at": None,
}

REFRESH_INTERVAL_HOURS = 12
STALE_THRESHOLD_HOURS = 24
MAX_HISTORY = 10
MAX_ERRORS = 5


def tracked_refresh():
    """Wrapper around refresh_jobs that tracks timing & history."""
    start = datetime.now()
    logger.info(f"⏰ Auto-refresh triggered at {start.strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        count = refresh_jobs()
        end = datetime.now()
        elapsed = (end - start).total_seconds()
        entry = {
            "time": end.strftime("%Y-%m-%d %H:%M:%S"),
            "jobs": count,
            "duration_seconds": round(elapsed, 1),
            "status": "success",
        }
        scheduler_info["last_refresh"] = end.strftime("%Y-%m-%d %H:%M:%S")
        scheduler_info["last_refresh_count"] = count
        scheduler_info["refresh_history"].append(entry)
        scheduler_info["refresh_history"] = scheduler_info["refresh_history"][-MAX_HISTORY:]
        logger.info(f"✅ Auto-refresh done: {count} jobs in {elapsed:.1f}s")
        return count
    except Exception as e:
        err_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "error": str(e),
        }
        scheduler_info["errors"].append(err_entry)
        scheduler_info["errors"] = scheduler_info["errors"][-MAX_ERRORS:]
        logger.error(f"❌ Auto-refresh failed: {e}")
        return 0


def is_data_stale():
    """Check if job data is older than STALE_THRESHOLD_HOURS."""
    try:
        data = load_jobs()
        last_updated = data.get("last_updated")
        if not last_updated:
            return True
        last_dt = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")
        age_hours = (datetime.now() - last_dt).total_seconds() / 3600
        return age_hours >= STALE_THRESHOLD_HOURS
    except Exception:
        return True


# ── Threading-based fallback scheduler ─────────────────────────────────
class SimpleScheduler:
    """Lightweight repeating-timer scheduler (zero dependencies)."""

    def __init__(self, interval_hours=12):
        self.interval = interval_hours * 3600
        self._timer = None
        self._running = False

    def _run(self):
        if self._running:
            tracked_refresh()
            self._schedule_next()

    def _schedule_next(self):
        self._timer = threading.Timer(self.interval, self._run)
        self._timer.daemon = True
        self._timer.start()
        scheduler_info["next_run"] = (
            datetime.now() + timedelta(seconds=self.interval)
        ).strftime("%Y-%m-%d %H:%M:%S")

    def start(self):
        self._running = True
        self._schedule_next()

    def stop(self):
        self._running = False
        if self._timer:
            self._timer.cancel()


# ── Start scheduler – local dev only (Vercel uses cron endpoint) ──────
if not IS_VERCEL:
    _scheduler_started = False

    # 1) Try APScheduler (preferred)
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(
            tracked_refresh, "interval",
            hours=REFRESH_INTERVAL_HOURS,
            id="refresh_interval",
            next_run_time=datetime.now() + timedelta(minutes=5),  # first run 5 min after boot
        )
        scheduler.add_job(
            tracked_refresh, "cron",
            hour=6, minute=0,
            id="daily_6am",
        )
        scheduler.start()
        _scheduler_started = True
        scheduler_info["active"] = True
        scheduler_info["type"] = "apscheduler"
        scheduler_info["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Track next run time
        job = scheduler.get_job("refresh_interval")
        if job and job.next_run_time:
            scheduler_info["next_run"] = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"🗓️  APScheduler running – every {REFRESH_INTERVAL_HOURS}h + daily 6 AM")
    except ImportError:
        logger.warning("⚠️  APScheduler not installed – trying fallback scheduler")
    except Exception as e:
        logger.warning(f"⚠️  APScheduler error: {e} – trying fallback scheduler")

    # 2) Fallback to simple threading scheduler
    if not _scheduler_started:
        try:
            _simple = SimpleScheduler(interval_hours=REFRESH_INTERVAL_HOURS)
            _simple.start()
            _scheduler_started = True
            scheduler_info["active"] = True
            scheduler_info["type"] = "threading"
            scheduler_info["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"🗓️  Simple scheduler running – every {REFRESH_INTERVAL_HOURS}h")
        except Exception as e:
            logger.error(f"❌ All schedulers failed: {e}")

    # 3) Startup freshness check – refresh immediately if data is stale
    if is_data_stale():
        logger.info("📦 Data is stale (>24h) or missing – refreshing on startup …")
        threading.Thread(target=tracked_refresh, daemon=True).start()
    else:
        data = load_jobs()
        logger.info(f"📦 Data is fresh – {len(data.get('jobs', []))} jobs, last updated {data.get('last_updated', 'N/A')}")


# ═══════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/")
def home():
    data = load_jobs()
    jobs = data.get("jobs", [])
    featured = jobs[:6]
    # Stats for the homepage
    companies = set(j.get("company", "") for j in jobs)
    cities = set(j.get("location_city", "") for j in jobs if j.get("location_city"))
    return render_template(
        "index.html",
        featured_jobs=featured,
        last_updated=data.get("last_updated"),
        total_jobs=len(jobs),
        total_companies=len(companies),
        total_cities=len(cities),
    )


@app.route("/jobs")
def jobs_page():
    return render_template("jobs.html")


@app.route("/job/<job_id>")
def job_detail(job_id):
    """Job detail page — searches main, India, and TN jobs by ID.
    Accepts optional ?source= param to narrow the search."""
    # Normalise: try int conversion for files that use numeric IDs
    try:
        job_id_int = int(job_id)
    except (ValueError, TypeError):
        job_id_int = None

    source_hint = request.args.get("source", "").lower()

    # Search order based on source hint
    search_order = []
    if source_hint == "india":
        search_order = [(load_india_jobs, "india"), (load_jobs, "main"), (load_tn_jobs, "tamilnadu")]
    elif source_hint == "tamilnadu":
        search_order = [(load_tn_jobs, "tamilnadu"), (load_jobs, "main"), (load_india_jobs, "india")]
    else:
        search_order = [(load_jobs, "main"), (load_india_jobs, "india"), (load_tn_jobs, "tamilnadu")]

    job = None
    for loader, src_name in search_order:
        data = loader()
        jobs = data.get("jobs", [])
        job = next((j for j in jobs if str(j.get("id")) == str(job_id) or j.get("id") == job_id_int), None)
        if job:
            job["_source_db"] = src_name
            break

    if not job:
        abort(404)
    return render_template("job_detail.html", job=job)


@app.route("/career-guidance")
def career_guidance():
    return render_template("career_guidance.html")


@app.route("/resume-builder")
def resume_builder():
    return render_template("resume_builder.html")


@app.route("/student-dashboard")
@login_required
def student_dashboard():
    # Fetch user details
    response = supabase.table("users").select("*").eq("id", session['user_id']).execute()
    if not response.data:
        session.clear()
        return redirect(url_for('login'))
        
    user = response.data[0]
    
    # Parse JSON arrays if present
    try:
        user['skills_list'] = json.loads(user.get('skills') or '[]')
    except:
        user['skills_list'] = [s.strip() for s in str(user.get('skills', '')).split(',') if s.strip()]
        
    try:
        user['interests_list'] = json.loads(user.get('interests') or '[]')
    except:
        user['interests_list'] = [i.strip() for i in str(user.get('interests', '')).split(',') if i.strip()]

    return render_template("student_dashboard.html", user=user)


# ═══════════════════════════════════════════════════════════════════════
# AUTHENTICATION ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        response = supabase.table("users").select("*").eq("email", email).execute()
        
        if response.data and check_password_hash(response.data[0]['password_hash'], password):
            user = response.data[0]
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            
            # Check if onboarding is complete
            if not user.get('interests'):
                return redirect(url_for('onboarding'))
            return redirect(url_for('student_dashboard'))
        else:
            return render_template("login.html", error="Invalid email or password.")
            
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        
        # Check if email exists
        existing = supabase.table("users").select("id").eq("email", email).execute()
        if existing.data:
            return render_template("signup.html", error="Email already exists.")
            
        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        try:
            new_user = supabase.table("users").insert({
                "name": name,
                "email": email,
                "password_hash": hashed_pw,
                "skills": "",
                "interests": "",
                "experience_level": ""
            }).execute()
            
            if new_user.data:
                user = new_user.data[0]
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                return redirect(url_for('onboarding'))
            else:
                return render_template("signup.html", error="Failed to create account.")
                
        except Exception as e:
            return render_template("signup.html", error=f"Database error: {str(e)}")
            
    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    if request.method == "POST":
        skills = request.form.get("skills")
        interests = request.form.getlist("interests")
        experience = request.form.get("experience")
        
        try:
            supabase.table("users").update({
                "skills": skills,
                "interests": json.dumps(interests),
                "experience_level": experience
            }).eq("id", session['user_id']).execute()
            
            return redirect(url_for('student_dashboard'))
        except Exception as e:
            logger.error(f"Onboarding error: {e}")
            return render_template("onboarding.html", error="Failed to save profile.")
        
    return render_template("onboarding.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/blog")
def blog():
    return render_template("blog.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


# ═══════════════════════════════════════════════════════════════════════
# PROFILE, RESUME, ALERTS, BOOKMARKS, COMMENTS
# ═══════════════════════════════════════════════════════════════════════

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    uid = session['user_id']
    response = supabase.table("users").select("*").eq("id", uid).execute()
    if not response.data:
        session.clear()
        return redirect(url_for('login'))
    user = response.data[0]

    if request.method == "POST":
        name = request.form.get("name", user['name'])
        skills = request.form.get("skills", "")
        interests = request.form.getlist("interests") or []
        experience = request.form.get("experience_level", "")
        bio = request.form.get("bio", "")
        linkedin = request.form.get("linkedin", "")
        github = request.form.get("github", "")
        phone = request.form.get("phone", "")

        update_data = {
            "name": name,
            "skills": skills,
            "interests": json.dumps(interests) if isinstance(interests, list) else interests,
            "experience_level": experience,
        }
        # Store extra fields in scraped_data (flexible storage)
        extra = {"bio": bio, "linkedin": linkedin, "github": github, "phone": phone}
        try:
            supabase.table("users").update(update_data).eq("id", uid).execute()
            supabase.table("scraped_data").upsert({
                "kind": f"user_profile_{uid}",
                "data": extra,
                "updated_at": datetime.now().isoformat(),
            }).execute()
            session['user_name'] = name
            flash("Profile updated successfully!", "success")
        except Exception as e:
            logger.error(f"Profile update error: {e}")
            flash("Failed to update profile.", "error")
        return redirect(url_for('profile'))

    # Load extra profile data
    extra = {}
    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"user_profile_{uid}").execute()
        if resp.data:
            extra = resp.data[0].get("data", {})
    except Exception:
        pass

    # Parse skills/interests
    try:
        user['skills_list'] = json.loads(user.get('skills') or '[]')
    except Exception:
        user['skills_list'] = [s.strip() for s in str(user.get('skills', '')).split(',') if s.strip()]
    try:
        user['interests_list'] = json.loads(user.get('interests') or '[]')
    except Exception:
        user['interests_list'] = [i.strip() for i in str(user.get('interests', '')).split(',') if i.strip()]

    # Resume info
    resume_info = None
    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"user_resume_{uid}").execute()
        if resp.data:
            resume_info = resp.data[0].get("data", {})
    except Exception:
        pass

    # Stats
    stats = {"applications": 0, "saved": 0, "profile_views": 0}
    try:
        saved = supabase.table("saved_jobs").select("id", count="exact").eq("user_id", uid).execute()
        stats["saved"] = saved.count if saved.count is not None else len(saved.data or [])
    except Exception:
        pass
    try:
        apps = _get_user_applications(uid)
        stats["applications"] = len(apps)
    except Exception:
        pass
    try:
        views = _get_profile_views(uid)
        stats["profile_views"] = views.get("count", 0)
    except Exception:
        pass

    return render_template("profile.html", user=user, extra=extra, resume_info=resume_info, stats=stats)


@app.route("/api/upload-resume", methods=["POST"])
@login_required
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files['resume']
    if f.filename == '':
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "Only PDF, DOC, DOCX files allowed"}), 400

    uid = session['user_id']
    filename = secure_filename(f"{uid}_{f.filename}")
    filepath = os.path.join(UPLOAD_DIR, filename)
    f.save(filepath)

    resume_data = {
        "filename": f.filename,
        "stored_as": filename,
        "uploaded_at": datetime.now().isoformat(),
        "size": os.path.getsize(filepath),
    }
    try:
        supabase.table("scraped_data").upsert({
            "kind": f"user_resume_{uid}",
            "data": resume_data,
            "updated_at": datetime.now().isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Resume meta save error: {e}")

    return jsonify({"status": "success", "filename": f.filename})


@app.route("/api/delete-resume", methods=["POST"])
@login_required
def delete_resume():
    uid = session['user_id']
    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"user_resume_{uid}").execute()
        if resp.data:
            stored = resp.data[0]["data"].get("stored_as", "")
            filepath = os.path.join(UPLOAD_DIR, stored)
            if stored and os.path.exists(filepath):
                os.remove(filepath)
            supabase.table("scraped_data").delete().eq("kind", f"user_resume_{uid}").execute()
        return jsonify({"status": "deleted"})
    except Exception as e:
        logger.error(f"Resume delete error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/toggle-alert", methods=["POST"])
@login_required
def toggle_alert():
    uid = session['user_id']
    data = request.json or {}
    keyword = data.get("keyword", "").strip()
    if not keyword:
        return jsonify({"error": "Keyword required"}), 400

    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"user_alerts_{uid}").execute()
        alerts = resp.data[0]["data"] if resp.data else []

        existing = [a for a in alerts if a.get("keyword", "").lower() == keyword.lower()]
        if existing:
            alerts = [a for a in alerts if a.get("keyword", "").lower() != keyword.lower()]
            action = "removed"
        else:
            alerts.append({"keyword": keyword, "created_at": datetime.now().isoformat(), "active": True})
            action = "added"

        supabase.table("scraped_data").upsert({
            "kind": f"user_alerts_{uid}",
            "data": alerts,
            "updated_at": datetime.now().isoformat(),
        }).execute()
        return jsonify({"status": action, "alerts": alerts})
    except Exception as e:
        logger.error(f"Alert toggle error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/alerts", methods=["GET"])
@login_required
def get_alerts():
    uid = session['user_id']
    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"user_alerts_{uid}").execute()
        alerts = resp.data[0]["data"] if resp.data else []
        return jsonify({"alerts": alerts})
    except Exception as e:
        return jsonify({"alerts": []})


@app.route("/api/bookmark-company", methods=["POST"])
@login_required
def bookmark_company():
    uid = session['user_id']
    data = request.json or {}
    company = data.get("company", "").strip()
    if not company:
        return jsonify({"error": "Company name required"}), 400

    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"user_bookmarks_{uid}").execute()
        bookmarks = resp.data[0]["data"] if resp.data else []

        existing = [b for b in bookmarks if b.get("company", "").lower() == company.lower()]
        if existing:
            bookmarks = [b for b in bookmarks if b.get("company", "").lower() != company.lower()]
            action = "removed"
        else:
            bookmarks.append({"company": company, "created_at": datetime.now().isoformat()})
            action = "added"

        supabase.table("scraped_data").upsert({
            "kind": f"user_bookmarks_{uid}",
            "data": bookmarks,
            "updated_at": datetime.now().isoformat(),
        }).execute()
        return jsonify({"status": action, "bookmarks": bookmarks})
    except Exception as e:
        logger.error(f"Bookmark error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/bookmarked-companies", methods=["GET"])
@login_required
def get_bookmarked_companies():
    uid = session['user_id']
    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"user_bookmarks_{uid}").execute()
        bookmarks = resp.data[0]["data"] if resp.data else []
        return jsonify({"bookmarks": bookmarks})
    except Exception as e:
        return jsonify({"bookmarks": []})


@app.route("/api/job-comment", methods=["POST"])
@login_required
def post_comment():
    uid = session['user_id']
    data = request.json or {}
    job_id = str(data.get("job_id", ""))
    text = data.get("text", "").strip()
    if not job_id or not text:
        return jsonify({"error": "Job ID and comment text required"}), 400
    if len(text) > 500:
        return jsonify({"error": "Comment too long (max 500 chars)"}), 400

    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"job_comments_{job_id}").execute()
        comments = resp.data[0]["data"] if resp.data else []

        comments.append({
            "user_id": uid,
            "user_name": session.get('user_name', 'Anonymous'),
            "text": text,
            "created_at": datetime.now().isoformat(),
        })

        supabase.table("scraped_data").upsert({
            "kind": f"job_comments_{job_id}",
            "data": comments,
            "updated_at": datetime.now().isoformat(),
        }).execute()
        return jsonify({"status": "posted", "comment": comments[-1]})
    except Exception as e:
        logger.error(f"Comment error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/job-comments/<job_id>", methods=["GET"])
def get_comments(job_id):
    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"job_comments_{job_id}").execute()
        comments = resp.data[0]["data"] if resp.data else []
        return jsonify({"comments": comments})
    except Exception:
        return jsonify({"comments": []})


@app.route("/api/personalized-guidance", methods=["GET"])
@login_required
def personalized_guidance():
    uid = session['user_id']
    try:
        user_resp = supabase.table("users").select("skills,interests,experience_level").eq("id", uid).execute()
        user = user_resp.data[0] if user_resp.data else {}

        skills_raw = user.get('skills', '')
        try:
            skills = json.loads(skills_raw) if skills_raw else []
        except Exception:
            skills = [s.strip() for s in skills_raw.split(',') if s.strip()]

        interests_raw = user.get('interests', '')
        try:
            interests = json.loads(interests_raw) if interests_raw else []
        except Exception:
            interests = [i.strip() for i in interests_raw.split(',') if i.strip()]

        experience = user.get('experience_level', '')

        # Generate personalized suggestions based on user profile
        suggestions = []
        skill_set = set(s.lower() for s in skills)
        interest_set = set(i.lower() for i in interests)

        career_map = {
            'python': {'path': 'Data Science / AI / Backend', 'next': ['Machine Learning', 'Django/Flask', 'Data Engineering'], 'resources': ['Kaggle', 'fast.ai', 'CS50 AI']},
            'javascript': {'path': 'Full Stack / Frontend', 'next': ['React/Next.js', 'Node.js', 'TypeScript'], 'resources': ['freeCodeCamp', 'JavaScript.info', 'Scrimba']},
            'java': {'path': 'Enterprise / Android', 'next': ['Spring Boot', 'Microservices', 'Android Dev'], 'resources': ['Baeldung', 'NPTEL Java', 'Udemy']},
            'react': {'path': 'Frontend Engineering', 'next': ['TypeScript', 'Next.js', 'Testing'], 'resources': ['React.dev', 'Kent C. Dodds', 'Vercel Docs']},
            'machine learning': {'path': 'AI/ML Engineering', 'next': ['Deep Learning', 'NLP', 'MLOps'], 'resources': ['Andrew Ng Coursera', 'fast.ai', 'Papers With Code']},
            'data science': {'path': 'Data Analytics / ML', 'next': ['Statistics', 'SQL', 'Visualization'], 'resources': ['Kaggle Learn', 'DataCamp', 'NPTEL']},
            'cloud': {'path': 'Cloud / DevOps', 'next': ['AWS/Azure/GCP', 'Kubernetes', 'IaC'], 'resources': ['AWS Free Tier', 'KodeKloud', 'Cloud Guru']},
            'sql': {'path': 'Data Engineering / Analytics', 'next': ['Python', 'ETL Pipelines', 'BI Tools'], 'resources': ['Mode Analytics', 'SQLZoo', 'DataLemur']},
        }

        for skill in skills:
            sl = skill.lower().strip()
            for key, info in career_map.items():
                if key in sl:
                    suggestions.append({
                        'based_on': skill,
                        'career_path': info['path'],
                        'learn_next': info['next'],
                        'resources': info['resources'],
                    })
                    break

        # Job recommendations count based on skills
        all_jobs = _load_all_jobs()
        matching_jobs = 0
        for job in all_jobs:
            job_text = (json.dumps(job.get('skills', [])) + ' ' + job.get('title', '') + ' ' + job.get('description', '')).lower()
            if any(s.lower() in job_text for s in skills[:5]):
                matching_jobs += 1

        return jsonify({
            "suggestions": suggestions[:5],
            "matching_jobs": matching_jobs,
            "experience": experience,
            "skills": skills,
            "interests": interests,
        })
    except Exception as e:
        logger.error(f"Personalized guidance error: {e}")
        return jsonify({"suggestions": [], "matching_jobs": 0})


# ═══════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/jobs")
def api_jobs():
    """
    Return jobs with advanced filtering:
      ?keyword=      – title / company / category / skills (comma-sep for OR)
      ?location=     – city / state / display (fuzzy)
      ?country=      – exact country match
      ?city=         – exact city match
      ?type=         – job type (comma-sep for multiple, e.g. Full-time,Remote)
      ?experience=   – experience level (comma-sep)
      ?category=     – job category (comma-sep)
      ?source=       – source name (comma-sep)
      ?salary_min=   – minimum salary (numeric)
      ?sort=         – newest | oldest | title | company | quality
      ?page=         – pagination (default 1)
      ?per_page=     – items per page (default 50, max 500)
    """
    data = load_jobs()
    jobs = data.get("jobs", [])

    # ── Keyword search (title, company, category, skills, description) ─
    keyword = request.args.get("keyword", "").strip().lower()
    if keyword:
        # Support comma-separated keywords (OR logic)
        keywords = [k.strip() for k in keyword.split(",") if k.strip()]
        jobs = [
            j for j in jobs
            if any(
                kw in j.get("title", "").lower()
                or kw in j.get("company", "").lower()
                or kw in j.get("category", "").lower()
                or kw in j.get("industry", "").lower()
                or kw in j.get("description", "").lower()[:500]
                or any(kw in s.lower() for s in j.get("skills", []))
                for kw in keywords
            )
        ]

    # ── Location filters (hierarchical: country → city → text) ────
    country = request.args.get("country", "").strip().lower()
    city = request.args.get("city", "").strip().lower()
    location = request.args.get("location", "").strip().lower()

    if country:
        jobs = [j for j in jobs if country in j.get("location_country", "").lower()]
    if city:
        jobs = [j for j in jobs if city in j.get("location_city", "").lower()]
    if location:
        jobs = [
            j for j in jobs
            if location in j.get("location", "").lower()
            or location in j.get("location_city", "").lower()
            or location in j.get("location_state", "").lower()
            or location in j.get("location_country", "").lower()
        ]

    # ── Multi-value filters (comma-separated) ─────────────────────
    job_type = request.args.get("type", "").strip()
    experience = request.args.get("experience", "").strip()
    category = request.args.get("category", "").strip()
    source = request.args.get("source", "").strip()

    if job_type:
        type_vals = [t.strip().lower() for t in job_type.split(",") if t.strip()]
        jobs = [j for j in jobs if any(tv in j.get("type", "").lower() for tv in type_vals)]
    if experience:
        exp_vals = [e.strip().lower() for e in experience.split(",") if e.strip()]
        jobs = [j for j in jobs if any(ev in j.get("experience", "").lower() for ev in exp_vals)]
    if category:
        cat_vals = [c.strip().lower() for c in category.split(",") if c.strip()]
        jobs = [j for j in jobs if any(cv in j.get("category", "").lower() for cv in cat_vals)]
    if source:
        src_vals = [s.strip().lower() for s in source.split(",") if s.strip()]
        jobs = [j for j in jobs if any(sv in j.get("source", "").lower() for sv in src_vals)]

    # ── Salary filter ──────────────────────────────────────────────
    salary_min = request.args.get("salary_min", "").strip()
    if salary_min:
        try:
            min_val = int(salary_min)
            def parse_salary(s):
                """Extract numeric from salary string."""
                import re
                nums = re.findall(r'[\d,]+', str(s).replace(',', ''))
                return int(nums[0]) if nums else 0
            jobs = [j for j in jobs if parse_salary(j.get("salary_min", "0")) >= min_val or parse_salary(j.get("salary_max", "0")) >= min_val]
        except (ValueError, TypeError):
            pass

    # ── Sorting ────────────────────────────────────────────────────
    sort = request.args.get("sort", "newest").strip().lower()
    if sort == "newest":
        jobs.sort(key=lambda j: j.get("posted_date", ""), reverse=True)
    elif sort == "oldest":
        jobs.sort(key=lambda j: j.get("posted_date", ""))
    elif sort == "title":
        jobs.sort(key=lambda j: j.get("title", "").lower())
    elif sort == "company":
        jobs.sort(key=lambda j: j.get("company", "").lower())
    elif sort == "quality":
        jobs.sort(key=lambda j: j.get("quality_score", 0), reverse=True)

    # ── Pagination ─────────────────────────────────────────────────
    total = len(jobs)
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(500, max(1, int(request.args.get("per_page", 50))))
    start = (page - 1) * per_page
    paginated = jobs[start : start + per_page]

    # ── Build filter counts from the FULL matched set (pre-pagination) ──
    from collections import Counter
    type_counts = Counter(j.get("type", "Other") for j in jobs)
    exp_counts = Counter(j.get("experience", "Unknown") for j in jobs)
    cat_counts = Counter(j.get("category", "Other") for j in jobs)
    src_counts = Counter(j.get("source", "Unknown") for j in jobs)

    return jsonify({
        "jobs": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "last_updated": data.get("last_updated"),
        "filter_counts": {
            "types": dict(type_counts),
            "experience": dict(exp_counts),
            "categories": dict(cat_counts),
            "sources": dict(src_counts),
        },
    })


@app.route("/api/job/<int:job_id>")
def api_job_detail(job_id):
    """Return a single job by ID."""
    data = load_jobs()
    job = next((j for j in data.get("jobs", []) if j.get("id") == job_id), None)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """Manual refresh trigger."""
    count = tracked_refresh()
    return jsonify({"status": "success", "message": f"Refreshed {count} jobs", "count": count})


@app.route("/api/cron")
def api_cron():
    """
    Vercel Cron endpoint – called daily by vercel.json cron config.
    Also callable manually: GET /api/cron?secret=YOUR_SECRET
    """
    # Optional secret check
    expected = os.environ.get("CRON_SECRET", "")
    provided = request.args.get("secret", "") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if expected and provided != expected:
        return jsonify({"error": "Unauthorized"}), 401

    count = tracked_refresh()
    return jsonify({
        "status": "success",
        "jobs_scraped": count,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


def _check_cron_secret():
    """Shared secret check for cron endpoints."""
    expected = os.environ.get("CRON_SECRET", "")
    provided = request.args.get("secret", "") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if expected and provided != expected:
        return False
    return True


@app.route("/api/cron/tn")
def api_cron_tn():
    """
    Vercel Cron – Tamil Nadu & Pondicherry scraper (separate to stay within timeout).
    """
    if not _check_cron_secret():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        count = refresh_tn_jobs()
        return jsonify({
            "status": "success",
            "region": "Tamil Nadu",
            "jobs_scraped": count,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    except Exception as e:
        logger.error(f"❌ TN cron failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/cron/india")
def api_cron_india():
    """
    Vercel Cron – All-India mega scraper (separate to stay within timeout).
    """
    if not _check_cron_secret():
        return jsonify({"error": "Unauthorized"}), 401
    try:
        count = refresh_india_jobs()
        return jsonify({
            "status": "success",
            "region": "India",
            "jobs_scraped": count,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    except Exception as e:
        logger.error(f"❌ India cron failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/api/stats")
def api_stats():
    """Platform statistics."""
    data = load_jobs()
    jobs = data.get("jobs", [])
    locations = {}
    types = {}
    categories = {}
    countries = {}
    cities = {}
    sources = {}
    for j in jobs:
        loc = j.get("location", "Unknown")
        locations[loc] = locations.get(loc, 0) + 1
        t = j.get("type", "Unknown")
        types[t] = types.get(t, 0) + 1
        cat = j.get("category", "Other")
        categories[cat] = categories.get(cat, 0) + 1
        country = j.get("location_country", "Unknown")
        countries[country] = countries.get(country, 0) + 1
        city = j.get("location_city", "Unknown")
        cities[city] = cities.get(city, 0) + 1
        src = j.get("source", "Unknown")
        sources[src] = sources.get(src, 0) + 1

    return jsonify({
        "total_jobs": len(jobs),
        "locations": locations,
        "types": types,
        "categories": categories,
        "countries": countries,
        "cities": cities,
        "sources": sources,
        "last_updated": data.get("last_updated"),
    })


@app.route("/api/locations")
def api_locations():
    """Return all unique locations grouped by country for filter dropdowns."""
    data = load_jobs()
    jobs = data.get("jobs", [])
    country_cities = {}
    for j in jobs:
        country = j.get("location_country", "Other")
        city = j.get("location_city", "")
        if country not in country_cities:
            country_cities[country] = set()
        if city:
            country_cities[country].add(city)
    # Convert sets to sorted lists
    result = {k: sorted(v) for k, v in sorted(country_cities.items())}
    return jsonify(result)


@app.route("/api/autocomplete/locations")
def api_autocomplete_locations():
    """Return a flat list of all unique cities, states, countries for autocomplete."""
    # Comprehensive Indian cities – always available even without scraped jobs
    INDIAN_CITIES = [
        # Andhra Pradesh
        "Visakhapatnam", "Vijayawada", "Guntur", "Tirupati", "Rajahmundry",
        "Kakinada", "Nellore", "Amaravati",
        # Arunachal Pradesh
        "Itanagar",
        # Assam
        "Guwahati", "Dibrugarh", "Silchar",
        # Bihar
        "Patna", "Gaya", "Muzaffarpur", "Bhagalpur",
        # Chhattisgarh
        "Raipur", "Bhilai", "Bilaspur",
        # Delhi
        "Delhi NCR", "New Delhi",
        # Goa
        "Panaji", "Margao", "Vasco da Gama",
        # Gujarat
        "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar", "Bhavnagar",
        # Haryana
        "Gurugram", "Faridabad", "Karnal", "Ambala", "Hisar", "Panipat", "Rohtak",
        # Himachal Pradesh
        "Shimla", "Dharamshala", "Manali",
        # Jharkhand
        "Ranchi", "Jamshedpur", "Dhanbad", "Bokaro",
        # Karnataka
        "Bangalore", "Mysore", "Hubli", "Mangalore", "Belgaum", "Davangere",
        # Kerala
        "Kochi", "Thiruvananthapuram", "Kozhikode", "Thrissur", "Kollam",
        "Palakkad", "Kannur",
        # Madhya Pradesh
        "Indore", "Bhopal", "Jabalpur", "Gwalior", "Ujjain",
        # Maharashtra
        "Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Thane",
        "Navi Mumbai", "Solapur", "Kolhapur",
        # Manipur
        "Imphal",
        # Meghalaya
        "Shillong",
        # Mizoram
        "Aizawl",
        # Nagaland
        "Kohima", "Dimapur",
        # Odisha
        "Bhubaneswar", "Cuttack", "Rourkela",
        # Punjab
        "Chandigarh", "Ludhiana", "Amritsar", "Jalandhar", "Patiala",
        "Bathinda", "Mohali",
        # Rajasthan
        "Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner",
        # Sikkim
        "Gangtok",
        # Tamil Nadu
        "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem",
        "Tirunelveli", "Erode", "Vellore", "Thoothukudi", "Dindigul",
        "Thanjavur", "Hosur", "Nagercoil", "Kanchipuram", "Kumbakonam",
        "Karur", "Tirupur", "Sivakasi",
        # Telangana
        "Hyderabad", "Warangal", "Karimnagar", "Nizamabad",
        # Tripura
        "Agartala",
        # Uttar Pradesh
        "Noida", "Lucknow", "Greater Noida", "Kanpur", "Agra", "Varanasi",
        "Prayagraj", "Meerut", "Ghaziabad", "Bareilly",
        # Uttarakhand
        "Dehradun", "Haridwar", "Rishikesh",
        # West Bengal
        "Kolkata", "Howrah", "Durgapur", "Siliguri", "Asansol",
        # Union Territories
        "Pondicherry", "Puducherry", "Karaikal", "Port Blair", "Daman",
        "Silvassa", "Srinagar", "Jammu", "Leh",
        # Remote
        "Remote",
    ]

    INDIAN_STATES = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
        "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
        "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
        "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
        "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
        "Uttarakhand", "West Bengal", "Puducherry", "Jammu & Kashmir", "Ladakh",
        "Andaman & Nicobar", "Chandigarh", "Lakshadweep",
        "Dadra & Nagar Haveli and Daman & Diu",
    ]

    data = load_jobs()
    jobs = data.get("jobs", [])
    suggestions = set(INDIAN_CITIES + INDIAN_STATES)
    for j in jobs:
        city = j.get("location_city", "").strip()
        state = j.get("location_state", "").strip()
        country = j.get("location_country", "").strip()
        loc = j.get("location", "").strip()
        if city:
            suggestions.add(city)
        if state:
            suggestions.add(state)
        if country:
            suggestions.add(country)
        if loc and loc not in ("Remote",):
            suggestions.add(loc)
    q = request.args.get("q", "").strip().lower()
    results = sorted(suggestions)
    if q:
        # Prioritize starts-with, then contains
        starts = [s for s in results if s.lower().startswith(q)]
        contains = [s for s in results if q in s.lower() and s not in starts]
        results = starts + contains
    return jsonify(results[:20])


# ═══════════════════════════════════════════════════════════════════════
# AI-POWERED ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/smart-search")
def api_smart_search():
    """
    AI-powered semantic search:
      ?q=          – natural language query (e.g. "python jobs in bangalore")
      ?top_k=      – max results (default 50)
    Uses NLP to expand queries, match synonyms, and rank by relevance.
    """
    query = request.args.get("q", "").strip()
    top_k = min(100, max(1, int(request.args.get("top_k", 50))))

    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400

    data = load_jobs()
    jobs = data.get("jobs", [])

    try:
        from scraper.ai_processor import AIJobProcessor, LocationIntelligence

        # Resolve location aliases in query
        words = query.split()
        resolved_words = []
        for word in words:
            resolved = LocationIntelligence.resolve_location(word)
            resolved_words.append(resolved)
        resolved_query = " ".join(resolved_words)

        ai = AIJobProcessor()
        results = ai.smart_search(resolved_query, jobs, top_k)

        return jsonify({
            "query": query,
            "resolved_query": resolved_query,
            "results": results,
            "total": len(results),
            "ai_powered": True,
        })
    except Exception as e:
        logger.warning(f"Smart search fallback: {e}")
        # Fallback to basic search
        q_lower = query.lower()
        results = [
            j for j in jobs
            if q_lower in j.get("title", "").lower()
            or q_lower in j.get("company", "").lower()
            or q_lower in j.get("location", "").lower()
            or any(q_lower in s.lower() for s in j.get("skills", []))
        ]
        return jsonify({
            "query": query,
            "results": results[:top_k],
            "total": len(results),
            "ai_powered": False,
        })


@app.route("/api/jobs/search-all")
def api_search_all():
    """
    Unified search across ALL job sources (main + India + TN).
    Returns combined results grouped by source with apply links.
      ?keyword=     – search in title, company, skills
      ?location=    – search in city, location text
      ?per_page=    – max results (default 20)
    """
    keyword = request.args.get("keyword", "").strip().lower()
    location = request.args.get("location", "").strip().lower()
    per_page = min(100, max(1, int(request.args.get("per_page", 20))))

    if not keyword and not location:
        return jsonify({"jobs": [], "total": 0, "sources": {}})

    all_jobs = []

    # 1. Main jobs
    main_data = load_jobs()
    for j in main_data.get("jobs", []):
        j["_source_db"] = "main"
        all_jobs.append(j)

    # 2. India jobs
    india_data = load_india_jobs()
    seen_keys = set()
    for j in india_data.get("jobs", []):
        key = f"{j.get('title','')}-{j.get('company','')}-{j.get('location','')}".lower()
        if key not in seen_keys:
            seen_keys.add(key)
            j["_source_db"] = "india"
            all_jobs.append(j)

    # 3. TN jobs
    tn_data = load_tn_jobs()
    for j in tn_data.get("jobs", []):
        key = f"{j.get('title','')}-{j.get('company','')}-{j.get('location','')}".lower()
        if key not in seen_keys:
            seen_keys.add(key)
            j["_source_db"] = "tamilnadu"
            all_jobs.append(j)

    # Filter by keyword
    if keyword:
        keywords = [k.strip() for k in keyword.split(",") if k.strip()]
        all_jobs = [
            j for j in all_jobs
            if any(
                kw in j.get("title", "").lower()
                or kw in j.get("company", "").lower()
                or kw in j.get("category", "").lower()
                or any(kw in s.lower() for s in j.get("skills", []))
                for kw in keywords
            )
        ]

    # Filter by location
    if location:
        loc_terms = [l.strip() for l in location.split(",") if l.strip()]
        all_jobs = [
            j for j in all_jobs
            if any(
                lt in j.get("location", "").lower()
                or lt in j.get("location_city", "").lower()
                or lt in j.get("location_state", "").lower()
                or lt in j.get("location_country", "").lower()
                for lt in loc_terms
            )
        ]

    # Sort by quality/composite score then freshness
    all_jobs.sort(
        key=lambda j: (
            j.get("composite_score", j.get("quality_score", 50)),
            j.get("posted_date", "")
        ),
        reverse=True,
    )

    from collections import Counter
    source_counts = Counter(j.get("_source_db", "main") for j in all_jobs)
    portal_counts = Counter(j.get("source", "CareerPath Pro") for j in all_jobs)

    # Keep source_db for frontend link building, rename to cleaner key
    paginated = all_jobs[:per_page]
    for j in paginated:
        j["source_db"] = j.pop("_source_db", "main")

    return jsonify({
        "jobs": paginated,
        "total": len(all_jobs),
        "returned": len(paginated),
        "sources": {
            "main": source_counts.get("main", 0),
            "india": source_counts.get("india", 0),
            "tamilnadu": source_counts.get("tamilnadu", 0),
        },
        "portals": dict(portal_counts.most_common(10)),
    })


@app.route("/api/trending")
def api_trending():
    """
    Get trending job market analysis:
      - Top skills, roles, companies, locations
      - Growth signals & salary insights
      - Career paths
    Data is updated on each daily scrape.
    """
    try:
        from scraper.trend_analyzer import TrendAnalyzer
        analyzer = TrendAnalyzer(DATA_DIR)
        trends = analyzer.get_latest_trends()

        if not trends:
            # Generate trends on-the-fly if no cached data
            data = load_jobs()
            jobs = data.get("jobs", [])
            trends = analyzer.analyze(jobs)

        return jsonify(trends)
    except Exception as e:
        logger.error(f"Trending endpoint error: {e}")
        # Fallback basic stats
        data = load_jobs()
        jobs = data.get("jobs", [])
        from collections import Counter
        skill_counter = Counter()
        for j in jobs:
            for s in j.get("skills", []):
                skill_counter[s] += 1
        return jsonify({
            "total_jobs": len(jobs),
            "top_skills": [{"skill": s, "count": c} for s, c in skill_counter.most_common(20)],
            "error": "Full analysis unavailable, showing basic stats",
        })


@app.route("/api/recommendations")
def api_recommendations():
    """
    AI job recommendations based on user skills:
      ?skills=Python,React,AWS  – comma-separated skill list
      ?top_k=10                 – max results
    Returns jobs ranked by match score with skill gap analysis.
    """
    skills_param = request.args.get("skills", "").strip()
    if not skills_param:
        return jsonify({"error": "Parameter 'skills' is required (comma-separated)"}), 400

    user_skills = [s.strip() for s in skills_param.split(",") if s.strip()]
    top_k = min(50, max(1, int(request.args.get("top_k", 10))))

    data = load_jobs()
    jobs = data.get("jobs", [])

    try:
        from scraper.ai_processor import AIJobProcessor
        ai = AIJobProcessor()
        recommendations = ai.get_ai_recommendations(user_skills, jobs, top_k)
        return jsonify({
            "user_skills": user_skills,
            "recommendations": recommendations,
            "total": len(recommendations),
        })
    except Exception as e:
        logger.error(f"Recommendations error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/companies")
def api_companies():
    """
    Get top hiring companies with profiles:
      ?top_k=20  – number of companies
    Returns company profiles with job counts, tech stacks, and metadata.
    """
    top_k = min(50, max(1, int(request.args.get("top_k", 20))))
    data = load_jobs()
    jobs = data.get("jobs", [])

    try:
        from scraper.company_scraper import CompanyScraper
        scraper = CompanyScraper()
        companies = scraper.get_top_hiring_companies(jobs, top_k)
        return jsonify({
            "companies": companies,
            "total": len(companies),
        })
    except Exception as e:
        logger.error(f"Companies endpoint error: {e}")
        from collections import Counter
        counts = Counter(j.get("company", "Unknown") for j in jobs)
        return jsonify({
            "companies": [{"name": c, "open_positions": n} for c, n in counts.most_common(top_k)],
            "total": min(top_k, len(counts)),
        })


@app.route("/api/company/<company_name>")
def api_company_detail(company_name):
    """Get detailed profile for a specific company."""
    data = load_jobs()
    jobs = data.get("jobs", [])

    company_jobs = [j for j in jobs if company_name.lower() in j.get("company", "").lower()]
    if not company_jobs:
        return jsonify({"error": "Company not found"}), 404

    try:
        from scraper.company_scraper import CompanyScraper
        scraper = CompanyScraper()
        profile = scraper.get_company_profile(company_name)
        profile["open_positions"] = len(company_jobs)
        profile["jobs"] = company_jobs[:20]
        return jsonify(profile)
    except Exception:
        return jsonify({
            "name": company_name,
            "open_positions": len(company_jobs),
            "jobs": company_jobs[:20],
        })


@app.route("/api/career-paths")
def api_career_paths():
    """Get AI-generated career path recommendations with real job data."""
    try:
        from scraper.trend_analyzer import TrendAnalyzer
        analyzer = TrendAnalyzer(DATA_DIR)
        trends = analyzer.get_latest_trends()
        if trends and "career_paths" in trends:
            return jsonify({"career_paths": trends["career_paths"]})

        data = load_jobs()
        jobs = data.get("jobs", [])
        analysis = analyzer.analyze(jobs)
        return jsonify({"career_paths": analysis.get("career_paths", [])})
    except Exception as e:
        logger.error(f"Career paths error: {e}")
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════
# TAMIL NADU & PONDICHERRY – API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.route("/jobs/tamilnadu")
def tn_jobs_page():
    """Dedicated Tamil Nadu & Pondicherry jobs page."""
    return render_template("tn_jobs.html")


@app.route("/api/jobs/tamilnadu")
def api_tn_jobs():
    """
    Return Tamil Nadu & Pondicherry jobs with filters:
      ?keyword=         – title / company / skills search
      ?city=            – specific TN city (e.g. Chennai, Coimbatore)
      ?type=            – job type (Full-time, Internship, Fresher, etc.)
      ?experience=      – experience level
      ?category=        – job category
      ?source=          – source portal
      ?sort=            – newest | oldest | title | company
      ?page= &per_page= – pagination
    """
    # Try dedicated TN file first, then filter from main jobs
    tn_data = load_tn_jobs()
    tn_jobs = tn_data.get("jobs", [])

    # Also include any TN jobs from the main jobs file
    main_data = load_jobs()
    main_jobs = main_data.get("jobs", [])
    tn_states = {"tamil nadu", "puducherry"}
    tn_city_names = {c.lower() for c in _get_tn_cities()}

    for j in main_jobs:
        state = (j.get("location_state", "") or "").lower()
        city = (j.get("location_city", "") or "").lower()
        loc = (j.get("location", "") or "").lower()
        if state in tn_states or city in tn_city_names or "tamil nadu" in loc or "pondicherry" in loc or "puducherry" in loc:
            # Check if already in tn_jobs (avoid dups)
            key = f"{j.get('title','')}-{j.get('company','')}-{j.get('location','')}".lower()
            existing = {f"{tj.get('title','')}-{tj.get('company','')}-{tj.get('location','')}".lower() for tj in tn_jobs}
            if key not in existing:
                j["is_tamilnadu"] = True
                j["region"] = "Tamil Nadu & Pondicherry"
                tn_jobs.append(j)

    jobs = tn_jobs

    # ── Keyword search ─────────────────────────────────────────────
    keyword = request.args.get("keyword", "").strip().lower()
    if keyword:
        keywords = [k.strip() for k in keyword.split(",") if k.strip()]
        jobs = [
            j for j in jobs
            if any(
                kw in j.get("title", "").lower()
                or kw in j.get("company", "").lower()
                or kw in j.get("category", "").lower()
                or kw in j.get("description", "").lower()[:500]
                or any(kw in s.lower() for s in j.get("skills", []))
                for kw in keywords
            )
        ]

    # ── City filter ────────────────────────────────────────────────
    city = request.args.get("city", "").strip().lower()
    if city:
        jobs = [j for j in jobs if city in j.get("location_city", "").lower()
                or city in j.get("location", "").lower()]

    # ── State filter ───────────────────────────────────────────────
    state = request.args.get("state", "").strip().lower()
    if state:
        jobs = [j for j in jobs if state in j.get("location_state", "").lower()]

    # ── Other filters ──────────────────────────────────────────────
    job_type = request.args.get("type", "").strip()
    experience = request.args.get("experience", "").strip()
    category = request.args.get("category", "").strip()
    source = request.args.get("source", "").strip()

    if job_type:
        type_vals = [t.strip().lower() for t in job_type.split(",") if t.strip()]
        jobs = [j for j in jobs if any(tv in j.get("type", "").lower() for tv in type_vals)]
    if experience:
        exp_vals = [e.strip().lower() for e in experience.split(",") if e.strip()]
        jobs = [j for j in jobs if any(ev in j.get("experience", "").lower() for ev in exp_vals)]
    if category:
        cat_vals = [c.strip().lower() for c in category.split(",") if c.strip()]
        jobs = [j for j in jobs if any(cv in j.get("category", "").lower() for cv in cat_vals)]
    if source:
        src_vals = [s.strip().lower() for s in source.split(",") if s.strip()]
        jobs = [j for j in jobs if any(sv in j.get("source", "").lower() for sv in src_vals)]

    # ── Sorting ────────────────────────────────────────────────────
    sort = request.args.get("sort", "newest").strip().lower()
    if sort == "newest":
        jobs.sort(key=lambda j: j.get("posted_date", ""), reverse=True)
    elif sort == "oldest":
        jobs.sort(key=lambda j: j.get("posted_date", ""))
    elif sort == "title":
        jobs.sort(key=lambda j: j.get("title", "").lower())
    elif sort == "company":
        jobs.sort(key=lambda j: j.get("company", "").lower())

    # ── Pagination ─────────────────────────────────────────────────
    total = len(jobs)
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(500, max(1, int(request.args.get("per_page", 50))))
    start = (page - 1) * per_page
    paginated = jobs[start : start + per_page]

    # ── Filter counts ──────────────────────────────────────────────
    from collections import Counter
    city_counts = Counter(j.get("location_city", "Unknown") for j in tn_jobs)
    type_counts = Counter(j.get("type", "Other") for j in jobs)
    exp_counts = Counter(j.get("experience", "Unknown") for j in jobs)
    cat_counts = Counter(j.get("category", "Other") for j in jobs)
    src_counts = Counter(j.get("source", "Unknown") for j in jobs)

    return jsonify({
        "jobs": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "region": "Tamil Nadu & Pondicherry",
        "last_updated": tn_data.get("last_updated") or main_data.get("last_updated"),
        "filter_counts": {
            "cities": dict(city_counts.most_common(50)),
            "types": dict(type_counts),
            "experience": dict(exp_counts),
            "categories": dict(cat_counts),
            "sources": dict(src_counts),
        },
    })


@app.route("/api/jobs/tamilnadu/cities")
def api_tn_cities():
    """Return all Tamil Nadu & Pondicherry cities with job counts."""
    tn_data = load_tn_jobs()
    tn_jobs = tn_data.get("jobs", [])

    # Also count TN jobs from main file
    main_data = load_jobs()
    for j in main_data.get("jobs", []):
        state = (j.get("location_state", "") or "").lower()
        if state in ("tamil nadu", "puducherry"):
            tn_jobs.append(j)

    from collections import Counter
    city_counts = Counter(j.get("location_city", "Unknown") for j in tn_jobs)

    # Always include all known TN cities even with 0 count
    all_cities = _get_tn_cities()
    for c in all_cities:
        if c not in city_counts:
            city_counts[c] = 0

    cities = [{"city": c, "count": n} for c, n in city_counts.most_common() if c != "Unknown"]
    return jsonify({
        "cities": cities,
        "total_cities": len(cities),
        "total_jobs": len(tn_jobs),
        "region": "Tamil Nadu & Pondicherry",
    })


@app.route("/api/jobs/tamilnadu/stats")
def api_tn_stats():
    """Statistics for Tamil Nadu & Pondicherry job market."""
    tn_data = load_tn_jobs()
    tn_jobs = tn_data.get("jobs", [])

    # Also include TN jobs from main data
    main_data = load_jobs()
    for j in main_data.get("jobs", []):
        state = (j.get("location_state", "") or "").lower()
        if state in ("tamil nadu", "puducherry"):
            tn_jobs.append(j)

    from collections import Counter
    city_counts = Counter(j.get("location_city", "Unknown") for j in tn_jobs)
    type_counts = Counter(j.get("type", "Other") for j in tn_jobs)
    cat_counts = Counter(j.get("category", "Other") for j in tn_jobs)
    exp_counts = Counter(j.get("experience", "Unknown") for j in tn_jobs)
    src_counts = Counter(j.get("source", "Unknown") for j in tn_jobs)
    company_counts = Counter(j.get("company", "Unknown") for j in tn_jobs)

    # Computed stats
    fresher_jobs = sum(1 for j in tn_jobs if "fresher" in (j.get("type", "") or "").lower()
                       or "entry" in (j.get("experience", "") or "").lower()
                       or "internship" in (j.get("type", "") or "").lower())
    remote_jobs = sum(1 for j in tn_jobs if "remote" in (j.get("type", "") or "").lower()
                      or "wfh" in (j.get("type", "") or "").lower()
                      or "hybrid" in (j.get("type", "") or "").lower())

    top_cities = [{"city": c, "count": n} for c, n in city_counts.most_common(15) if c != "Unknown"]

    return jsonify({
        "total_jobs": len(tn_jobs),
        "unique_cities": len([c for c in city_counts if c != "Unknown"]),
        "unique_companies": len(company_counts) - (1 if "Unknown" in company_counts else 0),
        "fresher_jobs": fresher_jobs,
        "remote_jobs": remote_jobs,
        "last_updated": tn_data.get("last_updated"),
        "region": "Tamil Nadu & Pondicherry",
        "cities": dict(city_counts.most_common(50)),
        "top_cities": top_cities,
        "types": dict(type_counts),
        "categories": dict(cat_counts),
        "experience": dict(exp_counts),
        "sources": dict(src_counts),
        "top_companies": dict(company_counts.most_common(20)),
    })


@app.route("/api/jobs/tamilnadu/refresh", methods=["POST"])
def api_tn_refresh():
    """Manually trigger Tamil Nadu job scraper refresh."""
    count = refresh_tn_jobs()
    return jsonify({
        "status": "success",
        "message": f"Refreshed {count} Tamil Nadu & Pondicherry jobs",
        "count": count,
        "jobs_count": count,
        "region": "Tamil Nadu & Pondicherry",
    })


def _get_tn_cities():
    """Return the list of TN city names (strings)."""
    try:
        from scraper.tamilnadu_scraper import TAMILNADU_CITIES
        return list(set(c["city"] for c in TAMILNADU_CITIES))
    except ImportError:
        return [
            "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem",
            "Tirunelveli", "Erode", "Vellore", "Hosur", "Tirupur",
            "Pondicherry", "Puducherry", "Karaikal", "Thanjavur", "Dindigul",
            "Thoothukudi", "Nagercoil", "Kanchipuram",
        ]


# ═══════════════════════════════════════════════════════════════════════
# ALL INDIA – PAGE & API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.route("/jobs/india")
def india_jobs_page():
    """Dedicated All-India jobs page with AI-powered organization."""
    return render_template("india_jobs.html")


@app.route("/api/jobs/india")
def api_india_jobs():
    """
    Return All-India jobs with comprehensive filters:
      ?keyword=         – title / company / skills text search
      ?city=            – specific city (Bangalore, Mumbai, Delhi NCR, etc.)
      ?state=           – state filter (Karnataka, Maharashtra, etc.)
      ?type=            – job type (Full-time, Remote, Internship, etc.)
      ?experience=      – experience level (Entry Level, Junior, Mid Level, etc.)
      ?category=        – job category (Technology, Data Science, etc.)
      ?source=          – source portal (Naukri.com, LinkedIn, etc.)
      ?sort=            – newest | oldest | title | company | score | trending
      ?page= &per_page= – pagination (default 50 per page)
    """
    india_data = load_india_jobs()
    india_jobs = india_data.get("jobs", [])

    # Also include India-tagged jobs from main jobs file
    main_data = load_jobs()
    main_jobs = main_data.get("jobs", [])
    existing_keys = {
        f"{j.get('title','')}-{j.get('company','')}-{j.get('location','')}".lower()
        for j in india_jobs
    }
    for j in main_jobs:
        country = (j.get("location_country", "") or "").lower()
        location = (j.get("location", "") or "").lower()
        if "india" in country or "india" in location:
            key = f"{j.get('title','')}-{j.get('company','')}-{j.get('location','')}".lower()
            if key not in existing_keys:
                existing_keys.add(key)
                j["is_india"] = True
                j["region"] = "India"
                india_jobs.append(j)

    jobs = india_jobs

    # ── Keyword search ─────────────────────────────────────────────
    keyword = request.args.get("keyword", "").strip().lower()
    if keyword:
        keywords = [k.strip() for k in keyword.split(",") if k.strip()]
        jobs = [
            j for j in jobs
            if any(
                kw in j.get("title", "").lower()
                or kw in j.get("company", "").lower()
                or kw in j.get("category", "").lower()
                or kw in j.get("description", "").lower()[:500]
                or any(kw in s.lower() for s in j.get("skills", []))
                for kw in keywords
            )
        ]

    # ── City filter ────────────────────────────────────────────────
    city = request.args.get("city", "").strip().lower()
    if city:
        jobs = [j for j in jobs
                if city in j.get("location_city", "").lower()
                or city in j.get("location", "").lower()]

    # ── State filter ───────────────────────────────────────────────
    state = request.args.get("state", "").strip().lower()
    if state:
        jobs = [j for j in jobs
                if state in j.get("location_state", "").lower()]

    # ── Other filters ──────────────────────────────────────────────
    job_type = request.args.get("type", "").strip()
    experience = request.args.get("experience", "").strip()
    category = request.args.get("category", "").strip()
    source = request.args.get("source", "").strip()

    if job_type:
        type_vals = [t.strip().lower() for t in job_type.split(",") if t.strip()]
        jobs = [j for j in jobs if any(tv in j.get("type", "").lower() for tv in type_vals)]
    if experience:
        exp_vals = [e.strip().lower() for e in experience.split(",") if e.strip()]
        jobs = [j for j in jobs if any(ev in j.get("experience", "").lower() for ev in exp_vals)]
    if category:
        cat_vals = [c.strip().lower() for c in category.split(",") if c.strip()]
        jobs = [j for j in jobs if any(cv in j.get("category", "").lower() for cv in cat_vals)]
    if source:
        src_vals = [s.strip().lower() for s in source.split(",") if s.strip()]
        jobs = [j for j in jobs if any(sv in j.get("source", "").lower() for sv in src_vals)]

    # ── Sorting ────────────────────────────────────────────────────
    sort = request.args.get("sort", "score").strip().lower()
    if sort == "newest":
        jobs.sort(key=lambda j: j.get("posted_date", ""), reverse=True)
    elif sort == "oldest":
        jobs.sort(key=lambda j: j.get("posted_date", ""))
    elif sort == "title":
        jobs.sort(key=lambda j: j.get("title", "").lower())
    elif sort == "company":
        jobs.sort(key=lambda j: j.get("company", "").lower())
    elif sort == "score":
        jobs.sort(key=lambda j: j.get("composite_score", 0), reverse=True)
    elif sort == "trending":
        jobs.sort(key=lambda j: (1 if j.get("trending") else 0, j.get("composite_score", 0)), reverse=True)

    # ── Pagination ─────────────────────────────────────────────────
    total = len(jobs)
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(500, max(1, int(request.args.get("per_page", 50))))
    start_idx = (page - 1) * per_page
    paginated = jobs[start_idx : start_idx + per_page]

    # ── Filter counts ──────────────────────────────────────────────
    from collections import Counter
    state_counts = Counter(j.get("location_state", "Unknown") for j in india_jobs if j.get("location_state"))
    city_counts = Counter(j.get("location_city", "Unknown") for j in india_jobs if j.get("location_city"))
    type_counts = Counter(j.get("type", "Other") for j in jobs)
    exp_counts = Counter(j.get("experience", "Unknown") for j in jobs)
    cat_counts = Counter(j.get("category", "Other") for j in jobs)
    src_counts = Counter(j.get("source", "Unknown") for j in jobs)

    return jsonify({
        "jobs": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "region": "India",
        "last_updated": india_data.get("last_updated") or main_data.get("last_updated"),
        "filter_counts": {
            "states": dict(state_counts.most_common(40)),
            "cities": dict(city_counts.most_common(50)),
            "types": dict(type_counts),
            "experience": dict(exp_counts),
            "categories": dict(cat_counts),
            "sources": dict(src_counts),
        },
    })


@app.route("/api/jobs/india/states")
def api_india_states():
    """Return all Indian states/UTs with job counts."""
    india_data = load_india_jobs()
    india_jobs = india_data.get("jobs", [])

    from collections import Counter
    state_counts = Counter(j.get("location_state", "Unknown") for j in india_jobs if j.get("location_state"))

    # Include all known states even with 0 count
    try:
        from scraper.india_scraper import ALL_INDIA_REGIONS
        for state_name in ALL_INDIA_REGIONS:
            if state_name not in state_counts:
                state_counts[state_name] = 0
    except ImportError:
        pass

    states = [{"state": s, "count": n} for s, n in state_counts.most_common() if s != "Unknown"]
    return jsonify({
        "states": states,
        "total_states": len(states),
        "total_jobs": len(india_jobs),
        "region": "India",
    })


@app.route("/api/jobs/india/cities")
def api_india_cities():
    """Return top India cities with job counts."""
    india_data = load_india_jobs()
    india_jobs = india_data.get("jobs", [])

    from collections import Counter
    city_counts = Counter(j.get("location_city", "Unknown") for j in india_jobs if j.get("location_city"))

    cities = [{"city": c, "count": n, "state": _resolve_city_state(c)}
              for c, n in city_counts.most_common(100) if c != "Unknown"]
    return jsonify({
        "cities": cities,
        "total_cities": len(cities),
        "total_jobs": len(india_jobs),
        "region": "India",
    })


@app.route("/api/jobs/india/stats")
def api_india_stats():
    """Comprehensive statistics for All-India job market."""
    india_data = load_india_jobs()
    india_jobs = india_data.get("jobs", [])

    from collections import Counter
    state_counts = Counter(j.get("location_state", "Unknown") for j in india_jobs if j.get("location_state"))
    city_counts = Counter(j.get("location_city", "Unknown") for j in india_jobs if j.get("location_city"))
    type_counts = Counter(j.get("type", "Other") for j in india_jobs)
    cat_counts = Counter(j.get("category", "Other") for j in india_jobs)
    exp_counts = Counter(j.get("experience", "Unknown") for j in india_jobs)
    src_counts = Counter(j.get("source", "Unknown") for j in india_jobs)
    company_counts = Counter(j.get("company", "Unknown") for j in india_jobs)
    skill_counter = Counter()
    for j in india_jobs:
        for s in j.get("skills", []):
            skill_counter[s] += 1

    # Computed stats
    fresher_jobs = sum(1 for j in india_jobs if "fresher" in (j.get("type", "") or "").lower()
                       or "entry" in (j.get("experience", "") or "").lower()
                       or "internship" in (j.get("type", "") or "").lower())
    remote_jobs = sum(1 for j in india_jobs if "remote" in (j.get("type", "") or "").lower()
                      or "wfh" in (j.get("type", "") or "").lower()
                      or "hybrid" in (j.get("type", "") or "").lower())
    trending_jobs = sum(1 for j in india_jobs if j.get("trending", False))

    top_cities = [{"city": c, "count": n} for c, n in city_counts.most_common(20) if c != "Unknown"]
    top_states = [{"state": s, "count": n} for s, n in state_counts.most_common(15) if s != "Unknown"]

    return jsonify({
        "total_jobs": len(india_jobs),
        "unique_states": len([s for s in state_counts if s != "Unknown"]),
        "unique_cities": len([c for c in city_counts if c != "Unknown"]),
        "unique_companies": len(company_counts) - (1 if "Unknown" in company_counts else 0),
        "fresher_jobs": fresher_jobs,
        "remote_jobs": remote_jobs,
        "trending_jobs": trending_jobs,
        "last_updated": india_data.get("last_updated"),
        "region": "India",
        "top_cities": top_cities,
        "top_states": top_states,
        "types": dict(type_counts),
        "categories": dict(cat_counts),
        "experience": dict(exp_counts),
        "sources": dict(src_counts),
        "top_companies": dict(company_counts.most_common(30)),
        "top_skills": dict(skill_counter.most_common(30)),
    })


@app.route("/api/jobs/india/trending")
def api_india_trending():
    """Return trending skills, roles, and companies in India job market."""
    india_data = load_india_jobs()
    india_jobs = india_data.get("jobs", [])

    from collections import Counter
    skill_counter = Counter()
    role_counter = Counter()
    company_counter = Counter()
    city_counter = Counter()

    for j in india_jobs:
        for s in j.get("skills", []):
            skill_counter[s] += 1
        role_counter[j.get("title", "")] += 1
        company_counter[j.get("company", "")] += 1
        if j.get("location_city"):
            city_counter[j["location_city"]] += 1

    # Recently posted (last 7 days)
    from datetime import datetime as dt_cls
    recent_count = 0
    for j in india_jobs:
        try:
            posted = dt_cls.strptime(j.get("posted_date", "")[:10], "%Y-%m-%d")
            if (dt_cls.now() - posted).days <= 7:
                recent_count += 1
        except Exception:
            continue

    return jsonify({
        "trending_skills": [{"skill": s, "count": n} for s, n in skill_counter.most_common(20)],
        "trending_roles": [{"role": r, "count": n} for r, n in role_counter.most_common(15)],
        "top_hiring_companies": [{"company": c, "count": n} for c, n in company_counter.most_common(15)],
        "top_hiring_cities": [{"city": c, "count": n} for c, n in city_counter.most_common(15)],
        "jobs_posted_last_7_days": recent_count,
        "total_jobs": len(india_jobs),
    })


@app.route("/api/jobs/india/refresh", methods=["POST"])
def api_india_refresh():
    """Manually trigger All-India job scraper refresh."""
    count = refresh_india_jobs()
    return jsonify({
        "status": "success",
        "message": f"Refreshed {count} All-India jobs",
        "count": count,
        "jobs_count": count,
        "region": "India",
    })


def _resolve_city_state(city_name):
    """Helper: return state name for a city."""
    try:
        from scraper.india_scraper import ALL_INDIA_REGIONS
        city_lower = city_name.lower().strip()
        for state, info in ALL_INDIA_REGIONS.items():
            for c in info["cities"]:
                if c.lower() == city_lower:
                    return state
        return ""
    except ImportError:
        return ""


@app.route("/api/location-intelligence")
def api_location_intelligence():
    """
    Smart location search with AI:
      ?q=bengaluru  → resolves to Bangalore, shows nearby cities, job counts
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Parameter 'q' is required"}), 400

    try:
        from scraper.ai_processor import LocationIntelligence
        resolved = LocationIntelligence.resolve_location(query)
        nearby = LocationIntelligence.get_nearby_cities(resolved)

        data = load_jobs()
        jobs = data.get("jobs", [])

        # Count jobs in resolved location
        resolved_lower = resolved.lower()
        job_count = sum(
            1 for j in jobs
            if resolved_lower in j.get("location_city", "").lower()
            or resolved_lower in j.get("location", "").lower()
        )

        # Count nearby city jobs
        nearby_counts = {}
        for city in nearby:
            city_lower = city.lower()
            nearby_counts[city] = sum(
                1 for j in jobs
                if city_lower in j.get("location_city", "").lower()
            )

        return jsonify({
            "query": query,
            "resolved": resolved,
            "jobs_count": job_count,
            "nearby_cities": nearby_counts,
            "suggestions": nearby,
        })
    except Exception as e:
        return jsonify({"query": query, "error": str(e)}), 500


@app.route("/api/refresh-status")
def api_refresh_status():
    """Get the status of the last data refresh + scheduler info."""
    data = load_jobs()
    jobs = data.get("jobs", [])
    last_updated = data.get("last_updated", "Never")

    from collections import Counter
    sources = Counter(j.get("source", "Unknown") for j in jobs)
    countries = Counter(j.get("location_country", "Unknown") for j in jobs)
    categories = Counter(j.get("category", "Other") for j in jobs)

    # Check data freshness
    is_fresh = False
    hours_since_update = None
    if last_updated and last_updated != "Never":
        try:
            last_dt = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")
            hours_since_update = round((datetime.now() - last_dt).total_seconds() / 3600, 1)
            is_fresh = hours_since_update < STALE_THRESHOLD_HOURS
        except Exception:
            pass

    return jsonify({
        "last_updated": last_updated,
        "hours_since_update": hours_since_update,
        "total_jobs": len(jobs),
        "is_fresh": is_fresh,
        "sources": dict(sources),
        "countries_covered": len(countries),
        "categories": dict(categories),
        "top_countries": dict(countries.most_common(10)),
        "scheduler": {
            "active": scheduler_info["active"],
            "type": scheduler_info["type"],
            "next_run": scheduler_info["next_run"],
            "started_at": scheduler_info["started_at"],
            "refresh_interval_hours": REFRESH_INTERVAL_HOURS,
        },
    })


@app.route("/api/scheduler-status")
def api_scheduler_status():
    """Detailed scheduler status – for admin/debug dashboard."""
    data = load_jobs()
    last_updated = data.get("last_updated", "Never")

    # Compute time until next run
    time_to_next = None
    if scheduler_info["next_run"]:
        try:
            next_dt = datetime.strptime(scheduler_info["next_run"], "%Y-%m-%d %H:%M:%S")
            delta = next_dt - datetime.now()
            if delta.total_seconds() > 0:
                hours = int(delta.total_seconds() // 3600)
                mins = int((delta.total_seconds() % 3600) // 60)
                time_to_next = f"{hours}h {mins}m"
            else:
                time_to_next = "imminent"
        except Exception:
            pass

    return jsonify({
        "scheduler_active": scheduler_info["active"],
        "scheduler_type": scheduler_info["type"],
        "started_at": scheduler_info["started_at"],
        "refresh_interval_hours": REFRESH_INTERVAL_HOURS,
        "stale_threshold_hours": STALE_THRESHOLD_HOURS,
        "next_run": scheduler_info["next_run"],
        "time_to_next_run": time_to_next,
        "last_refresh": scheduler_info["last_refresh"],
        "last_refresh_count": scheduler_info["last_refresh_count"],
        "data_last_updated": last_updated,
        "refresh_history": scheduler_info["refresh_history"],
        "recent_errors": scheduler_info["errors"],
    })


# ── Error Handlers ─────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    logged_in = 'user_id' in session
    if logged_in:
        cta = '<a href="/" class="btn btn-primary" style="display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:#0f4c75;color:#fff;border-radius:10px;text-decoration:none;font-weight:600;"><i class="fas fa-home"></i> Go Home</a>'
    else:
        cta = (
            '<p style="color:var(--text-secondary,#546478);margin:0 0 20px;font-size:1.05rem;">Login to access full features and explore all opportunities.</p>'
            '<div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">'
            '<a href="/login" style="display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:#0f4c75;color:#fff;border-radius:10px;text-decoration:none;font-weight:600;"><i class="fas fa-sign-in-alt"></i> Login to Continue</a>'
            '<a href="/signup" style="display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:transparent;color:#0f4c75;border:2px solid #0f4c75;border-radius:10px;text-decoration:none;font-weight:600;"><i class="fas fa-user-plus"></i> Sign Up Free</a>'
            '</div>'
            '<p style="margin-top:16px;"><a href="/" style="color:#3282b8;text-decoration:none;font-size:0.9rem;"><i class="fas fa-arrow-left"></i> Back to Home</a></p>'
        )
    return f"""
    <html><head><title>CareerPath Pro</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    </head><body style="display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;background:var(--bg-primary,#fff);font-family:'Inter',sans-serif;">
    <div style="max-width:480px;padding:40px;">
        <div style="width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#0f4c75,#3282b8);display:flex;align-items:center;justify-content:center;margin:0 auto 24px;">
            <i class="fas fa-lock" style="color:#fff;font-size:2rem;"></i>
        </div>
        <h1 style="font-size:1.8rem;color:var(--text-primary,#1a2332);margin:0 0 8px;">Login to Access Full Features</h1>
        <p style="color:var(--text-secondary,#546478);margin:0 0 24px;">This page requires an account. Sign in to unlock jobs, dashboards, career tools and more.</p>
        {cta}
    </div>
    </body></html>
    """, 404


# ── WSGI alias (some Vercel runtime versions look for `application`) ───
application = app

# ── Run (local dev only – Vercel uses the `app` WSGI object) ──────────
# ── Student Capabilities ──────────────────────────────────────────────

def _load_all_jobs():
    """Load all job JSON files from data directory and seed files."""
    all_jobs = []
    for fpath in [JOBS_FILE, TN_JOBS_FILE, INDIA_JOBS_FILE, SEED_FILE, TN_SEED_FILE, INDIA_SEED_FILE]:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                if isinstance(raw, dict) and 'jobs' in raw:
                    all_jobs.extend(raw['jobs'])
                elif isinstance(raw, list):
                    all_jobs.extend(raw)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    # Deduplicate by id
    seen = {}
    for j in all_jobs:
        jid = j.get('id')
        if jid and jid not in seen:
            seen[jid] = j
    return list(seen.values())


@app.route("/api/save-job", methods=["POST"])
@login_required
def save_job():
    """Save a job ID for the logged-in user."""
    data = request.json
    job_id = data.get("job_id")
    
    if not job_id:
        return jsonify({"error": "Job ID required"}), 400
        
    try:
        existing = supabase.table("saved_jobs").select("id").eq("user_id", session['user_id']).eq("job_id", job_id).execute()
        if existing.data:
            return jsonify({"status": "already_saved"})
            
        supabase.table("saved_jobs").insert({
            "user_id": session['user_id'],
            "job_id": job_id
        }).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error saving job: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/unsave-job", methods=["POST"])
@login_required
def unsave_job():
    """Remove a saved job for the logged-in user."""
    data = request.json
    job_id = data.get("job_id")
    if not job_id:
        return jsonify({"error": "Job ID required"}), 400
    try:
        supabase.table("saved_jobs").delete().eq("user_id", session['user_id']).eq("job_id", job_id).execute()
        return jsonify({"status": "removed"})
    except Exception as e:
        logger.error(f"Error unsaving job: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/saved-jobs", methods=["GET"])
@login_required
def get_saved_jobs():
    """Get all saved job details for the logged-in user."""
    try:
        response = supabase.table("saved_jobs").select("job_id").eq("user_id", session['user_id']).execute()
        saved_job_ids = [row['job_id'] for row in response.data]
        
        if not saved_job_ids:
            return jsonify({"jobs": []})
        
        all_jobs = _load_all_jobs()
        saved_set = set(saved_job_ids)
        saved_jobs_data = [j for j in all_jobs if str(j.get('id')) in saved_set]
        
        return jsonify({"jobs": saved_jobs_data})
    except Exception as e:
        logger.error(f"Error fetching saved jobs: {e}")
        return jsonify({"error": str(e)}), 500


def _get_user_applications(uid):
    """Load applications list from scraped_data for a user."""
    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"user_apps_{uid}").execute()
        if resp.data and resp.data[0].get("data"):
            return resp.data[0]["data"]
    except Exception:
        pass
    return []


def _save_user_applications(uid, apps):
    """Persist applications list to scraped_data for a user."""
    supabase.table("scraped_data").upsert({
        "kind": f"user_apps_{uid}",
        "data": apps,
        "updated_at": datetime.now().isoformat(),
    }).execute()


def _get_profile_views(uid):
    """Load profile view count from scraped_data for a user."""
    try:
        resp = supabase.table("scraped_data").select("data").eq("kind", f"profile_views_{uid}").execute()
        if resp.data and resp.data[0].get("data"):
            return resp.data[0]["data"]
    except Exception:
        pass
    return {"count": 0, "viewers": []}


def _save_profile_views(uid, views_data):
    """Persist profile views data to scraped_data."""
    supabase.table("scraped_data").upsert({
        "kind": f"profile_views_{uid}",
        "data": views_data,
        "updated_at": datetime.now().isoformat(),
    }).execute()


@app.route("/api/apply-job", methods=["POST"])
@login_required
def apply_job():
    """Record that the user applied for a job."""
    data = request.json
    job_id = str(data.get("job_id", ""))
    if not job_id:
        return jsonify({"error": "Job ID required"}), 400
    try:
        uid = session['user_id']
        apps = _get_user_applications(uid)
        # Check if already applied
        if any(a['job_id'] == job_id for a in apps):
            return jsonify({"status": "already_applied"})
        apps.append({
            "job_id": job_id,
            "status": "applied",
            "created_at": datetime.now().isoformat(),
        })
        _save_user_applications(uid, apps)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error applying to job: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/applications", methods=["GET"])
@login_required
def get_applications():
    """Get all applications with job details for the logged-in user."""
    try:
        uid = session['user_id']
        apps = _get_user_applications(uid)

        job_ids = {a['job_id'] for a in apps}
        all_jobs = _load_all_jobs()
        jobs_map = {str(j['id']): j for j in all_jobs if str(j.get('id')) in job_ids}

        result = []
        for a in reversed(apps):  # newest first
            job = jobs_map.get(a['job_id'], {})
            result.append({
                "job_id": a['job_id'],
                "status": a.get('status', 'applied'),
                "applied_at": a.get('created_at', ''),
                "title": job.get('title', 'Unknown Position'),
                "company": job.get('company', 'Unknown Company'),
                "location": job.get('location', ''),
            })
        return jsonify({"applications": result})
    except Exception as e:
        logger.error(f"Error fetching applications: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/track-profile-view", methods=["POST"])
@login_required
def track_profile_view():
    """Increment profile view count when dashboard is loaded."""
    uid = session['user_id']
    try:
        views = _get_profile_views(uid)
        views["count"] = views.get("count", 0) + 1
        _save_profile_views(uid, views)
        return jsonify({"views": views["count"]})
    except Exception as e:
        logger.error(f"Error tracking profile view: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/dashboard-stats", methods=["GET"])
@login_required
def dashboard_stats():
    """Return real counts for dashboard stat cards."""
    uid = session['user_id']
    stats = {"applications_sent": 0, "interview_calls": 0, "saved_jobs": 0, "profile_views": 0}
    
    try:
        saved = supabase.table("saved_jobs").select("id", count="exact").eq("user_id", uid).execute()
        stats["saved_jobs"] = saved.count if saved.count is not None else len(saved.data or [])
    except Exception as e:
        logger.warning(f"saved_jobs count failed: {e}")
    
    try:
        apps = _get_user_applications(uid)
        stats["applications_sent"] = len(apps)
        stats["interview_calls"] = sum(1 for a in apps if a.get("status") == "interview")
    except Exception as e:
        logger.warning(f"applications count failed: {e}")
    
    try:
        views = _get_profile_views(uid)
        stats["profile_views"] = views.get("count", 0)
    except Exception as e:
        logger.warning(f"profile views count failed: {e}")
    
    return jsonify(stats)


if __name__ == "__main__":
    app.run(port=8080, debug=True)
