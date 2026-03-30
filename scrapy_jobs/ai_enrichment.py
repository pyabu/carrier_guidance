"""
Careerguidance – AI Job Enrichment Engine
═════════════════════════════════════════════
Uses Google Gemini (free tier) or OpenAI to:
  1. Extract & validate skills from job descriptions
  2. Categorize jobs into career tracks
  3. Score job listing quality
  4. Generate brief summaries
  5. Normalize locations & salary data

Falls back to local NLP if no API key is available.
"""

import os
import re
import json
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# ── Skill Taxonomy ─────────────────────────────────────────────────────
SKILL_TAXONOMY = {
    "Languages": ["Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go",
                   "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "Dart",
                   "Perl", "Lua", "MATLAB", "Shell", "SQL", "HTML", "CSS"],
    "Frontend": ["React", "Angular", "Vue.js", "Next.js", "Nuxt.js", "Svelte",
                  "Tailwind CSS", "Bootstrap", "jQuery", "Redux", "Webpack",
                  "TypeScript", "HTML5", "CSS3", "SASS", "Material UI"],
    "Backend": ["Node.js", "Django", "Flask", "FastAPI", "Spring Boot", "Express.js",
                 "Rails", "ASP.NET", "Laravel", "NestJS", "GraphQL", "REST APIs",
                 "Microservices", "gRPC"],
    "Databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
                   "DynamoDB", "Cassandra", "Oracle", "SQL Server", "Firebase",
                   "SQLite", "Neo4j", "InfluxDB"],
    "Cloud & DevOps": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform",
                        "Jenkins", "GitHub Actions", "CI/CD", "Ansible", "Helm",
                        "Prometheus", "Grafana", "Nginx", "Linux", "Serverless"],
    "AI / ML": ["TensorFlow", "PyTorch", "scikit-learn", "OpenCV", "NLP",
                 "LLM", "GPT", "Transformers", "Deep Learning", "Computer Vision",
                 "RAG", "Langchain", "Hugging Face", "MLOps", "Neural Networks"],
    "Data": ["Pandas", "NumPy", "Spark", "Hadoop", "Airflow", "dbt", "Tableau",
              "Power BI", "Snowflake", "BigQuery", "Redshift", "Kafka",
              "ETL", "Data Pipeline", "Data Warehouse"],
    "Mobile": ["React Native", "Flutter", "SwiftUI", "Jetpack Compose",
                "iOS", "Android", "Xamarin", "Ionic"],
    "Security": ["OWASP", "Penetration Testing", "SOC", "SIEM", "Firewalls",
                  "Encryption", "IAM", "Zero Trust", "Compliance"],
    "Tools": ["Git", "Jira", "Confluence", "Figma", "Postman", "VS Code",
               "IntelliJ", "Slack", "Notion", "Agile", "Scrum"],
}

# Flatten for lookup
ALL_SKILLS = {}
for category, skills in SKILL_TAXONOMY.items():
    for skill in skills:
        ALL_SKILLS[skill.lower()] = {"name": skill, "category": category}

SKILL_ALIASES = {
    "k8s": "Kubernetes", "k8": "Kubernetes", "js": "JavaScript",
    "ts": "TypeScript", "py": "Python", "pg": "PostgreSQL",
    "postgres": "PostgreSQL", "mongo": "MongoDB", "tf": "Terraform",
    "gke": "Kubernetes", "eks": "Kubernetes", "aks": "Kubernetes",
    "ec2": "AWS", "s3": "AWS", "lambda": "AWS", "sagemaker": "AWS",
    "react.js": "React", "reactjs": "React", "vue": "Vue.js",
    "vuejs": "Vue.js", "angular.js": "Angular", "angularjs": "Angular",
    "node": "Node.js", "nodejs": "Node.js", "express": "Express.js",
    "nextjs": "Next.js", "django rest": "Django", "drf": "Django",
    "spring": "Spring Boot", "dotnet": "ASP.NET", ".net": "ASP.NET",
    "aws cloud": "AWS", "google cloud": "GCP", "gcloud": "GCP",
    "ml": "Machine Learning", "dl": "Deep Learning", "ai": "AI / ML",
    "nlp": "NLP", "cv": "Computer Vision", "llms": "LLM",
    "ci cd": "CI/CD", "cicd": "CI/CD",
}

