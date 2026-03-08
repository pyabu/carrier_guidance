"""
CareerPath Pro – Production Multi-Source Job Scraper
═══════════════════════════════════════════════════════════
Pulls REAL jobs daily from 8+ public job APIs / feeds:
  1. Remotive          – remote jobs (free, no key)
  2. Arbeitnow         – EU/global jobs (free, no key)
  3. RemoteOK          – remote tech jobs (free, no key)
  4. Jobicy             – remote jobs (free, no key)
  5. The Muse           – US jobs (free, no key)
  6. Adzuna             – UK/US/AU/IN (free tier, key optional)
  7. FindWork           – dev jobs (free, no key)
  8. LinkedIn / Indeed  – via RSS proxy (public feeds)

Also generates supplemental data from 80+ real companies
so the board always has rich content even when APIs are down.
"""

import logging
import os
import random
import re
import hashlib
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# ── 80+ real-world companies (global + India + startups) ──────────────
COMPANIES = [
    # FAANG / Big Tech
    {"name": "Google", "logo": "https://logo.clearbit.com/google.com", "industry": "Technology", "hq": "Mountain View, CA"},
    {"name": "Microsoft", "logo": "https://logo.clearbit.com/microsoft.com", "industry": "Technology", "hq": "Redmond, WA"},
    {"name": "Amazon", "logo": "https://logo.clearbit.com/amazon.com", "industry": "E-Commerce", "hq": "Seattle, WA"},
    {"name": "Apple", "logo": "https://logo.clearbit.com/apple.com", "industry": "Technology", "hq": "Cupertino, CA"},
    {"name": "Meta", "logo": "https://logo.clearbit.com/meta.com", "industry": "Social Media", "hq": "Menlo Park, CA"},
    {"name": "Netflix", "logo": "https://logo.clearbit.com/netflix.com", "industry": "Entertainment", "hq": "Los Gatos, CA"},
    # Cloud & Enterprise
    {"name": "Salesforce", "logo": "https://logo.clearbit.com/salesforce.com", "industry": "Cloud / SaaS", "hq": "San Francisco, CA"},
    {"name": "Oracle", "logo": "https://logo.clearbit.com/oracle.com", "industry": "Enterprise Software", "hq": "Austin, TX"},
    {"name": "IBM", "logo": "https://logo.clearbit.com/ibm.com", "industry": "Technology", "hq": "Armonk, NY"},
    {"name": "SAP", "logo": "https://logo.clearbit.com/sap.com", "industry": "Enterprise Software", "hq": "Walldorf, Germany"},
    {"name": "ServiceNow", "logo": "https://logo.clearbit.com/servicenow.com", "industry": "Cloud / SaaS", "hq": "Santa Clara, CA"},
    {"name": "Snowflake", "logo": "https://logo.clearbit.com/snowflake.com", "industry": "Data / Cloud", "hq": "Bozeman, MT"},
    {"name": "Databricks", "logo": "https://logo.clearbit.com/databricks.com", "industry": "Data / AI", "hq": "San Francisco, CA"},
    {"name": "Palantir", "logo": "https://logo.clearbit.com/palantir.com", "industry": "Data Analytics", "hq": "Denver, CO"},
    # Fintech / Payments
    {"name": "Stripe", "logo": "https://logo.clearbit.com/stripe.com", "industry": "Fintech", "hq": "San Francisco, CA"},
    {"name": "PayPal", "logo": "https://logo.clearbit.com/paypal.com", "industry": "Fintech", "hq": "San Jose, CA"},
    {"name": "Square (Block)", "logo": "https://logo.clearbit.com/block.xyz", "industry": "Fintech", "hq": "San Francisco, CA"},
    {"name": "Razorpay", "logo": "https://logo.clearbit.com/razorpay.com", "industry": "Fintech", "hq": "Bangalore, India"},
    {"name": "PhonePe", "logo": "https://logo.clearbit.com/phonepe.com", "industry": "Fintech", "hq": "Bangalore, India"},
    {"name": "Visa", "logo": "https://logo.clearbit.com/visa.com", "industry": "Fintech", "hq": "San Francisco, CA"},
    {"name": "Goldman Sachs", "logo": "https://logo.clearbit.com/goldmansachs.com", "industry": "Finance", "hq": "New York, NY"},
    {"name": "JPMorgan Chase", "logo": "https://logo.clearbit.com/jpmorganchase.com", "industry": "Finance", "hq": "New York, NY"},
    # India IT / Consulting
    {"name": "Infosys", "logo": "https://logo.clearbit.com/infosys.com", "industry": "IT Services", "hq": "Bangalore, India"},
    {"name": "TCS", "logo": "https://logo.clearbit.com/tcs.com", "industry": "IT Services", "hq": "Mumbai, India"},
    {"name": "Wipro", "logo": "https://logo.clearbit.com/wipro.com", "industry": "IT Services", "hq": "Bangalore, India"},
    {"name": "HCL Technologies", "logo": "https://logo.clearbit.com/hcltech.com", "industry": "IT Services", "hq": "Noida, India"},
    {"name": "Tech Mahindra", "logo": "https://logo.clearbit.com/techmahindra.com", "industry": "IT Services", "hq": "Pune, India"},
    {"name": "Cognizant", "logo": "https://logo.clearbit.com/cognizant.com", "industry": "IT Services", "hq": "Teaneck, NJ"},
    {"name": "Accenture", "logo": "https://logo.clearbit.com/accenture.com", "industry": "Consulting", "hq": "Dublin, Ireland"},
    {"name": "Deloitte", "logo": "https://logo.clearbit.com/deloitte.com", "industry": "Consulting", "hq": "London, UK"},
    # India Product Companies
    {"name": "Flipkart", "logo": "https://logo.clearbit.com/flipkart.com", "industry": "E-Commerce", "hq": "Bangalore, India"},
    {"name": "Swiggy", "logo": "https://logo.clearbit.com/swiggy.com", "industry": "Food Tech", "hq": "Bangalore, India"},
    {"name": "Zomato", "logo": "https://logo.clearbit.com/zomato.com", "industry": "Food Tech", "hq": "Gurugram, India"},
    {"name": "Paytm", "logo": "https://logo.clearbit.com/paytm.com", "industry": "Fintech", "hq": "Noida, India"},
    {"name": "CRED", "logo": "https://logo.clearbit.com/cred.club", "industry": "Fintech", "hq": "Bangalore, India"},
    {"name": "Meesho", "logo": "https://logo.clearbit.com/meesho.com", "industry": "E-Commerce", "hq": "Bangalore, India"},
    {"name": "Ola", "logo": "https://logo.clearbit.com/olacabs.com", "industry": "Transportation", "hq": "Bangalore, India"},
    {"name": "Zerodha", "logo": "https://logo.clearbit.com/zerodha.com", "industry": "Fintech", "hq": "Bangalore, India"},
    {"name": "Freshworks", "logo": "https://logo.clearbit.com/freshworks.com", "industry": "Cloud / SaaS", "hq": "Chennai, India"},
    {"name": "Zoho", "logo": "https://logo.clearbit.com/zoho.com", "industry": "Cloud / SaaS", "hq": "Chennai, India"},
    {"name": "Dream11", "logo": "https://logo.clearbit.com/dream11.com", "industry": "Gaming / Sports", "hq": "Mumbai, India"},
    {"name": "Byju's", "logo": "https://logo.clearbit.com/byjus.com", "industry": "EdTech", "hq": "Bangalore, India"},
    {"name": "Unacademy", "logo": "https://logo.clearbit.com/unacademy.com", "industry": "EdTech", "hq": "Bangalore, India"},
    {"name": "Nykaa", "logo": "https://logo.clearbit.com/nykaa.com", "industry": "E-Commerce", "hq": "Mumbai, India"},
    {"name": "Groww", "logo": "https://logo.clearbit.com/groww.in", "industry": "Fintech", "hq": "Bangalore, India"},
    {"name": "ShareChat", "logo": "https://logo.clearbit.com/sharechat.com", "industry": "Social Media", "hq": "Bangalore, India"},
    {"name": "Ather Energy", "logo": "https://logo.clearbit.com/atherenergy.com", "industry": "EV / Automotive", "hq": "Bangalore, India"},
    {"name": "Delhivery", "logo": "https://logo.clearbit.com/delhivery.com", "industry": "Logistics", "hq": "Gurugram, India"},
    {"name": "Pine Labs", "logo": "https://logo.clearbit.com/pinelabs.com", "industry": "Fintech", "hq": "Noida, India"},
    {"name": "PolicyBazaar", "logo": "https://logo.clearbit.com/policybazaar.com", "industry": "InsurTech", "hq": "Gurugram, India"},
    # US / Global Tech
    {"name": "Tesla", "logo": "https://logo.clearbit.com/tesla.com", "industry": "Automotive / Energy", "hq": "Austin, TX"},
    {"name": "Uber", "logo": "https://logo.clearbit.com/uber.com", "industry": "Transportation", "hq": "San Francisco, CA"},
    {"name": "Airbnb", "logo": "https://logo.clearbit.com/airbnb.com", "industry": "Hospitality", "hq": "San Francisco, CA"},
    {"name": "Spotify", "logo": "https://logo.clearbit.com/spotify.com", "industry": "Music / Media", "hq": "Stockholm, Sweden"},
    {"name": "Adobe", "logo": "https://logo.clearbit.com/adobe.com", "industry": "Software", "hq": "San Jose, CA"},
    {"name": "Shopify", "logo": "https://logo.clearbit.com/shopify.com", "industry": "E-Commerce / SaaS", "hq": "Ottawa, Canada"},
    {"name": "Atlassian", "logo": "https://logo.clearbit.com/atlassian.com", "industry": "Software", "hq": "Sydney, Australia"},
    {"name": "Twilio", "logo": "https://logo.clearbit.com/twilio.com", "industry": "Cloud / APIs", "hq": "San Francisco, CA"},
    {"name": "Slack", "logo": "https://logo.clearbit.com/slack.com", "industry": "Communication", "hq": "San Francisco, CA"},
    {"name": "Zoom", "logo": "https://logo.clearbit.com/zoom.us", "industry": "Communication", "hq": "San Jose, CA"},
    {"name": "Twitter / X", "logo": "https://logo.clearbit.com/x.com", "industry": "Social Media", "hq": "San Francisco, CA"},
    {"name": "LinkedIn", "logo": "https://logo.clearbit.com/linkedin.com", "industry": "Social Media / HR Tech", "hq": "Sunnyvale, CA"},
    {"name": "Pinterest", "logo": "https://logo.clearbit.com/pinterest.com", "industry": "Social Media", "hq": "San Francisco, CA"},
    {"name": "Snap Inc.", "logo": "https://logo.clearbit.com/snap.com", "industry": "Social Media", "hq": "Santa Monica, CA"},
    {"name": "Reddit", "logo": "https://logo.clearbit.com/reddit.com", "industry": "Social Media", "hq": "San Francisco, CA"},
    {"name": "Dropbox", "logo": "https://logo.clearbit.com/dropbox.com", "industry": "Cloud Storage", "hq": "San Francisco, CA"},
    {"name": "Notion", "logo": "https://logo.clearbit.com/notion.so", "industry": "Productivity", "hq": "San Francisco, CA"},
    {"name": "Figma", "logo": "https://logo.clearbit.com/figma.com", "industry": "Design Tools", "hq": "San Francisco, CA"},
    {"name": "Canva", "logo": "https://logo.clearbit.com/canva.com", "industry": "Design Tools", "hq": "Sydney, Australia"},
    {"name": "GitHub", "logo": "https://logo.clearbit.com/github.com", "industry": "Developer Tools", "hq": "San Francisco, CA"},
    {"name": "GitLab", "logo": "https://logo.clearbit.com/gitlab.com", "industry": "Developer Tools", "hq": "Remote"},
    {"name": "Docker", "logo": "https://logo.clearbit.com/docker.com", "industry": "Developer Tools", "hq": "Palo Alto, CA"},
    {"name": "HashiCorp", "logo": "https://logo.clearbit.com/hashicorp.com", "industry": "Cloud Infrastructure", "hq": "San Francisco, CA"},
    {"name": "Cloudflare", "logo": "https://logo.clearbit.com/cloudflare.com", "industry": "Cloud / Security", "hq": "San Francisco, CA"},
    {"name": "Elastic", "logo": "https://logo.clearbit.com/elastic.co", "industry": "Search / Analytics", "hq": "San Francisco, CA"},
    {"name": "MongoDB", "logo": "https://logo.clearbit.com/mongodb.com", "industry": "Database", "hq": "New York, NY"},
    {"name": "Confluent", "logo": "https://logo.clearbit.com/confluent.io", "industry": "Data Streaming", "hq": "Mountain View, CA"},
    # AI / ML Companies
    {"name": "OpenAI", "logo": "https://logo.clearbit.com/openai.com", "industry": "AI / ML", "hq": "San Francisco, CA"},
    {"name": "Anthropic", "logo": "https://logo.clearbit.com/anthropic.com", "industry": "AI / ML", "hq": "San Francisco, CA"},
    {"name": "NVIDIA", "logo": "https://logo.clearbit.com/nvidia.com", "industry": "Semiconductors / AI", "hq": "Santa Clara, CA"},
    {"name": "DeepMind", "logo": "https://logo.clearbit.com/deepmind.com", "industry": "AI Research", "hq": "London, UK"},
    {"name": "Hugging Face", "logo": "https://logo.clearbit.com/huggingface.co", "industry": "AI / ML", "hq": "New York, NY"},
    # E-Commerce / Retail
    {"name": "Walmart", "logo": "https://logo.clearbit.com/walmart.com", "industry": "Retail", "hq": "Bentonville, AR"},
    {"name": "Target", "logo": "https://logo.clearbit.com/target.com", "industry": "Retail", "hq": "Minneapolis, MN"},
    {"name": "eBay", "logo": "https://logo.clearbit.com/ebay.com", "industry": "E-Commerce", "hq": "San Jose, CA"},
    {"name": "Etsy", "logo": "https://logo.clearbit.com/etsy.com", "industry": "E-Commerce", "hq": "Brooklyn, NY"},
    # Healthcare / Biotech
    {"name": "Johnson & Johnson", "logo": "https://logo.clearbit.com/jnj.com", "industry": "Healthcare", "hq": "New Brunswick, NJ"},
    {"name": "Pfizer", "logo": "https://logo.clearbit.com/pfizer.com", "industry": "Pharma", "hq": "New York, NY"},
    # Telecom
    {"name": "Cisco", "logo": "https://logo.clearbit.com/cisco.com", "industry": "Networking", "hq": "San Jose, CA"},
    {"name": "Intel", "logo": "https://logo.clearbit.com/intel.com", "industry": "Semiconductors", "hq": "Santa Clara, CA"},
    {"name": "Samsung", "logo": "https://logo.clearbit.com/samsung.com", "industry": "Electronics", "hq": "Seoul, South Korea"},
    {"name": "Qualcomm", "logo": "https://logo.clearbit.com/qualcomm.com", "industry": "Semiconductors", "hq": "San Diego, CA"},
]

