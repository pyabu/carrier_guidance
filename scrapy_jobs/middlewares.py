"""
CareerPath Pro – Scrapy Middlewares
Rotating user-agents and anti-blocking strategies.
"""

import random
import time
import logging
import warnings
from scrapy import signals

logger = logging.getLogger(__name__)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        from fake_useragent import UserAgent
        _ua = UserAgent(browsers=["chrome", "firefox", "safari", "edge"], os=["windows", "macos", "linux"])
    except Exception:
        _ua = None

_FALLBACK_UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def _random_ua():
    if _ua:
        try:
            return _ua.random
        except Exception:
            pass
    return random.choice(_FALLBACK_UAS)


class RotateUserAgentMiddleware:
    """Rotates User-Agent header per request using fake_useragent."""

    def __init__(self, user_agents):
        self.user_agents = user_agents

    @classmethod
    def from_crawler(cls, crawler):
        ua_list = crawler.settings.getlist("USER_AGENT_LIST", [])
        if not ua_list:
            ua_list = [crawler.settings.get("USER_AGENT", "Scrapy")]
        return cls(ua_list)

    def process_request(self, request, spider):
        request.headers["User-Agent"] = _random_ua()


class AntiBlockMiddleware:
    """
    Adds realistic browser headers, handles blocking responses
    with exponential backoff, and randomises request timing.
    """

    REFERERS = [
        "https://www.google.com/",
        "https://www.google.co.in/",
        "https://www.bing.com/",
        "https://in.search.yahoo.com/",
        "https://duckduckgo.com/",
    ]

    def process_request(self, request, spider):
        ua = request.headers.get("User-Agent", b"").decode("utf-8", errors="ignore")

        # Build realistic headers matching the chosen browser
        headers = {
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
        }

        # Add Sec-Ch-Ua for Chrome-based UAs
        if "Chrome" in ua and "Edg" not in ua:
            headers["Sec-Ch-Ua"] = '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"'
            headers["Sec-Ch-Ua-Mobile"] = "?0"
            headers["Sec-Ch-Ua-Platform"] = '"Windows"' if "Windows" in ua else '"macOS"'
        elif "Edg" in ua:
            headers["Sec-Ch-Ua"] = '"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"'
            headers["Sec-Ch-Ua-Mobile"] = "?0"
            headers["Sec-Ch-Ua-Platform"] = '"Windows"'

        for key, value in headers.items():
            if key.encode() not in request.headers:
                request.headers[key] = value

        if b"Referer" not in request.headers:
            request.headers["Referer"] = random.choice(self.REFERERS)

    def process_response(self, request, response, spider):
        if response.status == 403:
            logger.warning(f"403 Forbidden: {request.url} – may be blocked, will retry with new UA")
            request.headers["User-Agent"] = _random_ua()
            # Scrapy retry middleware will handle the actual retry
        elif response.status == 429:
            wait = random.uniform(3.0, 8.0)
            logger.warning(f"429 Rate Limited: {request.url} – backing off {wait:.1f}s")
            time.sleep(wait)
            request.headers["User-Agent"] = _random_ua()
        return response
