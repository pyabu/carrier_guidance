"""
Careerguidance – Anti-Blocking Utilities
═══════════════════════════════════════════════
Shared session factory & request helpers that bypass common
anti-bot protections (Cloudflare, TLS fingerprinting, rate limiting).

Usage:
    from scraper.anti_block import create_stealth_session, safe_get

    session = create_stealth_session()
    resp = safe_get(session, url, max_retries=3)
"""

import logging
import random
import time
import warnings

import cloudscraper

# Suppress noisy fake_useragent warnings about browser fallback
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        from fake_useragent import UserAgent
    except ImportError:
        UserAgent = None

logger = logging.getLogger(__name__)

# ── Realistic User-Agents (fallback if fake_useragent unavailable) ────
_FALLBACK_UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

# ── Realistic referers ────────────────────────────────────────────────
REFERERS = [
    "https://www.google.com/",
    "https://www.google.co.in/",
    "https://www.bing.com/",
    "https://in.search.yahoo.com/",
    "https://duckduckgo.com/",
    "https://www.google.com/search?q=jobs",
    "https://www.google.co.in/search?q=jobs+in+india",
]

# ── Initialize fake_useragent (cached) ────────────────────────────────
try:
    _ua = UserAgent(browsers=["chrome", "firefox", "safari", "edge"], os=["windows", "macos", "linux"]) if UserAgent else None
except Exception:
    _ua = None


def get_random_ua() -> str:
    """Get a random realistic User-Agent string."""
    if _ua:
        try:
            return _ua.random
        except Exception:
            pass
    return random.choice(_FALLBACK_UAS)


def get_browser_headers(referer: str = None) -> dict:
    """
    Return a full set of browser-like headers.
    Rotates UA and referer on every call.
    """
    ua = get_random_ua()
    # Determine browser type from UA for consistent Sec-Ch-Ua
    if "Chrome" in ua and "Edg" not in ua:
        sec_ch_ua = '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"'
        sec_ch_ua_mobile = "?0"
        sec_ch_ua_platform = '"macOS"' if "Mac" in ua else '"Windows"'
    elif "Firefox" in ua:
        sec_ch_ua = ""
        sec_ch_ua_mobile = ""
        sec_ch_ua_platform = ""
    elif "Edg" in ua:
        sec_ch_ua = '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"'
        sec_ch_ua_mobile = "?0"
        sec_ch_ua_platform = '"Windows"'
    else:
        sec_ch_ua = ""
        sec_ch_ua_mobile = ""
        sec_ch_ua_platform = ""

    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8,ta;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Referer": referer or random.choice(REFERERS),
    }

    if sec_ch_ua:
        headers["Sec-Ch-Ua"] = sec_ch_ua
        headers["Sec-Ch-Ua-Mobile"] = sec_ch_ua_mobile
        headers["Sec-Ch-Ua-Platform"] = sec_ch_ua_platform

    return headers


def create_stealth_session() -> cloudscraper.CloudScraper:
    """
    Create a CloudScraper session that:
    - Bypasses Cloudflare and similar bot protections
    - Uses realistic TLS fingerprints (matches real browsers)
    - Rotates User-Agent on each request via an adapter
    - Handles cookies properly
    """
    scraper = cloudscraper.create_scraper(
        browser={
            "browser": random.choice(["chrome", "firefox"]),
            "platform": random.choice(["windows", "darwin", "linux"]),
            "desktop": True,
        },
        delay=1,  # small delay between challenge solves
    )

    # Set baseline headers
    scraper.headers.update(get_browser_headers())

    return scraper


def safe_get(session, url: str, max_retries: int = 3, timeout: int = 15,
             extra_headers: dict = None, min_delay: float = 1.0,
             max_delay: float = 3.0, **kwargs) -> "requests.Response | None":
    """
    Make a GET request with:
    - Per-request User-Agent rotation
    - Exponential backoff on 403/429/5xx
    - Random human-like delays between retries
    - Realistic headers

    Returns Response object or None if all retries exhausted.
    """
    # Fetch any extra headers outside loop
    req_headers = kwargs.get("headers", {})

    for attempt in range(max_retries):
        try:
            # Rotate UA and headers on each attempt
            headers = get_browser_headers()
            if extra_headers:
                headers.update(extra_headers)

            # Merge with any headers in kwargs
            headers.update(req_headers)

            # Make copy of kwargs without 'headers' to pass to session.get
            get_kwargs = {k: v for k, v in kwargs.items() if k != "headers"}
            resp = session.get(url, timeout=timeout, headers=headers, **get_kwargs)

            if resp.status_code == 200:
                return resp

            if resp.status_code in (403, 429):
                wait = (2 ** attempt) * random.uniform(1.5, 3.0)
                logger.warning(
                    f"[anti_block] {resp.status_code} on {url[:80]}… "
                    f"(attempt {attempt+1}/{max_retries}, waiting {wait:.1f}s)"
                )
                time.sleep(wait)
                # Refresh session UA for next attempt
                session.headers["User-Agent"] = get_random_ua()
                continue

            if resp.status_code >= 500:
                wait = (2 ** attempt) * random.uniform(1.0, 2.0)
                logger.warning(
                    f"[anti_block] Server error {resp.status_code} on {url[:80]}… "
                    f"retrying in {wait:.1f}s"
                )
                time.sleep(wait)
                continue

            # Non-200 but not retryable (301, 404, etc.) — return as-is
            return resp

        except Exception as e:
            wait = (2 ** attempt) * random.uniform(1.0, 2.0)
            logger.warning(
                f"[anti_block] Request error on {url[:80]}…: {e} "
                f"(attempt {attempt+1}/{max_retries}, waiting {wait:.1f}s)"
            )
            time.sleep(wait)

    logger.error(f"[anti_block] All {max_retries} retries exhausted for {url[:80]}")
    return None


def human_delay(min_sec: float = 1.0, max_sec: float = 3.5):
    """Sleep for a random human-like duration."""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def warm_cookies(session, base_url: str):
    """
    Visit the homepage first to collect cookies / tokens
    before making search requests. Helps bypass bot detection
    that requires a valid session cookie.
    """
    try:
        resp = safe_get(session, base_url, max_retries=2, timeout=10)
        if resp and resp.status_code == 200:
            logger.debug(f"[anti_block] Warmed cookies for {base_url}")
            return True
    except Exception as e:
        logger.debug(f"[anti_block] Cookie warming failed for {base_url}: {e}")
    return False