# ── 40 unique roles spanning all career tracks ────────────────────────
ROLES = [
    # Software Engineering
    {"title": "Software Engineer", "category": "Technology", "skills": ["Python", "Java", "System Design", "DSA"]},
    {"title": "Senior Software Engineer", "category": "Technology", "skills": ["Python", "Microservices", "AWS", "System Design"]},
    {"title": "Frontend Developer", "category": "Technology", "skills": ["React", "JavaScript", "TypeScript", "CSS"]},
    {"title": "Backend Developer", "category": "Technology", "skills": ["Node.js", "Python", "PostgreSQL", "REST APIs"]},
    {"title": "Full Stack Developer", "category": "Technology", "skills": ["React", "Node.js", "MongoDB", "Docker"]},
    {"title": "Mobile Developer", "category": "Technology", "skills": ["React Native", "Flutter", "Swift", "Kotlin"]},
    {"title": "iOS Developer", "category": "Technology", "skills": ["Swift", "SwiftUI", "Xcode", "Core Data"]},
    {"title": "Android Developer", "category": "Technology", "skills": ["Kotlin", "Jetpack Compose", "Android SDK", "Firebase"]},
    # DevOps / Cloud / Infra
    {"title": "DevOps Engineer", "category": "Technology", "skills": ["AWS", "Docker", "Kubernetes", "CI/CD"]},
    {"title": "SRE / Platform Engineer", "category": "Technology", "skills": ["Kubernetes", "Terraform", "Prometheus", "Go"]},
    {"title": "Cloud Architect", "category": "Technology", "skills": ["AWS", "Azure", "GCP", "Terraform"]},
    {"title": "Cybersecurity Analyst", "category": "Technology", "skills": ["Security", "SIEM", "Penetration Testing", "IAM"]},
    # Data & AI
    {"title": "Data Scientist", "category": "Data Science", "skills": ["Python", "Machine Learning", "SQL", "TensorFlow"]},
    {"title": "Data Analyst", "category": "Data Science", "skills": ["SQL", "Python", "Tableau", "Power BI"]},
    {"title": "Data Engineer", "category": "Data Science", "skills": ["Spark", "Python", "Airflow", "BigQuery"]},
    {"title": "ML Engineer", "category": "Data Science", "skills": ["PyTorch", "Python", "MLOps", "Deep Learning"]},
    {"title": "AI Research Scientist", "category": "Data Science", "skills": ["NLP", "Computer Vision", "Python", "Research"]},
    {"title": "LLM / GenAI Engineer", "category": "Data Science", "skills": ["LangChain", "Python", "Fine-tuning", "RAG"]},
    {"title": "Business Intelligence Analyst", "category": "Data Science", "skills": ["Tableau", "SQL", "Excel", "Looker"]},
    # QA / Testing
    {"title": "QA Engineer", "category": "Technology", "skills": ["Selenium", "Cypress", "Automation", "JIRA"]},
    {"title": "SDET", "category": "Technology", "skills": ["Java", "Selenium", "API Testing", "CI/CD"]},
    # Design
    {"title": "UI/UX Designer", "category": "Design", "skills": ["Figma", "Adobe XD", "Prototyping", "User Research"]},
    {"title": "Product Designer", "category": "Design", "skills": ["Figma", "Design Systems", "Wireframing", "UX"]},
    {"title": "Graphic Designer", "category": "Design", "skills": ["Photoshop", "Illustrator", "Branding", "Typography"]},
    # Management / Business
    {"title": "Product Manager", "category": "Management", "skills": ["Agile", "Strategy", "Analytics", "Roadmapping"]},
    {"title": "Engineering Manager", "category": "Management", "skills": ["Leadership", "Agile", "System Design", "Mentoring"]},
    {"title": "Scrum Master", "category": "Management", "skills": ["Scrum", "JIRA", "Facilitation", "Kanban"]},
    {"title": "Technical Program Manager", "category": "Management", "skills": ["Program Management", "Agile", "Stakeholders", "Roadmapping"]},
    {"title": "Business Analyst", "category": "Business", "skills": ["SQL", "Excel", "Requirements", "Stakeholder Management"]},
    # Marketing / Content
    {"title": "Digital Marketing Manager", "category": "Marketing", "skills": ["SEO", "Google Ads", "Analytics", "Content Strategy"]},
    {"title": "Content Writer", "category": "Marketing", "skills": ["Writing", "SEO", "Research", "Editing"]},
    {"title": "Growth Hacker", "category": "Marketing", "skills": ["SEO", "CRO", "A/B Testing", "Analytics"]},
    {"title": "Social Media Manager", "category": "Marketing", "skills": ["Social Media", "Content", "Analytics", "Copywriting"]},
    # HR / Ops
    {"title": "HR Manager", "category": "Human Resources", "skills": ["Recruitment", "Employee Relations", "HRIS", "Compliance"]},
    {"title": "Technical Recruiter", "category": "Human Resources", "skills": ["Sourcing", "ATS", "Interviewing", "Employer Branding"]},
    # Finance / Consulting
    {"title": "Financial Analyst", "category": "Finance", "skills": ["Excel", "Financial Modeling", "SQL", "Forecasting"]},
    {"title": "Management Consultant", "category": "Consulting", "skills": ["Strategy", "Excel", "Presentation", "Problem Solving"]},
    # Internships
    {"title": "Software Engineering Intern", "category": "Internship", "skills": ["Python", "Java", "DSA", "Git"]},
    {"title": "Data Science Intern", "category": "Internship", "skills": ["Python", "ML", "SQL", "Statistics"]},
    {"title": "Marketing Intern", "category": "Internship", "skills": ["Social Media", "Content", "Analytics", "Communication"]},
    {"title": "Design Intern", "category": "Internship", "skills": ["Figma", "UI Design", "Prototyping", "Creativity"]},
]

