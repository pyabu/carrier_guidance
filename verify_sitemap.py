#!/usr/bin/env python3
"""
Sitemap Verification Script
Comprehensive checks to ensure sitemap.xml is readable by Google
"""

import os
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SITEMAP_PATH = os.path.join(BASE_DIR, "sitemap.xml")

def check_file_exists():
    """Check if sitemap.xml exists."""
    if os.path.exists(SITEMAP_PATH):
        size = os.path.getsize(SITEMAP_PATH)
        print(f"✅ File exists: {SITEMAP_PATH}")
        print(f"✅ File size: {size:,} bytes ({size/1024/1024:.2f} MB)")
        return True
    else:
        print(f"❌ File not found: {SITEMAP_PATH}")
        return False

def check_xml_validity():
    """Check if XML is valid."""
    try:
        tree = ET.parse(SITEMAP_PATH)
        root = tree.getroot()
        print(f"✅ Valid XML structure")
        print(f"✅ Root element: {root.tag}")
        print(f"✅ Namespace: {root.get('xmlns', 'None')}")
        return True
    except Exception as e:
        print(f"❌ Invalid XML: {e}")
        return False

def check_url_count():
    """Check URL count and structure."""
    try:
        tree = ET.parse(SITEMAP_PATH)
        root = tree.getroot()
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = root.findall('sm:url', ns)
        
        print(f"✅ Total URLs: {len(urls)}")
        
        if len(urls) == 0:
            print(f"❌ No URLs found in sitemap!")
            return False
        
        print(f"✅ URL count is valid")
        return True
    except Exception as e:
        print(f"❌ Error counting URLs: {e}")
        return False

def check_url_validity():
    """Check if all URLs are valid."""
    try:
        tree = ET.parse(SITEMAP_PATH)
        root = tree.getroot()
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = root.findall('sm:url', ns)
        
        invalid_urls = 0
        for url_elem in urls:
            loc = url_elem.find('sm:loc', ns)
            if loc is None or not loc.text:
                invalid_urls += 1
            else:
                # Validate URL format
                try:
                    result = urlparse(loc.text)
                    if not all([result.scheme, result.netloc]):
                        invalid_urls += 1
                except:
                    invalid_urls += 1
        
        if invalid_urls == 0:
            print(f"✅ All URLs are valid")
            return True
        else:
            print(f"❌ Found {invalid_urls} invalid URLs")
            return False
    except Exception as e:
        print(f"❌ Error validating URLs: {e}")
        return False

def check_encoding():
    """Check file encoding."""
    try:
        with open(SITEMAP_PATH, 'rb') as f:
            content = f.read()
        
        # Check for UTF-8 BOM or declaration
        if content.startswith(b'\xef\xbb\xbf'):
            print(f"✅ Has UTF-8 BOM")
        elif b'encoding="UTF-8"' in content or b"encoding='UTF-8'" in content:
            print(f"✅ UTF-8 encoding declared")
        else:
            print(f"⚠️  No explicit encoding declaration (assuming UTF-8)")
        
        # Try to decode as UTF-8
        content.decode('utf-8')
        print(f"✅ Valid UTF-8 encoding")
        return True
    except Exception as e:
        print(f"❌ Encoding error: {e}")
        return False

def check_required_fields():
    """Check if all URLs have required fields."""
    try:
        tree = ET.parse(SITEMAP_PATH)
        root = tree.getroot()
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = root.findall('sm:url', ns)
        
        missing_loc = 0
        missing_lastmod = 0
        
        for url_elem in urls:
            if url_elem.find('sm:loc', ns) is None:
                missing_loc += 1
            if url_elem.find('sm:lastmod', ns) is None:
                missing_lastmod += 1
        
        if missing_loc == 0:
            print(f"✅ All URLs have <loc> tag")
        else:
            print(f"⚠️  {missing_loc} URLs missing <loc> tag")
        
        if missing_lastmod == 0:
            print(f"✅ All URLs have <lastmod> tag")
        else:
            print(f"⚠️  {missing_lastmod} URLs missing <lastmod> tag")
        
        return True
    except Exception as e:
        print(f"❌ Error checking fields: {e}")
        return False

def check_special_characters():
    """Check for unescaped special characters."""
    try:
        with open(SITEMAP_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for unescaped special characters in <loc> tags
        unescaped_chars = re.findall(r'<loc>([^<]*[&<>][^<]*)</loc>', content)
        
        if not unescaped_chars:
            print(f"✅ No unescaped special characters found")
            return True
        else:
            print(f"⚠️  Found {len(unescaped_chars)} URLs with potential unescaped characters")
            for char in unescaped_chars[:5]:
                print(f"    - {char[:80]}")
            return False
    except Exception as e:
        print(f"❌ Error checking special characters: {e}")
        return False

def check_file_readable():
    """Check if file is readable by checking permissions."""
    try:
        with open(SITEMAP_PATH, 'r') as f:
            f.read(1)  # Try to read first character
        print(f"✅ File is readable")
        return True
    except Exception as e:
        print(f"❌ File is not readable: {e}")
        return False

def main():
    """Run all checks."""
    print("=" * 70)
    print("🔍 SITEMAP VERIFICATION REPORT")
    print("=" * 70)
    print()
    
    checks = [
        ("File Exists", check_file_exists),
        ("File Readable", check_file_readable),
        ("XML Validity", check_xml_validity),
        ("URL Count", check_url_count),
        ("URL Validity", check_url_validity),
        ("File Encoding", check_encoding),
        ("Required Fields", check_required_fields),
        ("Special Characters", check_special_characters),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        print("-" * 70)
        result = check_func()
        results.append((name, result))
        print()
    
    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All checks passed! Sitemap is ready for Google.")
        print("✅ Submit to Google Search Console: https://careerguidance.me/sitemap.xml")
        return 0
    else:
        print(f"\n⚠️  {total - passed} check(s) failed. Review above for details.")
        return 1

if __name__ == "__main__":
    exit(main())
