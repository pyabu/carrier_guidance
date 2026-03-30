"""
Careerguidance – Scrapy Settings
Anti-blocking, polite crawling, and pipeline configuration.
"""

BOT_NAME = "careerguidance"
SPIDER_MODULES = ["scrapy_jobs.spiders"]
NEWSPIDER_MODULE = "scrapy_jobs.spiders"

# ── Crawl Responsibly ──────────────────────────────────────────────────
ROBOTSTXT_OBEY = False          # Many job sites block bots via robots.txt
CONCURRENT_REQUESTS = 4         # Reduced to avoid triggering rate limits
CONCURRENT_REQUESTS_PER_DOMAIN = 1  # One request per domain at a time
DOWNLOAD_DELAY = 2.5            # Polite delay between requests
RANDOMIZE_DOWNLOAD_DELAY = True # 0.5x - 1.5x of DOWNLOAD_DELAY
DOWNLOAD_TIMEOUT = 30

# ── Retry ──────────────────────────────────────────────────────────────
RETRY_ENABLED = True
RETRY_TIMES = 5                 # More retries for blocked requests
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]  # Also retry 403

# ── User-Agent Rotation ───────────────────────────────────────────────
USER_AGENT_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# ── Middlewares ────────────────────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    "scrapy_jobs.middlewares.RotateUserAgentMiddleware": 400,
    "scrapy_jobs.middlewares.AntiBlockMiddleware": 500,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

# ── Pipelines ─────────────────────────────────────────────────────────
ITEM_PIPELINES = {
    "scrapy_jobs.pipelines.CleaningPipeline": 100,
    "scrapy_jobs.pipelines.DedupPipeline": 200,
    "scrapy_jobs.pipelines.AIEnrichmentPipeline": 300,
    "scrapy_jobs.pipelines.JsonExportPipeline": 900,
}

# ── HTTP Cache (for dev/testing) ──────────────────────────────────────
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = "httpcache"

# ── Logging ───────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ── Feed Export ───────────────────────────────────────────────────────
FEED_EXPORT_ENCODING = "utf-8"

# ── AutoThrottle ──────────────────────────────────────────────────────
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3
AUTOTHROTTLE_MAX_DELAY = 15
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0  # Conservative to avoid detection

# ── Twisted Reactor (macOS fix) ───────────────────────────────────────
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

# ── Custom Settings ───────────────────────────────────────────────────
# Google Gemini API key for AI enrichment (set via env var)
import os
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Output directory
import os as _os
DATA_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "data")