# ── 60+ locations with proper city / state / country structure ─────────
LOCATIONS = [
    # United States
    {"city": "San Francisco", "state": "CA", "country": "United States", "display": "San Francisco, CA, USA"},
    {"city": "New York", "state": "NY", "country": "United States", "display": "New York, NY, USA"},
    {"city": "Seattle", "state": "WA", "country": "United States", "display": "Seattle, WA, USA"},
    {"city": "Austin", "state": "TX", "country": "United States", "display": "Austin, TX, USA"},
    {"city": "Chicago", "state": "IL", "country": "United States", "display": "Chicago, IL, USA"},
    {"city": "Boston", "state": "MA", "country": "United States", "display": "Boston, MA, USA"},
    {"city": "Los Angeles", "state": "CA", "country": "United States", "display": "Los Angeles, CA, USA"},
    {"city": "Denver", "state": "CO", "country": "United States", "display": "Denver, CO, USA"},
    {"city": "Atlanta", "state": "GA", "country": "United States", "display": "Atlanta, GA, USA"},
    {"city": "San Jose", "state": "CA", "country": "United States", "display": "San Jose, CA, USA"},
    {"city": "Mountain View", "state": "CA", "country": "United States", "display": "Mountain View, CA, USA"},
    {"city": "Redmond", "state": "WA", "country": "United States", "display": "Redmond, WA, USA"},
    # India – All States & Union Territories with major cities
    # Andhra Pradesh
    {"city": "Visakhapatnam", "state": "Andhra Pradesh", "country": "India", "display": "Visakhapatnam, India"},
    {"city": "Vijayawada", "state": "Andhra Pradesh", "country": "India", "display": "Vijayawada, India"},
    {"city": "Guntur", "state": "Andhra Pradesh", "country": "India", "display": "Guntur, India"},
    {"city": "Tirupati", "state": "Andhra Pradesh", "country": "India", "display": "Tirupati, India"},
    {"city": "Rajahmundry", "state": "Andhra Pradesh", "country": "India", "display": "Rajahmundry, India"},
    {"city": "Kakinada", "state": "Andhra Pradesh", "country": "India", "display": "Kakinada, India"},
    {"city": "Nellore", "state": "Andhra Pradesh", "country": "India", "display": "Nellore, India"},
    {"city": "Amaravati", "state": "Andhra Pradesh", "country": "India", "display": "Amaravati, India"},
    # Arunachal Pradesh
    {"city": "Itanagar", "state": "Arunachal Pradesh", "country": "India", "display": "Itanagar, India"},
    # Assam
    {"city": "Guwahati", "state": "Assam", "country": "India", "display": "Guwahati, India"},
    {"city": "Dibrugarh", "state": "Assam", "country": "India", "display": "Dibrugarh, India"},
    {"city": "Silchar", "state": "Assam", "country": "India", "display": "Silchar, India"},
    # Bihar
    {"city": "Patna", "state": "Bihar", "country": "India", "display": "Patna, India"},
    {"city": "Gaya", "state": "Bihar", "country": "India", "display": "Gaya, India"},
    {"city": "Muzaffarpur", "state": "Bihar", "country": "India", "display": "Muzaffarpur, India"},
    {"city": "Bhagalpur", "state": "Bihar", "country": "India", "display": "Bhagalpur, India"},
    # Chhattisgarh
    {"city": "Raipur", "state": "Chhattisgarh", "country": "India", "display": "Raipur, India"},
    {"city": "Bhilai", "state": "Chhattisgarh", "country": "India", "display": "Bhilai, India"},
    {"city": "Bilaspur", "state": "Chhattisgarh", "country": "India", "display": "Bilaspur, India"},
    # Delhi
    {"city": "Delhi NCR", "state": "Delhi", "country": "India", "display": "Delhi NCR, India"},
    {"city": "New Delhi", "state": "Delhi", "country": "India", "display": "New Delhi, India"},
    # Goa
    {"city": "Panaji", "state": "Goa", "country": "India", "display": "Panaji, India"},
    {"city": "Margao", "state": "Goa", "country": "India", "display": "Margao, India"},
    {"city": "Vasco da Gama", "state": "Goa", "country": "India", "display": "Vasco da Gama, India"},
    # Gujarat
    {"city": "Ahmedabad", "state": "Gujarat", "country": "India", "display": "Ahmedabad, India"},
    {"city": "Surat", "state": "Gujarat", "country": "India", "display": "Surat, India"},
    {"city": "Vadodara", "state": "Gujarat", "country": "India", "display": "Vadodara, India"},
    {"city": "Rajkot", "state": "Gujarat", "country": "India", "display": "Rajkot, India"},
    {"city": "Gandhinagar", "state": "Gujarat", "country": "India", "display": "Gandhinagar, India"},
    {"city": "Bhavnagar", "state": "Gujarat", "country": "India", "display": "Bhavnagar, India"},
    # Haryana
    {"city": "Gurugram", "state": "Haryana", "country": "India", "display": "Gurugram, India"},
    {"city": "Faridabad", "state": "Haryana", "country": "India", "display": "Faridabad, India"},
    {"city": "Karnal", "state": "Haryana", "country": "India", "display": "Karnal, India"},
    {"city": "Ambala", "state": "Haryana", "country": "India", "display": "Ambala, India"},
    {"city": "Hisar", "state": "Haryana", "country": "India", "display": "Hisar, India"},
    {"city": "Panipat", "state": "Haryana", "country": "India", "display": "Panipat, India"},
    {"city": "Rohtak", "state": "Haryana", "country": "India", "display": "Rohtak, India"},
    # Himachal Pradesh
    {"city": "Shimla", "state": "Himachal Pradesh", "country": "India", "display": "Shimla, India"},
    {"city": "Dharamshala", "state": "Himachal Pradesh", "country": "India", "display": "Dharamshala, India"},
    {"city": "Manali", "state": "Himachal Pradesh", "country": "India", "display": "Manali, India"},
    # Jharkhand
    {"city": "Ranchi", "state": "Jharkhand", "country": "India", "display": "Ranchi, India"},
    {"city": "Jamshedpur", "state": "Jharkhand", "country": "India", "display": "Jamshedpur, India"},
    {"city": "Dhanbad", "state": "Jharkhand", "country": "India", "display": "Dhanbad, India"},
    {"city": "Bokaro", "state": "Jharkhand", "country": "India", "display": "Bokaro, India"},
    # Karnataka
    {"city": "Bangalore", "state": "Karnataka", "country": "India", "display": "Bangalore, India"},
    {"city": "Mysore", "state": "Karnataka", "country": "India", "display": "Mysore, India"},
    {"city": "Hubli", "state": "Karnataka", "country": "India", "display": "Hubli, India"},
    {"city": "Mangalore", "state": "Karnataka", "country": "India", "display": "Mangalore, India"},
    {"city": "Belgaum", "state": "Karnataka", "country": "India", "display": "Belgaum, India"},
    {"city": "Davangere", "state": "Karnataka", "country": "India", "display": "Davangere, India"},
    # Kerala
    {"city": "Kochi", "state": "Kerala", "country": "India", "display": "Kochi, India"},
    {"city": "Thiruvananthapuram", "state": "Kerala", "country": "India", "display": "Thiruvananthapuram, India"},
    {"city": "Kozhikode", "state": "Kerala", "country": "India", "display": "Kozhikode, India"},
    {"city": "Thrissur", "state": "Kerala", "country": "India", "display": "Thrissur, India"},
    {"city": "Kollam", "state": "Kerala", "country": "India", "display": "Kollam, India"},
    {"city": "Palakkad", "state": "Kerala", "country": "India", "display": "Palakkad, India"},
    {"city": "Kannur", "state": "Kerala", "country": "India", "display": "Kannur, India"},
    # Madhya Pradesh
    {"city": "Indore", "state": "Madhya Pradesh", "country": "India", "display": "Indore, India"},
    {"city": "Bhopal", "state": "Madhya Pradesh", "country": "India", "display": "Bhopal, India"},
    {"city": "Jabalpur", "state": "Madhya Pradesh", "country": "India", "display": "Jabalpur, India"},
    {"city": "Gwalior", "state": "Madhya Pradesh", "country": "India", "display": "Gwalior, India"},
    {"city": "Ujjain", "state": "Madhya Pradesh", "country": "India", "display": "Ujjain, India"},
    # Maharashtra
    {"city": "Mumbai", "state": "Maharashtra", "country": "India", "display": "Mumbai, India"},
    {"city": "Pune", "state": "Maharashtra", "country": "India", "display": "Pune, India"},
    {"city": "Nagpur", "state": "Maharashtra", "country": "India", "display": "Nagpur, India"},
    {"city": "Nashik", "state": "Maharashtra", "country": "India", "display": "Nashik, India"},
    {"city": "Aurangabad", "state": "Maharashtra", "country": "India", "display": "Aurangabad, India"},
    {"city": "Thane", "state": "Maharashtra", "country": "India", "display": "Thane, India"},
    {"city": "Navi Mumbai", "state": "Maharashtra", "country": "India", "display": "Navi Mumbai, India"},
    {"city": "Solapur", "state": "Maharashtra", "country": "India", "display": "Solapur, India"},
    {"city": "Kolhapur", "state": "Maharashtra", "country": "India", "display": "Kolhapur, India"},
    # Manipur
    {"city": "Imphal", "state": "Manipur", "country": "India", "display": "Imphal, India"},
    # Meghalaya
    {"city": "Shillong", "state": "Meghalaya", "country": "India", "display": "Shillong, India"},
    # Mizoram
    {"city": "Aizawl", "state": "Mizoram", "country": "India", "display": "Aizawl, India"},
    # Nagaland
    {"city": "Kohima", "state": "Nagaland", "country": "India", "display": "Kohima, India"},
    {"city": "Dimapur", "state": "Nagaland", "country": "India", "display": "Dimapur, India"},
    # Odisha
    {"city": "Bhubaneswar", "state": "Odisha", "country": "India", "display": "Bhubaneswar, India"},
    {"city": "Cuttack", "state": "Odisha", "country": "India", "display": "Cuttack, India"},
    {"city": "Rourkela", "state": "Odisha", "country": "India", "display": "Rourkela, India"},
    # Punjab
    {"city": "Chandigarh", "state": "Punjab", "country": "India", "display": "Chandigarh, India"},
    {"city": "Ludhiana", "state": "Punjab", "country": "India", "display": "Ludhiana, India"},
    {"city": "Amritsar", "state": "Punjab", "country": "India", "display": "Amritsar, India"},
    {"city": "Jalandhar", "state": "Punjab", "country": "India", "display": "Jalandhar, India"},
    {"city": "Patiala", "state": "Punjab", "country": "India", "display": "Patiala, India"},
    {"city": "Bathinda", "state": "Punjab", "country": "India", "display": "Bathinda, India"},
    {"city": "Mohali", "state": "Punjab", "country": "India", "display": "Mohali, India"},
    # Rajasthan
    {"city": "Jaipur", "state": "Rajasthan", "country": "India", "display": "Jaipur, India"},
    {"city": "Jodhpur", "state": "Rajasthan", "country": "India", "display": "Jodhpur, India"},
    {"city": "Udaipur", "state": "Rajasthan", "country": "India", "display": "Udaipur, India"},
    {"city": "Kota", "state": "Rajasthan", "country": "India", "display": "Kota, India"},
    {"city": "Ajmer", "state": "Rajasthan", "country": "India", "display": "Ajmer, India"},
    {"city": "Bikaner", "state": "Rajasthan", "country": "India", "display": "Bikaner, India"},
    # Sikkim
    {"city": "Gangtok", "state": "Sikkim", "country": "India", "display": "Gangtok, India"},
    # Tamil Nadu
    {"city": "Chennai", "state": "Tamil Nadu", "country": "India", "display": "Chennai, India"},
    {"city": "Coimbatore", "state": "Tamil Nadu", "country": "India", "display": "Coimbatore, India"},
    {"city": "Madurai", "state": "Tamil Nadu", "country": "India", "display": "Madurai, India"},
    {"city": "Tiruchirappalli", "state": "Tamil Nadu", "country": "India", "display": "Tiruchirappalli, India"},
    {"city": "Salem", "state": "Tamil Nadu", "country": "India", "display": "Salem, India"},
    {"city": "Tirunelveli", "state": "Tamil Nadu", "country": "India", "display": "Tirunelveli, India"},
    {"city": "Erode", "state": "Tamil Nadu", "country": "India", "display": "Erode, India"},
    {"city": "Vellore", "state": "Tamil Nadu", "country": "India", "display": "Vellore, India"},
    {"city": "Thoothukudi", "state": "Tamil Nadu", "country": "India", "display": "Thoothukudi, India"},
    {"city": "Dindigul", "state": "Tamil Nadu", "country": "India", "display": "Dindigul, India"},
    {"city": "Thanjavur", "state": "Tamil Nadu", "country": "India", "display": "Thanjavur, India"},
    {"city": "Hosur", "state": "Tamil Nadu", "country": "India", "display": "Hosur, India"},
    {"city": "Nagercoil", "state": "Tamil Nadu", "country": "India", "display": "Nagercoil, India"},
    {"city": "Kanchipuram", "state": "Tamil Nadu", "country": "India", "display": "Kanchipuram, India"},
    {"city": "Kumbakonam", "state": "Tamil Nadu", "country": "India", "display": "Kumbakonam, India"},
    {"city": "Karur", "state": "Tamil Nadu", "country": "India", "display": "Karur, India"},
    {"city": "Tirupur", "state": "Tamil Nadu", "country": "India", "display": "Tirupur, India"},
    {"city": "Sivakasi", "state": "Tamil Nadu", "country": "India", "display": "Sivakasi, India"},
    # Telangana
    {"city": "Hyderabad", "state": "Telangana", "country": "India", "display": "Hyderabad, India"},
    {"city": "Warangal", "state": "Telangana", "country": "India", "display": "Warangal, India"},
    {"city": "Karimnagar", "state": "Telangana", "country": "India", "display": "Karimnagar, India"},
    {"city": "Nizamabad", "state": "Telangana", "country": "India", "display": "Nizamabad, India"},
    # Tripura
    {"city": "Agartala", "state": "Tripura", "country": "India", "display": "Agartala, India"},
    # Uttar Pradesh
    {"city": "Noida", "state": "Uttar Pradesh", "country": "India", "display": "Noida, India"},
    {"city": "Lucknow", "state": "Uttar Pradesh", "country": "India", "display": "Lucknow, India"},
    {"city": "Greater Noida", "state": "Uttar Pradesh", "country": "India", "display": "Greater Noida, India"},
    {"city": "Kanpur", "state": "Uttar Pradesh", "country": "India", "display": "Kanpur, India"},
    {"city": "Agra", "state": "Uttar Pradesh", "country": "India", "display": "Agra, India"},
    {"city": "Varanasi", "state": "Uttar Pradesh", "country": "India", "display": "Varanasi, India"},
    {"city": "Prayagraj", "state": "Uttar Pradesh", "country": "India", "display": "Prayagraj, India"},
    {"city": "Meerut", "state": "Uttar Pradesh", "country": "India", "display": "Meerut, India"},
    {"city": "Ghaziabad", "state": "Uttar Pradesh", "country": "India", "display": "Ghaziabad, India"},
    {"city": "Bareilly", "state": "Uttar Pradesh", "country": "India", "display": "Bareilly, India"},
    # Uttarakhand
    {"city": "Dehradun", "state": "Uttarakhand", "country": "India", "display": "Dehradun, India"},
    {"city": "Haridwar", "state": "Uttarakhand", "country": "India", "display": "Haridwar, India"},
    {"city": "Rishikesh", "state": "Uttarakhand", "country": "India", "display": "Rishikesh, India"},
    # West Bengal
    {"city": "Kolkata", "state": "West Bengal", "country": "India", "display": "Kolkata, India"},
    {"city": "Howrah", "state": "West Bengal", "country": "India", "display": "Howrah, India"},
    {"city": "Durgapur", "state": "West Bengal", "country": "India", "display": "Durgapur, India"},
    {"city": "Siliguri", "state": "West Bengal", "country": "India", "display": "Siliguri, India"},
    {"city": "Asansol", "state": "West Bengal", "country": "India", "display": "Asansol, India"},
    # Union Territories
    {"city": "Pondicherry", "state": "Puducherry", "country": "India", "display": "Pondicherry, India"},
    {"city": "Puducherry", "state": "Puducherry", "country": "India", "display": "Puducherry, India"},
    {"city": "Karaikal", "state": "Puducherry", "country": "India", "display": "Karaikal, India"},
    {"city": "Port Blair", "state": "Andaman & Nicobar", "country": "India", "display": "Port Blair, India"},
    {"city": "Daman", "state": "Dadra & Nagar Haveli and Daman & Diu", "country": "India", "display": "Daman, India"},
    {"city": "Silvassa", "state": "Dadra & Nagar Haveli and Daman & Diu", "country": "India", "display": "Silvassa, India"},
    {"city": "Kavaratti", "state": "Lakshadweep", "country": "India", "display": "Kavaratti, India"},
    {"city": "Srinagar", "state": "Jammu & Kashmir", "country": "India", "display": "Srinagar, India"},
    {"city": "Jammu", "state": "Jammu & Kashmir", "country": "India", "display": "Jammu, India"},
    {"city": "Leh", "state": "Ladakh", "country": "India", "display": "Leh, India"},
    # United Kingdom
    {"city": "London", "state": "England", "country": "United Kingdom", "display": "London, UK"},
    {"city": "Manchester", "state": "England", "country": "United Kingdom", "display": "Manchester, UK"},
    {"city": "Edinburgh", "state": "Scotland", "country": "United Kingdom", "display": "Edinburgh, UK"},
    {"city": "Birmingham", "state": "England", "country": "United Kingdom", "display": "Birmingham, UK"},
    # Europe
    {"city": "Berlin", "state": "", "country": "Germany", "display": "Berlin, Germany"},
    {"city": "Munich", "state": "", "country": "Germany", "display": "Munich, Germany"},
    {"city": "Amsterdam", "state": "", "country": "Netherlands", "display": "Amsterdam, Netherlands"},
    {"city": "Dublin", "state": "", "country": "Ireland", "display": "Dublin, Ireland"},
    {"city": "Paris", "state": "", "country": "France", "display": "Paris, France"},
    {"city": "Stockholm", "state": "", "country": "Sweden", "display": "Stockholm, Sweden"},
    {"city": "Zurich", "state": "", "country": "Switzerland", "display": "Zurich, Switzerland"},
    {"city": "Barcelona", "state": "", "country": "Spain", "display": "Barcelona, Spain"},
    # Asia Pacific
    {"city": "Singapore", "state": "", "country": "Singapore", "display": "Singapore"},
    {"city": "Tokyo", "state": "", "country": "Japan", "display": "Tokyo, Japan"},
    {"city": "Sydney", "state": "NSW", "country": "Australia", "display": "Sydney, Australia"},
    {"city": "Melbourne", "state": "VIC", "country": "Australia", "display": "Melbourne, Australia"},
    {"city": "Seoul", "state": "", "country": "South Korea", "display": "Seoul, South Korea"},
    # Canada
    {"city": "Toronto", "state": "ON", "country": "Canada", "display": "Toronto, Canada"},
    {"city": "Vancouver", "state": "BC", "country": "Canada", "display": "Vancouver, Canada"},
    {"city": "Montreal", "state": "QC", "country": "Canada", "display": "Montreal, Canada"},
    # Middle East
    {"city": "Dubai", "state": "", "country": "UAE", "display": "Dubai, UAE"},
    {"city": "Abu Dhabi", "state": "", "country": "UAE", "display": "Abu Dhabi, UAE"},
    # Remote
    {"city": "Remote", "state": "", "country": "Worldwide", "display": "Remote"},
    {"city": "Remote", "state": "", "country": "United States", "display": "Remote (US)"},
    {"city": "Remote", "state": "", "country": "Europe", "display": "Remote (Europe)"},
    {"city": "Remote", "state": "", "country": "India", "display": "Remote (India)"},
]

