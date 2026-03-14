"""
Careerguidance – Job Market Trend Analyzer
═══════════════════════════════════════════
Analyzes job market data to produce:
  1. Trending skills (rising demand)
  2. Hot job roles
  3. Top hiring companies & locations
  4. Salary insights
  5. Industry growth signals
  6. Historical comparison (if data available)
  7. Career path recommendations

Runs as part of the daily refresh pipeline.
Saves trend data for the frontend dashboard.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    Analyze job market trends from scraped data.
    Produces insights for dashboards and AI recommendations.
    """

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.trends_file = os.path.join(self.data_dir, "trends.json")
        self.history_file = os.path.join(self.data_dir, "trend_history.json")

    def analyze(self, jobs: list[dict]) -> dict:
        """
        Run full trend analysis on job data.
        Returns comprehensive insights dict.
        """
        logger.info(f"📊 Analyzing trends for {len(jobs)} jobs...")

        analysis = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_jobs": len(jobs),

            # Core metrics
            "skills": self._analyze_skills(jobs),
            "roles": self._analyze_roles(jobs),
            "companies": self._analyze_companies(jobs),
            "locations": self._analyze_locations(jobs),
            "categories": self._analyze_categories(jobs),
            "sources": self._analyze_sources(jobs),

            # Salary insights
            "salary_insights": self._analyze_salaries(jobs),

            # Growth signals
            "freshness": self._analyze_freshness(jobs),

            # Career path data
            "career_paths": self._generate_career_paths(jobs),

            # Recommendations
            "hot_combinations": self._find_hot_skill_combos(jobs),
        }

        # Save trends
        self._save_trends(analysis)
        self._update_history(analysis)

        logger.info("✅ Trend analysis complete")
        return analysis

    def get_latest_trends(self) -> dict:
        """Load the most recent trend analysis."""
        if os.path.exists(self.trends_file):
            with open(self.trends_file, "r") as f:
                return json.load(f)
        return {}

    def get_trend_history(self, days: int = 30) -> list[dict]:
        """Load trend history for the past N days."""
        if not os.path.exists(self.history_file):
            return []
        with open(self.history_file, "r") as f:
            history = json.load(f)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [h for h in history if h.get("date", "") >= cutoff]

    # ──────────────────────────────────────────────────────────────────
    # ANALYSIS METHODS
    # ──────────────────────────────────────────────────────────────────

    def _analyze_skills(self, jobs: list[dict]) -> dict:
        """Analyze skill demand patterns."""
        skill_counter = Counter()
        skill_by_type = defaultdict(Counter)
        skill_by_exp = defaultdict(Counter)
        skill_by_country = defaultdict(Counter)

        for job in jobs:
            skills = job.get("skills", [])
            job_type = job.get("type", "Unknown")
            exp = job.get("experience", "Unknown")
            country = job.get("location_country", "Unknown")

            for skill in skills:
                skill_counter[skill] += 1
                skill_by_type[job_type][skill] += 1
                skill_by_exp[exp][skill] += 1
                skill_by_country[country][skill] += 1

        return {
            "top_25": [{"skill": s, "count": c, "percentage": round(c / len(jobs) * 100, 1)}
                       for s, c in skill_counter.most_common(25)],
            "by_job_type": {
                t: [{"skill": s, "count": c} for s, c in counter.most_common(10)]
                for t, counter in skill_by_type.items()
            },
            "by_experience": {
                e: [{"skill": s, "count": c} for s, c in counter.most_common(10)]
                for e, counter in skill_by_exp.items()
            },
            "by_country": {
                co: [{"skill": s, "count": c} for s, c in counter.most_common(10)]
                for co, counter in list(skill_by_country.items())[:10]
            },
            "total_unique": len(skill_counter),
        }

    def _analyze_roles(self, jobs: list[dict]) -> dict:
        """Analyze role/title patterns."""
        role_counter = Counter()
        role_by_exp = defaultdict(Counter)

        for job in jobs:
            title = job.get("title", "Unknown")
            exp = job.get("experience", "Unknown")
            role_counter[title] += 1
            role_by_exp[exp][title] += 1

        return {
            "top_20": [{"role": r, "count": c} for r, c in role_counter.most_common(20)],
            "by_experience": {
                e: [{"role": r, "count": c} for r, c in counter.most_common(5)]
                for e, counter in role_by_exp.items()
            },
            "total_unique": len(role_counter),
        }

    def _analyze_companies(self, jobs: list[dict]) -> dict:
        """Analyze hiring companies."""
        company_counter = Counter()
        company_categories = defaultdict(set)

        for job in jobs:
            company = job.get("company", "Unknown")
            cat = job.get("category", "Other")
            company_counter[company] += 1
            company_categories[company].add(cat)

        top_companies = []
        for company, count in company_counter.most_common(30):
            top_companies.append({
                "company": company,
                "open_positions": count,
                "categories": list(company_categories.get(company, set())),
            })

        return {
            "top_30": top_companies,
            "total_unique": len(company_counter),
        }

    def _analyze_locations(self, jobs: list[dict]) -> dict:
        """Analyze location distribution."""
        city_counter = Counter()
        country_counter = Counter()
        remote_count = 0

        for job in jobs:
            city = job.get("location_city", "Unknown")
            country = job.get("location_country", "Unknown")
            job_type = job.get("type", "").lower()

            city_counter[city] += 1
            country_counter[country] += 1
            if "remote" in job_type or city.lower() == "remote":
                remote_count += 1

        return {
            "top_cities": [{"city": c, "count": n} for c, n in city_counter.most_common(20)],
            "top_countries": [{"country": c, "count": n} for c, n in country_counter.most_common(15)],
            "remote_percentage": round(remote_count / max(len(jobs), 1) * 100, 1),
            "total_remote": remote_count,
        }

    def _analyze_categories(self, jobs: list[dict]) -> dict:
        """Analyze job category distribution."""
        cat_counter = Counter()
        cat_by_country = defaultdict(Counter)

        for job in jobs:
            cat = job.get("category", "Other")
            country = job.get("location_country", "Unknown")
            cat_counter[cat] += 1
            cat_by_country[country][cat] += 1

        return {
            "distribution": [
                {"category": c, "count": n, "percentage": round(n / max(len(jobs), 1) * 100, 1)}
                for c, n in cat_counter.most_common()
            ],
            "by_country": {
                co: [{"category": c, "count": n} for c, n in counter.most_common(5)]
                for co, counter in list(cat_by_country.items())[:10]
            },
        }

    def _analyze_sources(self, jobs: list[dict]) -> dict:
        """Analyze data source quality."""
        source_counter = Counter()
        source_quality = defaultdict(list)

        for job in jobs:
            src = job.get("source", "Unknown")
            source_counter[src] += 1
            quality = job.get("quality_score", 50)
            source_quality[src].append(quality)

        return {
            "distribution": [
                {
                    "source": s,
                    "count": c,
                    "avg_quality": round(sum(source_quality[s]) / max(len(source_quality[s]), 1), 1),
                }
                for s, c in source_counter.most_common()
            ],
        }

    def _analyze_salaries(self, jobs: list[dict]) -> dict:
        """Analyze salary data where available."""
        salary_by_role = defaultdict(list)
        salary_by_exp = defaultdict(list)

        for job in jobs:
            sal = job.get("salary_min", "")
            if not sal or sal == "Competitive":
                continue

            role = job.get("title", "Unknown")
            exp = job.get("experience", "Unknown")
            salary_by_role[role].append(sal)
            salary_by_exp[exp].append(sal)

        return {
            "jobs_with_salary": sum(1 for j in jobs if j.get("salary_min", "Competitive") != "Competitive"),
            "salary_transparency": round(
                sum(1 for j in jobs if j.get("salary_min", "Competitive") != "Competitive")
                / max(len(jobs), 1) * 100, 1
            ),
            "by_experience": {
                exp: {"count": len(sals), "sample": sals[:3]}
                for exp, sals in salary_by_exp.items()
            },
        }

    def _analyze_freshness(self, jobs: list[dict]) -> dict:
        """Analyze how fresh the job data is."""
        today = datetime.now().date()
        age_buckets = {"today": 0, "this_week": 0, "this_month": 0, "older": 0}

        for job in jobs:
            posted = job.get("posted_date", "")
            if not posted:
                age_buckets["older"] += 1
                continue
            try:
                post_date = datetime.strptime(posted, "%Y-%m-%d").date()
                diff = (today - post_date).days
                if diff == 0:
                    age_buckets["today"] += 1
                elif diff <= 7:
                    age_buckets["this_week"] += 1
                elif diff <= 30:
                    age_buckets["this_month"] += 1
                else:
                    age_buckets["older"] += 1
            except ValueError:
                age_buckets["older"] += 1

        return age_buckets

    def _generate_career_paths(self, jobs: list[dict]) -> list[dict]:
        """Generate career path recommendations based on job data."""
        paths = [
            {
                "name": "Full Stack Developer",
                "stages": [
                    {"level": "Intern", "role": "Software Engineering Intern", "skills": ["HTML", "CSS", "JavaScript", "Git"]},
                    {"level": "Junior", "role": "Junior Developer", "skills": ["React", "Node.js", "SQL", "REST APIs"]},
                    {"level": "Mid", "role": "Full Stack Developer", "skills": ["TypeScript", "Docker", "MongoDB", "CI/CD"]},
                    {"level": "Senior", "role": "Senior Full Stack Developer", "skills": ["System Design", "Microservices", "AWS", "Kubernetes"]},
                    {"level": "Lead", "role": "Tech Lead / Architect", "skills": ["Architecture", "Leadership", "Team Management"]},
                ],
                "avg_salary_progression": ["₹3-5 LPA", "₹6-12 LPA", "₹12-24 LPA", "₹24-40 LPA", "₹40-60 LPA"],
            },
            {
                "name": "Data Scientist",
                "stages": [
                    {"level": "Intern", "role": "Data Science Intern", "skills": ["Python", "Statistics", "SQL", "Excel"]},
                    {"level": "Junior", "role": "Data Analyst", "skills": ["Pandas", "Tableau", "A/B Testing", "SQL"]},
                    {"level": "Mid", "role": "Data Scientist", "skills": ["Machine Learning", "scikit-learn", "Deep Learning", "NLP"]},
                    {"level": "Senior", "role": "Senior Data Scientist", "skills": ["PyTorch", "MLOps", "Feature Engineering", "Research"]},
                    {"level": "Lead", "role": "ML Engineering Manager", "skills": ["Team Leadership", "Strategy", "MLOps", "Product Sense"]},
                ],
                "avg_salary_progression": ["₹3-6 LPA", "₹8-15 LPA", "₹15-30 LPA", "₹30-50 LPA", "₹50-80 LPA"],
            },
            {
                "name": "DevOps / Cloud Engineer",
                "stages": [
                    {"level": "Intern", "role": "IT / Cloud Intern", "skills": ["Linux", "Git", "Bash", "Networking"]},
                    {"level": "Junior", "role": "Junior DevOps Engineer", "skills": ["Docker", "CI/CD", "AWS Basics", "Terraform"]},
                    {"level": "Mid", "role": "DevOps Engineer", "skills": ["Kubernetes", "Prometheus", "Ansible", "IaC"]},
                    {"level": "Senior", "role": "Senior DevOps / SRE", "skills": ["Multi-Cloud", "Security", "SLOs", "Incident Management"]},
                    {"level": "Lead", "role": "Platform Architect", "skills": ["Architecture", "Cost Optimization", "Team Leadership"]},
                ],
                "avg_salary_progression": ["₹3-5 LPA", "₹7-14 LPA", "₹14-28 LPA", "₹28-45 LPA", "₹45-70 LPA"],
            },
            {
                "name": "AI / ML Engineer",
                "stages": [
                    {"level": "Intern", "role": "ML Intern", "skills": ["Python", "NumPy", "Pandas", "Linear Algebra"]},
                    {"level": "Junior", "role": "ML Engineer", "skills": ["scikit-learn", "TensorFlow", "Feature Engineering", "SQL"]},
                    {"level": "Mid", "role": "ML Engineer", "skills": ["PyTorch", "NLP", "Computer Vision", "MLOps"]},
                    {"level": "Senior", "role": "Senior ML Engineer / GenAI", "skills": ["LLMs", "RAG", "Fine-tuning", "Distributed Training"]},
                    {"level": "Lead", "role": "AI Lead / Research Scientist", "skills": ["Research", "Publications", "Team Building", "Strategy"]},
                ],
                "avg_salary_progression": ["₹4-7 LPA", "₹10-18 LPA", "₹18-35 LPA", "₹35-60 LPA", "₹60-1Cr+"],
            },
            {
                "name": "Product Manager",
                "stages": [
                    {"level": "Intern", "role": "PM Intern / APM", "skills": ["Market Research", "User Interviews", "Wireframing", "Analytics"]},
                    {"level": "Junior", "role": "Associate PM", "skills": ["PRDs", "Agile", "SQL", "A/B Testing"]},
                    {"level": "Mid", "role": "Product Manager", "skills": ["Roadmapping", "Strategy", "Stakeholder Management", "Metrics"]},
                    {"level": "Senior", "role": "Senior PM", "skills": ["P&L Ownership", "Team Leadership", "Go-to-Market", "OKRs"]},
                    {"level": "Lead", "role": "VP Product / CPO", "skills": ["Vision", "Board Presentation", "Multi-Product Strategy"]},
                ],
                "avg_salary_progression": ["₹4-8 LPA", "₹10-18 LPA", "₹18-35 LPA", "₹35-55 LPA", "₹55-1Cr+"],
            },
        ]

        # Enrich with actual job counts from data
        for path in paths:
            relevant_jobs = 0
            for stage in path["stages"]:
                role_lower = stage["role"].lower()
                matching = sum(
                    1 for j in jobs
                    if any(word in j.get("title", "").lower() for word in role_lower.split()[:2])
                )
                stage["available_jobs"] = matching
                relevant_jobs += matching
            path["total_available_jobs"] = relevant_jobs

        return paths

    def _find_hot_skill_combos(self, jobs: list[dict]) -> list[dict]:
        """Find the most in-demand skill combinations."""
        combo_counter = Counter()

        for job in jobs:
            skills = sorted(job.get("skills", []))[:5]
            for i in range(len(skills)):
                for j in range(i + 1, len(skills)):
                    combo = f"{skills[i]} + {skills[j]}"
                    combo_counter[combo] += 1

        return [
            {"combination": combo, "demand": count}
            for combo, count in combo_counter.most_common(15)
        ]

    # ──────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────

    def _save_trends(self, analysis: dict):
        """Save latest trend analysis."""
        with open(self.trends_file, "w") as f:
            json.dump(analysis, f, indent=2)
        logger.info(f"💾 Trends saved to {self.trends_file}")

    def _update_history(self, analysis: dict):
        """Append today's summary to trend history."""
        history = []
        if os.path.exists(self.history_file):
            with open(self.history_file, "r") as f:
                history = json.load(f)

        today = datetime.now().strftime("%Y-%m-%d")
        summary = {
            "date": today,
            "total_jobs": analysis["total_jobs"],
            "top_5_skills": [s["skill"] for s in analysis["skills"]["top_25"][:5]],
            "top_5_companies": [c["company"] for c in analysis["companies"]["top_30"][:5]],
            "remote_percentage": analysis["locations"]["remote_percentage"],
        }

        # Remove existing entry for today
        history = [h for h in history if h.get("date") != today]
        history.append(summary)

        # Keep only last 90 days
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        history = [h for h in history if h.get("date", "") >= cutoff]

        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)
