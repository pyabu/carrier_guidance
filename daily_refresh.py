#!/usr/bin/env python3
"""
CareerPath Pro – Daily Cron Script
═══════════════════════════════════════════════
Run this script once a day (via cron, launchd, or Task Scheduler)
to refresh all job listings from 8+ real sources.

Usage:
  python daily_refresh.py              # Full refresh
  python daily_refresh.py --dry-run    # Preview only, don't save

Crontab example (every day at 6 AM):
  0 6 * * * cd /path/to/carrier_guidance && /usr/bin/python3 daily_refresh.py >> logs/cron.log 2>&1

macOS launchd alternative:
  See daily_refresh.plist for a launchd configuration.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from collections import Counter

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from scraper.job_scraper import JobScraper

# ── Setup ──────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

JOBS_FILE = os.path.join(DATA_DIR, "jobs.json")
LOG_FILE = os.path.join(LOG_DIR, "scraper.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("daily_refresh")


def main():
    parser = argparse.ArgumentParser(description="CareerPath Pro – Daily Job Refresh")
    parser.add_argument("--dry-run", action="store_true", help="Preview only; don't save to disk")
    args = parser.parse_args()

    start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"🚀 Starting daily job refresh at {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # Run scraper
    scraper = JobScraper()
    jobs = scraper.scrape_all()

    # Stats
    total = len(jobs)
    src_counts = Counter(j["source"] for j in jobs)
    country_counts = Counter(j.get("location_country", "Unknown") for j in jobs)
    cat_counts = Counter(j.get("category", "Other") for j in jobs)

    logger.info(f"\n📊 RESULTS SUMMARY")
    logger.info(f"   Total unique jobs: {total}")
    logger.info(f"\n   📡 By source:")
    for src, cnt in src_counts.most_common():
        logger.info(f"      {src:20s} → {cnt}")
    logger.info(f"\n   🌍 By country (top 10):")
    for country, cnt in country_counts.most_common(10):
        logger.info(f"      {country:20s} → {cnt}")
    logger.info(f"\n   📂 By category:")
    for cat, cnt in cat_counts.most_common():
        logger.info(f"      {cat:20s} → {cnt}")

    if args.dry_run:
        logger.info(f"\n⚠️  DRY RUN – not saving to disk")
        logger.info(f"   Would save {total} jobs to {JOBS_FILE}")
    else:
        # Save
        payload = {
            "jobs": jobs,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sources": list(src_counts.keys()),
            "total": total,
            "stats": {
                "by_source": dict(src_counts),
                "by_country": dict(country_counts.most_common(20)),
                "by_category": dict(cat_counts),
            },
        }
        with open(JOBS_FILE, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"\n✅ Saved {total} jobs to {JOBS_FILE}")

        # ── Run Trend Analysis ─────────────────────────────────────
        try:
            from scraper.trend_analyzer import TrendAnalyzer
            analyzer = TrendAnalyzer(DATA_DIR)
            trends = analyzer.analyze(jobs)
            logger.info(f"\n📊 TREND ANALYSIS")
            top_skills = trends.get("skills", {}).get("top_25", [])[:10]
            if top_skills:
                logger.info(f"   🔥 Top Skills:")
                for s in top_skills:
                    logger.info(f"      {s['skill']:20s} → {s['count']} jobs ({s['percentage']}%)")

            career_paths = trends.get("career_paths", [])
            if career_paths:
                logger.info(f"\n   🛤️  Career Paths:")
                for path in career_paths:
                    logger.info(f"      {path['name']:25s} → {path['total_available_jobs']} available jobs")

            hot_combos = trends.get("hot_combinations", [])[:5]
            if hot_combos:
                logger.info(f"\n   🔥 Hot Skill Combos:")
                for combo in hot_combos:
                    logger.info(f"      {combo['combination']:35s} → {combo['demand']} jobs")

        except Exception as e:
            logger.warning(f"\n⚠️  Trend analysis failed: {e}")

        # Keep a daily backup
        backup_dir = os.path.join(DATA_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f"jobs_{start.strftime('%Y%m%d')}.json")
        with open(backup_file, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"   Backup: {backup_file}")

    # ── Refresh Tamil Nadu & Pondicherry Jobs ──────────────────────
    tn_jobs_file = os.path.join(DATA_DIR, "tn_jobs.json")
    try:
        from scraper.tamilnadu_scraper import TamilNaduJobScraper
        logger.info("\n🗺️  Refreshing Tamil Nadu & Pondicherry jobs …")
        tn_scraper = TamilNaduJobScraper()
        tn_jobs = tn_scraper.scrape_all()
        for i, j in enumerate(tn_jobs):
            j["id"] = i + 1
        tn_payload = {
            "jobs": tn_jobs,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "region": "Tamil Nadu & Pondicherry",
            "total": len(tn_jobs),
        }
        if not args.dry_run:
            with open(tn_jobs_file, "w") as f:
                json.dump(tn_payload, f, indent=2)
            logger.info(f"✅ Saved {len(tn_jobs)} TN jobs to {tn_jobs_file}")
        else:
            logger.info(f"⚠️  DRY RUN – Would save {len(tn_jobs)} TN jobs")
    except ImportError:
        logger.warning("⚠️  TN scraper module not found – skipping")
    except Exception as e:
        logger.warning(f"⚠️  TN scraper failed: {e}")

    # ── Refresh All-India Jobs ─────────────────────────────────────
    india_jobs_file = os.path.join(DATA_DIR, "india_jobs.json")
    try:
        from scraper.india_scraper import IndiaJobScraper
        logger.info("\n🇮🇳 Refreshing All-India jobs …")
        india_scraper = IndiaJobScraper()
        india_jobs = india_scraper.scrape_all(min_jobs=500)
        for i, j in enumerate(india_jobs):
            j["id"] = i + 1
        india_payload = {
            "jobs": india_jobs,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "region": "India",
            "total": len(india_jobs),
            "states_covered": len(set(j.get("location_state", "") for j in india_jobs if j.get("location_state"))),
            "cities_covered": len(set(j.get("location_city", "") for j in india_jobs if j.get("location_city"))),
        }
        if not args.dry_run:
            with open(india_jobs_file, "w") as f:
                json.dump(india_payload, f, indent=2)
            logger.info(f"✅ Saved {len(india_jobs)} India jobs to {india_jobs_file}")
        else:
            logger.info(f"⚠️  DRY RUN – Would save {len(india_jobs)} India jobs")
    except ImportError:
        logger.warning("⚠️  India scraper module not found – skipping")
    except Exception as e:
        logger.warning(f"⚠️  India scraper failed: {e}")

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"\n⏱  Completed in {elapsed:.1f} seconds")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
