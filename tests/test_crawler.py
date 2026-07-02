"""Crawler tests with a fake HTTP layer — no network involved."""

import httpx
import pytest

from page_miner import crawler
from page_miner.fetcher import FetchResult, NotHtmlError

# A tiny three-page site: home links to /a and /b, /a links back home.
SITE = {
    "https://example.com": '<a href="/a">a</a> <a href="/b">b</a> <p>home</p>',
    "https://example.com/a": '<a href="/">home</a> <p>page a</p>',
    "https://example.com/b": "<p>page b</p>",
}


@pytest.fixture
def fake_site(monkeypatch):
    """Route fetch() to the in-memory SITE and disable the politeness delay."""
    requested: list[str] = []

    def fake_fetch(client, url):
        requested.append(url)
        if url not in SITE:
            request = httpx.Request("GET", url)
            raise httpx.HTTPStatusError(
                "404", request=request, response=httpx.Response(404, request=request)
            )
        return FetchResult(final_url=url, html=SITE[url])

    monkeypatch.setattr(crawler, "fetch", fake_fetch)
    return requested


def test_crawl_visits_each_page_once(fake_site):
    pages = crawler.crawl("https://example.com", delay=0)
    assert [p.url for p in pages] == [
        "https://example.com",
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert fake_site == [p.url for p in pages]  # no duplicate requests


def test_max_pages_caps_the_crawl(fake_site):
    pages = crawler.crawl("https://example.com", max_pages=2, delay=0)
    assert len(pages) == 2


def test_max_depth_zero_fetches_only_start_page(fake_site):
    pages = crawler.crawl("https://example.com", max_depth=0, delay=0)
    assert [p.url for p in pages] == ["https://example.com"]


def test_failed_page_is_skipped_not_fatal(monkeypatch):
    def fake_fetch(client, url):
        if url.endswith("/bad"):
            request = httpx.Request("GET", url)
            raise httpx.HTTPStatusError(
                "500", request=request, response=httpx.Response(500, request=request)
            )
        return FetchResult(final_url=url, html='<a href="/bad">x</a> <p>ok</p>')

    monkeypatch.setattr(crawler, "fetch", fake_fetch)
    pages = crawler.crawl("https://example.com", delay=0)
    assert [p.url for p in pages] == ["https://example.com"]


def test_redirect_alias_saved_once(monkeypatch):
    # Both queued URLs redirect to the same canonical page.
    def fake_fetch(client, url):
        return FetchResult(
            final_url="https://example.com/canonical",
            html='<a href="/other">x</a> <p>content</p>',
        )

    monkeypatch.setattr(crawler, "fetch", fake_fetch)
    pages = crawler.crawl("https://example.com", delay=0)
    assert [p.url for p in pages] == ["https://example.com/canonical"]


def test_identical_content_saved_once(monkeypatch):
    # /pl and /pl/lang are different URLs serving byte-identical pages.
    site = {
        "https://example.com": '<a href="/pl/lang">pl</a> <p>homepage</p>',
        "https://example.com/pl/lang": '<a href="/pl/lang">pl</a> <p>homepage</p>',
    }

    def fake_fetch(client, url):
        return FetchResult(final_url=url, html=site[url])

    monkeypatch.setattr(crawler, "fetch", fake_fetch)
    pages = crawler.crawl("https://example.com", delay=0)
    assert [p.url for p in pages] == ["https://example.com"]


def test_off_domain_redirect_is_skipped(monkeypatch):
    def fake_fetch(client, url):
        return FetchResult(final_url="https://elsewhere.com/page", html="<p>x</p>")

    monkeypatch.setattr(crawler, "fetch", fake_fetch)
    assert crawler.crawl("https://example.com", delay=0) == []


def test_non_html_page_is_skipped(monkeypatch):
    def fake_fetch(client, url):
        raise NotHtmlError("Non-HTML content-type: application/pdf")

    monkeypatch.setattr(crawler, "fetch", fake_fetch)
    assert crawler.crawl("https://example.com", delay=0) == []
