# Fix Legacy Job URLs - Action Plan

## Problem
Google has indexed old-format job URLs:
- `https://careerguidance.me/job/2` (Principal Solution Architect)
- `https://careerguidance.me/job/6` (Senior Backend Engineer)

These URLs now redirect (301) to canonical URLs:
- `/job/2` → `/job/main/2`
- `/job/6` → `/job/main/6`

## What We Fixed

### 1. ✅ Added noindex header to legacy redirects
```python
@app.route("/job/<job_id>")
def job_detail(job_id):
    # ... resolve job ...
    response = redirect(job["detail_path"], code=301)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response
```

### 2. ✅ Canonical URLs are properly set
The new format `/job/{source}/{id}` has proper canonical tags and structured data.

## Actions Required in Google Search Console

### Step 1: Request Removal of Legacy URLs

1. Go to: https://search.google.com/search-console
2. Select property: `careerguidance.me`
3. Click "Removals" in left menu
4. Click "New Request"
5. Enter URL: `https://careerguidance.me/job/2`
6. Select "Remove this URL only"
7. Click "Next" → "Submit"
8. Repeat for: `https://careerguidance.me/job/6`

### Step 2: Request Indexing of Canonical URLs

1. Click "URL Inspection" in left menu
2. Enter: `https://careerguidance.me/job/main/2`
3. Click "Request Indexing"
4. Wait for confirmation
5. Repeat for: `https://careerguidance.me/job/main/6`

### Step 3: Verify the Fix

After 24-48 hours:

```bash
# Test that legacy URLs redirect with noindex
curl -I https://careerguidance.me/job/2

# Should show:
# HTTP/2 301
# location: /job/main/2
# x-robots-tag: noindex, nofollow

# Test that canonical URLs work
curl -I https://careerguidance.me/job/main/2

# Should show:
# HTTP/2 200
# (no x-robots-tag, meaning indexable)
```

## Why This Happened

These legacy URLs were likely:
1. In an old sitemap that Google cached
2. Linked from external sites
3. Crawled before the canonical URL system was implemented

## Prevention

✅ All new job URLs use the canonical format: `/job/{source}/{id}`
✅ Legacy URLs redirect with 301 + noindex headers
✅ Sitemap only contains canonical URLs
✅ Structured data uses canonical URLs

## Timeline

| Action | When | Status |
|--------|------|--------|
| Add noindex to redirects | ✅ Done | Complete |
| Request removal in GSC | 🔄 Now | Pending |
| Request indexing of canonical | 🔄 Now | Pending |
| Google processes removal | 1-3 days | Waiting |
| Google indexes canonical | 1-7 days | Waiting |
| Verify in GSC | 1 week | Pending |

## Expected Outcome

After 1-2 weeks:
- ❌ `/job/2` and `/job/6` removed from Google index
- ✅ `/job/main/2` and `/job/main/6` indexed properly
- ✅ No more "Duplicate without user-selected canonical" errors

## Monitoring

Check weekly in Google Search Console:
- Pages → "Why pages aren't indexed"
- Should see decrease in duplicate issues
- Legacy URLs should appear in "Excluded" section

---

**Last Updated:** 2026-04-07
**Status:** Fix deployed, awaiting Google recrawl
