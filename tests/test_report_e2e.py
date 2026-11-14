"""End-to-end check of the HTML report in a real browser (skipped if Playwright is not installed)."""
import pytest

from scholar_ingest.models import make_record
from scholar_ingest.report import render_html

sync_api = pytest.importorskip("playwright.sync_api")


def test_report_renders_in_browser(tmp_path):
    recs = [make_record("10.1/a", "<b>Alpha</b>", 2020, [], "openalex"), make_record("10.1/b", "Beta", 2021, [], "pubmed")]
    issues = [{"id": "10.1/a", "issue": "no_authors"}]
    page_file = tmp_path / "report.html"
    page_file.write_text(render_html(recs, issues, {"coverage": 0.5}), encoding="utf-8")
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # browser binary not installed
            pytest.skip(f"Chromium unavailable: {exc}")
        page = browser.new_page()
        page.goto(page_file.as_uri())
        assert page.inner_text("#count") == "2 publications"
        assert page.locator("#records tbody tr").count() == 2
        assert page.inner_text("#coverage").endswith("50.0%")
        assert "<b>Alpha</b>" in page.inner_text("#records")  # HTML in titles must be escaped, not rendered
        assert page.locator("li.issue").count() == 1
        browser.close()