JOB_TYPES = ["Full-time", "Part-time", "Remote", "Hybrid", "Contract", "Internship", "Fresher"]
EXPERIENCE_LEVELS = ["Entry Level", "Junior", "Mid Level", "Senior", "Lead", "Principal"]

SALARY_RANGES_USD = {
    "Entry Level": ("$45,000", "$70,000"),
    "Junior":      ("$60,000", "$90,000"),
    "Mid Level":   ("$90,000", "$130,000"),
    "Senior":      ("$130,000", "$180,000"),
    "Lead":        ("$160,000", "$220,000"),
    "Principal":   ("$200,000", "$280,000"),
}
SALARY_RANGES_INR = {
    "Entry Level": ("₹3,50,000", "₹7,00,000"),
    "Junior":      ("₹6,00,000", "₹12,00,000"),
    "Mid Level":   ("₹12,00,000", "₹24,00,000"),
    "Senior":      ("₹24,00,000", "₹40,00,000"),
    "Lead":        ("₹35,00,000", "₹55,00,000"),
    "Principal":   ("₹50,00,000", "₹80,00,000"),
}
SALARY_RANGES_GBP = {
    "Entry Level": ("£25,000", "£38,000"),
    "Junior":      ("£35,000", "£50,000"),
    "Mid Level":   ("£50,000", "£75,000"),
    "Senior":      ("£75,000", "£105,000"),
    "Lead":        ("£95,000", "£130,000"),
    "Principal":   ("£120,000", "£160,000"),
}
SALARY_RANGES_EUR = {
    "Entry Level": ("€30,000", "€45,000"),
    "Junior":      ("€40,000", "€60,000"),
    "Mid Level":   ("€60,000", "€90,000"),
    "Senior":      ("€85,000", "€125,000"),
    "Lead":        ("€110,000", "€155,000"),
    "Principal":   ("€140,000", "€195,000"),
}

# Map countries to salary tables
COUNTRY_SALARY_MAP = {
    "United States": SALARY_RANGES_USD,
    "India":         SALARY_RANGES_INR,
    "United Kingdom": SALARY_RANGES_GBP,
    "Germany":       SALARY_RANGES_EUR,
    "France":        SALARY_RANGES_EUR,
    "Netherlands":   SALARY_RANGES_EUR,
    "Ireland":       SALARY_RANGES_EUR,
    "Sweden":        SALARY_RANGES_EUR,
    "Switzerland":   SALARY_RANGES_EUR,
    "Spain":         SALARY_RANGES_EUR,
}


# ═══════════════════════════════════════════════════════════════════════
# LOCATION NORMALISER
# ═══════════════════════════════════════════════════════════════════════

def normalise_location(raw: str) -> dict:
    """Parse a raw location string into {city, state, country, display}."""
    if not raw or raw.strip().lower() in ("", "anywhere", "global", "worldwide"):
        return {"city": "Remote", "state": "", "country": "Worldwide", "display": "Remote"}

    raw_lower = raw.lower().strip()
    if raw_lower in ("remote", "remote - worldwide"):
        return {"city": "Remote", "state": "", "country": "Worldwide", "display": "Remote"}

    # Try matching against our known locations
    for loc in LOCATIONS:
        if loc["city"].lower() in raw_lower or loc["display"].lower() in raw_lower:
            return loc.copy()

    # Country-level matching
    country_hints = {
        "india": "India", "usa": "United States", "us": "United States",
        "united states": "United States", "uk": "United Kingdom",
        "united kingdom": "United Kingdom", "germany": "Germany",
        "canada": "Canada", "australia": "Australia", "france": "France",
        "singapore": "Singapore", "japan": "Japan", "uae": "UAE",
        "netherlands": "Netherlands", "ireland": "Ireland", "sweden": "Sweden",
    }
    detected_country = "Other"
    for hint, country in country_hints.items():
        if hint in raw_lower:
            detected_country = country
            break

    return {"city": raw.strip(), "state": "", "country": detected_country, "display": raw.strip()}


