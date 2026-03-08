"""
CareerPath Pro – AI-Powered Job Processor
═══════════════════════════════════════════
Uses AI (OpenAI / free fallback) to:
  1. Smart categorize & tag jobs
  2. Extract key skills from descriptions
  3. Generate concise job summaries
  4. Score job relevance / quality
  5. Detect trending skills & roles
  6. Smart search with NLP understanding
  7. Location intelligence (fuzzy matching)

Works with or without an OpenAI API key.
Falls back to local NLP (TF-IDF + keyword extraction) when no key is set.
"""

import os
import re
import json
import math
import logging
import hashlib
from datetime import datetime
from collections import Counter, defaultdict

logger = logging.getLogger(__name__)

# ── Optional AI imports ────────────────────────────────────────────────
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ═══════════════════════════════════════════════════════════════════════
# SKILL TAXONOMY (comprehensive, 200+ skills)
# ═══════════════════════════════════════════════════════════════════════

SKILL_TAXONOMY = {
    # Programming Languages
    "languages": [
        "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
        "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl",
        "Dart", "Lua", "Haskell", "Elixir", "Clojure", "Julia", "Solidity",
    ],
    # Frontend
    "frontend": [
        "React", "Angular", "Vue.js", "Next.js", "Nuxt.js", "Svelte", "HTML5",
        "CSS3", "Tailwind CSS", "Bootstrap", "Material UI", "Chakra UI",
        "Redux", "MobX", "Zustand", "jQuery", "Webpack", "Vite", "Sass",
    ],
    # Backend
    "backend": [
        "Node.js", "Express.js", "Django", "Flask", "FastAPI", "Spring Boot",
        "Ruby on Rails", "Laravel", "ASP.NET", "Gin", "Fiber", "NestJS",
        "GraphQL", "REST APIs", "gRPC", "WebSocket", "Microservices",
    ],
    # Databases
    "databases": [
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
        "DynamoDB", "SQLite", "Oracle DB", "SQL Server", "Neo4j", "CouchDB",
        "InfluxDB", "TimescaleDB", "Supabase", "Firebase",
    ],
    # Cloud & DevOps
    "cloud_devops": [
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Ansible",
        "Jenkins", "GitHub Actions", "GitLab CI", "CircleCI", "ArgoCD",
        "Helm", "Prometheus", "Grafana", "Datadog", "New Relic", "Nginx",
        "Apache", "Cloudflare", "Vercel", "Netlify", "Heroku",
    ],
    # AI / ML / Data
    "ai_ml": [
        "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
        "TensorFlow", "PyTorch", "Keras", "scikit-learn", "XGBoost",
        "LightGBM", "OpenCV", "Hugging Face", "LangChain", "LlamaIndex",
        "RAG", "Fine-tuning", "Prompt Engineering", "GPT", "BERT",
        "Transformer", "Neural Networks", "Reinforcement Learning",
        "MLOps", "MLflow", "Kubeflow", "Feature Engineering",
    ],
    # Data Engineering
    "data_eng": [
        "Spark", "Hadoop", "Airflow", "Kafka", "Flink", "dbt",
        "BigQuery", "Redshift", "Snowflake", "Databricks", "ETL",
        "Data Pipeline", "Data Warehouse", "Data Lake", "Presto", "Hive",
    ],
    # Data Analysis / BI
    "data_analysis": [
        "SQL", "Tableau", "Power BI", "Looker", "Excel", "Pandas",
        "NumPy", "Matplotlib", "Seaborn", "Plotly", "Jupyter", "R Studio",
        "A/B Testing", "Statistics", "Data Visualization",
    ],
    # Mobile
    "mobile": [
        "React Native", "Flutter", "Swift", "SwiftUI", "Kotlin",
        "Android SDK", "iOS", "Xcode", "Jetpack Compose", "Expo",
    ],
    # Security
    "security": [
        "Cybersecurity", "Penetration Testing", "OWASP", "SOC", "SIEM",
        "IAM", "OAuth", "JWT", "SSL/TLS", "Encryption", "Zero Trust",
        "Vulnerability Assessment", "Incident Response", "CISSP",
    ],
    # Design
    "design": [
        "Figma", "Sketch", "Adobe XD", "Photoshop", "Illustrator",
        "InDesign", "Canva", "Prototyping", "Wireframing", "User Research",
        "Design Systems", "Accessibility", "Information Architecture",
    ],
    # Project / Product
    "management": [
        "Agile", "Scrum", "Kanban", "JIRA", "Confluence", "Asana",
        "Trello", "Monday.com", "Roadmapping", "OKRs", "Sprint Planning",
        "Stakeholder Management", "Risk Management", "PMP", "SAFe",
    ],
    # Marketing
    "marketing": [
        "SEO", "SEM", "Google Ads", "Facebook Ads", "Google Analytics",
        "HubSpot", "Mailchimp", "Content Strategy", "Copywriting",
        "Social Media Marketing", "Email Marketing", "CRO", "Growth Hacking",
    ],
    # Soft Skills
    "soft_skills": [
        "Leadership", "Communication", "Problem Solving", "Teamwork",
        "Critical Thinking", "Time Management", "Presentation Skills",
        "Mentoring", "Negotiation", "Adaptability",
    ],
}

