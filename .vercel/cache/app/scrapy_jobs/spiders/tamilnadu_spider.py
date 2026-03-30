"""
Careerguidance – Scrapy Spider: Tamil Nadu & Pondicherry Jobs
═══════════════════════════════════════════════════════════════
Focused spider for jobs in Tamil Nadu cities + Puducherry.
Scrapes from multiple sources filtering by TN locations.
"""

import json
import re
import scrapy
from datetime import datetime
from urllib.parse import quote_plus

from scrapy_jobs.items import JobItem


class TamilNaduJobsSpider(scrapy.Spider):
    """
    Multi-source spider for Tamil Nadu & Pondicherry jobs.
    Targets: LinkedIn, Indeed, Internshala, Remotive, Himalayas,
    TheMuse, Naukri-like pages, and Freshersworld.
    """

    name = "tamilnadu_jobs"
    custom_settings = {
        "CONCURRENT_REQUESTS": 6,
        "DOWNLOAD_DELAY": 2,
    }

    TN_CITIES = [
        "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Trichy",
        "Salem", "Tirunelveli", "Erode", "Vellore", "Thoothukudi",
        "Tiruppur", "Thanjavur", "Dindigul", "Hosur", "Nagercoil",
        "Kanchipuram", "Karur", "Sivakasi", "Ramanathapuram",
        "Puducherry", "Pondicherry",
    ]

    TN_SEARCH_TERMS = TN_CITIES[:8]  # Top cities for search queries

    SEARCH_KEYWORDS = [
        "software developer", "python developer", "java developer",
        "data analyst", "web developer", "react developer",
        "full stack developer", "QA engineer", "devops",
        "machine learning", "digital marketing", "UI designer",
        "android developer", "business analyst", "content writer",
    ]

    def start_requests(self):
        """Generate requests targeting TN locations across all sources."""
        yield from self._linkedin_tn_requests()
        yield from self._indeed_tn_requests()
        yield from self._internshala_tn_requests()
        yield from self._themuse_tn_requests()
        yield from self._himalayas_tn_requests()
        yield from self._freshersworld_tn_requests()
        yield from self._remotive_tn_requests()
        yield from self._naukri_tn_requests()

    # ── 1. LinkedIn – TN Cities ───────────────────────────────────────
    def _linkedin_tn_requests(self):
        cities = ["Chennai", "Coimbatore", "Madurai", "Trichy", "Puducherry"]
        keywords = ["developer", "software+engineer", "data+analyst",
                     "python", "java", "react", "devops", "QA"]
        for city in cities:
            for kw in keywords:
                url = (f"https://www.linkedin.com/jobs-guest/jobs/api/"
                       f"seeMoreJobPostings/search?"
                       f"keywords={kw}&location={quote_plus(city)}%2C+Tamil+Nadu%2C+India"
                       f"&start=0&count=25")
                yield scrapy.Request(url, callback=self.parse_linkedin,
                                    meta={"source": "LinkedIn", "city": city},
                                    dont_filter=True)

    def parse_linkedin(self, response):
        try:
            cards = response.css("li")
            for card in cards:
                title = card.css("h3.base-search-card__title::text").get("").strip()
                company = card.css("h4.base-search-card__subtitle a::text").get("").strip()
                location = card.css("span.job-search-card__location::text").get("").strip()
                link = card.css("a.base-card__full-link::attr(href)").get("")
                posted = card.css("time::attr(datetime)").get("")
                logo = card.css("img.artdeco-entity-image::attr(data-delayed-url)").get("")

                if title and company and self._is_tn_location(location):
                    yield self._make_item(
                        title=title,
                        company=company,
                        location=location,
                        source="LinkedIn",
                        source_url=link.split("?")[0] if link else "",
                        apply_url=link.split("?")[0] if link else "",
                        posted_date=posted,
                        company_logo=logo,
                    )
        except Exception as e:
            self.logger.error(f"LinkedIn TN parse error: {e}")

    # ── 2. Indeed – TN Cities ─────────────────────────────────────────
    def _indeed_tn_requests(self):
        cities_indeed = ["Chennai", "Coimbatore", "Madurai", "Trichy", "Pondicherry"]
        queries = ["software+developer", "python", "java+developer",
                    "data+analyst", "react+developer", "full+stack"]
        for city in cities_indeed:
            for q in queries:
                url = f"https://www.indeed.co.in/rss?q={q}&l={quote_plus(city)}&sort=date"
                yield scrapy.Request(url, callback=self.parse_indeed_rss,
                                    meta={"source": "Indeed", "city": city},
                                    dont_filter=True)

    def parse_indeed_rss(self, response):
        try:
            items = response.xpath("//item")
            for item in items:
                raw_title = item.xpath("title/text()").get("").strip()
                link = item.xpath("link/text()").get("").strip()
                desc = item.xpath("description/text()").get("").strip()
                pub_date = item.xpath("pubDate/text()").get("").strip()

                parts = raw_title.split(" - ")
                job_title = parts[0] if parts else raw_title
                company = parts[1] if len(parts) > 1 else ""
                location = parts[2] if len(parts) > 2 else response.meta.get("city", "Tamil Nadu")

                if job_title:
                    yield self._make_item(
                        title=job_title,
                        company=company,
                        location=location,
                        description=self._clean_html(desc),
                        source="Indeed",
                        source_url=link,
                        apply_url=link,
                        posted_date=pub_date,
                    )
        except Exception as e:
            self.logger.error(f"Indeed TN parse error: {e}")

    # ── 3. Internshala – TN ───────────────────────────────────────────
    def _internshala_tn_requests(self):
        categories = [
            "web-development", "python-django-development", "java-development",
            "data-science", "react-development", "mobile-app-development",
            "machine-learning", "digital-marketing", "graphic-design",
        ]
        cities = ["chennai", "coimbatore", "madurai", "pondicherry"]
        for cat in categories:
            for city in cities:
                # Internshala jobs with location filter
                url = f"https://internshala.com/jobs/{cat}-jobs-in-{city}"
                yield scrapy.Request(url, callback=self.parse_internshala,
                                    meta={"source": "Internshala", "city": city},
                                    dont_filter=True)
                # Internships too
                url2 = f"https://internshala.com/internships/{cat}-internship-in-{city}"
                yield scrapy.Request(url2, callback=self.parse_internshala,
                                    meta={"source": "Internshala", "city": city,
                                           "is_internship": True},
                                    dont_filter=True)

    def parse_internshala(self, response):
        try:
            is_internship = response.meta.get("is_internship", False)
            cards = response.css("div.individual_internship, .container-fluid.individual_internship")
            if not cards:
                cards = response.css(".internship_meta")

            for card in cards:
                title = card.css("h3.heading_4_5 a::text, .job-internship-name a::text").get("").strip()
                company = card.css("h4.heading_6 a::text, .company_name a::text").get("").strip()
                location = ", ".join(
                    card.css("#location_names span a::text, .location_link span::text").getall()
                ).strip() or response.meta.get("city", "Tamil Nadu")
                link_path = card.css("h3.heading_4_5 a::attr(href), .job-internship-name a::attr(href)").get("")
                stipend = card.css(".stipend::text, span.desktop-text::text").get("").strip()

                apply_url = f"https://internshala.com{link_path}" if link_path else ""

                if title and self._is_tn_location(location):
                    yield self._make_item(
                        title=title,
                        company=company,
                        location=location,
                        job_type="Internship" if is_internship else "Full-time",
                        salary=stipend,
                        source="Internshala",
                        source_url=apply_url,
                        apply_url=apply_url,
                    )
        except Exception as e:
            self.logger.error(f"Internshala TN parse error: {e}")

    # ── 4. TheMuse – TN ──────────────────────────────────────────────
    def _themuse_tn_requests(self):
        for city in ["Chennai, India", "Coimbatore, India"]:
            url = f"https://www.themuse.com/api/public/jobs?location={quote_plus(city)}&page=1"
            yield scrapy.Request(url, callback=self.parse_themuse,
                                meta={"source": "TheMuse"}, dont_filter=True)

    def parse_themuse(self, response):
        try:
            data = json.loads(response.text)
            for job in data.get("results", []):
                locations = [loc.get("name", "") for loc in job.get("locations", [])]
                loc_str = ", ".join(locations) if locations else "Tamil Nadu"

                if self._is_tn_location(loc_str):
                    company_info = job.get("company", {})
                    yield self._make_item(
                        title=job.get("name", ""),
                        company=company_info.get("name", ""),
                        location=loc_str,
                        description=job.get("contents", ""),
                        source="TheMuse",
                        source_url=f"https://www.themuse.com/jobs/{job.get('short_name', '')}",
                        apply_url=job.get("refs", {}).get("landing_page", ""),
                        posted_date=job.get("publication_date", ""),
                    )
        except Exception as e:
            self.logger.error(f"TheMuse TN parse error: {e}")

    # ── 5. Himalayas – TN Filter ──────────────────────────────────────
    def _himalayas_tn_requests(self):
        url = "https://himalayas.app/jobs/api?limit=100&country=India"
        yield scrapy.Request(url, callback=self.parse_himalayas,
                            meta={"source": "Himalayas"}, dont_filter=True)

    def parse_himalayas(self, response):
        try:
            data = json.loads(response.text)
            for job in data.get("jobs", []):
                loc = job.get("location", "")
                if self._is_tn_location(loc):
                    yield self._make_item(
                        title=job.get("title", ""),
                        company=job.get("companyName", ""),
                        location=loc,
                        description=job.get("description", ""),
                        source="Himalayas",
                        source_url=f"https://himalayas.app/jobs/{job.get('slug', '')}",
                        apply_url=job.get("applicationLink", ""),
                        posted_date=job.get("pubDate", ""),
                        company_logo=job.get("companyLogo", ""),
                    )
        except Exception as e:
            self.logger.error(f"Himalayas TN parse error: {e}")

    # ── 6. Freshersworld ──────────────────────────────────────────────
    def _freshersworld_tn_requests(self):
        cities = ["chennai", "coimbatore", "madurai", "trichy", "pondicherry"]
        for city in cities:
            url = f"https://www.freshersworld.com/jobs-in-{city}"
            yield scrapy.Request(url, callback=self.parse_freshersworld,
                                meta={"source": "Freshersworld", "city": city},
                                dont_filter=True)

    def parse_freshersworld(self, response):
        try:
            cards = response.css("div.job-container .col-md-12, .job_listing_block")
            for card in cards:
                title = card.css("h2 a::text, .wrap-mob a span::text").get("").strip()
                company = card.css(".company-name a::text, .company-name::text").get("").strip()
                location = card.css(".job-location span::text, .location-info::text").get("").strip()
                link = card.css("h2 a::attr(href), .wrap-mob a::attr(href)").get("")
                exp = card.css(".experience::text").get("").strip()

                if title:
                    yield self._make_item(
                        title=title,
                        company=company,
                        location=location or response.meta.get("city", "Tamil Nadu"),
                        experience_level=exp,
                        source="Freshersworld",
                        source_url=link if link.startswith("http") else f"https://www.freshersworld.com{link}",
                        apply_url=link if link.startswith("http") else f"https://www.freshersworld.com{link}",
                    )
        except Exception as e:
            self.logger.error(f"Freshersworld TN parse error: {e}")

    # ── 7. Remotive (TN filter) ───────────────────────────────────────
    def _remotive_tn_requests(self):
        for cat in ["software-dev", "data", "design", "devops-sysadmin"]:
            url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=50"
            yield scrapy.Request(url, callback=self.parse_remotive,
                                meta={"source": "Remotive"}, dont_filter=True)

    def parse_remotive(self, response):
        try:
            data = json.loads(response.text)
            for job in data.get("jobs", []):
                loc = (job.get("candidate_required_location") or "").lower()
                # Include worldwide/India remote jobs as TN-eligible
                if any(kw in loc for kw in ["india", "asia", "worldwide", "anywhere"]) or \
                   any(city.lower() in loc for city in self.TN_CITIES):
                    yield self._make_item(
                        title=job.get("title", ""),
                        company=job.get("company_name", ""),
                        location=job.get("candidate_required_location", "Remote (Tamil Nadu eligible)"),
                        description=self._clean_html(job.get("description", "")),
                        job_type=job.get("job_type", "Remote"),
                        salary=job.get("salary", ""),
                        source="Remotive",
                        source_url=job.get("url", ""),
                        apply_url=job.get("url", ""),
                        posted_date=job.get("publication_date", ""),
                        tags=job.get("tags", []),
                        company_logo=job.get("company_logo", ""),
                    )
        except Exception as e:
            self.logger.error(f"Remotive TN parse error: {e}")

    # ── 8. Naukri-like (Google cache / career pages) ──────────────────
    def _naukri_tn_requests(self):
        # Scrape Naukri job listing pages for TN
        cities = ["chennai", "coimbatore", "madurai", "trichy"]
        for city in cities:
            url = f"https://www.naukri.com/{city}-jobs"
            yield scrapy.Request(url, callback=self.parse_naukri,
                                meta={"source": "Naukri", "city": city},
                                errback=self._errback,
                                dont_filter=True)

    def parse_naukri(self, response):
        try:
            # Naukri uses dynamic JS rendering, but some data is in the initial HTML
            cards = response.css("article.jobTuple, .srp-jobtuple-wrapper, .jobTupleHeader")
            for card in cards:
                title = card.css("a.title::text, .title::text").get("").strip()
                company = card.css("a.subTitle::text, .comp-name::text").get("").strip()
                location = card.css(".loc span::text, .locWdth::text").get("").strip()
                link = card.css("a.title::attr(href), .title::attr(href)").get("")
                exp = card.css(".expwdth::text, .exp::text").get("").strip()
                salary = card.css(".sal::text, .salary::text").get("").strip()

                if title:
                    yield self._make_item(
                        title=title,
                        company=company,
                        location=location or response.meta.get("city", "Tamil Nadu"),
                        experience_level=exp,
                        salary=salary,
                        source="Naukri",
                        source_url=link or "",
                        apply_url=link or "",
                    )
        except Exception as e:
            self.logger.error(f"Naukri TN parse error: {e}")

    # ── Helpers ────────────────────────────────────────────────────────

    def _is_tn_location(self, location):
        """Check if a location string refers to Tamil Nadu or Puducherry."""
        if not location:
            return False
        loc_lower = location.lower()
        tn_keywords = [c.lower() for c in self.TN_CITIES] + [
            "tamil nadu", "tamilnadu", "tn", "puducherry",
        ]
        return any(kw in loc_lower for kw in tn_keywords)

    def _make_item(self, **kwargs):
        """Create a standardized JobItem for TN."""
        item = JobItem()
        item["title"] = kwargs.get("title", "").strip()
        item["company"] = kwargs.get("company", "").strip()
        item["location"] = kwargs.get("location", "Tamil Nadu").strip()
        item["location_country"] = "India"
        item["location_state"] = "Tamil Nadu"
        item["description"] = kwargs.get("description", "")
        item["job_type"] = kwargs.get("job_type", "Full-time")
        item["experience_level"] = kwargs.get("experience_level", "")
        item["salary"] = kwargs.get("salary", "")
        item["salary_currency"] = "INR"
        item["category"] = kwargs.get("category", "")
        item["skills"] = kwargs.get("skills", [])
        item["tags"] = kwargs.get("tags", [])
        item["source"] = kwargs.get("source", "")
        item["source_url"] = kwargs.get("source_url", "")
        item["apply_url"] = kwargs.get("apply_url", "")
        item["posted_date"] = kwargs.get("posted_date", "")
        item["company_logo"] = kwargs.get("company_logo", "")
        item["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Parse city
        self._parse_tn_city(item)
        return item

    def _parse_tn_city(self, item):
        """Extract specific TN city from location."""
        loc = item.get("location", "").lower()
        city_map = {
            "chennai": "Chennai",
            "coimbatore": "Coimbatore",
            "madurai": "Madurai",
            "trichy": "Tiruchirappalli",
            "tiruchirappalli": "Tiruchirappalli",
            "salem": "Salem",
            "tirunelveli": "Tirunelveli",
            "erode": "Erode",
            "vellore": "Vellore",
            "thoothukudi": "Thoothukudi",
            "tiruppur": "Tiruppur",
            "thanjavur": "Thanjavur",
            "hosur": "Hosur",
            "dindigul": "Dindigul",
            "puducherry": "Puducherry",
            "pondicherry": "Puducherry",
        }
        for key, city in city_map.items():
            if key in loc:
                item["location_city"] = city
                return
        item["location_city"] = item.get("location", "").split(",")[0].strip()

    def _clean_html(self, text):
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()[:2000]

    def _errback(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url} – {failure.value}")