def _dedup_key(job: dict) -> str:
    """Create a deterministic key for deduplication."""
    raw = f"{job.get('title','')}-{job.get('company','')}-{job.get('location','')}".lower()
    return hashlib.md5(raw.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════
# SCRAPER CLASS
# ═══════════════════════════════════════════════════════════════════════

class JobScraper:
    """
    Production multi-source job scraper.
    Pulls from 16 real public sources in parallel, deduplicates,
    normalises locations, and supplements with curated data.

    Sources:
    ── Global / Remote ─────────────────────────────────────────
    1. Remotive          (Remote jobs API)
    2. Arbeitnow         (EU & global jobs API)
    3. RemoteOK          (Remote jobs API)
    4. Jobicy            (Remote jobs API)
    5. The Muse          (US companies API)
    6. FindWork          (Dev jobs API)
    7. LinkedIn          (Public search scraper)
    8. Indeed            (RSS feed)
    ── Indian Portals ──────────────────────────────────────────
    9. Naukri.com        (India #1 job portal)
    10. Foundit          (Monster India)
    11. Shine.com        (HT Media)
    12. Freshersworld    (Fresher/entry-level)
    13. TimesJobs        (Times Group)
    14. Internshala      (Internships & fresher jobs)
    ── Remote-Focused ──────────────────────────────────────────
    15. We Work Remotely (Remote jobs RSS)
    16. FlexJobs         (Flexible & remote)
    ── Aggregators ─────────────────────────────────────────────
    17. Himalayas         (104K+ jobs, public JSON API)
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json",
        })
        self.seen_keys = set()   # dedup tracker

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    def scrape_all(self) -> list[dict]:
        """
        Run all scrapers in parallel, merge, dedup, normalise, assign IDs.
        Returns list[dict] ready for JSON serialisation.
        """
        scrapers = [
            # ── Global / Remote APIs ──────────────────────────────────
            ("Remotive",            self._scrape_remotive),
            ("Arbeitnow",           self._scrape_arbeitnow),
            ("RemoteOK",            self._scrape_remoteok),
            ("Jobicy",              self._scrape_jobicy),
            ("The Muse",            self._scrape_themuse),
            ("FindWork",            self._scrape_findwork),
            ("LinkedIn RSS",        self._scrape_linkedin_rss),
            ("Indeed RSS",          self._scrape_indeed_rss),
            # ── Indian Job Portals ────────────────────────────────────
            ("Naukri.com",          self._scrape_naukri),
            ("Foundit",             self._scrape_foundit),
            ("Shine.com",           self._scrape_shine),
            ("Freshersworld",       self._scrape_freshersworld),
            ("TimesJobs",           self._scrape_timesjobs),
            ("Internshala",         self._scrape_internshala),
            # ── Remote Job Sites ──────────────────────────────────────
            ("We Work Remotely",    self._scrape_weworkremotely),
            ("FlexJobs",            self._scrape_flexjobs),
            # ── Aggregators ───────────────────────────────────────────
            ("Himalayas",           self._scrape_himalayas),
        ]

        all_jobs = []

        # Run all scrapers in parallel (max 10 threads)
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(fn): name for name, fn in scrapers}
            for future in as_completed(futures):
                src = futures[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                    logger.info(f"✅ {src}: {len(jobs)} jobs")
                except Exception as e:
                    logger.warning(f"⚠️  {src} failed: {e}")

        logger.info(f"📥 Total scraped from APIs: {len(all_jobs)}")

        # Supplement with generated data if total < 200
        shortfall = max(0, 200 - len(all_jobs))
        if shortfall > 0:
            generated = self._generate_realistic_jobs(shortfall)
            all_jobs.extend(generated)
            logger.info(f"🏭 Generated {len(generated)} supplemental jobs")

        # Dedup
        unique = []
        for job in all_jobs:
            key = _dedup_key(job)
            if key not in self.seen_keys:
                self.seen_keys.add(key)
                unique.append(job)
        logger.info(f"🧹 After dedup: {len(unique)} unique jobs")

        # Normalise locations & assign IDs
        for i, job in enumerate(unique):
            job["id"] = i + 1
            loc = normalise_location(job.get("location", ""))
            job["location"]         = loc["display"]
            job["location_city"]    = loc["city"]
            job["location_state"]   = loc["state"]
            job["location_country"] = loc["country"]

        # ── AI Processing Pipeline ────────────────────────────────────
        try:
            from scraper.ai_processor import AIJobProcessor
            ai = AIJobProcessor()
            unique = ai.process_jobs(unique)
            logger.info("🤖 AI processing complete")
        except Exception as e:
            logger.warning(f"⚠️  AI processing skipped: {e}")

        # ── Company Enrichment ────────────────────────────────────────
        try:
            from scraper.company_scraper import CompanyScraper
            company_scraper = CompanyScraper()
            unique = company_scraper.enrich_jobs_with_company_data(unique)
            logger.info("🏢 Company enrichment complete")
        except Exception as e:
            logger.warning(f"⚠️  Company enrichment skipped: {e}")

        return unique

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 1: Remotive (remote jobs, free, no key)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_remotive(self) -> list[dict]:
        """https://remotive.com/api/remote-jobs"""
        categories = [
            "software-dev", "data", "design", "product",
            "customer-support", "marketing", "devops",
            "human-resources", "finance-legal", "qa",
        ]
        jobs = []
        for cat in categories:
            try:
                url = f"https://remotive.com/api/remote-jobs?category={cat}&limit=30"
                resp = self.session.get(url, timeout=12)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for item in data.get("jobs", []):
                    tags = item.get("tags", []) or []
                    jobs.append(self._make_job(
                        title=item.get("title", ""),
                        company=item.get("company_name", ""),
                        logo=item.get("company_logo", ""),
                        location=item.get("candidate_required_location", "Remote") or "Remote",
                        job_type="Remote",
                        category=self._map_category(item.get("category", "")),
                        description=self._clean_html(item.get("description", "")),
                        skills=tags[:6],
                        apply_url=item.get("url", "#"),
                        posted=item.get("publication_date", "")[:10],
                        salary=item.get("salary", ""),
                        source="Remotive",
                    ))
                time.sleep(0.3)
            except Exception as e:
                logger.debug(f"Remotive category {cat}: {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 2: Arbeitnow (EU + global, free, no key)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_arbeitnow(self) -> list[dict]:
        """https://www.arbeitnow.com/api/job-board-api"""
        jobs = []
        for page in range(1, 4):
            try:
                url = f"https://www.arbeitnow.com/api/job-board-api?page={page}"
                resp = self.session.get(url, timeout=12)
                if resp.status_code != 200:
                    break
                data = resp.json()
                for item in data.get("data", []):
                    tags = item.get("tags", []) or []
                    remote = item.get("remote", False)
                    jobs.append(self._make_job(
                        title=item.get("title", ""),
                        company=item.get("company_name", ""),
                        logo=item.get("company_logo", ""),
                        location=item.get("location", "Remote") if not remote else "Remote",
                        job_type="Remote" if remote else "Full-time",
                        category=self._map_category(", ".join(tags)),
                        description=self._clean_html(item.get("description", "")),
                        skills=tags[:6],
                        apply_url=item.get("url", "#"),
                        posted=item.get("created_at", "")[:10] if item.get("created_at") else "",
                        salary="",
                        source="Arbeitnow",
                    ))
                time.sleep(0.3)
            except Exception as e:
                logger.debug(f"Arbeitnow page {page}: {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 3: RemoteOK (remote tech, free, no key)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_remoteok(self) -> list[dict]:
        """https://remoteok.com/api"""
        resp = self.session.get("https://remoteok.com/api", timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs = []
        for item in data:
            if not isinstance(item, dict) or "slug" not in item:
                continue
            tags = item.get("tags", []) or []
            salary_min = item.get("salary_min", "")
            salary_max = item.get("salary_max", "")
            sal_str = ""
            if salary_min and salary_max:
                sal_str = f"${int(salary_min):,} – ${int(salary_max):,}"
            elif salary_min:
                sal_str = f"${int(salary_min):,}+"
            jobs.append(self._make_job(
                title=item.get("position", ""),
                company=item.get("company", ""),
                logo=item.get("company_logo", ""),
                location=item.get("location", "Remote") or "Remote",
                job_type="Remote",
                category=self._map_category(", ".join(tags)),
                description=self._clean_html(item.get("description", "")),
                skills=tags[:6],
                apply_url=item.get("url", f"https://remoteok.com/remote-jobs/{item.get('slug', '')}"),
                posted=item.get("date", "")[:10],
                salary=sal_str,
                source="RemoteOK",
            ))
        return jobs[:50]

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 4: Jobicy (remote jobs, free, no key)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_jobicy(self) -> list[dict]:
        """https://jobicy.com/api/v2/remote-jobs"""
        jobs = []
        for page_count in ["50"]:
            try:
                url = f"https://jobicy.com/api/v2/remote-jobs?count={page_count}"
                resp = self.session.get(url, timeout=12)
                if resp.status_code != 200:
                    break
                data = resp.json()
                for item in data.get("jobs", []):
                    jobs.append(self._make_job(
                        title=item.get("jobTitle", ""),
                        company=item.get("companyName", ""),
                        logo=item.get("companyLogo", ""),
                        location=item.get("jobGeo", "Remote") or "Remote",
                        job_type="Remote",
                        category=self._map_category(item.get("jobIndustry", [""]) if isinstance(item.get("jobIndustry"), list) else str(item.get("jobIndustry", ""))),
                        description=self._clean_html(item.get("jobDescription", "")),
                        skills=self._extract_skills_from_text(item.get("jobDescription", "")),
                        apply_url=item.get("url", "#"),
                        posted=item.get("pubDate", "")[:10],
                        salary=item.get("annualSalaryMin", ""),
                        source="Jobicy",
                    ))
            except Exception as e:
                logger.debug(f"Jobicy: {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 5: The Muse (US companies, free, no key)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_themuse(self) -> list[dict]:
        """https://www.themuse.com/api/public/jobs"""
        jobs = []
        for page in range(0, 3):
            try:
                url = f"https://www.themuse.com/api/public/jobs?page={page}&descending=true"
                resp = self.session.get(url, timeout=12)
                if resp.status_code != 200:
                    break
                data = resp.json()
                for item in data.get("results", []):
                    company_obj = item.get("company", {}) or {}
                    locs = item.get("locations", [])
                    loc_str = locs[0].get("name", "Remote") if locs else "Remote"
                    cats = item.get("categories", [])
                    cat_str = cats[0].get("name", "Other") if cats else "Other"
                    levels = item.get("levels", [])
                    level_str = levels[0].get("name", "Mid Level") if levels else "Mid Level"
                    jobs.append(self._make_job(
                        title=item.get("name", ""),
                        company=company_obj.get("name", ""),
                        logo="",
                        location=loc_str,
                        job_type="Full-time",
                        category=self._map_category(cat_str),
                        description=self._clean_html(item.get("contents", "")),
                        skills=self._extract_skills_from_text(item.get("contents", "")),
                        apply_url=item.get("refs", {}).get("landing_page", "#"),
                        posted=item.get("publication_date", "")[:10],
                        salary="",
                        source="The Muse",
                        experience=self._map_experience(level_str),
                    ))
                time.sleep(0.3)
            except Exception as e:
                logger.debug(f"The Muse page {page}: {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 6: FindWork (dev jobs, free, no key)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_findwork(self) -> list[dict]:
        """https://findwork.dev/api/jobs/"""
        url = "https://findwork.dev/api/jobs/?order_by=-date_posted"
        resp = self.session.get(url, timeout=15, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs = []
        for item in data.get("results", [])[:30]:
            kw = item.get("keywords", []) or []
            jobs.append(self._make_job(
                title=item.get("role", ""),
                company=item.get("company_name", ""),
                logo=item.get("logo", ""),
                location=item.get("location", "Remote") or "Remote",
                job_type="Remote" if item.get("remote") else "Full-time",
                category="Technology",
                description=(item.get("text", "") or "")[:600],
                skills=kw[:6],
                apply_url=item.get("url", "#"),
                posted=(item.get("date_posted", "") or "")[:10],
                salary="",
                source="FindWork",
            ))
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 7: LinkedIn RSS (via Google News proxy)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_linkedin_rss(self) -> list[dict]:
        """
        Pull LinkedIn job listings via their public RSS feed.
        LinkedIn provides RSS feeds for job searches.
        """
        jobs = []
        search_terms = [
            "software+engineer", "data+scientist", "product+manager",
            "devops+engineer", "frontend+developer", "machine+learning",
        ]
        for term in search_terms:
            try:
                # LinkedIn public job RSS feed
                url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={term}&start=0"
                resp = self.session.get(url, timeout=12, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                })
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="base-card") or soup.find_all("li")
                for card in cards[:10]:
                    title_el = card.find("h3", class_="base-search-card__title") or card.find("h3")
                    company_el = card.find("h4", class_="base-search-card__subtitle") or card.find("h4")
                    location_el = card.find("span", class_="job-search-card__location") or card.find("span")
                    link_el = card.find("a", class_="base-card__full-link") or card.find("a")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = location_el.get_text(strip=True) if location_el else "Remote"
                    url_link = link_el.get("href", "#") if link_el else "#"

                    if not title:
                        continue

                    jobs.append(self._make_job(
                        title=title,
                        company=company,
                        logo=f"https://logo.clearbit.com/{company.lower().replace(' ', '').replace(',', '')}.com" if company else "",
                        location=location,
                        job_type="Full-time",
                        category=self._map_category(term.replace("+", " ")),
                        description=f"{title} role at {company}. Found on LinkedIn.",
                        skills=self._extract_skills_from_text(f"{title} {term}"),
                        apply_url=url_link,
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary="",
                        source="LinkedIn",
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"LinkedIn RSS ({term}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 8: Indeed RSS
    # ──────────────────────────────────────────────────────────────────

    def _scrape_indeed_rss(self) -> list[dict]:
        """
        Pull Indeed job listings via their public RSS feed.
        """
        jobs = []
        queries = [
            ("software+developer",  ""),
            ("data+analyst",        ""),
            ("python+developer",    ""),
            ("react+developer",     ""),
            ("devops",              ""),
            ("product+manager",     ""),
        ]
        for query, location in queries:
            try:
                url = f"https://www.indeed.com/rss?q={query}&l={location}&sort=date&limit=25"
                resp = self.session.get(url, timeout=12, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                })
                if resp.status_code != 200:
                    continue
                soup = BeautifulSoup(resp.text, "xml")
                items = soup.find_all("item")
                for item in items[:15]:
                    title = item.find("title").get_text(strip=True) if item.find("title") else ""
                    link = item.find("link").get_text(strip=True) if item.find("link") else "#"
                    pub_date = item.find("pubDate").get_text(strip=True) if item.find("pubDate") else ""
                    source_el = item.find("source")
                    company = source_el.get_text(strip=True) if source_el else ""
                    # Parse location from title or georss
                    geo = item.find("georss:point")
                    loc_str = "United States"

                    if not title:
                        continue

                    # Try to parse date
                    posted = datetime.now().strftime("%Y-%m-%d")
                    if pub_date:
                        try:
                            from email.utils import parsedate_to_datetime
                            posted = parsedate_to_datetime(pub_date).strftime("%Y-%m-%d")
                        except Exception:
                            pass

                    jobs.append(self._make_job(
                        title=title,
                        company=company,
                        logo=f"https://logo.clearbit.com/{company.lower().replace(' ', '').replace(',', '')}.com" if company else "",
                        location=loc_str,
                        job_type="Full-time",
                        category=self._map_category(query.replace("+", " ")),
                        description=f"{title} at {company}. Found on Indeed.",
                        skills=self._extract_skills_from_text(f"{title} {query}"),
                        apply_url=link,
                        posted=posted,
                        salary="",
                        source="Indeed",
                    ))
                time.sleep(0.4)
            except Exception as e:
                logger.debug(f"Indeed RSS ({query}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 9: Naukri.com (India's largest job portal)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_naukri(self) -> list[dict]:
        """
        Scrape Naukri.com public search listings for Indian tech jobs.
        Note: Naukri uses heavy JS rendering + reCAPTCHA.
        Uses their guest search page which occasionally serves SSR content.
        """
        jobs = []
        search_terms = [
            "software-developer", "data-scientist", "python-developer",
            "java-developer", "react-developer", "devops-engineer",
            "machine-learning", "full-stack-developer", "product-manager",
            "cloud-engineer", "frontend-developer", "backend-developer",
        ]
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.naukri.com/",
            "Cache-Control": "no-cache",
        }
        for term in search_terms:
            try:
                url = f"https://www.naukri.com/{term}-jobs"
                resp = self.session.get(url, timeout=15, headers=headers)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # Try multiple selectors — Naukri changes DOM frequently
                cards = (
                    soup.find_all("article", class_="jobTuple") or
                    soup.find_all("div", class_="srp-jobtuple-wrapper") or
                    soup.find_all("div", class_="cust-job-tuple") or
                    soup.find_all("div", attrs={"data-job-id": True}) or
                    soup.find_all("div", class_="jobTupleHeader")
                )

                # Also try to extract from embedded JSON-LD
                scripts = soup.find_all("script", type="application/ld+json")
                for script in scripts:
                    try:
                        import json as _json
                        ld_data = _json.loads(script.string or "")
                        if isinstance(ld_data, dict) and ld_data.get("@type") == "JobPosting":
                            ld_data = [ld_data]
                        if isinstance(ld_data, list):
                            for item in ld_data:
                                if item.get("@type") != "JobPosting":
                                    continue
                                org = item.get("hiringOrganization", {}) or {}
                                loc = item.get("jobLocation", {})
                                if isinstance(loc, list):
                                    loc = loc[0] if loc else {}
                                addr = loc.get("address", {}) if isinstance(loc, dict) else {}
                                if isinstance(addr, list):
                                    addr = addr[0] if addr else {}
                                city = addr.get("addressLocality", "India") if isinstance(addr, dict) else "India"

                                sal = item.get("baseSalary", {}) or {}
                                sal_val = sal.get("value", {}) or {}
                                sal_str = ""
                                if isinstance(sal_val, dict):
                                    mn = sal_val.get("minValue", "")
                                    mx = sal_val.get("maxValue", "")
                                    cur = sal.get("currency", "INR")
                                    if mn and mx:
                                        sal_str = f"{cur} {mn} - {mx}"

                                jobs.append(self._make_job(
                                    title=item.get("title", ""),
                                    company=org.get("name", ""),
                                    logo=org.get("logo", ""),
                                    location=city,
                                    job_type=item.get("employmentType", "Full-time"),
                                    category=self._map_category(term.replace("-", " ")),
                                    description=self._clean_html(item.get("description", "")),
                                    skills=self._extract_skills_from_text(item.get("description", "")),
                                    apply_url=item.get("url", "#"),
                                    posted=(item.get("datePosted", "") or "")[:10],
                                    salary=sal_str,
                                    source="Naukri.com",
                                ))
                    except Exception:
                        pass

                for card in cards[:8]:
                    title_el = (
                        card.find("a", class_="title") or
                        card.find("a", class_="jobTitle") or
                        card.find("a", attrs={"class": lambda c: c and "title" in str(c).lower()})
                    )
                    company_el = (
                        card.find("a", class_="subTitle") or
                        card.find("a", class_="comp-name") or
                        card.find("span", class_="comp-name")
                    )
                    loc_el = (
                        card.find("li", class_="location") or
                        card.find("span", class_="loc") or
                        card.find("span", class_="locWdth") or
                        card.find("span", attrs={"class": lambda c: c and "loc" in str(c).lower()})
                    )
                    exp_el = card.find("li", class_="experience") or card.find("span", class_="expwdth")
                    sal_el = card.find("li", class_="salary") or card.find("span", class_="sal")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else "India"
                    experience = exp_el.get_text(strip=True) if exp_el else ""
                    salary = sal_el.get_text(strip=True) if sal_el else ""
                    link = title_el.get("href", "#") if title_el else "#"

                    if not title or not company:
                        continue

                    if "," in location:
                        location = location.split(",")[0].strip()

                    jobs.append(self._make_job(
                        title=title,
                        company=company,
                        logo=f"https://logo.clearbit.com/{company.lower().replace(' ', '').replace(',', '')}.com",
                        location=location if location else "India",
                        job_type="Full-time",
                        category=self._map_category(term.replace("-", " ")),
                        description=f"{title} at {company}. {experience} experience required. Found on Naukri.com",
                        skills=self._extract_skills_from_text(f"{title} {term.replace('-', ' ')}"),
                        apply_url=link if link.startswith("http") else f"https://www.naukri.com{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary=salary,
                        source="Naukri.com",
                        experience=self._map_experience(experience),
                    ))
                time.sleep(0.6)
            except Exception as e:
                logger.debug(f"Naukri ({term}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 10: Foundit / Monster India
    # ──────────────────────────────────────────────────────────────────

    def _scrape_foundit(self) -> list[dict]:
        """Scrape Foundit.in (formerly Monster India) job listings."""
        jobs = []
        search_terms = [
            "software-developer", "data-analyst", "python",
            "java", "react", "devops", "machine-learning",
            "product-manager", "frontend", "backend",
        ]
        for term in search_terms:
            try:
                url = f"https://www.foundit.in/srp/results?searchId=&query={term.replace('-', '+')}&locations=India"
                resp = self.session.get(url, timeout=15, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-IN,en;q=0.9",
                    "Referer": "https://www.foundit.in/",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="card-apply-content") or \
                        soup.find_all("div", class_="srpResultCardHeader") or \
                        soup.find_all("div", attrs={"class": lambda c: c and "jobCard" in str(c)})

                for card in cards[:8]:
                    title_el = card.find("a", class_="card-title") or card.find("a", attrs={"class": lambda c: c and "title" in str(c).lower()})
                    company_el = card.find("span", class_="card-company") or card.find("a", class_="comp-name")
                    loc_el = card.find("span", class_="card-location") or card.find("span", attrs={"class": lambda c: c and "loc" in str(c).lower()})
                    exp_el = card.find("span", class_="card-experience")
                    sal_el = card.find("span", class_="card-salary")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else "India"
                    experience = exp_el.get_text(strip=True) if exp_el else ""
                    salary = sal_el.get_text(strip=True) if sal_el else ""
                    link = title_el.get("href", "#") if title_el else "#"

                    if not title:
                        continue

                    jobs.append(self._make_job(
                        title=title,
                        company=company or "Confidential",
                        logo=f"https://logo.clearbit.com/{company.lower().replace(' ', '').replace(',', '')}.com" if company else "",
                        location=location,
                        job_type="Full-time",
                        category=self._map_category(term.replace("-", " ")),
                        description=f"{title} at {company}. {experience}. Found on Foundit.in",
                        skills=self._extract_skills_from_text(f"{title} {term.replace('-', ' ')}"),
                        apply_url=link if link.startswith("http") else f"https://www.foundit.in{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary=salary,
                        source="Foundit",
                        experience=self._map_experience(experience),
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Foundit ({term}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 11: Shine.com (HT Media job portal)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_shine(self) -> list[dict]:
        """Scrape Shine.com for Indian job listings."""
        jobs = []
        search_terms = [
            "python-developer", "java-developer", "react-developer",
            "data-scientist", "devops-engineer", "product-manager",
            "machine-learning-engineer", "cloud-engineer", "frontend-developer",
        ]
        for term in search_terms:
            try:
                url = f"https://www.shine.com/job-search/{term}-jobs"
                resp = self.session.get(url, timeout=15, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-IN,en;q=0.9",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="result_content") or \
                        soup.find_all("div", class_="jobCard") or \
                        soup.find_all("div", attrs={"id": lambda i: i and "job_" in str(i)})

                for card in cards[:8]:
                    title_el = card.find("a", class_="job_title_anchor") or card.find("a", attrs={"class": lambda c: c and "title" in str(c).lower()})
                    company_el = card.find("span", class_="comp_name") or card.find("a", class_="companyName")
                    loc_el = card.find("span", class_="loc") or card.find("span", attrs={"class": lambda c: c and "loc" in str(c).lower()})
                    exp_el = card.find("span", class_="exp")
                    sal_el = card.find("span", class_="salary")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else "India"
                    experience = exp_el.get_text(strip=True) if exp_el else ""
                    salary = sal_el.get_text(strip=True) if sal_el else ""
                    link = title_el.get("href", "#") if title_el else "#"

                    if not title:
                        continue

                    jobs.append(self._make_job(
                        title=title,
                        company=company or "Confidential",
                        logo=f"https://logo.clearbit.com/{company.lower().replace(' ', '').replace(',', '')}.com" if company else "",
                        location=location,
                        job_type="Full-time",
                        category=self._map_category(term.replace("-", " ")),
                        description=f"{title} at {company}. {experience}. Found on Shine.com",
                        skills=self._extract_skills_from_text(f"{title} {term.replace('-', ' ')}"),
                        apply_url=link if link.startswith("http") else f"https://www.shine.com{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary=salary,
                        source="Shine.com",
                        experience=self._map_experience(experience),
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Shine ({term}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 12: Freshersworld (entry-level / fresher jobs India)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_freshersworld(self) -> list[dict]:
        """Scrape Freshersworld.com for fresher and entry-level Indian jobs."""
        jobs = []
        categories = [
            "it-software", "data-science", "python", "java",
            "web-development", "cloud-computing", "machine-learning",
            "devops", "cyber-security", "testing",
        ]
        for cat in categories:
            try:
                url = f"https://www.freshersworld.com/jobs/category/{cat}"
                resp = self.session.get(url, timeout=15, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-IN,en;q=0.9",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="job-container") or \
                        soup.find_all("div", class_="latest_jobs_in") or \
                        soup.find_all("div", class_="job-details") or \
                        soup.find_all("span", class_="wrap-header") or \
                        soup.find_all("div", attrs={"class": lambda c: c and "job" in str(c).lower() and "card" in str(c).lower()})

                for card in cards[:8]:
                    title_el = card.find("a") or card.find("span", class_="job-title")
                    company_el = card.find("h3", class_="company-name") or card.find("span", class_="company-name") or card.find("span", class_="comp_name")
                    loc_el = card.find("span", class_="job-location") or card.find("span", attrs={"class": lambda c: c and "loc" in str(c).lower()})
                    qual_el = card.find("span", class_="qualification")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else "India"
                    link = title_el.get("href", "#") if title_el and title_el.name == "a" else "#"

                    if not title or len(title) < 5:
                        continue

                    jobs.append(self._make_job(
                        title=title,
                        company=company or "Multiple Companies",
                        logo=f"https://logo.clearbit.com/{company.lower().replace(' ', '').replace(',', '')}.com" if company else "",
                        location=location or "India",
                        job_type="Full-time",
                        category=self._map_category(cat.replace("-", " ")),
                        description=f"{title} for freshers at {company}. Found on Freshersworld.com",
                        skills=self._extract_skills_from_text(f"{title} {cat.replace('-', ' ')}"),
                        apply_url=link if link.startswith("http") else f"https://www.freshersworld.com{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary="",
                        source="Freshersworld",
                        experience="Entry Level",
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Freshersworld ({cat}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 13: TimesJobs (Times Group job portal)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_timesjobs(self) -> list[dict]:
        """Scrape TimesJobs.com for Indian job listings."""
        jobs = []
        search_terms = [
            "python", "java", "react", "data+scientist",
            "devops", "machine+learning", "cloud+engineer",
            "full+stack", "product+manager", "software+engineer",
        ]
        for term in search_terms:
            try:
                url = f"https://www.timesjobs.com/candidate/job-search.html?searchType=personal498&from=submit&searchTextSrc=&searchTextText=&txtKeywords={term}&txtLocation="
                resp = self.session.get(url, timeout=15, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-IN,en;q=0.9",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("li", class_="clearfix job-bx") or \
                        soup.find_all("div", class_="job-bx-title") or \
                        soup.find_all("div", class_="clearfix job-bx")

                for card in cards[:8]:
                    title_el = card.find("h2") or card.find("a", class_="title")
                    if title_el and title_el.find("a"):
                        title_link = title_el.find("a")
                        title = title_link.get_text(strip=True)
                        link = title_link.get("href", "#")
                    else:
                        title = title_el.get_text(strip=True) if title_el else ""
                        link = "#"

                    company_el = card.find("h3", class_="joblist-comp-name") or card.find("h3")
                    loc_el = card.find("span", class_="loc") or card.find("ul", class_="top-jd-dtl")
                    exp_el = card.find("li") if card.find("ul", class_="top-jd-dtl") else None

                    company = company_el.get_text(strip=True) if company_el else ""
                    location = ""
                    if loc_el:
                        location = loc_el.get_text(strip=True)
                    # Extract from detail list
                    detail_list = card.find("ul", class_="top-jd-dtl")
                    if detail_list:
                        detail_items = detail_list.find_all("li")
                        for di in detail_items:
                            icon = di.find("i")
                            text = di.get_text(strip=True)
                            if icon and "location" in str(icon.get("class", [])):
                                location = text
                            elif not location and any(city in text for city in ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune"]):
                                location = text

                    experience = ""
                    if detail_list:
                        first_li = detail_list.find("li")
                        if first_li:
                            experience = first_li.get_text(strip=True)

                    if not title or len(title) < 3:
                        continue

                    jobs.append(self._make_job(
                        title=title,
                        company=company or "Confidential",
                        logo=f"https://logo.clearbit.com/{company.lower().replace(' ', '').replace(',', '')}.com" if company else "",
                        location=location or "India",
                        job_type="Full-time",
                        category=self._map_category(term.replace("+", " ")),
                        description=f"{title} at {company}. Found on TimesJobs.com",
                        skills=self._extract_skills_from_text(f"{title} {term.replace('+', ' ')}"),
                        apply_url=link if link.startswith("http") else f"https://www.timesjobs.com{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary="",
                        source="TimesJobs",
                        experience=self._map_experience(experience),
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"TimesJobs ({term}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 14: Internshala (internships & fresher jobs)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_internshala(self) -> list[dict]:
        """Scrape Internshala for internships and fresher jobs in India."""
        jobs = []
        categories = [
            ("internships/computer-science-internship", "Internship"),
            ("internships/web-development-internship", "Internship"),
            ("internships/python-django-internship", "Internship"),
            ("internships/data-science-internship", "Internship"),
            ("internships/machine-learning-internship", "Internship"),
            ("internships/graphic-design-internship", "Internship"),
            ("internships/digital-marketing-internship", "Internship"),
            ("fresher-jobs/computer-science-jobs", "Full-time"),
            ("fresher-jobs/web-development-jobs", "Full-time"),
            ("fresher-jobs/data-science-jobs", "Full-time"),
        ]
        for path, default_type in categories:
            try:
                url = f"https://internshala.com/{path}"
                resp = self.session.get(url, timeout=15, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-IN,en;q=0.9",
                    "X-Requested-With": "XMLHttpRequest",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="individual_internship") or \
                        soup.find_all("div", class_="internship_meta") or \
                        soup.find_all("div", attrs={"class": lambda c: c and "internship" in str(c).lower()}) or \
                        soup.find_all("div", attrs={"class": lambda c: c and "job_" in str(c).lower()})

                for card in cards[:6]:
                    # Title
                    title_el = card.find("a", class_="view_detail_button") or \
                               card.find("h3", class_="heading_4_5") or \
                               card.find("a", class_="job-title-href") or \
                               card.find("h3")
                    company_el = card.find("p", class_="company_name") or \
                                 card.find("a", class_="link_display_like_text") or \
                                 card.find("h4")
                    loc_el = card.find("a", class_="location_link") or \
                             card.find("p", class_="location") or \
                             card.find("span", class_="location")
                    stipend_el = card.find("span", class_="stipend") or \
                                 card.find("span", class_="desktop-text") or \
                                 card.find("span", attrs={"class": lambda c: c and "stipend" in str(c).lower()})

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else "India"
                    stipend = stipend_el.get_text(strip=True) if stipend_el else ""
                    link = title_el.get("href", "#") if title_el and title_el.name == "a" else "#"

                    if not title or len(title) < 3:
                        continue

                    cat_name = path.split("/")[-1].replace("-internship", "").replace("-jobs", "").replace("-", " ")
                    jobs.append(self._make_job(
                        title=title,
                        company=company or "Startup",
                        logo=f"https://logo.clearbit.com/{company.lower().replace(' ', '').replace(',', '')}.com" if company else "",
                        location=location or "India",
                        job_type=default_type,
                        category=self._map_category(cat_name) if default_type != "Internship" else "Internship",
                        description=f"{title} at {company}. {stipend}. Found on Internshala.",
                        skills=self._extract_skills_from_text(f"{title} {cat_name}"),
                        apply_url=link if link.startswith("http") else f"https://internshala.com{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary=stipend,
                        source="Internshala",
                        experience="Entry Level",
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Internshala ({path}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 15: We Work Remotely (remote jobs, RSS feeds)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_weworkremotely(self) -> list[dict]:
        """Scrape We Work Remotely via their public RSS feeds."""
        jobs = []
        rss_feeds = [
            ("programming", "https://weworkremotely.com/categories/remote-programming-jobs.rss"),
            ("devops", "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss"),
            ("design", "https://weworkremotely.com/categories/remote-design-jobs.rss"),
            ("management", "https://weworkremotely.com/categories/remote-product-jobs.rss"),
            ("front-end", "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss"),
            ("back-end", "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"),
            ("full-stack", "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss"),
        ]
        for cat, feed_url in rss_feeds:
            try:
                resp = self.session.get(feed_url, timeout=12, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "application/rss+xml,application/xml,text/xml",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "xml")
                items = soup.find_all("item")

                for item in items[:8]:
                    title_text = item.find("title").get_text(strip=True) if item.find("title") else ""
                    link = item.find("link").get_text(strip=True) if item.find("link") else "#"
                    pub_date = item.find("pubDate").get_text(strip=True) if item.find("pubDate") else ""
                    description = item.find("description").get_text(strip=True) if item.find("description") else ""

                    if not title_text:
                        continue

                    # Parse company from title (format: "Company: Job Title")
                    company = ""
                    title = title_text
                    if ":" in title_text:
                        parts = title_text.split(":", 1)
                        company = parts[0].strip()
                        title = parts[1].strip()

                    # Parse date
                    posted = datetime.now().strftime("%Y-%m-%d")
                    if pub_date:
                        try:
                            from email.utils import parsedate_to_datetime
                            posted = parsedate_to_datetime(pub_date).strftime("%Y-%m-%d")
                        except Exception:
                            pass

                    # Clean HTML description
                    clean_desc = self._clean_html(description)

                    jobs.append(self._make_job(
                        title=title,
                        company=company or "Remote Company",
                        logo=f"https://logo.clearbit.com/{company.lower().replace(' ', '').replace(',', '')}.com" if company else "",
                        location="Remote",
                        job_type="Remote",
                        category=self._map_category(cat),
                        description=clean_desc or f"{title} at {company}. Remote position via We Work Remotely.",
                        skills=self._extract_skills_from_text(f"{title} {clean_desc[:200]}"),
                        apply_url=link,
                        posted=posted,
                        salary="",
                        source="We Work Remotely",
                    ))
                time.sleep(0.3)
            except Exception as e:
                logger.debug(f"WWR ({cat}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 16: FlexJobs (remote & flexible jobs)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_flexjobs(self) -> list[dict]:
        """Scrape FlexJobs for remote and flexible job listings."""
        jobs = []
        search_terms = [
            "software-developer", "data-scientist", "python",
            "devops", "product-manager",
        ]
        for term in search_terms:
            try:
                url = f"https://www.flexjobs.com/search?search={term.replace('-', '+')}&location="
                resp = self.session.get(url, timeout=8, headers={
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.flexjobs.com/",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_="job-card") or \
                        soup.find_all("li", class_="job-post") or \
                        soup.find_all("div", class_="sc-job-card") or \
                        soup.find_all("a", attrs={"class": lambda c: c and "job" in str(c).lower()})

                for card in cards[:6]:
                    title_el = card.find("a", class_="job-title") or card.find("h5") or card.find("a")
                    company_el = card.find("span", class_="company") or card.find("div", class_="company")
                    loc_el = card.find("span", class_="location") or card.find("li", class_="location")
                    type_el = card.find("span", class_="job-type") or card.find("li", class_="job-type")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = loc_el.get_text(strip=True) if loc_el else "Remote"
                    job_type = type_el.get_text(strip=True) if type_el else "Remote"
                    link = title_el.get("href", "#") if title_el and title_el.name == "a" else "#"

                    if not title or len(title) < 3:
                        continue

                    jobs.append(self._make_job(
                        title=title,
                        company=company or "Flexible Company",
                        logo=f"https://logo.clearbit.com/{company.lower().replace(' ', '').replace(',', '')}.com" if company else "",
                        location=location,
                        job_type=job_type if job_type in ["Remote", "Part-time", "Freelance", "Hybrid"] else "Remote",
                        category=self._map_category(term.replace("-", " ")),
                        description=f"{title} at {company}. Flexible/remote position via FlexJobs.",
                        skills=self._extract_skills_from_text(f"{title} {term.replace('-', ' ')}"),
                        apply_url=link if link.startswith("http") else f"https://www.flexjobs.com{link}",
                        posted=datetime.now().strftime("%Y-%m-%d"),
                        salary="",
                        source="FlexJobs",
                    ))
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"FlexJobs ({term}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # SOURCE 17: Himalayas (104K+ jobs, public JSON API)
    # ──────────────────────────────────────────────────────────────────

    def _scrape_himalayas(self) -> list[dict]:
        """
        Scrape Himalayas.app via their public JSON API.
        104K+ jobs, excellent data quality with salary, seniority, location.
        """
        jobs = []
        # Fetch multiple pages with offset for broader coverage
        offsets = [0, 50, 100]
        for offset in offsets:
            try:
                url = f"https://himalayas.app/jobs/api?limit=50&offset={offset}"
                resp = self.session.get(url, timeout=15, headers={
                    "Accept": "application/json",
                    "User-Agent": random.choice(USER_AGENTS),
                })
                if resp.status_code != 200:
                    continue

                data = resp.json()
                for item in data.get("jobs", []):
                    title = item.get("title", "")
                    company = item.get("companyName", "")
                    logo = item.get("companyLogo", "")
                    emp_type = item.get("employmentType", "Full Time")
                    min_sal = item.get("minSalary")
                    max_sal = item.get("maxSalary")
                    currency = item.get("currency", "USD")
                    seniority = item.get("seniority", [])
                    loc_restrictions = item.get("locationRestrictions", [])
                    categories = item.get("categories", [])
                    description = item.get("description", "")
                    apply_link = item.get("applicationLink", "#")
                    pub_date = item.get("pubDate")

                    if not title:
                        continue

                    # Build location string
                    location = "Remote"
                    if loc_restrictions:
                        location = ", ".join(loc_restrictions[:2])
                        if len(loc_restrictions) > 2:
                            location += f" +{len(loc_restrictions)-2} more"

                    # Build salary string
                    sal_str = ""
                    if min_sal and max_sal:
                        sal_str = f"{currency} {min_sal:,} – {max_sal:,}"
                    elif min_sal:
                        sal_str = f"{currency} {min_sal:,}+"

                    # Parse date from unix timestamp
                    posted = datetime.now().strftime("%Y-%m-%d")
                    if pub_date:
                        try:
                            posted = datetime.fromtimestamp(pub_date).strftime("%Y-%m-%d")
                        except Exception:
                            pass

                    # Map employment type
                    type_map = {
                        "Full Time": "Full-time",
                        "Part Time": "Part-time",
                        "Contract": "Contract",
                        "Freelance": "Freelance",
                        "Internship": "Internship",
                    }
                    job_type = type_map.get(emp_type, "Full-time")

                    # Map seniority
                    exp = "Mid Level"
                    if seniority:
                        exp = self._map_experience(seniority[0])

                    # Map category from job categories
                    cat = self._map_category(", ".join(categories[:3]))

                    jobs.append(self._make_job(
                        title=title,
                        company=company,
                        logo=logo or f"https://ui-avatars.com/api/?name={company[:2]}&background=667eea&color=fff&size=80",
                        location=location,
                        job_type=job_type,
                        category=cat,
                        description=self._clean_html(description),
                        skills=self._extract_skills_from_text(description[:500]),
                        apply_url=apply_link,
                        posted=posted,
                        salary=sal_str,
                        source="Himalayas",
                        experience=exp,
                    ))
                time.sleep(0.3)
            except Exception as e:
                logger.debug(f"Himalayas (offset {offset}): {e}")
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # REALTIME GENERATED DATA (supplemental)
    # ──────────────────────────────────────────────────────────────────

    def _generate_realistic_jobs(self, count: int = 150) -> list[dict]:
        """Generate realistic job listings from 80+ companies, weighted toward India."""
        jobs = []
        now = datetime.now()

        # Split locations into India vs other for weighted selection
        india_locations = [l for l in LOCATIONS if l["country"] == "India"]
        india_companies = [c for c in COMPANIES if "India" in c.get("hq", "")]
        all_locations = LOCATIONS
        all_companies = COMPANIES

        for _ in range(count):
            # 60% chance of Indian job, 40% other
            if random.random() < 0.6:
                company = random.choice(india_companies) if india_companies else random.choice(all_companies)
                location = random.choice(india_locations) if india_locations else random.choice(all_locations)
            else:
                company = random.choice(all_companies)
                location = random.choice(all_locations)
            role = random.choice(ROLES)
            exp = random.choice(EXPERIENCE_LEVELS)
            job_type = random.choice(JOB_TYPES)

            # Internship adjustments
            if "Intern" in role["title"]:
                exp = "Entry Level"
                job_type = "Internship"

            # Location-aware salary
            country = location["country"]
            salary_table = COUNTRY_SALARY_MAP.get(country, SALARY_RANGES_USD)
            sal = salary_table.get(exp, salary_table["Mid Level"])

            posted_days_ago = random.randint(0, 21)
            posted_date = (now - timedelta(days=posted_days_ago)).strftime("%Y-%m-%d")

            jobs.append({
                "title": role["title"],
                "company": company["name"],
                "company_logo": company["logo"],
                "industry": company["industry"],
                "location": location["display"],
                "location_city": location["city"],
                "location_state": location["state"],
                "location_country": location["country"],
                "type": job_type,
                "category": role["category"],
                "experience": exp,
                "salary_min": sal[0],
                "salary_max": sal[1],
                "description": self._generate_description(role, company, exp),
                "skills": role["skills"],
                "apply_url": f"https://careers.{company['name'].lower().replace(' ', '').replace('/', '').replace('(', '').replace(')', '')}.com",
                "posted_date": posted_date,
                "source": "CareerPath Pro",
            })
        return jobs

    # ──────────────────────────────────────────────────────────────────
    # HELPER METHODS
    # ──────────────────────────────────────────────────────────────────

    def _make_job(self, *, title, company, logo, location, job_type,
                  category, description, skills, apply_url, posted,
                  salary, source, experience="Mid Level") -> dict:
        """Build a normalised job dict."""
        # Clean up empties
        if not title:
            title = "Open Position"
        if not company:
            company = "Confidential"

        # Parse salary string
        sal_min = salary if salary else "Competitive"
        sal_max = ""
        if isinstance(salary, str) and "–" in salary:
            parts = salary.split("–")
            sal_min = parts[0].strip()
            sal_max = parts[1].strip() if len(parts) > 1 else ""
        elif isinstance(salary, str) and "-" in salary and "$" in salary:
            parts = salary.split("-")
            sal_min = parts[0].strip()
            sal_max = parts[1].strip() if len(parts) > 1 else ""

        return {
            "title": title.strip(),
            "company": company.strip(),
            "company_logo": logo or f"https://ui-avatars.com/api/?name={company[:2]}&background=667eea&color=fff&size=80",
            "industry": "",
            "location": location,
            "type": job_type,
            "category": category,
            "experience": experience,
            "salary_min": sal_min or "Competitive",
            "salary_max": sal_max,
            "description": (description or "No description provided.")[:1000],
            "skills": [s.strip() for s in skills if s] if skills else [],
            "apply_url": apply_url or "#",
            "posted_date": posted or datetime.now().strftime("%Y-%m-%d"),
            "source": source,
        }

    def _map_category(self, raw) -> str:
        """Map free-text category names to our standard categories."""
        if isinstance(raw, list):
            raw = ", ".join(str(r) for r in raw)
        raw = (raw or "").lower()
        mapping = {
            "software": "Technology", "dev": "Technology", "engineer": "Technology",
            "data": "Data Science", "machine learning": "Data Science", "ml": "Data Science",
            "ai": "Data Science", "analytics": "Data Science",
            "design": "Design", "ux": "Design", "ui": "Design", "creative": "Design",
            "product": "Management", "project": "Management", "management": "Management",
            "marketing": "Marketing", "seo": "Marketing", "content": "Marketing", "growth": "Marketing",
            "sales": "Sales", "business": "Business",
            "hr": "Human Resources", "recruit": "Human Resources", "people": "Human Resources",
            "devops": "Technology", "cloud": "Technology", "infra": "Technology", "sre": "Technology",
            "security": "Technology", "cyber": "Technology",
            "qa": "Technology", "test": "Technology", "quality": "Technology",
            "finance": "Finance", "account": "Finance", "legal": "Finance",
            "customer": "Customer Service", "support": "Customer Service",
            "intern": "Internship",
            "writing": "Marketing", "edit": "Marketing",
        }
        for keyword, cat in mapping.items():
            if keyword in raw:
                return cat
        return "Technology"

    def _map_experience(self, raw: str) -> str:
        """Map level names to standard experience levels."""
        raw_lower = (raw or "").lower()
        if "intern" in raw_lower or "entry" in raw_lower:
            return "Entry Level"
        if "junior" in raw_lower:
            return "Junior"
        if "senior" in raw_lower:
            return "Senior"
        if "lead" in raw_lower or "director" in raw_lower or "principal" in raw_lower:
            return "Lead"
        if "manager" in raw_lower or "head" in raw_lower:
            return "Lead"
        return "Mid Level"

    def _extract_skills_from_text(self, text: str) -> list[str]:
        """Extract tech skills from free text using keyword matching."""
        if not text:
            return []
        text_lower = text.lower()
        skill_bank = [
            "Python", "Java", "JavaScript", "TypeScript", "React", "Angular", "Vue.js",
            "Node.js", "Go", "Rust", "C++", "C#", ".NET", "Ruby", "PHP", "Swift",
            "Kotlin", "Flutter", "SQL", "PostgreSQL", "MongoDB", "Redis", "MySQL",
            "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "CI/CD",
            "Machine Learning", "Deep Learning", "NLP", "TensorFlow", "PyTorch",
            "Tableau", "Power BI", "Excel", "Figma", "Photoshop", "Illustrator",
            "SEO", "Google Ads", "Agile", "Scrum", "JIRA", "Git", "Linux",
            "REST APIs", "GraphQL", "Microservices", "System Design",
            "Selenium", "Cypress", "Jenkins", "Spark", "Airflow", "Kafka",
            "LangChain", "RAG", "Fine-tuning", "Prompt Engineering",
        ]
        found = []
        for skill in skill_bank:
            if skill.lower() in text_lower:
                found.append(skill)
            if len(found) >= 6:
                break
        return found or ["Problem Solving", "Communication"]

    def _generate_description(self, role, company, experience) -> str:
        """Generate a realistic job description."""
        benefits = random.choice([
            "Competitive salary, equity, health insurance, flexible PTO, learning budget",
            "Market-rate compensation, RSUs, wellness benefits, remote-friendly, 401(k)",
            "Attractive package, ESOPs, health & dental, unlimited leaves, team outings",
            "Great pay, stock options, medical coverage, work from anywhere, conference budget",
        ])
        return (
            f"Join {company['name']} as a {role['title']}!\n\n"
            f"We're hiring a {experience} {role['title']} to work on cutting-edge "
            f"projects in {company['industry']}. You'll collaborate with a world-class team "
            f"building products used by millions.\n\n"
            f"**Key Responsibilities:**\n"
            f"• Design, build, and maintain high-quality solutions\n"
            f"• Collaborate with cross-functional teams (Engineering, Design, Product)\n"
            f"• Write clean, tested, production-ready code\n"
            f"• Participate in code reviews, architectural decisions\n"
            f"• Mentor team members and contribute to engineering culture\n\n"
            f"**Requirements:**\n"
            f"• Strong proficiency in {', '.join(role['skills'][:3])}\n"
            f"• Experience with {role['skills'][-1] if role['skills'] else 'modern tools'}\n"
            f"• Excellent problem-solving and communication skills\n"
            f"• Passion for building great products at scale\n\n"
            f"**What We Offer:**\n"
            f"• {benefits}\n"
            f"• A collaborative, inclusive work environment"
        )

    def _clean_html(self, html_text: str) -> str:
        """Strip HTML tags and limit text length."""
        if not html_text:
            return ""
        soup = BeautifulSoup(html_text, "html.parser")
        return soup.get_text(separator="\n", strip=True)[:1000]


# ═══════════════════════════════════════════════════════════════════════
# DAILY CRON SCRIPT – can be called directly: python scraper/job_scraper.py
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json as _json
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    scraper = JobScraper()
    jobs = scraper.scrape_all()

    # Save to data/jobs.json
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "jobs.json")
    payload = {
        "jobs": jobs,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": list({j["source"] for j in jobs}),
        "total": len(jobs),
    }
    with open(out_path, "w") as f:
        _json.dump(payload, f, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ Total unique jobs: {len(jobs)}")
    print(f"📁 Saved to: {out_path}")
    print(f"{'='*60}")

    # Summary by source
    from collections import Counter
    src_counts = Counter(j["source"] for j in jobs)
    for src, count in src_counts.most_common():
        print(f"   {src:20s} → {count} jobs")

    # Summary by country
    country_counts = Counter(j.get("location_country", "Unknown") for j in jobs)
    print(f"\n📍 Jobs by country:")
    for country, count in country_counts.most_common(10):
        print(f"   {country:20s} → {count} jobs")

    print(f"\n🔍 Sample jobs:")
    for j in jobs[:8]:
        print(f"   📌 {j['title']} @ {j['company']} | 📍 {j['location']} | via {j['source']}")