CATEGORY_MAP = {
    "Software Development": ["developer", "engineer", "programmer", "full stack",
                              "frontend", "backend", "web developer", "software"],
    "Data Science": ["data scientist", "data analyst", "analytics", "statistician",
                      "business intelligence", "bi developer"],
    "AI / Machine Learning": ["machine learning", "ai engineer", "deep learning",
                               "nlp", "computer vision", "ml engineer", "llm"],
    "Cloud & DevOps": ["devops", "cloud engineer", "sre", "site reliability",
                        "infrastructure", "platform engineer", "kubernetes"],
    "Mobile Development": ["mobile developer", "android", "ios developer",
                            "flutter", "react native", "mobile engineer"],
    "Cybersecurity": ["security", "cybersecurity", "penetration", "soc analyst",
                       "security engineer", "infosec"],
    "Design": ["ui designer", "ux designer", "product designer", "graphic design",
                "ui/ux", "ux researcher", "visual designer"],
    "Product Management": ["product manager", "product owner", "scrum master",
                            "program manager", "project manager"],
    "Marketing": ["digital marketing", "seo", "content marketing", "growth",
                   "social media", "marketing manager"],
    "QA & Testing": ["qa engineer", "test engineer", "quality assurance",
                      "automation testing", "sdet", "test analyst"],
}


