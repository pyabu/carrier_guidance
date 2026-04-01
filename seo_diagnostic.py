"""
SEO Diagnostic Tool - Identify and fix indexing issues
============================================================
This script helps identify:
1. Server errors (5xx) that prevent indexing
2. Pages blocked by robots.txt but indexed
3. Canonical URL conflicts
4. Duplicate content issues
5. Sitemap problems

Run: python seo_diagnostic.py
"""

import json
import os
import sys
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://careerguidance.me"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class SEODiagnostic:
    """Comprehensive SEO diagnostic tool."""
    
    def __init__(self):
        self.issues = {
            "critical": [],
            "warnings": [],
            "info": []
        }
        self.load_config()
    
    def load_config(self):
        """Load SEO configuration from JSON."""
        try:
            seo_file = os.path.join(BASE_DIR, "data", "seo_settings.json")
            with open(seo_file, 'r') as f:
                self.config = json.load(f)
            logger.info("✅ SEO configuration loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load SEO config: {e}")
            self.config = {}
    
    def check_robots_txt(self):
        """Verify robots.txt doesn't accidentally block index-able pages."""
        logger.info("\n🤖 Checking robots.txt...")
        
        robots_path = os.path.join(BASE_DIR, "robots.txt")
        try:
            with open(robots_path, 'r') as f:
                content = f.read()
            
            # Check for conflicting rules
            if "Disallow: /api/" in content and "Allow: /api/" in content:
                self.issues["critical"].append(
                    "❌ Conflicting rules in robots.txt: Both Allow and Disallow for /api/"
                )
            
            # Check if public pages are accidentally blocked
            public_paths = self.config.get("indexing_rules", {}).get("allow_indexing", [])
            for path in public_paths:
                if path in ["/", "/*"]:
                    continue
                path_check = f"Disallow: {path}"
                if path_check in content:
                    self.issues["critical"].append(
                        f"❌ Public page blocked in robots.txt: {path}"
                    )
            
            if "Sitemap:" in content and BASE_URL in content:
                self.issues["info"].append("✅ Sitemap URL present in robots.txt")
            else:
                self.issues["warnings"].append("⚠️ Sitemap URL missing or incorrect in robots.txt")
                
        except Exception as e:
            self.issues["critical"].append(f"❌ Cannot read robots.txt: {e}")
    
    def check_sitemap_xml(self):
        """Verify sitemap.xml configuration."""
        logger.info("\n🗺️  Checking sitemap.xml...")
        
        sitemap_path = os.path.join(BASE_DIR, "sitemap.xml")
        
        try:
            with open(sitemap_path, 'r') as f:
                content = f.read()
            
            if not content.strip():
                self.issues["critical"].append("❌ sitemap.xml is empty")
                return
            
            # Check XML validity
            if '<?xml' not in content:
                self.issues["critical"].append("❌ sitemap.xml missing XML declaration")
            
            if '<urlset' not in content:
                self.issues["critical"].append("❌ sitemap.xml missing urlset tag")
            
            # Count URLs
            url_count = content.count("<loc>")
            if url_count == 0:
                self.issues["critical"].append("❌ sitemap.xml has 0 URLs")
            elif url_count < 10:
                self.issues["warnings"].append(f"⚠️ sitemap.xml has only {url_count} URLs (expected 100+)")
            else:
                self.issues["info"].append(f"✅ sitemap.xml contains {url_count} URLs")
            
            # Check for duplicates
            import re
            loc_pattern = r'<loc>(.*?)</loc>'
            urls = re.findall(loc_pattern, content)
            
            duplicates = [url for url in urls if urls.count(url) > 1]
            if duplicates:
                self.issues["critical"].append(
                    f"❌ Duplicate URLs in sitemap: {set(duplicates)}"
                )
            else:
                self.issues["info"].append("✅ No duplicate URLs in sitemap")
            
            # Check for proper lastmod dates
            lastmod_pattern = r'<lastmod>(.*?)</lastmod>'
            lastmods = re.findall(lastmod_pattern, content)
            
            if len(lastmods) != len(urls):
                self.issues["warnings"].append(
                    f"⚠️ Not all URLs have lastmod dates ({len(lastmods)}/{len(urls)})"
                )
            
        except FileNotFoundError:
            self.issues["critical"].append("❌ sitemap.xml not found")
        except Exception as e:
            self.issues["critical"].append(f"❌ Error reading sitemap.xml: {e}")
    
    def check_canonical_urls(self):
        """Verify canonical URL configuration."""
        logger.info("\n🔗 Checking canonical URLs...")
        
        canonical_rules = self.config.get("canonical_rules", {})
        
        if canonical_rules.get("enforce_https"):
            self.issues["info"].append("✅ HTTPS enforcement enabled")
        else:
            self.issues["warnings"].append("⚠️ HTTPS enforcement disabled")
        
        if not canonical_rules.get("trailing_slash"):
            self.issues["info"].append("✅ Trailing slash removal enabled")
        else:
            self.issues["warnings"].append("⚠️ Trailing slash not normalized")
        
        exclude_params = canonical_rules.get("remove_query_params", [])
        if exclude_params:
            self.issues["info"].append(f"✅ Query parameters removed from canonical: {exclude_params}")
        else:
            self.issues["warnings"].append("⚠️ No query parameters excluded from canonical")
    
    def check_error_handling(self):
        """Verify error pages are properly configured."""
        logger.info("\n⚠️  Checking error handling...")
        
        error_config = self.config.get("error_handling", {})
        
        # Check 404 handling
        if error_config.get("404_status_code") == 404 and error_config.get("404_noindex"):
            self.issues["info"].append("✅ 404 errors properly configured with noindex")
        else:
            self.issues["critical"].append("❌ 404 error handling misconfigured")
        
        # Check 500 handling
        if error_config.get("500_status_code") == 500:
            if error_config.get("500_noindex") and error_config.get("500_no_cache"):
                self.issues["info"].append("✅ 500 errors properly configured with noindex and no-cache")
            else:
                self.issues["critical"].append("❌ 500 error pages should have noindex and no-cache headers")
        
        # Check 503 handling
        if error_config.get("503_status_code") == 503:
            retry_after = error_config.get("503_retry_after")
            if error_config.get("503_noindex") and retry_after:
                self.issues["info"].append(f"✅ 503 errors configured with Retry-After: {retry_after}s")
            else:
                self.issues["warnings"].append("⚠️ 503 error handling could be improved")
    
    def check_indexing_rules(self):
        """Verify indexing rules configuration."""
        logger.info("\n📋 Checking indexing rules...")
        
        allow_list = self.config.get("indexing_rules", {}).get("allow_indexing", [])
        noindex_list = self.config.get("indexing_rules", {}).get("noindex_pages", [])
        block_list = self.config.get("indexing_rules", {}).get("block_crawl", [])
        
        if allow_list:
            self.issues["info"].append(f"✅ {len(allow_list)} pages allowed for indexing")
        else:
            self.issues["warnings"].append("⚠️ Allow indexing list is empty")
        
        if noindex_list:
            self.issues["info"].append(f"✅ {len(noindex_list)} pages marked as noindex")
        else:
            self.issues["warnings"].append("⚠️ Noindex list is empty")
        
        if block_list:
            self.issues["info"].append(f"✅ {len(block_list)} paths blocked from crawling")
        
        # Check for conflicts
        conflicts = set(allow_list) & set(noindex_list)
        if conflicts:
            self.issues["critical"].append(
                f"❌ Indexing conflicts detected: {conflicts}"
            )
    
    def run_diagnostics(self):
        """Run all diagnostic checks."""
        logger.info("=" * 70)
        logger.info("🔍 CAREERGUIDANCE.ME - SEO DIAGNOSTIC REPORT")
        logger.info(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        # Run all checks
        self.check_robots_txt()
        self.check_sitemap_xml()
        self.check_canonical_urls()
        self.check_error_handling()
        self.check_indexing_rules()
        
        # Print results
        self.print_results()
        
        # Return exit code
        return 0 if not self.issues["critical"] else 1
    
    def print_results(self):
        """Print diagnostic results."""
        print("\n" + "=" * 70)
        print("📊 DIAGNOSTIC RESULTS")
        print("=" * 70)
        
        # Critical issues
        if self.issues["critical"]:
            print(f"\n🔴 CRITICAL ISSUES ({len(self.issues['critical'])})")
            print("-" * 70)
            for issue in self.issues["critical"]:
                print(f"  {issue}")
        
        # Warnings
        if self.issues["warnings"]:
            print(f"\n🟡 WARNINGS ({len(self.issues['warnings'])})")
            print("-" * 70)
            for warning in self.issues["warnings"]:
                print(f"  {warning}")
        
        # Info messages
        if self.issues["info"]:
            print(f"\n🟢 PASSED CHECKS ({len(self.issues['info'])})")
            print("-" * 70)
            for info in self.issues["info"]:
                print(f"  {info}")
        
        # Summary
        print("\n" + "=" * 70)
        total_issues = len(self.issues["critical"]) + len(self.issues["warnings"])
        if total_issues == 0:
            print("✅ All SEO checks passed! Your site is ready for indexing.")
        else:
            print(f"⚠️  Found {total_issues} issues to fix:")
            if self.issues["critical"]:
                print(f"   - {len(self.issues['critical'])} critical (must fix)")
            if self.issues["warnings"]:
                print(f"   - {len(self.issues['warnings'])} warnings (should fix)")
        
        print("=" * 70 + "\n")
    
    def generate_report(self, filename="seo_diagnostic_report.txt"):
        """Generate a detailed report file."""
        report_path = os.path.join(BASE_DIR, filename)
        
        with open(report_path, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("CAREERGUIDANCE.ME - SEO DIAGNOSTIC DETAILED REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            
            f.write("CRITICAL ISSUES:\n")
            f.write("-" * 70 + "\n")
            for issue in self.issues["critical"]:
                f.write(f"{issue}\n")
            
            f.write("\n\nWARNINGS:\n")
            f.write("-" * 70 + "\n")
            for warning in self.issues["warnings"]:
                f.write(f"{warning}\n")
            
            f.write("\n\nPASSED CHECKS:\n")
            f.write("-" * 70 + "\n")
            for info in self.issues["info"]:
                f.write(f"{info}\n")
            
            f.write("\n\nRECOMMENDATIONS:\n")
            f.write("-" * 70 + "\n")
            f.write("1. Run diagnostics regularly (weekly recommended)\n")
            f.write("2. Fix all critical issues before deploying to production\n")
            f.write("3. Monitor Search Console for indexing issues\n")
            f.write("4. Regenerate sitemap.xml after major content changes\n")
            f.write("5. Test canonical URLs and redirects\n")
        
        logger.info(f"📄 Detailed report saved: {filename}")


if __name__ == "__main__":
    diagnostic = SEODiagnostic()
    exit_code = diagnostic.run_diagnostics()
    diagnostic.generate_report()
    sys.exit(exit_code)
