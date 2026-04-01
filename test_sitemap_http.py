#!/usr/bin/env python3
"""Test sitemap HTTP response"""
import os

sitemap_path = 'sitemap.xml'

print('Testing sitemap file...')
print(f'Exists: {os.path.exists(sitemap_path)}')

if os.path.exists(sitemap_path):
    with open(sitemap_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f'✅ File size: {len(content)} bytes')
    print(f'✅ First 100 chars:')
    print(content[:100])
    print(f'✅ Last 100 chars:')
    print(content[-100:])
    
    # Check for issues
    if '<?xml' in content:
        print('✅ Has XML declaration')
    if '<urlset' in content:
        print('✅ Has urlset element')
    if '</urlset>' in content:
        print('✅ Has closing urlset tag')
else:
    print('❌ sitemap.xml not found')
