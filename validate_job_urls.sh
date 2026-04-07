#!/bin/bash
# Validation script for job URL fixes

echo "🔍 Testing Legacy Job URLs..."
echo ""

echo "1️⃣ Testing /job/2 (should redirect with noindex)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -sI https://careerguidance.me/job/2 | grep -E "(HTTP|location|x-robots-tag)"
echo ""

echo "2️⃣ Testing /job/6 (should redirect with noindex)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -sI https://careerguidance.me/job/6 | grep -E "(HTTP|location|x-robots-tag)"
echo ""

echo "3️⃣ Testing /job/main/2 (canonical - should be indexable)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -sI https://careerguidance.me/job/main/2 | grep -E "(HTTP|x-robots-tag|content-type)"
echo ""

echo "4️⃣ Testing /job/main/6 (canonical - should be indexable)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -sI https://careerguidance.me/job/main/6 | grep -E "(HTTP|x-robots-tag|content-type)"
echo ""

echo "5️⃣ Checking canonical tags in HTML"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s https://careerguidance.me/job/main/2 | grep -o '<link rel="canonical"[^>]*>' | head -1
echo ""

echo "✅ Validation complete!"
echo ""
echo "Expected results:"
echo "  ✓ Legacy URLs (/job/2, /job/6) should return:"
echo "    - HTTP 301 (redirect)"
echo "    - location: /job/main/{id}"
echo "    - x-robots-tag: noindex, nofollow"
echo ""
echo "  ✓ Canonical URLs (/job/main/2, /job/main/6) should return:"
echo "    - HTTP 200 (success)"
echo "    - NO x-robots-tag (indexable)"
echo "    - content-type: text/html"
echo "    - canonical tag pointing to itself"