# Flatten for quick lookup
ALL_SKILLS = {}
for category, skills in SKILL_TAXONOMY.items():
    for skill in skills:
        ALL_SKILLS[skill.lower()] = {"name": skill, "category": category}

# ── Synonyms for smart matching ─────────────────────────────────────────
SKILL_SYNONYMS = {
    "js": "JavaScript", "ts": "TypeScript", "py": "Python",
    "k8s": "Kubernetes", "tf": "Terraform", "postgres": "PostgreSQL",
    "mongo": "MongoDB", "react.js": "React", "vue": "Vue.js",
    "node": "Node.js", "express": "Express.js", "django rest": "Django",
    "spring": "Spring Boot", "dotnet": ".NET", "asp.net": "ASP.NET",
    "rails": "Ruby on Rails", "c sharp": "C#", "objective-c": "Swift",
    "android": "Android SDK", "ios development": "iOS",
    "aws cloud": "AWS", "google cloud": "GCP", "microsoft azure": "Azure",
    "ci cd": "CI/CD", "github ci": "GitHub Actions", "gitlab ci": "GitLab CI",
    "elasticsearch": "Elasticsearch", "elastic": "Elasticsearch",
    "data science": "Machine Learning", "ml": "Machine Learning",
    "dl": "Deep Learning", "llm": "GPT", "chatgpt": "GPT",
    "natural language processing": "NLP", "cv": "Computer Vision",
    "big data": "Spark", "stream processing": "Kafka",
    "user experience": "User Research", "ux design": "User Research",
    "ui design": "Figma", "product design": "Figma",
    "project management": "Agile", "pm": "Agile",
    "search engine optimization": "SEO", "ppc": "Google Ads",
}

# ═══════════════════════════════════════════════════════════════════════
# JOB QUALITY & RELEVANCE SCORING
# ═══════════════════════════════════════════════════════════════════════

QUALITY_WEIGHTS = {
    "has_title": 10,
    "has_company": 10,
    "has_description": 15,
    "description_length": 10,   # scaled by length
    "has_salary": 15,
    "has_skills": 10,
    "has_apply_url": 10,
    "has_location": 5,
    "has_posted_date": 5,
    "from_api_source": 10,     # vs generated
}


