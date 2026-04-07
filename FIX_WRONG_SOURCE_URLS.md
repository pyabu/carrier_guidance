# Fix Wrong-Source Job URLs

## 🔍 Problem

Google found: `https://careerguidance.me/job/main/6`  
But the job is actually in the India dataset.  
Correct URL: `https://careerguidance.me/job/india/6`

## ✅ What We Fixed

### 1. Added Redirect with noindex Header
When someone visits `/job/main/6`, the server now:
1. Detects the job is actually in the `india` dataset
2. Redirects (301) to `/job/india/6`
3. Adds `X-Robots-Tag: noindex, nofollow` to prevent indexing

### 2. Updated Sitemap
The sitemap only contains correct canonical URLs:
- ✅ `/job/india/6` is in sitemap
- ❌ `/job/main/6` is NOT in sitemap

## 🎯 Actions Required in Google Search Console

### Step 1: Request Removal of Wrong URL

1. Go to: https://search.google.com/search-console
2. Click **"Removals"** in left menu
3. Click **"New Request"**
4. Enter: `https://careerguidance.me/job/main/6`
5. Select: **"Remove this URL only"**
6. Click **"Next"** → **"Submit"**

### Step 2: Request Indexing of Correct URL

1. Click **"URL Inspection"** (top search bar)
2. Enter: `https://careerguidance.me/job/india/6`
3. Click **"Request Indexing"**
4. Wait for confirmation

### Step 3: Submit Updated Sitemap

1. Go to **"Sitemaps"** in left menu
2. Check if `sitemap.xml` is listed
3. If yes, click the 3 dots → **"Remove"**
4. Click **"Add a new sitemap"**
5. Enter: `sitemap.xml`
6. Click **"Submit"**

This tells Google:
- The sitemap has been updated
- `/job/india/6` is the canonical URL
- `/job/main/6` should not be indexed

## 🧪 Verification

### Test the redirect (after Vercel deployment):

```bash
# Test wrong-source URL redirects
curl -I https://careerguidance.me/job/main/6

# Should show:
# HTTP/2 301
# location: /job/india/6
# x-robots-tag: noindex, nofollow
```

### Test correct URL works:

```bash
# Test correct canonical URL
curl -I https://careerguidance.me/job/india/6

# Should show:
# HTTP/2 200
# content-type: text/html
# (no x-robots-tag = indexable)
```

### Check sitemap:

```bash
# Verify correct URL is in sitemap
grep "job/india/6" sitemap.xml
# Should find: <loc>https://careerguidance.me/job/india/6</loc>

# Verify wrong URL is NOT in sitemap
grep "job/main/6" sitemap.xml
# Should find nothing
```

## 📊 Expected Timeline

| Action | Timeline | Status |
|--------|----------|--------|
| Deploy fix | ✅ Done | Complete |
| Submit removal request | 🔄 Now | **Do this** |
| Submit sitemap | 🔄 Now | **Do this** |
| Request indexing | 🔄 Now | **Do this** |
| Google processes removal | 1-24 hours | Waiting |
| Google recrawls correct URL | 1-7 days | Waiting |
| Sitemap processed | 1-3 days | Waiting |
| "No referring sitemaps" resolved | 3-7 days | Waiting |

## 🎓 Why This Happened

1. **Empty main dataset:** The `data/jobs.json` file is empty (only 57 bytes)
2. **All jobs in India/TN:** All actual jobs are in `india_jobs.json` or `tn_jobs.json`
3. **Legacy redirect:** Old URL `/job/6` was redirecting to `/job/main/6` (due to search order)
4. **Google cached it:** Google found and indexed the wrong URL before we fixed it

## 🔧 Prevention

### For Future:
1. **Keep datasets populated:** Don't let `jobs.json` stay empty
2. **Regenerate sitemap regularly:** Run `python3 generate_sitemap.py` after scraping
3. **Monitor GSC weekly:** Check for "No referring sitemaps" issues
4. **Test redirects:** Use validation scripts after deployments

### Automated Check:
Add this to your deployment process:

```bash
#!/bin/bash
# Check for wrong-source URLs
echo "Testing job URL redirects..."

# Test a few known jobs
for id in 1 2 3 6; do
  # Try main source
  status=$(curl -s -o /dev/null -w "%{http_code}" https://careerguidance.me/job/main/$id)
  if [ "$status" = "301" ]; then
    echo "✅ /job/main/$id redirects correctly"
  elif [ "$status" = "200" ]; then
    echo "⚠️  /job/main/$id returns 200 (should redirect!)"
  fi
done
```

## 📋 Checklist

- [x] Added redirect logic for wrong-source URLs
- [x] Added noindex headers to redirects
- [x] Regenerated sitemap with correct URLs
- [x] Deployed fixes to Vercel
- [ ] Request removal of `/job/main/6` in GSC
- [ ] Request indexing of `/job/india/6` in GSC
- [ ] Submit updated sitemap in GSC
- [ ] Wait 1 week and verify in GSC
- [ ] Check "No referring sitemaps" is resolved

## 🆘 If Issue Persists

### After 1 week, if still showing "No referring sitemaps":

1. **Check sitemap status:**
   - GSC → Sitemaps
   - Verify `sitemap.xml` shows "Success"
   - Check "Discovered URLs" count

2. **Verify URL in sitemap:**
   ```bash
   curl https://careerguidance.me/sitemap.xml | grep "job/india/6"
   ```

3. **Force Google to recrawl:**
   - GSC → URL Inspection
   - Enter: `https://careerguidance.me/sitemap.xml`
   - Click "Request Indexing"

4. **Check for sitemap errors:**
   - GSC → Sitemaps
   - Click on `sitemap.xml`
   - Look for any errors or warnings

## 📞 Support Resources

- [Google Sitemap Guidelines](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Canonical URLs Best Practices](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [URL Inspection Tool Guide](https://support.google.com/webmasters/answer/9012289)

---

**Last Updated:** 2026-04-07  
**Status:** Fix deployed, awaiting GSC actions  
**Priority:** HIGH - Complete today
