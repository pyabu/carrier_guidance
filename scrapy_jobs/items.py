"""
Careerguidance – Scrapy Items
Defines the data model for scraped job listings.
"""

import scrapy


class JobItem(scrapy.Item):
    """Standardized job listing item."""
    # Core fields
    title = scrapy.Field()
    company = scrapy.Field()
    location = scrapy.Field()
    location_city = scrapy.Field()
    location_state = scrapy.Field()
    location_country = scrapy.Field()

    # Job details
    description = scrapy.Field()
    requirements = scrapy.Field()
    job_type = scrapy.Field()          # Full-time, Part-time, Contract, Internship
    experience_level = scrapy.Field()  # Entry, Mid, Senior, Lead
    experience_years = scrapy.Field()
    salary = scrapy.Field()
    salary_min = scrapy.Field()
    salary_max = scrapy.Field()
    salary_currency = scrapy.Field()
    category = scrapy.Field()

    # Skills & Tags
    skills = scrapy.Field()
    tags = scrapy.Field()

    # Source info
    source = scrapy.Field()
    source_url = scrapy.Field()
    apply_url = scrapy.Field()
    job_id = scrapy.Field()

    # Company info
    company_logo = scrapy.Field()
    company_url = scrapy.Field()

    # Timestamps
    posted_date = scrapy.Field()
    scraped_at = scrapy.Field()

    # AI-enriched fields (filled by pipeline)
    ai_category = scrapy.Field()
    ai_skills = scrapy.Field()
    ai_quality_score = scrapy.Field()
    ai_summary = scrapy.Field()
