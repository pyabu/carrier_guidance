# Google Search Console - Required Actions

## 🎯 Immediate Actions Required

### Problem URLs Fixed:
1. ✅ `https://careerguidance.me/job/2` - Now redirects to `/job/main/2`
2. ✅ `https://careerguidance.me/job/6` - Now redirects to `/job/main/6`

---

## 📋 Step-by-Step Instructions

### Action 1: Remove Legacy URLs from Index

#### For /job/2:
1. Go to: https://search.google.com/search-console
2. Select property: **careerguidance.me**
3. Click **"Removals"** in the left sidebar
4. Click **"New Request"** button (top right)
5. Enter URL: `https://careerguidance.me/job/2`
6. Select: **"Remove this URL only"**
7. Click **"Next"**
8. Click **"Submit"**
9. ✅ Confirmation: "Removal request submitted"

#### For /job/6:
Repeat steps 4-9 with URL: `https://careerguidance.me/job/6`

**Expected Result:** Both URLs will be temporarily removed within 24 hours

---

### Action 2: Request Indexing of Canonical URLs

#### For /job/main/2:
1. In Google Search Console, click **"URL Inspection"** (top search bar or left menu)
2. Enter: `https://careerguidance.me/job/main/2`
3. Press Enter and wait for inspection to complete
4. Click **"Request Indexing"** button
5. Wait for confirmation (may take 1-2 minutes)
6. ✅ Confirmation: "Indexing requested"

#### For /job/main/6:
Repeat steps 2-5 with URL: `https://careerguidance.me/job/main/6`

**Expected Result:** Google will prioritize crawling these URLs within 1-7 days

---

### Action 3: Request Indexing for /api/saved-jobs Removal

Since we added noindex headers to this API endpoint:

1. Click **"URL Inspection"**
2. Enter: `https://careerguidance.me/api/saved-jobs`
3. Click **"Request Indexing"**
4. Google will recrawl and see the noindex header
5. The URL will be removed from index automatically

---

## 📊 Monitoring Progress

### Check After 24 Hours:

1. Go to **"Removals"** tab
   - Status should show: "Temporarily removed"
   - Duration: 6 months

2. Go to **"Pages"** → **"Why pages aren't indexed"**
   - Click **"Duplicate without user-selected canonical"**
   - The count should decrease from 2 to 0

### Check After 1 Week:

1. Go to **"URL Inspection"**
2. Test: `https://careerguidance.me/job/main/2`
3. Should show: **"URL is on Google"**
4. Repeat for `/job/main/6`

---

## 🔍 Validation Commands

Run these commands to verify the fixes are working:

```bash
# Test legacy URL redirects
curl -I https://careerguidance.me/job/2
# Should show: HTTP 301, location: /job/main/2

curl -I https://careerguidance.me/job/6
# Should show: HTTP 301, location: /job/main/6

# Test canonical URLs work
curl -I https://careerguidance.me/job/main/2
# Should show: HTTP 200

curl -I https://careerguidance.me/job/main/6
# Should show: HTTP 200

# Or run the validation script:
./validate_job_urls.sh
```

---

## 📈 Expected Timeline

| Action | Timeline | Status |
|--------|----------|--------|
| Deploy fixes | ✅ Complete | Done |
| Submit removal requests | 🔄 Now | **Do this now** |
| Request indexing | 🔄 Now | **Do this now** |
| Google processes removals | 1-24 hours | Waiting |
| Google recrawls canonical URLs | 1-7 days | Waiting |
| Index status updates | 1-2 weeks | Waiting |
| Verify in GSC | 2 weeks | Pending |

---

## ✅ Success Criteria

After 2 weeks, you should see:

1. **Removals Tab:**
   - `/job/2` - Status: "Temporarily removed"
   - `/job/6` - Status: "Temporarily removed"
   - `/api/saved-jobs` - Status: "Removed"

2. **Pages Tab:**
   - "Duplicate without user-selected canonical": **0 pages** (down from 2)
   - "Alternate page with proper canonical tag": May increase (this is good!)

3. **URL Inspection:**
   - `/job/main/2` - "URL is on Google" ✅
   - `/job/main/6` - "URL is on Google" ✅

---

## 🆘 Troubleshooting

### If removal request fails:
- Make sure you're logged into the correct Google account
- Verify you have owner/admin access to the property
- Try using "Temporarily hide" instead of "Remove"

### If canonical URLs don't get indexed:
- Wait 2 weeks (Google can be slow)
- Request indexing again
- Check if URLs return 200 status code
- Verify canonical tags are present in HTML

### If you see "Crawled - currently not indexed":
- This is normal for new URLs
- Wait 2-4 weeks
- Improve content quality if needed
- Add internal links to these pages

---

## 📞 Support

If issues persist after 2 weeks:
1. Check the validation script output
2. Review `INDEXING_ISSUES_ANALYSIS.md`
3. Review `FIX_LEGACY_JOB_URLS.md`
4. Post in Google Search Central Community

---

**Last Updated:** 2026-04-07  
**Status:** Fixes deployed, awaiting your action in GSC  
**Priority:** HIGH - Do this today for fastest results
