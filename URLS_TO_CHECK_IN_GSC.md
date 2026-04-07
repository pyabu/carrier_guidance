# URLs to Check in Google Search Console

## 🔍 How to Find Problem URLs

### Method 1: Check "Why pages aren't indexed"
1. Go to: https://search.google.com/search-console
2. Click **"Pages"** in left menu
3. Scroll to **"Why pages aren't indexed"**
4. Click on each issue to see specific URLs

### Method 2: Check "Duplicate" Issues
1. In the "Why pages aren't indexed" section
2. Click **"Duplicate without user-selected canonical"** (2 pages)
3. Click **"Duplicate, Google chose different canonical than user"** (4 pages)
4. Note all URLs shown

---

## 🎯 Known Problem URLs (Already Fixed)

### Legacy Job URLs - Request Removal:
```
https://careerguidance.me/job/2
https://careerguidance.me/job/6
```

**Action:** Request removal in GSC → Removals → New Request

**Then request indexing of canonical versions:**
```
https://careerguidance.me/job/main/2
https://careerguidance.me/job/main/6
```

---

## 🔎 Other Potential Legacy URLs to Check

### Pattern 1: Old Job URLs (single digit)
If Google indexed these before the canonical system:
```
https://careerguidance.me/job/1
https://careerguidance.me/job/3
https://careerguidance.me/job/4
https://careerguidance.me/job/5
https://careerguidance.me/job/7
https://careerguidance.me/job/8
https://careerguidance.me/job/9
https://careerguidance.me/job/10
```

**How to check:**
```bash
# Test if they exist and redirect properly
curl -I https://careerguidance.me/job/1
curl -I https://careerguidance.me/job/3
curl -I https://careerguidance.me/job/4
```

**If they show up in GSC:** Request removal for each

---

## 🚫 API Endpoints - Should NOT be Indexed

### Already Fixed with noindex headers:
```
https://careerguidance.me/api/saved-jobs
https://careerguidance.me/api/alerts
https://careerguidance.me/api/bookmarked-companies
https://careerguidance.me/api/search
https://careerguidance.me/api/stats
```

**Action:** If any appear in GSC, request re-indexing so Google sees the noindex headers

---

## 📄 URLs with Query Parameters

### These should have noindex (already implemented):
```
https://careerguidance.me/jobs?utm_source=...
https://careerguidance.me/jobs?page=2
https://careerguidance.me/jobs?sort=date
https://careerguidance.me/jobs?category=...
```

**Status:** ✅ These are handled correctly with:
- Canonical tag pointing to clean URL
- noindex meta tag for filtered views
- Should appear as "Alternate page with proper canonical tag" (this is good!)

---

## 🔄 Trailing Slash Variants

### These should redirect to non-trailing slash:
```
https://careerguidance.me/jobs/
https://careerguidance.me/about/
https://careerguidance.me/contact/
```

**Status:** ✅ Already handled by canonical redirect system

---

## 🌐 WWW vs Non-WWW

### Check if both versions are indexed:
```
https://www.careerguidance.me/
https://careerguidance.me/
```

**How to check in GSC:**
1. Go to Settings → Property settings
2. Check which version is verified
3. If both exist, consolidate to one

**Current setup:** Non-WWW (careerguidance.me) is canonical

---

## 📋 Complete Checklist

### Step 1: Identify All Problem URLs
- [ ] Go to GSC → Pages → "Why pages aren't indexed"
- [ ] Click "Duplicate without user-selected canonical" → Note URLs
- [ ] Click "Duplicate, Google chose different canonical" → Note URLs
- [ ] Click "Crawled - currently not indexed" → Note URLs
- [ ] Click "Server error (5xx)" → Note URLs

### Step 2: For Each Legacy Job URL Found
- [ ] Request removal: GSC → Removals → New Request → Enter URL
- [ ] Find canonical version (e.g., /job/2 → /job/main/2)
- [ ] Request indexing: GSC → URL Inspection → Request Indexing

### Step 3: For Each API Endpoint Found
- [ ] Request re-indexing: GSC → URL Inspection → Request Indexing
- [ ] Google will see noindex header and remove it automatically

### Step 4: For Duplicate Issues
- [ ] Check if canonical tag is present
- [ ] Verify canonical URL is correct
- [ ] Request indexing of canonical version

---

## 🧪 Testing Script

Run this to test common legacy URLs:

```bash
#!/bin/bash
echo "Testing legacy job URLs..."

for i in {1..10}; do
  echo "Testing /job/$i"
  status=$(curl -s -o /dev/null -w "%{http_code}" https://careerguidance.me/job/$i)
  if [ "$status" = "301" ]; then
    echo "  ✅ Redirects (301)"
  elif [ "$status" = "404" ]; then
    echo "  ❌ Not found (404)"
  elif [ "$status" = "200" ]; then
    echo "  ⚠️  Returns 200 (should redirect!)"
  else
    echo "  ❓ Status: $status"
  fi
done
```

Save as `test_legacy_urls.sh` and run: `bash test_legacy_urls.sh`

---

## 📊 Expected GSC Status After Fixes

### "Why pages aren't indexed" should show:

| Issue | Before | After | Status |
|-------|--------|-------|--------|
| Crawled - currently not indexed | 5 | 0-2 | ⏳ Monitor |
| Alternate page with proper canonical | 143 | 150+ | ✅ Good |
| Blocked by robots.txt | 39 | 39 | ✅ Correct |
| Server error (5xx) | 2 | 0 | ✅ Fixed |
| Duplicate, Google chose different | 4 | 0 | ✅ Fixed |
| Duplicate without canonical | 2 | 0 | ✅ Fixed |

---

## 🎯 Priority Actions (Do First)

1. **HIGH:** Remove `/job/2` and `/job/6` from index
2. **HIGH:** Request indexing of `/job/main/2` and `/job/main/6`
3. **MEDIUM:** Check for other legacy job URLs in GSC
4. **MEDIUM:** Request re-indexing of any API endpoints found
5. **LOW:** Monitor "Crawled - currently not indexed" pages

---

## 📞 Need More URLs?

If you see other problem URLs in Google Search Console that aren't listed here:

1. Copy the URL from GSC
2. Test it: `curl -I [URL]`
3. Check if it redirects properly
4. If it's a legacy format, request removal
5. Request indexing of the canonical version

---

**Last Updated:** 2026-04-07  
**Next Review:** Check GSC in 1 week to see progress