class AIEnrichment:
    """
    AI-powered job data enrichment.
    Uses Gemini API for batch processing, falls back to local NLP.
    """

    def __init__(self, gemini_key=None, openai_key=None):
        self.gemini_key = gemini_key or os.environ.get("GEMINI_API_KEY", "")
        self.openai_key = openai_key or os.environ.get("OPENAI_API_KEY", "")
        self.use_gemini = bool(self.gemini_key)
        self.use_openai = bool(self.openai_key) and not self.use_gemini
        self._gemini_client = None

        if self.use_gemini:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.gemini_key)
                logger.info("🤖 AI Enrichment: Using Google Gemini 2.0 Flash")
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}. Falling back to local NLP.")
                self.use_gemini = False
        elif self.use_openai:
            logger.info("🤖 AI Enrichment: Using OpenAI")
        else:
            logger.info("🤖 AI Enrichment: Using local NLP engine (no API keys)")

    def enrich_job(self, job_dict):
        """Enrich a single job with AI-extracted data."""
        # Always do local extraction first (fast)
        job_dict["ai_skills"] = self._extract_skills_local(job_dict)
        job_dict["ai_category"] = self._categorize_local(job_dict)
        job_dict["ai_quality_score"] = self._score_quality(job_dict)

        return job_dict

    def enrich_batch_with_ai(self, jobs, batch_size=20):
        """
        Use Gemini to enrich a batch of jobs with better skill extraction,
        categorization, and summaries.
        """
        if not self.use_gemini or not self._gemini_client:
            logger.info("No Gemini key – skipping AI batch enrichment")
            return jobs

        enriched = []
        rate_limit_hit = False
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i + batch_size]

            if rate_limit_hit:
                # Already hit rate limit – skip remaining AI calls, use local
                enriched.extend(batch)
                continue

            try:
                enriched_batch = self._gemini_enrich_batch(batch)
                enriched.extend(enriched_batch)
                logger.info(f"🤖 Gemini enriched batch {i // batch_size + 1}: "
                            f"{len(enriched_batch)} jobs")

                # Small delay between batches to avoid rate limits
                import time
                time.sleep(1.5)

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    logger.warning(f"⚠️ Gemini rate limit hit at batch {i // batch_size + 1}. "
                                   f"Remaining jobs will use local NLP enrichment.")
                    rate_limit_hit = True
                    enriched.extend(batch)
                else:
                    logger.warning(f"Gemini batch {i // batch_size + 1} failed: {e}")
                    enriched.extend(batch)

        if rate_limit_hit:
            logger.info("💡 Tip: Gemini free tier allows ~1500 requests/day. "
                        "Quota resets daily. Local NLP was used for remaining jobs.")

        return enriched

    # Models to try (with fallback)
    GEMINI_MODELS = ["gemini-2.0-flash-lite", "gemini-2.0-flash"]

    def _gemini_enrich_batch(self, batch):
        """Send a batch of jobs to Gemini for enrichment with model fallback."""
        # Build a compact representation for the prompt
        jobs_for_prompt = []
        for j in batch:
            jobs_for_prompt.append({
                "idx": len(jobs_for_prompt),
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "desc": (j.get("description", "") or "")[:500],
                "tags": j.get("tags", [])[:10],
            })

        prompt = f"""You are a job data processor. Analyze these {len(jobs_for_prompt)} job listings and return a JSON array with enrichment data.

For each job, return:
- "idx": the original index
- "skills": array of specific technical skills mentioned (e.g. ["Python", "React", "AWS"])
- "category": one of: Software Development, Data Science, AI / Machine Learning, Cloud & DevOps, Mobile Development, Cybersecurity, Design, Product Management, Marketing, QA & Testing, Other
- "experience": "Entry" / "Mid" / "Senior" / "Lead"
- "summary": one-sentence job summary (max 100 chars)

Jobs:
{json.dumps(jobs_for_prompt, indent=None)}

Return ONLY valid JSON array. No markdown, no explanation."""

        from google.genai import types
        last_err = None

        for model_name in self.GEMINI_MODELS:
            try:
                response = self._gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=4096,
                        response_mime_type="application/json",
                    ),
                )

                result_text = response.text.strip()
                # Clean markdown code fences if present
                if result_text.startswith("```"):
                    result_text = re.sub(r"^```\w*\n?", "", result_text)
                    result_text = re.sub(r"\n?```$", "", result_text)

                ai_results = json.loads(result_text)

                # Merge AI results back into batch
                ai_map = {r["idx"]: r for r in ai_results}
                for j in batch:
                    idx = batch.index(j)
                    if idx in ai_map:
                        ai = ai_map[idx]
                        j["ai_skills"] = ai.get("skills", j.get("ai_skills", []))
                        j["ai_category"] = ai.get("category", j.get("ai_category", ""))
                        j["experience_level"] = ai.get("experience", j.get("experience_level", ""))
                        j["ai_summary"] = ai.get("summary", "")
                        existing = set(j.get("skills", []))
                        j["skills"] = list(existing | set(j["ai_skills"]))

                return batch  # Success – return enriched batch

            except Exception as e:
                last_err = e
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    # Try next model (different quota pool)
                    continue
                else:
                    logger.warning(f"Gemini {model_name} error: {e}")
                    break

        # All models exhausted – raise so caller can handle
        if last_err and ("429" in str(last_err) or "RESOURCE_EXHAUSTED" in str(last_err)):
            raise last_err
        elif last_err:
            logger.warning(f"Gemini parse error: {last_err}")

        return batch

    # ── Local NLP Methods ──────────────────────────────────────────────

    def _extract_skills_local(self, job):
        """Extract skills from title + description using keyword matching."""
        text = f"{job.get('title', '')} {job.get('description', '')} {' '.join(job.get('tags', []))}".lower()
        found = set()

        # Check all known skills
        for skill_lower, info in ALL_SKILLS.items():
            # Word boundary matching for short skills
            if len(skill_lower) <= 3:
                if re.search(rf"\b{re.escape(skill_lower)}\b", text):
                    found.add(info["name"])
            elif skill_lower in text:
                found.add(info["name"])

        # Check aliases
        for alias, canonical in SKILL_ALIASES.items():
            if alias in text:
                found.add(canonical)

        return list(found)

    def _categorize_local(self, job):
        """Categorize job based on title keywords."""
        title = job.get("title", "").lower()
        desc = (job.get("description", "") or "").lower()[:500]
        combined = f"{title} {desc}"

        best_cat = "Other"
        best_score = 0

        for category, keywords in CATEGORY_MAP.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_score:
                best_score = score
                best_cat = category

        return best_cat

    def _score_quality(self, job):
        """Score job listing quality (0-100)."""
        score = 0
        if job.get("title"):
            score += 20
        if job.get("company"):
            score += 15
        if job.get("location") and job["location"] != "India":
            score += 10
        if job.get("description") and len(job["description"]) > 100:
            score += 20
        if job.get("salary"):
            score += 15
        if job.get("apply_url"):
            score += 10
        if job.get("skills") or job.get("ai_skills"):
            score += 10
        return min(score, 100)

    def get_trending_skills(self, jobs):
        """Analyze skill frequency across all jobs."""
        all_skills = []
        for job in jobs:
            all_skills.extend(job.get("ai_skills", []))
            all_skills.extend(job.get("skills", []))
        return Counter(all_skills).most_common(20)