class AIJobProcessor:
    """
    AI-powered job processing engine.
    Enhances scraped jobs with:
      - Smart skill extraction
      - Quality scoring
      - Category mapping
      - Trend detection
      - Semantic search
      - Location intelligence
    """

    def __init__(self):
        self.openai_key = os.environ.get("OPENAI_API_KEY", "")
        self.use_ai = bool(self.openai_key and HAS_OPENAI)
        if self.use_ai:
            openai.api_key = self.openai_key
            logger.info("🤖 AI Processor initialized with OpenAI")
        else:
            logger.info("🧠 AI Processor using local NLP engine (no OpenAI key)")

        # TF-IDF cache
        self._tfidf_cache = {}
        self._skill_index = self._build_skill_index()

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def process_jobs(self, jobs: list[dict]) -> list[dict]:
        """
        Process all jobs through the AI pipeline:
          1. Extract skills
          2. Score quality
          3. Categorize
          4. Generate summary
          5. Tag trending
        """
        logger.info(f"🤖 Processing {len(jobs)} jobs through AI pipeline...")

        skill_counter = Counter()
        role_counter = Counter()

        for job in jobs:
            # 1. Enhanced skill extraction
            extracted = self.extract_skills(
                job.get("description", "") + " " + job.get("title", "")
            )
            existing = job.get("skills", [])
            merged = list(dict.fromkeys(existing + extracted))[:8]
            job["skills"] = merged

            # 2. Quality score
            job["quality_score"] = self.score_quality(job)

            # 3. AI Summary (only for high-quality jobs, and only with OpenAI)
            if self.use_ai and job["quality_score"] >= 70 and len(job.get("description", "")) > 200:
                job["ai_summary"] = self._generate_summary_ai(job)
            else:
                job["ai_summary"] = self._generate_summary_local(job)

            # 4. Smart category validation
            job["category"] = self._validate_category(job)

            # 5. Track for trending
            for skill in job["skills"]:
                skill_counter[skill] += 1
            role_counter[job.get("title", "")] += 1

        # 6. Tag trending skills on each job
        top_skills = set(s for s, _ in skill_counter.most_common(20))
        for job in jobs:
            job["trending_skills"] = [s for s in job.get("skills", []) if s in top_skills]
            job["is_trending"] = len(job.get("trending_skills", [])) >= 2

        logger.info(f"✅ AI processing complete. Top skills: {skill_counter.most_common(10)}")
        return jobs

    def extract_skills(self, text: str) -> list[str]:
        """
        Extract skills from text using multi-strategy approach:
          1. Direct keyword matching against taxonomy
          2. Synonym resolution
          3. Contextual N-gram matching
        """
        if not text:
            return []

        text_lower = text.lower()
        found_skills = set()

        # Strategy 1: Direct match from taxonomy
        for skill_lower, info in ALL_SKILLS.items():
            # Word boundary matching for short skills to avoid false positives
            if len(skill_lower) <= 3:
                if re.search(r'\b' + re.escape(skill_lower) + r'\b', text_lower):
                    found_skills.add(info["name"])
            else:
                if skill_lower in text_lower:
                    found_skills.add(info["name"])

        # Strategy 2: Synonym matching
        for synonym, canonical in SKILL_SYNONYMS.items():
            if synonym in text_lower:
                found_skills.add(canonical)

        # Strategy 3: Contextual patterns
        patterns = [
            (r'experience\s+(?:with|in)\s+(\w+(?:\.\w+)?)', None),
            (r'proficiency\s+in\s+(\w+(?:\.\w+)?)', None),
            (r'knowledge\s+of\s+(\w+(?:\.\w+)?)', None),
            (r'skilled\s+in\s+(\w+(?:\.\w+)?)', None),
            (r'(\w+(?:\.\w+)?)\s+developer', None),
            (r'(\w+(?:\.\w+)?)\s+engineer', None),
        ]
        for pattern, _ in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if match in ALL_SKILLS:
                    found_skills.add(ALL_SKILLS[match]["name"])

        return sorted(found_skills)[:8]

    def score_quality(self, job: dict) -> int:
        """Score job quality from 0-100 based on completeness and data quality."""
        score = 0

        if job.get("title") and job["title"] != "Open Position":
            score += QUALITY_WEIGHTS["has_title"]
        if job.get("company") and job["company"] != "Confidential":
            score += QUALITY_WEIGHTS["has_company"]

        desc = job.get("description", "")
        if desc and desc != "No description provided.":
            score += QUALITY_WEIGHTS["has_description"]
            # Bonus for longer descriptions
            length_bonus = min(10, len(desc) / 100)
            score += length_bonus

        sal = job.get("salary_min", "")
        if sal and sal != "Competitive":
            score += QUALITY_WEIGHTS["has_salary"]

        if job.get("skills") and len(job["skills"]) >= 2:
            score += QUALITY_WEIGHTS["has_skills"]

        if job.get("apply_url") and job["apply_url"] != "#":
            score += QUALITY_WEIGHTS["has_apply_url"]

        if job.get("location") and job["location"] != "Remote":
            score += QUALITY_WEIGHTS["has_location"]

        if job.get("posted_date"):
            score += QUALITY_WEIGHTS["has_posted_date"]

        if job.get("source", "") != "CareerPath Pro":
            score += QUALITY_WEIGHTS["has_apply_url"]

        return min(100, int(score))

    def smart_search(self, query: str, jobs: list[dict], top_k: int = 50) -> list[dict]:
        """
        AI-powered semantic search:
          1. Expand query with synonyms
          2. Multi-field matching with TF-IDF scoring
          3. Skill-aware ranking
          4. Location-aware boosting
        """
        if not query.strip():
            return jobs[:top_k]

        query_lower = query.lower().strip()
        expanded_terms = self._expand_query(query_lower)

        scored_jobs = []
        for job in jobs:
            score = self._compute_relevance(job, query_lower, expanded_terms)
            if score > 0:
                scored_jobs.append((score, job))

        scored_jobs.sort(key=lambda x: x[0], reverse=True)
        return [job for _, job in scored_jobs[:top_k]]

    def get_trending_analysis(self, jobs: list[dict]) -> dict:
        """
        Analyze job market trends:
          - Top skills in demand
          - Fastest growing roles
          - Top hiring companies
          - Location hotspots
          - Salary ranges by role
          - Category distribution
        """
        skill_counter = Counter()
        role_counter = Counter()
        company_counter = Counter()
        location_counter = Counter()
        category_counter = Counter()
        source_counter = Counter()
        salary_by_role = defaultdict(list)
        skills_by_category = defaultdict(Counter)

        for job in jobs:
            for skill in job.get("skills", []):
                skill_counter[skill] += 1
                skills_by_category[job.get("category", "Other")][skill] += 1

            role_counter[job.get("title", "Unknown")] += 1
            company_counter[job.get("company", "Unknown")] += 1
            location_counter[job.get("location_city", "Unknown")] += 1
            category_counter[job.get("category", "Other")] += 1
            source_counter[job.get("source", "Unknown")] += 1

            sal = job.get("salary_min", "")
            if sal and sal != "Competitive":
                salary_by_role[job.get("title", "Unknown")].append(sal)

        return {
            "total_jobs": len(jobs),
            "top_skills": [{"skill": s, "count": c} for s, c in skill_counter.most_common(25)],
            "top_roles": [{"role": r, "count": c} for r, c in role_counter.most_common(20)],
            "top_companies": [{"company": co, "count": c} for co, c in company_counter.most_common(20)],
            "top_locations": [{"city": l, "count": c} for l, c in location_counter.most_common(20)],
            "categories": dict(category_counter),
            "sources": dict(source_counter),
            "skills_by_category": {
                cat: [{"skill": s, "count": c} for s, c in counter.most_common(10)]
                for cat, counter in skills_by_category.items()
            },
            "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def get_ai_recommendations(self, user_skills: list[str], jobs: list[dict], top_k: int = 10) -> list[dict]:
        """
        Given a user's skills, recommend best-matching jobs using AI scoring.
        """
        user_skills_lower = {s.lower() for s in user_skills}
        scored = []

        for job in jobs:
            job_skills_lower = {s.lower() for s in job.get("skills", [])}
            overlap = user_skills_lower & job_skills_lower
            if not overlap:
                continue

            # Jaccard similarity
            union = user_skills_lower | job_skills_lower
            similarity = len(overlap) / len(union) if union else 0

            # Quality boost
            quality = job.get("quality_score", 50) / 100

            # Combined score
            score = (similarity * 0.7) + (quality * 0.3)

            scored.append({
                **job,
                "match_score": round(score * 100),
                "matching_skills": list(overlap),
                "missing_skills": list(job_skills_lower - user_skills_lower),
            })

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        return scored[:top_k]

    # ──────────────────────────────────────────────────────────────────
    # PRIVATE METHODS
    # ──────────────────────────────────────────────────────────────────

    def _build_skill_index(self) -> dict:
        """Build inverted index: skill → list of related skills."""
        index = defaultdict(set)
        for category, skills in SKILL_TAXONOMY.items():
            for skill in skills:
                for other in skills:
                    if skill != other:
                        index[skill.lower()].add(other)
        return index

    def _expand_query(self, query: str) -> set:
        """Expand query with synonyms and related terms."""
        terms = set(query.split())

        # Add synonym expansions
        for term in list(terms):
            if term in SKILL_SYNONYMS:
                terms.add(SKILL_SYNONYMS[term].lower())
            # Check ALL_SKILLS for matches
            if term in ALL_SKILLS:
                terms.add(ALL_SKILLS[term]["name"].lower())
                # Add related skills from same category
                category = ALL_SKILLS[term]["category"]
                related = SKILL_TAXONOMY.get(category, [])[:3]
                for r in related:
                    terms.add(r.lower())

        # Common job title expansions
        title_synonyms = {
            "sde": {"software engineer", "software developer"},
            "swe": {"software engineer"},
            "fe": {"frontend developer", "front end"},
            "be": {"backend developer", "back end"},
            "fs": {"full stack developer"},
            "pm": {"product manager", "project manager"},
            "ds": {"data scientist", "data science"},
            "de": {"data engineer"},
            "ml": {"machine learning", "ml engineer"},
            "devops": {"devops engineer", "site reliability"},
            "qa": {"qa engineer", "quality assurance", "tester"},
            "ux": {"ux designer", "ui/ux", "user experience"},
            "ui": {"ui designer", "ui/ux", "user interface"},
        }
        for term in list(terms):
            if term in title_synonyms:
                terms.update(title_synonyms[term])

        return terms

    def _compute_relevance(self, job: dict, query: str, expanded_terms: set) -> float:
        """Compute relevance score between job and search query."""
        score = 0.0

        title = job.get("title", "").lower()
        company = job.get("company", "").lower()
        category = job.get("category", "").lower()
        location = job.get("location", "").lower()
        skills = [s.lower() for s in job.get("skills", [])]
        desc = job.get("description", "").lower()[:500]

        # Exact match in title (highest weight)
        if query in title:
            score += 50

        # Expanded term matching
        for term in expanded_terms:
            if term in title:
                score += 20
            if term in company:
                score += 10
            if term in category:
                score += 8
            if term in skills:
                score += 15
            if term in desc:
                score += 3
            if term in location:
                score += 5

        # Quality bonus
        score += job.get("quality_score", 50) * 0.1

        # Trending bonus
        if job.get("is_trending"):
            score += 5

        return score

    def _generate_summary_ai(self, job: dict) -> str:
        """Generate job summary using OpenAI."""
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "You are a career advisor. Summarize this job posting in 2-3 sentences, highlighting key requirements and benefits. Be concise."
                }, {
                    "role": "user",
                    "content": f"Title: {job.get('title')}\nCompany: {job.get('company')}\nDescription: {job.get('description', '')[:800]}"
                }],
                max_tokens=100,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.debug(f"OpenAI summary failed: {e}")
            return self._generate_summary_local(job)

    def _generate_summary_local(self, job: dict) -> str:
        """Generate a concise summary without AI."""
        title = job.get("title", "Open Position")
        company = job.get("company", "a company")
        skills = job.get("skills", [])
        location = job.get("location", "")
        job_type = job.get("type", "")

        skill_str = ", ".join(skills[:3]) if skills else "relevant technologies"
        parts = [f"{title} at {company}"]
        if location:
            parts.append(f"based in {location}")
        if job_type:
            parts.append(f"({job_type})")
        parts.append(f"requiring {skill_str}.")

        return " ".join(parts)

    def _validate_category(self, job: dict) -> str:
        """Validate and potentially fix job category using skills and title."""
        current = job.get("category", "Technology")
        title = job.get("title", "").lower()
        skills = [s.lower() for s in job.get("skills", [])]

        # Check if skills suggest a different category
        category_signals = {
            "Data Science": {"machine learning", "deep learning", "nlp", "tensorflow",
                              "pytorch", "data science", "statistics", "pandas", "numpy"},
            "Design": {"figma", "sketch", "photoshop", "illustrator", "ux", "ui",
                       "wireframing", "prototyping", "design systems"},
            "Marketing": {"seo", "sem", "google ads", "content strategy", "social media",
                          "hubspot", "email marketing", "copywriting"},
            "Management": {"agile", "scrum", "roadmapping", "stakeholder management",
                           "sprint planning", "okrs"},
            "Internship": set(),
        }

        # Title-based overrides
        if "intern" in title:
            return "Internship"
        if "data scien" in title or "ml engi" in title or "machine learn" in title:
            return "Data Science"
        if "design" in title and ("ui" in title or "ux" in title or "product" in title):
            return "Design"
        if "marketing" in title or "seo" in title or "content" in title:
            return "Marketing"
        if "product manager" in title or "project manager" in title or "scrum" in title:
            return "Management"

        # Skill-based validation
        skill_set = set(skills)
        for cat, signals in category_signals.items():
            if len(skill_set & signals) >= 2:
                return cat

        return current


