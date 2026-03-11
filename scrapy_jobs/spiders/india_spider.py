"""
CareerPath Pro – Scrapy Spider: India Jobs (Multiple Sources)
═══════════════════════════════════════════════════════════════
Scrapes real job listings from APIs and job boards that serve Indian jobs.
Targets sources with public APIs / scrapeable pages for Indian market.
"""

import json
import re
import scrapy
from datetime import datetime
from urllib.parse import urlencode, quote_plus

from scrapy_jobs.items import JobItem


class IndiaJobsSpider(scrapy.Spider):
    """
    Multi-source spider for India jobs. Uses:
    1. Remotive API (India filter)
    2. Himalayas API (India)
    3. Arbeitnow API (India)
    4. RemoteOK API (India tags)
    5. Jobicy API (India)
    6. LinkedIn RSS feeds (India cities)
    7. Indeed RSS (India)
    8. Google Jobs RSS via SerpAPI / custom
    9. Internshala careers page
    10. Freshersworld listings
    11. Wellfound (AngelList) startup jobs
    12. Glassdoor listings
    """

    name = "india_jobs"
    custom_settings = {
        "CONCURRENT_REQUESTS": 8,
        "DOWNLOAD_DELAY": 2,
        "FEEDS": {},  # Handled by pipeline
    }

    # Indian cities to search
    INDIA_CITIES = [
        "Bangalore", "Mumbai", "Delhi", "Hyderabad", "Pune", "Chennai",
        "Kolkata", "Noida", "Gurgaon", "Ahmedabad", "Jaipur", "Kochi",
        "Coimbatore", "Indore", "Chandigarh", "Lucknow", "Thiruvananthapuram",
    ]

    SEARCH_KEYWORDS = [
        "software engineer", "developer", "data scientist", "python",
        "java developer", "react developer", "devops", "machine learning",
        "full stack", "frontend", "backend", "cloud engineer",
        "data analyst", "product manager", "UI UX designer",
        "cybersecurity", "android developer", "ios developer",
        "QA engineer", "business analyst",
    ]

    def start_requests(self):
        """Generate requests for all sources."""
        yield from self._remotive_requests()
        yield from self._himalayas_requests()
        yield from self._arbeitnow_requests()
        yield from self._remoteok_requests()
        yield from self._jobicy_requests()
        yield from self._linkedin_rss_requests()
        yield from self._indeed_rss_requests()
        yield from self._internshala_requests()
        yield from self._weworkremotely_requests()
        yield from self._themuse_requests()
        yield from self._adzuna_requests()
        yield from self._jooble_requests()

    # ── 1. Remotive API ────────────────────────────────────────────────
    def _remotive_requests(self):
        categories = [
            "software-dev", "data", "devops-sysadmin", "design",
            "product", "customer-support", "qa",
        ]
        for cat in categories:
            url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=50"
            yield scrapy.Request(url, callback=self.parse_remotive,
                                meta={"source": "Remotive"}, dont_filter=True)

    def parse_remotive(self, response):
        try:
            data = json.loads(response.text)
            for job in data.get("jobs", []):
                # Filter for India-related
                loc = (job.get("candidate_required_location") or "").lower()
                if any(c.lower() in loc for c in ["india", "asia", "worldwide", "anywhere"]) or \
                   any(city.lower() in loc for city in self.INDIA_CITIES):
                    yield self._make_item(
                        title=job.get("title", ""),
                        company=job.get("company_name", ""),
                        location=job.get("candidate_required_location", "India"),
                        description=self._clean_html(job.get("description", "")),
                        job_type=job.get("job_type", "Full-time"),
                        salary=job.get("salary", ""),
                        source="Remotive",
                        source_url=job.get("url", ""),
                        apply_url=job.get("url", ""),
                        posted_date=job.get("publication_date", ""),
                        tags=job.get("tags", []),
                        company_logo=job.get("company_logo", ""),
                    )
        except Exception as e:
            self.logger.error(f"Remotive parse error: {e}")

    # ── 2. Himalayas API ───────────────────────────────────────────────
    def _himalayas_requests(self):
        url = "https://himalayas.app/jobs/api?limit=100&country=India"
        yield scrapy.Request(url, callback=self.parse_himalayas,
                            meta={"source": "Himalayas"}, dont_filter=True)

    def parse_himalayas(self, response):
        try:
            data = json.loads(response.text)
            for job in data.get("jobs", []):
                yield self._make_item(
                    title=job.get("title", ""),
                    company=job.get("companyName", ""),
                    location=job.get("location", "India"),
                    description=job.get("description", ""),
                    salary=job.get("salary", ""),
                    source="Himalayas",
                    source_url=f"https://himalayas.app/jobs/{job.get('slug', '')}",
                    apply_url=job.get("applicationLink", ""),
                    posted_date=job.get("pubDate", ""),
                    tags=job.get("categories", []),
                    company_logo=job.get("companyLogo", ""),
                )
        except Exception as e:
            self.logger.error(f"Himalayas parse error: {e}")

    # ── 3. Arbeitnow API ──────────────────────────────────────────────
    def _arbeitnow_requests(self):
        url = "https://www.arbeitnow.com/api/job-board-api?country=India"
        yield scrapy.Request(url, callback=self.parse_arbeitnow,
                            meta={"source": "Arbeitnow"}, dont_filter=True)

    def parse_arbeitnow(self, response):
        try:
            data = json.loads(response.text)
            for job in data.get("data", []):
                loc = (job.get("location") or "").lower()
                if "india" in loc or any(c.lower() in loc for c in self.INDIA_CITIES):
                    yield self._make_item(
                        title=job.get("title", ""),
                        company=job.get("company_name", ""),
                        location=job.get("location", "India"),
                        description=job.get("description", ""),
                        job_type="Remote" if job.get("remote") else "Full-time",
                        tags=job.get("tags", []),
                        source="Arbeitnow",
                        source_url=job.get("url", ""),
                        apply_url=job.get("url", ""),
                        posted_date=job.get("created_at", ""),
                    )
        except Exception as e:
            self.logger.error(f"Arbeitnow parse error: {e}")

    # ── 4. RemoteOK API ───────────────────────────────────────────────
    def _remoteok_requests(self):
        url = "https://remoteok.com/api"
        yield scrapy.Request(url, callback=self.parse_remoteok,
                            meta={"source": "RemoteOK"},
                            headers={"Accept": "application/json"},
                            dont_filter=True)

    def parse_remoteok(self, response):
        try:
            data = json.loads(response.text)
            if isinstance(data, list):
                data = data[1:]  # First item is metadata
            for job in data:
                loc = (job.get("location") or "").lower()
                tags = [t.lower() for t in job.get("tags", [])]
                # Include worldwide remote jobs + India specific
                if any(kw in loc for kw in ["india", "asia", "worldwide", "anywhere", "remote"]):
                    yield self._make_item(
                        title=job.get("position", ""),
                        company=job.get("company", ""),
                        location=job.get("location", "Remote (India eligible)"),
                        description=self._clean_html(job.get("description", "")),
                        salary=job.get("salary", ""),
                        tags=job.get("tags", []),
                        source="RemoteOK",
                        source_url=f"https://remoteok.com/remote-jobs/{job.get('id', '')}",
                        apply_url=job.get("apply_url", job.get("url", "")),
                        posted_date=job.get("date", ""),
                        company_logo=job.get("company_logo", ""),
                    )
        except Exception as e:
            self.logger.error(f"RemoteOK parse error: {e}")

    # ── 5. Jobicy API ─────────────────────────────────────────────────
    def _jobicy_requests(self):
        url = "https://jobicy.com/api/v2/remote-jobs?count=50&geo=india"
        yield scrapy.Request(url, callback=self.parse_jobicy,
                            meta={"source": "Jobicy"}, dont_filter=True)

    def parse_jobicy(self, response):
        try:
            data = json.loads(response.text)
            for job in data.get("jobs", []):
                yield self._make_item(
                    title=job.get("jobTitle", ""),
                    company=job.get("companyName", ""),
                    location=job.get("jobGeo", "India"),
                    description=self._clean_html(job.get("jobDescription", "")),
                    job_type=job.get("jobType", ""),
                    salary=f"{job.get('annualSalaryMin', '')}-{job.get('annualSalaryMax', '')}",
                    source="Jobicy",
                    source_url=job.get("url", ""),
                    apply_url=job.get("url", ""),
                    posted_date=job.get("pubDate", ""),
                    tags=job.get("jobIndustry", []) if isinstance(job.get("jobIndustry"), list) else [],
                )
        except Exception as e:
            self.logger.error(f"Jobicy parse error: {e}")

    # ── 6. LinkedIn RSS ───────────────────────────────────────────────
    def _linkedin_rss_requests(self):
        keywords = ["software+engineer", "developer", "data+scientist",
                     "devops", "python", "java", "react", "product+manager"]
        for kw in keywords:
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={kw}&location=India&start=0&count=25"
            yield scrapy.Request(url, callback=self.parse_linkedin,
                                meta={"source": "LinkedIn", "keyword": kw},
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

                if title and company:
                    yield self._make_item(
                        title=title,
                        company=company,
                        location=location or "India",
                        source="LinkedIn",
                        source_url=link.split("?")[0] if link else "",
                        apply_url=link.split("?")[0] if link else "",
                        posted_date=posted,
                        company_logo=logo,
                    )
        except Exception as e:
            self.logger.error(f"LinkedIn parse error: {e}")

    # ── 7. Indeed RSS ─────────────────────────────────────────────────
    def _indeed_rss_requests(self):
        queries = ["software+developer", "data+analyst", "python+developer",
                    "devops+engineer", "java+developer", "react+developer"]
        for q in queries:
            url = f"https://www.indeed.co.in/rss?q={q}&l=India&sort=date"
            yield scrapy.Request(url, callback=self.parse_indeed_rss,
                                meta={"source": "Indeed"}, dont_filter=True)

    def parse_indeed_rss(self, response):
        try:
            items = response.xpath("//item")
            for item in items:
                title = item.xpath("title/text()").get("").strip()
                link = item.xpath("link/text()").get("").strip()
                desc = item.xpath("description/text()").get("").strip()
                pub_date = item.xpath("pubDate/text()").get("").strip()
                # Extract company and location from title
                # Indeed format: "Job Title - Company - Location"
                parts = title.split(" - ")
                job_title = parts[0] if parts else title
                company = parts[1] if len(parts) > 1 else ""
                location = parts[2] if len(parts) > 2 else "India"

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
            self.logger.error(f"Indeed RSS parse error: {e}")

    # ── 8. Internshala ────────────────────────────────────────────────
    def _internshala_requests(self):
        categories = [
            "web-development", "python-django-development", "data-science",
            "machine-learning", "mobile-app-development", "java-development",
            "react-development", "digital-marketing", "content-writing",
            "graphic-design",
        ]
        for cat in categories:
            for page in [1, 2]:
                url = f"https://internshala.com/jobs/{cat}-jobs/page-{page}"
                yield scrapy.Request(url, callback=self.parse_internshala,
                                    meta={"source": "Internshala", "category": cat},
                                    dont_filter=True)
            # Also internships
            url = f"https://internshala.com/internships/{cat}-internship"
            yield scrapy.Request(url, callback=self.parse_internshala,
                                meta={"source": "Internshala", "category": cat,
                                       "is_internship": True},
                                dont_filter=True)

    def parse_internshala(self, response):
        try:
            is_internship = response.meta.get("is_internship", False)
            # Internshala job cards
            cards = response.css("div.individual_internship, div.container-fluid.individual_internship")
            if not cards:
                cards = response.css(".internship_meta")

            for card in cards:
                title = card.css("h3.heading_4_5 a::text, .job-internship-name a::text").get("").strip()
                company = card.css("h4.heading_6 a::text, .company_name a::text").get("").strip()
                location = ", ".join(
                    card.css("#location_names span a::text, .location_link span::text").getall()
                ).strip() or "India"
                link_path = card.css("h3.heading_4_5 a::attr(href), .job-internship-name a::attr(href)").get("")
                stipend = card.css(".stipend::text, span.desktop-text::text").get("").strip()
                duration = card.css(".item_body:nth-child(2)::text").get("").strip()

                apply_url = f"https://internshala.com{link_path}" if link_path else ""

                if title:
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
            self.logger.error(f"Internshala parse error: {e}")

    # ── 9. We Work Remotely ───────────────────────────────────────────
    def _weworkremotely_requests(self):
        categories = [
            "remote-jobs/programming-jobs",
            "remote-jobs/design-jobs",
            "remote-jobs/devops-sysadmin-jobs",
            "remote-jobs/management-and-finance-jobs",
            "remote-jobs/sales-and-marketing-jobs",
        ]
        for cat in categories:
            url = f"https://weworkremotely.com/categories/{cat}"
            yield scrapy.Request(url, callback=self.parse_weworkremotely,
                                meta={"source": "WeWorkRemotely"}, dont_filter=True)

    def parse_weworkremotely(self, response):
        try:
            jobs = response.css("li.feature, li:not(.ad)")
            for job in jobs:
                link_tag = job.css("a[href*='/remote-jobs/']")
                if not link_tag:
                    continue
                href = link_tag.attrib.get("href", "")
                title = job.css(".title::text").get("").strip()
                company = job.css(".company::text").get("").strip()
                region = job.css(".region::text").get("").strip()

                # Include if region allows India
                if title and company:
                    yield self._make_item(
                        title=title,
                        company=company,
                        location=region if region else "Remote (Worldwide)",
                        source="WeWorkRemotely",
                        source_url=f"https://weworkremotely.com{href}",
                        apply_url=f"https://weworkremotely.com{href}",
                    )
        except Exception as e:
            self.logger.error(f"WeWorkRemotely parse error: {e}")

    # ── 10. The Muse API ──────────────────────────────────────────────
    def _themuse_requests(self):
        for page in range(1, 4):
            url = f"https://www.themuse.com/api/public/jobs?location=India&page={page}"
            yield scrapy.Request(url, callback=self.parse_themuse,
                                meta={"source": "TheMuse"}, dont_filter=True)

    def parse_themuse(self, response):
        try:
            data = json.loads(response.text)
            for job in data.get("results", []):
                locations = [loc.get("name", "") for loc in job.get("locations", [])]
                loc_str = ", ".join(locations) if locations else "India"
                company_info = job.get("company", {})

                yield self._make_item(
                    title=job.get("name", ""),
                    company=company_info.get("name", ""),
                    location=loc_str,
                    description=job.get("contents", ""),
                    tags=job.get("tags", []),
                    category=", ".join(c.get("name", "") for c in job.get("categories", [])),
                    source="TheMuse",
                    source_url=f"https://www.themuse.com/jobs/{job.get('short_name', '')}",
                    apply_url=job.get("refs", {}).get("landing_page", ""),
                    posted_date=job.get("publication_date", ""),
                )
        except Exception as e:
            self.logger.error(f"TheMuse parse error: {e}")

    # ── 11. Adzuna API ────────────────────────────────────────────────
    def _adzuna_requests(self):
        # Adzuna has a free API (limited) – India country code = "in"
        app_id = "a2379c1a"  # Free tier app_id placeholder – user should register
        app_key = "free"     # Placeholder
        queries = ["developer", "engineer", "data scientist", "devops"]
        for q in queries:
            url = (f"https://api.adzuna.com/v1/api/jobs/in/search/1"
                   f"?app_id={app_id}&app_key={app_key}"
                   f"&results_per_page=50&what={quote_plus(q)}&content-type=application/json")
            yield scrapy.Request(url, callback=self.parse_adzuna,
                                meta={"source": "Adzuna"},
                                errback=self._errback,
                                dont_filter=True)

    def parse_adzuna(self, response):
        try:
            data = json.loads(response.text)
            for job in data.get("results", []):
                loc = job.get("location", {})
                loc_parts = loc.get("display_name", "India")

                yield self._make_item(
                    title=job.get("title", ""),
                    company=job.get("company", {}).get("display_name", ""),
                    location=loc_parts,
                    description=job.get("description", ""),
                    salary=str(job.get("salary_max", "")),
                    salary_min=job.get("salary_min"),
                    salary_max=job.get("salary_max"),
                    source="Adzuna",
                    source_url=job.get("redirect_url", ""),
                    apply_url=job.get("redirect_url", ""),
                    posted_date=job.get("created", ""),
                    category=job.get("category", {}).get("label", ""),
                )
        except Exception as e:
            self.logger.error(f"Adzuna parse error: {e}")

    # ── 12. Jooble API ────────────────────────────────────────────────
    def _jooble_requests(self):
        # Jooble offers free API access (register at jooble.org/api/about)
        api_key = ""  # Set via settings or env
        if not api_key:
            return

        keywords = ["python developer", "java developer", "react developer",
                     "data scientist", "devops engineer"]
        for kw in keywords:
            url = f"https://jooble.org/api/{api_key}"
            yield scrapy.Request(
                url, method="POST",
                body=json.dumps({"keywords": kw, "location": "India"}),
                headers={"Content-Type": "application/json"},
                callback=self.parse_jooble,
                meta={"source": "Jooble"},
                dont_filter=True,
            )

    def parse_jooble(self, response):
        try:
            data = json.loads(response.text)
            for job in data.get("jobs", []):
                yield self._make_item(
                    title=job.get("title", ""),
                    company=job.get("company", ""),
                    location=job.get("location", "India"),
                    description=self._clean_html(job.get("snippet", "")),
                    salary=job.get("salary", ""),
                    source="Jooble",
                    source_url=job.get("link", ""),
                    apply_url=job.get("link", ""),
                    posted_date=job.get("updated", ""),
                    job_type=job.get("type", ""),
                )
        except Exception as e:
            self.logger.error(f"Jooble parse error: {e}")

    # ── Helpers ────────────────────────────────────────────────────────

    def _make_item(self, **kwargs):
        """Create a standardized JobItem."""
        item = JobItem()
        item["title"] = kwargs.get("title", "").strip()
        item["company"] = kwargs.get("company", "").strip()
        item["location"] = kwargs.get("location", "India").strip()
        item["location_country"] = "India"
        item["description"] = kwargs.get("description", "")
        item["job_type"] = kwargs.get("job_type", "Full-time")
        item["salary"] = kwargs.get("salary", "")
        item["salary_min"] = kwargs.get("salary_min")
        item["salary_max"] = kwargs.get("salary_max")
        item["salary_currency"] = kwargs.get("salary_currency", "INR")
        item["category"] = kwargs.get("category", "")
        item["skills"] = kwargs.get("skills", [])
        item["tags"] = kwargs.get("tags", [])
        item["source"] = kwargs.get("source", "")
        item["source_url"] = kwargs.get("source_url", "")
        item["apply_url"] = kwargs.get("apply_url", "")
        item["posted_date"] = kwargs.get("posted_date", "")
        item["company_logo"] = kwargs.get("company_logo", "")
        item["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Parse location into city/state
        self._parse_location(item)
        return item

    def _parse_location(self, item):
        """Extract city and state from location string."""
        loc = item.get("location", "")
        city_state_map = {
            "bangalore": ("Bangalore", "Karnataka"),
            "bengaluru": ("Bangalore", "Karnataka"),
            "mumbai": ("Mumbai", "Maharashtra"),
            "delhi": ("Delhi", "Delhi NCR"),
            "new delhi": ("New Delhi", "Delhi NCR"),
            "hyderabad": ("Hyderabad", "Telangana"),
            "pune": ("Pune", "Maharashtra"),
            "chennai": ("Chennai", "Tamil Nadu"),
            "kolkata": ("Kolkata", "West Bengal"),
            "gurgaon": ("Gurgaon", "Haryana"),
            "gurugram": ("Gurgaon", "Haryana"),
            "noida": ("Noida", "Uttar Pradesh"),
            "ahmedabad": ("Ahmedabad", "Gujarat"),
            "jaipur": ("Jaipur", "Rajasthan"),
            "kochi": ("Kochi", "Kerala"),
            "coimbatore": ("Coimbatore", "Tamil Nadu"),
            "indore": ("Indore", "Madhya Pradesh"),
            "chandigarh": ("Chandigarh", "Chandigarh"),
            "lucknow": ("Lucknow", "Uttar Pradesh"),
            "thiruvananthapuram": ("Thiruvananthapuram", "Kerala"),
            "madurai": ("Madurai", "Tamil Nadu"),
            "trichy": ("Tiruchirappalli", "Tamil Nadu"),
            "pondicherry": ("Puducherry", "Puducherry"),
            "puducherry": ("Puducherry", "Puducherry"),
        }
        loc_lower = loc.lower()
        for key, (city, state) in city_state_map.items():
            if key in loc_lower:
                item["location_city"] = city
                item["location_state"] = state
                return
        item["location_city"] = loc.split(",")[0].strip() if "," in loc else loc
        item["location_state"] = ""

    def _clean_html(self, text):
        """Strip HTML tags from text."""
        if not text:
            return ""
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()[:2000]

    def _errback(self, failure):
        self.logger.warning(f"Request failed: {failure.request.url} – {failure.value}")
