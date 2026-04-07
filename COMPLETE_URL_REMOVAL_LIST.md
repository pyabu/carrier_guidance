# Complete URL Removal List for Google Search Console

## 🎯 All Legacy Job URLs to Remove

These old-format URLs redirect to canonical versions and should be removed from Google's index:

### Legacy URLs (Request Removal):
```
https://careerguidance.me/job/1
https://careerguidance.me/job/2
https://careerguidance.me/job/3
https://careerguidance.me/job/4
https://careerguidance.me/job/5
https://careerguidance.me/job/6
https://careerguidance.me/job/7
https://careerguidance.me/job/8
https://careerguidance.me/job/9
https://careerguidance.me/job/10
https://careerguidance.me/job/11
https://careerguidance.me/job/12
https://careerguidance.me/job/13
https://careerguidance.me/job/14
https://careerguidance.me/job/15
https://careerguidance.me/job/16
https://careerguidance.me/job/17
https://careerguidance.me/job/18
https://careerguidance.me/job/19
https://careerguidance.me/job/20
```

---

## 📝 Canonical URLs to Request Indexing

After removing the legacy URLs, request indexing for these canonical versions:

```
https://careerguidance.me/job/main/1
https://careerguidance.me/job/main/2
https://careerguidance.me/job/main/3
https://careerguidance.me/job/main/4
https://careerguidance.me/job/main/5
https://careerguidance.me/job/main/6
https://careerguidance.me/job/main/7
https://careerguidance.me/job/main/8
https://careerguidance.me/job/main/9
https://careerguidance.me/job/main/10
https://careerguidance.me/job/main/11
https://careerguidance.me/job/main/12
https://careerguidance.me/job/main/13
https://careerguidance.me/job/main/14
https://careerguidance.me/job/main/15
https://careerguidance.me/job/main/16
https://careerguidance.me/job/main/17
https://careerguidance.me/job/main/18
https://careerguidance.me/job/main/19
https://careerguidance.me/job/main/20
```

---

## 🚀 Quick Action Method

### Option 1: Bulk Removal (Fastest)

Instead of removing each URL individually, you can remove the entire pattern:

1. Go to: https://search.google.com/search-console
2. Click **"Removals"**
3. Click **"New Request"**
4. Enter: `https://careerguidance.me/job/`
5. Select: **"Remove all URLs with this prefix"**
6. Click **"Next"** → **"Submit"**

⚠️ **Warning:** This will remove ALL job URLs including the canonical ones temporarily!

**Better approach:** Remove only the legacy pattern by checking GSC first to see which ones are actually indexed.

---

### Option 2: Check Which Are Actually Indexed First

Before requesting removal, check which legacy URLs Google actually has indexed:

1. Go to Google Search Console
2. Click **"Pages"** → **"Why pages aren't indexed"**
3. Look for these issues:
   - "Duplicate without user-selected canonical"
   - "Duplicate, Google chose different canonical than user"
4. Click each issue to see the specific URLs
5. Only request removal for URLs that appear there

---

## 📋 Step-by-Step Process

### For Each Legacy URL Found in GSC:

1. **Request Removal:**
   - GSC → Removals → New Request
   - Enter: `https://careerguidance.me/job/[number]`
   - Select: "Remove this URL only"
   - Submit

2. **Request Indexing of Canonical:**
   - GSC → URL Inspection
   - Enter: `https://careerguidance.me/job/main/[number]`
   - Click: "Request Indexing"

---

## 🔍 Priority URLs (Known Issues)

Based on your Google Search Console report, these are confirmed problem URLs:

### HIGH PRIORITY (Confirmed in GSC):
```
https://careerguidance.me/job/2  → Remove & replace with /job/main/2
https://careerguidance.me/job/6  → Remove & replace with /job/main/6
```

### MEDIUM PRIORITY (Likely indexed):
Check GSC for these common ones:
```
https://careerguidance.me/job/1
https://careerguidance.me/job/3
https://careerguidance.me/job/4
https://careerguidance.me/job/5
https://careerguidance.me/job/10
```

### LOW PRIORITY (Check if indexed):
All others (7-9, 11-20) - only remove if they appear in GSC

---

## 🤖 Automated Approach

If you want to be thorough, you can use the Google Search Console API or manually check:

### Manual Check Method:
```
site:careerguidance.me/job/1
site:careerguidance.me/job/2
site:careerguidance.me/job/3
```

Search these in Google. If they appear in results, they need removal.

---

## ⏱️ Time Estimate

- **Manual removal (20 URLs):** ~30 minutes
- **Bulk removal (prefix):** ~2 minutes (but removes all job URLs temporarily)
- **Request indexing (20 URLs):** ~20 minutes

**Recommended:** Start with the 2 confirmed URLs (/job/2 and /job/6), then check GSC to see if others are actually indexed before spending time on all 20.

---

## 📊 Expected Results

### After 24 hours:
- Legacy URLs: Temporarily removed from search results
- Canonical URLs: Queued for crawling

### After 1 week:
- Legacy URLs: Permanently deindexed (due to noindex headers)
- Canonical URLs: Indexed and appearing in search

### After 2 weeks:
- GSC "Duplicate" issues: Reduced to 0
- GSC "Alternate page with proper canonical": May increase (good!)

---

## ✅ Verification Checklist

- [ ] Confirmed /job/2 and /job/6 are in GSC as problem URLs
- [ ] Requested removal for /job/2
- [ ] Requested removal for /job/6
- [ ] Requested indexing for /job/main/2
- [ ] Requested indexing for /job/main/6
- [ ] Checked GSC for other legacy URLs (1, 3, 4, 5, etc.)
- [ ] Requested removal for any others found
- [ ] Requested indexing for their canonical versions
- [ ] Set calendar reminder to check GSC in 1 week

---

## 🆘 If You Have Many URLs

If Google Search Console shows dozens of legacy URLs indexed:

### Use the Bulk Removal Tool:
1. GSC → Removals → New Request
2. Enter: `https://careerguidance.me/job/`
3. Select: "Temporarily hide all URLs with this prefix"
4. This removes ALL job URLs for 6 months
5. Then request indexing for all canonical URLs
6. Google will re-index only the canonical ones (with proper headers)

**Note:** This is safe because:
- Legacy URLs have noindex headers (won't be re-indexed)
- Canonical URLs are indexable (will be re-indexed)
- It's faster than removing 100+ URLs individually

---

**Last Updated:** 2026-04-07  
**Status:** Ready for action  
**Priority:** Start with /job/2 and /job/6, then expand based on GSC data
