"""
Careerguidance – Scrapy Pipelines
═════════════════════════════════════
1. CleaningPipeline   – Normalize text, fix encoding, clean HTML
2. DedupPipeline      – Remove duplicate jobs by title+company
3. AIEnrichmentPipeline – Extract skills, categorize, score via AI
4. JsonExportPipeline  – Save results to JSON files
"""

import os
import re
import json
import hashlib
import logging
from datetime import datetime
from collections import Counter

from scrapy.exceptions import DropItem
from scrapy_jobs.ai_enrichment import AIEnrichment

logger = logging.getLogger(__name__)


class CleaningPipeline:
    """
    Cleans and normalizes job data:
    - Strip HTML from descriptions
    - Normalize whitespace
    - Fix common encoding issues
    - Validate required fields
    """

    def process_item(self, item, spider):
        # Must have title
        title = (item.get("title") or "").strip()
        if not title or len(title) < 3:
            raise DropItem(f"Missing or invalid title: {title}")

        item["title"] = self._clean_text(title)
        item["company"] = self._clean_text(item.get("company", "Unknown"))
        item["location"] = self._clean_text(item.get("location", "India"))

        # Clean description
        desc = item.get("description", "")
        if desc:
            item["description"] = self._clean_html(desc)[:3000]

        # Normalize job type
        item["job_type"] = self._normalize_job_type(item.get("job_type", ""))

        # Clean salary
        item["salary"] = self._clean_text(item.get("salary", ""))

        # Ensure lists
        if not isinstance(item.get("skills"), list):
            item["skills"] = []
        if not isinstance(item.get("tags"), list):
            item["tags"] = []

        # Generate stable job_id
        item["job_id"] = self._generate_id(item)

        return item

    def _clean_text(self, text):
        if not text:
            return ""
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        # Fix common encoding
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2013", "-").replace("\u2014", "-")
        return text

    def _clean_html(self, text):
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"&nbsp;", " ", clean)
        clean = re.sub(r"&amp;", "&", clean)
        clean = re.sub(r"&lt;", "<", clean)
        clean = re.sub(r"&gt;", ">", clean)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()

    def _normalize_job_type(self, jt):
        if not jt:
            return "Full-time"
        jt_lower = jt.lower().strip()
        mapping = {
            "full_time": "Full-time", "full-time": "Full-time", "fulltime": "Full-time",
            "part_time": "Part-time", "part-time": "Part-time", "parttime": "Part-time",
            "contract": "Contract", "freelance": "Contract",
            "internship": "Internship", "intern": "Internship",
            "remote": "Remote", "work from home": "Remote",
            "temporary": "Contract",
        }
        return mapping.get(jt_lower, jt.title())

    def _generate_id(self, item):
        key = f"{item.get('title', '')}-{item.get('company', '')}-{item.get('source', '')}".lower()
        return hashlib.md5(key.encode()).hexdigest()[:12]


class DedupPipeline:
    """Remove duplicate jobs based on title + company combination."""

    def __init__(self):
        self.seen = set()

    def process_item(self, item, spider):
        # Deduplicate by normalized title + company
        key = f"{item.get('title', '').lower().strip()}" \
              f"|{item.get('company', '').lower().strip()}"

        if key in self.seen:
            raise DropItem(f"Duplicate: {item.get('title')} at {item.get('company')}")

        self.seen.add(key)
        return item


class AIEnrichmentPipeline:
    """
    Uses AI (Gemini/OpenAI) to extract skills, categorize, and score jobs.
    Falls back to local NLP keyword extraction if no API key available.
    """

    def __init__(self):
        self.ai = None
        self.jobs_buffer = []
        self.batch_size = 20

    def open_spider(self, spider):
        gemini_key = spider.settings.get("GEMINI_API_KEY", "")
        openai_key = spider.settings.get("OPENAI_API_KEY", "")
        self.ai = AIEnrichment(gemini_key=gemini_key, openai_key=openai_key)
        self.jobs_buffer = []

    def process_item(self, item, spider):
        # Always do local enrichment (instant)
        job_dict = dict(item)
        job_dict = self.ai.enrich_job(job_dict)

        # Copy enriched fields back
        for key in ["ai_skills", "ai_category", "ai_quality_score"]:
            item[key] = job_dict.get(key, item.get(key))

        # Merge skills
        existing = set(item.get("skills", []))
        ai_skills = set(item.get("ai_skills", []))
        item["skills"] = list(existing | ai_skills)

        # Set category if not already set
        if not item.get("category") and item.get("ai_category"):
            item["category"] = item["ai_category"]

        return item

    def close_spider(self, spider):
        # Log stats
        logger.info(f"🤖 AI enrichment complete for spider '{spider.name}'")


class JsonExportPipeline:
    """
    Collects all items and exports to JSON files compatible with
    the existing Careerguidance data format.
    """

    def __init__(self):
        self.items = []

    def open_spider(self, spider):
        self.items = []
        self.spider_name = spider.name

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        if not self.items:
            logger.warning(f"No items collected for spider '{spider.name}'")
            return

        # Determine output file
        data_dir = spider.settings.get("DATA_DIR",
                                        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
        os.makedirs(data_dir, exist_ok=True)

        if spider.name == "india_jobs":
            output_file = os.path.join(data_dir, "india_jobs.json")
        elif spider.name == "tamilnadu_jobs":
            output_file = os.path.join(data_dir, "tn_jobs.json")
        else:
            output_file = os.path.join(data_dir, "jobs.json")

        # Format jobs for the existing app format
        formatted_jobs = self._format_jobs(self.items)

        # Build stats
        src_counts = Counter(j.get("source", "Unknown") for j in formatted_jobs)
        cat_counts = Counter(j.get("category", "Other") for j in formatted_jobs)
        city_counts = Counter(j.get("location_city", "Unknown") for j in formatted_jobs)

        payload = {
            "jobs": formatted_jobs,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(formatted_jobs),
            "sources": list(src_counts.keys()),
            "scraped_with": "scrapy",
            "stats": {
                "by_source": dict(src_counts),
                "by_category": dict(cat_counts),
                "by_city": dict(city_counts.most_common(20)),
            },
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"💾 Saved {len(formatted_jobs)} jobs to {output_file}")
        logger.info(f"   Sources: {dict(src_counts)}")
        logger.info(f"   Top categories: {dict(cat_counts.most_common(5))}")

    def _format_jobs(self, items):
        """Convert Scrapy items to the format expected by the Flask app."""
        formatted = []
        for item in items:
            job = {
                "id": item.get("job_id", ""),
                "title": item.get("title", ""),
                "company": item.get("company", ""),
                "company_logo": item.get("company_logo", ""),
                "location": item.get("location", ""),
                "location_city": item.get("location_city", ""),
                "location_state": item.get("location_state", ""),
                "location_country": item.get("location_country", "India"),
                "description": item.get("description", ""),
                "job_type": item.get("job_type", "Full-time"),
                "experience_level": item.get("experience_level", ""),
                "salary": item.get("salary", ""),
                "salary_currency": item.get("salary_currency", "INR"),
                "category": item.get("category") or item.get("ai_category", "Other"),
                "skills": item.get("skills", []),
                "tags": item.get("tags", []),
                "source": item.get("source", ""),
                "source_url": item.get("source_url", ""),
                "apply_url": item.get("apply_url") or item.get("source_url", ""),
                "posted_date": item.get("posted_date", ""),
                "scraped_at": item.get("scraped_at", ""),
                "quality_score": item.get("ai_quality_score", 0),
            }
            formatted.append(job)

        # Sort by quality score descending
        formatted.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        return formatted
