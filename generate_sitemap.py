#!/usr/bin/env python3
"""
Generate static sitemap.xml for CareerGuidance
This creates a one-time sitemap file that can be served to Google
"""

import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from xml.dom import minidom

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_URL = "https://careerguidance.me"


def load_jobs():
    """Load main jobs data."""
    try:
        with open(os.path.join(BASE_DIR, 'data', 'jobs.json'), 'r') as f:
            return json.load(f)
    except:
        return {"jobs": []}


def load_india_jobs():
    """Load India jobs data."""
    try:
        with open(os.path.join(BASE_DIR, 'data', 'india_jobs.json'), 'r') as f:
            return json.load(f)
    except:
        return {"jobs": []}


def load_tn_jobs():
    """Load Tamil Nadu jobs data."""
    try:
        with open(os.path.join(BASE_DIR, 'data', 'tn_jobs.json'), 'r') as f:
            return json.load(f)
    except:
        return {"jobs": []}


def generate_sitemap():
    """Generate sitemap.xml with all URLs using XML library."""
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Create root element
    root = ET.Element('urlset')
    root.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    
    # Static pages with priorities
    static_urls = [
        {"loc": "/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "/jobs", "priority": "0.95", "changefreq": "daily"},
        {"loc": "/jobs/india", "priority": "0.92", "changefreq": "daily"},
        {"loc": "/jobs/tamilnadu", "priority": "0.90", "changefreq": "daily"},
        {"loc": "/career-guidance", "priority": "0.85", "changefreq": "weekly"},
        {"loc": "/resume-builder", "priority": "0.85", "changefreq": "weekly"},
        {"loc": "/job-trends", "priority": "0.80", "changefreq": "weekly"},
        {"loc": "/blog", "priority": "0.80", "changefreq": "weekly"},
        {"loc": "/faq", "priority": "0.70", "changefreq": "monthly"},
        {"loc": "/about", "priority": "0.60", "changefreq": "monthly"},
        {"loc": "/contact", "priority": "0.55", "changefreq": "monthly"},
        {"loc": "/developer", "priority": "0.50", "changefreq": "quarterly"},
        {"loc": "/privacy", "priority": "0.30", "changefreq": "yearly"},
        {"loc": "/terms", "priority": "0.30", "changefreq": "yearly"},
    ]
    
    seen_urls = set()
    total_urls = 0
    
    # Add static pages
    for url in static_urls:
        loc = f"{BASE_URL}{url['loc']}"
        if loc not in seen_urls:
            url_elem = ET.SubElement(root, 'url')
            loc_elem = ET.SubElement(url_elem, 'loc')
            loc_elem.text = loc
            lastmod_elem = ET.SubElement(url_elem, 'lastmod')
            lastmod_elem.text = today
            changefreq_elem = ET.SubElement(url_elem, 'changefreq')
            changefreq_elem.text = url['changefreq']
            priority_elem = ET.SubElement(url_elem, 'priority')
            priority_elem.text = url['priority']
            seen_urls.add(loc)
            total_urls += 1
    
    # Add dynamic job detail pages (limit to avoid sitemap overflow)
    datasets = [
        ("main", load_jobs, "0.80"),
        ("india", load_india_jobs, "0.75"),
        ("tamilnadu", load_tn_jobs, "0.70"),
    ]
    
    total_jobs_added = 0
    max_jobs_per_source = 3000
    
    for source_name, loader, priority in datasets:
        try:
            data = loader()
            fallback_date = today
            
            if isinstance(data, dict) and "last_updated" in data:
                fallback_date = str(data.get("last_updated", today)).split(" ")[0]
            
            jobs_added = 0
            for job in data.get("jobs", []):
                if jobs_added >= max_jobs_per_source:
                    break
                
                job_id = job.get("id")
                if job_id in (None, "", ""):
                    continue
                
                # Create canonical job URL
                loc = f"{BASE_URL}/job/{source_name}/{job_id}"
                
                if loc in seen_urls:
                    continue
                
                seen_urls.add(loc)
                url_elem = ET.SubElement(root, 'url')
                loc_elem = ET.SubElement(url_elem, 'loc')
                loc_elem.text = loc
                lastmod_elem = ET.SubElement(url_elem, 'lastmod')
                lastmod_elem.text = fallback_date
                changefreq_elem = ET.SubElement(url_elem, 'changefreq')
                changefreq_elem.text = 'daily'
                priority_elem = ET.SubElement(url_elem, 'priority')
                priority_elem.text = priority
                jobs_added += 1
                total_jobs_added += 1
                total_urls += 1
        
        except Exception as e:
            print(f"⚠️ Error adding {source_name} jobs: {e}")
    
    print(f"✅ Generated sitemap with {total_urls} total entries ({total_jobs_added} job details)")
    
    # Pretty print XML
    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    # Remove extra blank lines
    xml_str = '\n'.join([line for line in xml_str.split('\n') if line.strip()])
    
    # Write to file with UTF-8 encoding
    sitemap_path = os.path.join(BASE_DIR, "sitemap.xml")
    with open(sitemap_path, 'w', encoding='utf-8') as f:
        f.write(xml_str)
    
    print(f"📝 Sitemap saved to: {sitemap_path}")
    return sitemap_path


if __name__ == "__main__":
    generate_sitemap()