# ═══════════════════════════════════════════════════════════════════════
# LOCATION INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════

class LocationIntelligence:
    """
    Smart location matching with:
      - Fuzzy matching
      - Alias resolution (Bengaluru ↔ Bangalore)
      - Nearby city suggestions
      - State/region awareness
    """

    CITY_ALIASES = {
        "bengaluru": "Bangalore", "bangalore": "Bangalore",
        "mumbai": "Mumbai", "bombay": "Mumbai",
        "chennai": "Chennai", "madras": "Chennai",
        "kolkata": "Kolkata", "calcutta": "Kolkata",
        "pune": "Pune", "poona": "Pune",
        "hyderabad": "Hyderabad", "hyd": "Hyderabad",
        "delhi": "Delhi NCR", "new delhi": "Delhi NCR", "ncr": "Delhi NCR",
        "gurgaon": "Gurugram", "gurugram": "Gurugram",
        "noida": "Noida", "greater noida": "Greater Noida",
        "trivandrum": "Thiruvananthapuram", "thiruvananthapuram": "Thiruvananthapuram",
        "trichy": "Tiruchirappalli", "tiruchirappalli": "Tiruchirappalli",
        "coimbatore": "Coimbatore", "kovai": "Coimbatore",
        "madurai": "Madurai",
        "pondicherry": "Puducherry", "puducherry": "Puducherry",
        "vizag": "Visakhapatnam", "visakhapatnam": "Visakhapatnam",
        "sf": "San Francisco", "san francisco": "San Francisco",
        "nyc": "New York", "new york": "New York",
        "la": "Los Angeles", "los angeles": "Los Angeles",
        "bay area": "San Francisco", "silicon valley": "San Jose",
        "london": "London", "ldn": "London",
        "remote": "Remote", "wfh": "Remote", "work from home": "Remote",
    }

    CITY_REGIONS = {
        "North India": ["Delhi NCR", "Noida", "Greater Noida", "Gurugram", "Ghaziabad",
                        "Lucknow", "Chandigarh", "Jaipur"],
        "South India": ["Bangalore", "Chennai", "Hyderabad", "Kochi", "Coimbatore",
                        "Madurai", "Thiruvananthapuram", "Mysore", "Mangalore"],
        "West India": ["Mumbai", "Pune", "Ahmedabad", "Surat", "Nagpur", "Nashik"],
        "East India": ["Kolkata", "Bhubaneswar", "Patna", "Ranchi", "Guwahati"],
        "US West Coast": ["San Francisco", "Los Angeles", "Seattle", "San Jose",
                          "Mountain View"],
        "US East Coast": ["New York", "Boston", "Atlanta", "Chicago"],
    }

    @classmethod
    def resolve_location(cls, query: str) -> str:
        """Resolve location aliases to canonical names."""
        q = query.lower().strip()
        return cls.CITY_ALIASES.get(q, query.strip())

    @classmethod
    def get_nearby_cities(cls, city: str, radius: int = 5) -> list[str]:
        """Get nearby/related cities for a given city."""
        city_lower = city.lower()
        canonical = cls.CITY_ALIASES.get(city_lower, city)
        nearby = []
        for region, cities in cls.CITY_REGIONS.items():
            if canonical in cities:
                nearby = [c for c in cities if c != canonical]
                break
        return nearby[:radius]

    @classmethod
    def fuzzy_match_location(cls, query: str, locations: list[str], threshold: float = 0.6) -> list[str]:
        """Simple fuzzy matching for locations."""
        q = query.lower().strip()
        resolved = cls.CITY_ALIASES.get(q, q)
        matches = []
        for loc in locations:
            loc_lower = loc.lower()
            # Exact or contains match
            if resolved.lower() in loc_lower or loc_lower in resolved.lower():
                matches.append(loc)
            # Character overlap ratio
            elif cls._char_similarity(resolved.lower(), loc_lower) >= threshold:
                matches.append(loc)
        return matches

    @staticmethod
    def _char_similarity(a: str, b: str) -> float:
        """Simple character-based similarity."""
        if not a or not b:
            return 0.0
        a_set = set(a)
        b_set = set(b)
        overlap = a_set & b_set
        return len(overlap) / max(len(a_set), len(b_set))
