import os

os.environ.setdefault("VERCEL", "1")
os.environ["GEMINI_API_KEY"] = ""

from app import app  # noqa: E402


def _client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_robots_txt_allows_crawl_cleanup_and_exposes_sitemap():
    response = _client().get("/robots.txt")

    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "Sitemap: https://careerguidance.me/sitemap.xml" in text
    assert "\nDisallow: /api/\n" not in text
    assert "\nDisallow: /login\n" not in text
    assert "Disallow: /static/uploads/" in text


def test_filtered_jobs_page_is_noindex_with_clean_canonical():
    response = _client().get("/jobs?type=remote")

    assert response.status_code == 200
    assert response.headers["X-Robots-Tag"] == "noindex, follow, max-image-preview:large"
    html = response.get_data(as_text=True)
    assert '<link rel="canonical" href="https://careerguidance.me/jobs">' in html
    assert '<meta name="robots" content="noindex, follow, max-image-preview:large">' in html


def test_login_page_is_noindex():
    response = _client().get("/login")

    assert response.status_code == 200
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert '<meta name="robots" content="noindex, nofollow">' in response.get_data(as_text=True)


def test_legacy_job_urls_redirect_to_source_specific_canonicals():
    client = _client()

    india = client.get("/job/1?source=india", follow_redirects=False)
    tamilnadu = client.get("/job/1?source=tamilnadu", follow_redirects=False)

    assert india.status_code == 301
    assert india.headers["Location"].endswith("/job/india/1")
    assert tamilnadu.status_code == 301
    assert tamilnadu.headers["Location"].endswith("/job/tamilnadu/1")


def test_canonical_job_pages_are_source_specific():
    client = _client()

    india = client.get("/job/india/1")
    tamilnadu = client.get("/job/tamilnadu/1")

    assert india.status_code == 200
    assert tamilnadu.status_code == 200

    india_html = india.get_data(as_text=True)
    tamilnadu_html = tamilnadu.get_data(as_text=True)

    assert '<link rel="canonical" href="https://careerguidance.me/job/india/1">' in india_html
    assert '<link rel="canonical" href="https://careerguidance.me/job/tamilnadu/1">' in tamilnadu_html


def test_api_routes_return_x_robots_noindex_header():
    response = _client().get("/api/search?keyword=python")

    assert response.status_code == 200
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow, noarchive"


def test_sitemap_contains_only_canonical_job_urls():
    response = _client().get("/sitemap.xml")

    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "/job/india/1" in text
    assert "/job/tamilnadu/1" in text
    assert "?source=" not in text
    assert "/login" not in text
