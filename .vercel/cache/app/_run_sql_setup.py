"""One-time script: create scraped_data table in Supabase via the Management API."""
import requests
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://yerecpvwemiuexucboee.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_eGUWBISpXTHlHQHO2LYhSA_E1bQB4ou")

# Step 1: Check if table already exists
print("Checking if scraped_data table exists...")
resp = requests.get(
    f"{SUPABASE_URL}/rest/v1/scraped_data?select=kind&limit=1",
    headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    },
)

if resp.status_code == 200:
    print("✅ scraped_data table already exists!")
    print(f"   Current rows: {resp.json()}")

    # Quick test: try upserting
    test = requests.post(
        f"{SUPABASE_URL}/rest/v1/scraped_data",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
        json={"kind": "_test", "data": {"test": True}},
    )
    if test.status_code in (200, 201):
        print("✅ Write access confirmed!")
        # Clean up test row
        requests.delete(
            f"{SUPABASE_URL}/rest/v1/scraped_data?kind=eq._test",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
        )
    else:
        print(f"⚠️  Write test failed ({test.status_code}): {test.text[:200]}")
        print("   You may need to adjust RLS policies in Supabase Dashboard.")
else:
    print(f"❌ Table does not exist (status {resp.status_code})")
    print(f"   Response: {resp.text[:300]}")
    print()
    print("=" * 60)
    print("Please create the table manually:")
    print("1. Open https://supabase.com/dashboard → your project")
    print("2. Go to SQL Editor → New Query")
    print("3. Paste and run this SQL:")
    print("=" * 60)
    with open("supabase_setup.sql") as f:
        print(f.read())
    print("=" * 60)
