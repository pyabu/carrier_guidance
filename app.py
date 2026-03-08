"""
CareerPath Pro – Flask Application
Complete career guidance and job portal backend
Works both locally and on Vercel (serverless).
"""

import os
import json
import shutil
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, abort
from flask_cors import CORS

# ── Vercel detection ───────────────────────────────────────────────────
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))

# ── App Configuration ──────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
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

# Seed file shipped with the repo (used as fallback on Vercel cold-start)
SEED_FILE = os.path.join(os.path.dirname(__file__), "data", "jobs.json")

# ── Helpers ────────────────────────────────────────────────────────────

def load_jobs():
    """Load cached jobs from JSON file, falling back to seed on Vercel."""
    if os.path.exists(JOBS_FILE):
        with open(JOBS_FILE, "r") as f:
            return json.load(f)
    # On Vercel cold-start: copy seed file to /tmp
    if IS_VERCEL and os.path.exists(SEED_FILE):
        os.makedirs(DATA_DIR, exist_ok=True)
        shutil.copy2(SEED_FILE, JOBS_FILE)
        logger.info("📦 Copied seed jobs.json to /tmp for Vercel cold-start")
        with open(JOBS_FILE, "r") as f:
            return json.load(f)
    return {"jobs": [], "last_updated": None}


def save_jobs(data):
    """Persist jobs to JSON file."""
    with open(JOBS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def refresh_jobs():
    """Run the scraper and save new results (lazy-imports scraper)."""
    logger.info("🔄 Refreshing job listings …")
    try:
        from scraper.job_scraper import JobScraper  # lazy import
        scraper = JobScraper()
        jobs = scraper.scrape_all()
        data = {
            "jobs": jobs,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_jobs(data)
        logger.info(f"✅ Saved {len(jobs)} jobs at {data['last_updated']}")
        return len(jobs)
    except Exception as e:
        logger.error(f"❌ Scraper error: {e}")
        return 0


# ── Scheduler – local dev only (Vercel uses cron endpoint instead) ─────
if not IS_VERCEL:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        scheduler.add_job(refresh_jobs, "interval", hours=12, id="refresh_12h")
        scheduler.add_job(refresh_jobs, "cron", hour=6, minute=0, id="daily_6am")
        scheduler.start()
    except ImportError:
        logger.warning("⚠️  APScheduler not installed – scheduler disabled")

    # Do initial scrape on boot if cache is empty
    if not os.path.exists(JOBS_FILE):
        refresh_jobs()


# ═══════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    data = load_jobs()
    featured = data.get("jobs", [])[:6]
    return render_template("index.html", featured_jobs=featured, last_updated=data.get("last_updated"))


@app.route("/jobs")
def jobs_page():
    return render_template("jobs.html")


@app.route("/job/<int:job_id>")
def job_detail(job_id):
    data = load_jobs()
    jobs = data.get("jobs", [])
    job = next((j for j in jobs if j.get("id") == job_id), None)
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
def student_dashboard():
    return render_template("student_dashboard.html")


@app.route("/employer-dashboard")
def employer_dashboard():
    return render_template("employer_dashboard.html")


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
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.route("/api/jobs")
def api_jobs():
    """
    Return jobs with advanced filtering:
      ?keyword=      – title / company / category / skills
      ?location=     – city / state / display (fuzzy)
      ?country=      – exact country match
      ?city=         – exact city match
      ?type=         – job type
      ?experience=   – experience level
      ?category=     – job category
      ?source=       – Remotive, Indeed, LinkedIn, etc.
      ?sort=         – newest | oldest | title | company
      ?page=         – pagination (default 1)
      ?per_page=     – items per page (default 24, max 100)
    """
    data = load_jobs()
    jobs = data.get("jobs", [])

    # ── Keyword search (title, company, category, skills) ──────────
    keyword = request.args.get("keyword", "").strip().lower()
    if keyword:
        jobs = [
            j for j in jobs
            if keyword in j.get("title", "").lower()
            or keyword in j.get("company", "").lower()
            or keyword in j.get("category", "").lower()
            or keyword in j.get("industry", "").lower()
            or any(keyword in s.lower() for s in j.get("skills", []))
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

    # ── Type / experience / category / source filters ──────────────
    job_type = request.args.get("type", "").strip().lower()
    experience = request.args.get("experience", "").strip().lower()
    category = request.args.get("category", "").strip().lower()
    source = request.args.get("source", "").strip().lower()

    if job_type:
        jobs = [j for j in jobs if job_type in j.get("type", "").lower()]
    if experience:
        jobs = [j for j in jobs if experience in j.get("experience", "").lower()]
    if category:
        jobs = [j for j in jobs if category in j.get("category", "").lower()]
    if source:
        jobs = [j for j in jobs if source in j.get("source", "").lower()]

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
    per_page = min(100, max(1, int(request.args.get("per_page", 24))))
    start = (page - 1) * per_page
    paginated = jobs[start : start + per_page]

    return jsonify({
        "jobs": paginated,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "last_updated": data.get("last_updated"),
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
    count = refresh_jobs()
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

    count = refresh_jobs()
    return jsonify({
        "status": "success",
        "jobs_scraped": count,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


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


# ── Error Handlers ─────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return """
    <html><head><title>404 - Not Found</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    </head><body style="display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center;">
    <div><h1 style="font-size:5rem;color:#667eea;">404</h1><h2>Page Not Found</h2>
    <p style="color:#5f6368;margin:12px 0 24px;">The page you're looking for doesn't exist.</p>
    <a href="/" class="btn btn-primary"><i class="fas fa-home"></i> Go Home</a></div>
    </body></html>
    """, 404


# ── Run (local dev only – Vercel uses the `app` WSGI object) ──────────
if __name__ == "__main__":
    app.run(debug=True, port=8080)
