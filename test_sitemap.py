from app import app

with app.app_context():
    client = app.test_client()
    resp = client.get('/sitemap.xml')
    print(f"Status: {resp.status_code}")
    print(f"Headers: {resp.headers}")
    print(f"Content Length: {len(resp.data)}")
    print("Beginning of content:")
    print(resp.data[:500].decode('utf-8', errors='replace'))
    print("End of content:")
    print(resp.data[-500:].decode('utf-8', errors='replace'))
