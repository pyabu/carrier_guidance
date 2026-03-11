#!/usr/bin/env python3
"""
CareerPath Pro – Scrapy Orchestrator
═════════════════════════════════════════
Runs all Scrapy spiders sequentially and applies AI enrichment.

Usage:
  python run_scrapy.py                    # Run all spiders
  python run_scrapy.py --spider india     # Run only India spider
  python run_scrapy.py --spider tn        # Run only Tamil Nadu spider
  python run_scrapy.py --dry-run          # Preview without saving
  python run_scrapy.py --ai-enrich        # Run with Gemini AI batch enrichment

Environment Variables:
  GEMINI_API_KEY    – Google Gemini API key (free at aistudio.google.com)
  OPENAI_API_KEY    – OpenAI API key (optional fallback)
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__)) \
    if "scrapy_jobs" in os.path.dirname(__file__) \
    else os.path.dirname(__file__)
sys.path.insert(0, PROJECT_ROOT)

# Load .env file if present
_env_file = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(_env_file):
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _val = _line.split("=", 1)
                os.environ.setdefault(_key.strip(), _val.strip())

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# ── Logging ────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "scrapy_scraper.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("scrapy_orchestrator")


def run_spiders(spider_name=None, dry_run=False, ai_enrich=False):
    """
    Run Scrapy spiders to fetch real job data.

    Args:
        spider_name: "india", "tn", or None (all)
        dry_run: If True, scrape but don't save files
        ai_enrich: If True, run Gemini AI batch enrichment after scraping
    """
    start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"🕷️  Scrapy Orchestrator started at {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"   Spider: {spider_name or 'ALL'} | Dry run: {dry_run} | AI: {ai_enrich}")
    logger.info("=" * 60)

    # Configure Scrapy settings
    os.environ["SCRAPY_SETTINGS_MODULE"] = "scrapy_jobs.settings"
    settings = get_project_settings()

    # Override DATA_DIR
    data_dir = os.path.join(PROJECT_ROOT, "data")
    settings.set("DATA_DIR", data_dir)

    if dry_run:
        # Disable JSON export pipeline in dry-run mode
        settings.set("ITEM_PIPELINES", {
            "scrapy_jobs.pipelines.CleaningPipeline": 100,
            "scrapy_jobs.pipelines.DedupPipeline": 200,
            "scrapy_jobs.pipelines.AIEnrichmentPipeline": 300,
        })

    # Create crawler process
    process = CrawlerProcess(settings)

    # Import spiders
    from scrapy_jobs.spiders.india_spider import IndiaJobsSpider
    from scrapy_jobs.spiders.tamilnadu_spider import TamilNaduJobsSpider

    if spider_name == "india" or spider_name is None:
        process.crawl(IndiaJobsSpider)
        logger.info("🇮🇳 Queued: India Jobs Spider (12 sources)")

    if spider_name == "tn" or spider_name is None:
        process.crawl(TamilNaduJobsSpider)
        logger.info("🏛️  Queued: Tamil Nadu Jobs Spider (8 sources)")

    # Run all queued spiders
    logger.info("🚀 Starting Scrapy crawl...")
    process.start()

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"⏱️  Scrapy crawl completed in {elapsed:.1f}s")

    # Post-processing: AI batch enrichment with Gemini
    if ai_enrich and not dry_run:
        _run_ai_batch_enrichment(data_dir, spider_name)

    # Summary
    _print_summary(data_dir, spider_name)

    logger.info("=" * 60)
    logger.info(f"✅ Scrapy orchestrator finished in {elapsed:.1f}s")
    logger.info("=" * 60)

    return True


def _run_ai_batch_enrichment(data_dir, spider_name):
    """Run Gemini AI batch enrichment on scraped data."""
    from scrapy_jobs.ai_enrichment import AIEnrichment

    ai = AIEnrichment()
    if not ai.use_gemini:
        logger.info("⚠️  No Gemini API key – skipping batch AI enrichment")
        return

    files_to_enrich = []
    if spider_name == "india" or spider_name is None:
        files_to_enrich.append(os.path.join(data_dir, "india_jobs.json"))
    if spider_name == "tn" or spider_name is None:
        files_to_enrich.append(os.path.join(data_dir, "tn_jobs.json"))

    for filepath in files_to_enrich:
        if not os.path.exists(filepath):
            continue

        logger.info(f"🤖 Gemini batch enrichment: {os.path.basename(filepath)}")
        with open(filepath, "r") as f:
            data = json.load(f)

        jobs = data.get("jobs", [])
        enriched = ai.enrich_batch_with_ai(jobs)
        data["jobs"] = enriched
        data["ai_enrichment"] = {
            "model": "gemini-1.5-flash",
            "enriched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_enriched": len(enriched),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        skills = ai.get_trending_skills(enriched)
        logger.info(f"   Enriched {len(enriched)} jobs | Top skills: {skills[:5]}")


def _print_summary(data_dir, spider_name):
    """Print summary of scraped data."""
    files = {
        "india": "india_jobs.json",
        "tn": "tn_jobs.json",
    }

    for key, filename in files.items():
        if spider_name and spider_name != key:
            continue

        filepath = os.path.join(data_dir, filename)
        if not os.path.exists(filepath):
            logger.warning(f"   {filename}: NOT FOUND")
            continue

        with open(filepath, "r") as f:
            data = json.load(f)

        total = data.get("total", 0)
        sources = data.get("sources", [])
        updated = data.get("last_updated", "unknown")
        stats = data.get("stats", {})

        logger.info(f"\n📊 {filename}:")
        logger.info(f"   Total jobs: {total}")
        logger.info(f"   Updated: {updated}")
        logger.info(f"   Sources: {', '.join(sources)}")
        if stats.get("by_source"):
            for src, cnt in stats["by_source"].items():
                logger.info(f"     {src:20s} → {cnt}")


def main():
    parser = argparse.ArgumentParser(description="CareerPath Pro – Scrapy Job Scraper")
    parser.add_argument("--spider", choices=["india", "tn"],
                        help="Run specific spider (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, don't save to disk")
    parser.add_argument("--ai-enrich", action="store_true",
                        help="Run Gemini AI batch enrichment after scraping")
    args = parser.parse_args()

    run_spiders(
        spider_name=args.spider,
        dry_run=args.dry_run,
        ai_enrich=args.ai_enrich,
    )


if __name__ == "__main__":
    main()
