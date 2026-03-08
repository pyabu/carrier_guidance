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

        # Run trend analysis after scrape
        try:
            from scraper.trend_analyzer import TrendAnalyzer
            analyzer = TrendAnalyzer(DATA_DIR)
            analyzer.analyze(jobs)
            logger.info("📊 Trend analysis complete")
        except Exception as e:
            logger.warning(f"⚠️  Trend analysis skipped: {e}")

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
    """Get the status of the last data refresh."""
    data = load_jobs()
    jobs = data.get("jobs", [])
    last_updated = data.get("last_updated", "Never")

    from collections import Counter
    sources = Counter(j.get("source", "Unknown") for j in jobs)
    countries = Counter(j.get("location_country", "Unknown") for j in jobs)
    categories = Counter(j.get("category", "Other") for j in jobs)

    # Check data freshness
    is_fresh = False
    if last_updated and last_updated != "Never":
        try:
            last_dt = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")
            hours_ago = (datetime.now() - last_dt).total_seconds() / 3600
            is_fresh = hours_ago < 24
        except Exception:
            pass

    return jsonify({
        "last_updated": last_updated,
        "total_jobs": len(jobs),
        "is_fresh": is_fresh,
        "sources": dict(sources),
        "countries_covered": len(countries),
        "categories": dict(categories),
        "top_countries": dict(countries.most_common(10)),
    })


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


# ── WSGI alias (some Vercel runtime versions look for `application`) ───
application = app

# ── Run (local dev only – Vercel uses the `app` WSGI object) ──────────
if __name__ == "__main__":
    app.run(debug=True, port=8080)
