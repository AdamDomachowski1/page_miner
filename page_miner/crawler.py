"""Breadth-first, same-domain crawler.

One shared HTTP client serves the whole crawl, each page's HTML is parsed
exactly once (Markdown + links in a single pass), and pages are deduplicated
twice over: by their *final* URL (redirect aliases aren't fetched twice) and
by a hash of their Markdown (two URLs serving identical content — e.g. a
language-switch link that just re-renders the homepage — are saved once).
A failure on a single page is logged and skipped — it never aborts the crawl.
"""

import hashlib
import time
from collections import deque
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from page_miner.config import CRAWL_DELAY, MAX_DEPTH, MAX_PAGES
from page_miner.fetcher import NotHtmlError, create_client, fetch
from page_miner.logging_setup import get_logger
from page_miner.parser import parse_page

log = get_logger(__name__)


@dataclass(frozen=True)
class Page:
    """One successfully crawled page."""

    url: str      # final URL (after redirects)
    depth: int    # 0 = start page
    content: str  # Markdown


def _canonical(url: str) -> str:
    """Normalize a URL for dedup: no fragment, no trailing slash."""
    return url.split("#")[0].rstrip("/")


def crawl(
    start_url: str,
    max_pages: int = MAX_PAGES,
    max_depth: int = MAX_DEPTH,
    delay: float = CRAWL_DELAY,
) -> list[Page]:
    """Breadth-first crawl of same-domain pages starting from start_url.

    Follows internal links up to max_depth, fetching at most max_pages pages,
    sleeping `delay` seconds between requests. Returns the successfully
    fetched pages in visit order.
    """
    start = _canonical(start_url)
    start_host = urlparse(start).netloc

    queue: deque[tuple[str, int]] = deque([(start, 0)])
    queued = {start}               # URLs ever enqueued, to avoid re-queueing
    visited: set[str] = set()      # final URLs already saved (catches redirect aliases)
    seen_content: set[str] = set() # Markdown hashes already saved (catches content aliases)
    pages: list[Page] = []

    with create_client() as client:
        while queue and len(pages) < max_pages:
            url, depth = queue.popleft()
            log.info("[%d/%d] depth %d: %s", len(pages) + 1, max_pages, depth, url)

            try:
                result = fetch(client, url)
            except NotHtmlError as exc:
                log.warning("Skipping %s — %s", url, exc)
                continue
            except httpx.HTTPStatusError as exc:
                log.warning("Skipping %s — HTTP %s", url, exc.response.status_code)
                continue
            except httpx.HTTPError as exc:
                log.warning("Skipping %s — network error: %s", url, exc)
                continue

            final_url = _canonical(result.final_url)
            if final_url in visited:
                log.debug("Skipping %s — redirects to already-saved %s", url, final_url)
                continue
            if urlparse(final_url).netloc != start_host:
                log.warning("Skipping %s — redirected off-domain to %s", url, final_url)
                continue
            visited.add(final_url)

            parsed = parse_page(result.html, base_url=final_url)

            # Content-hash dedup: different URLs can serve the same page.
            # Empty pages are exempt — two blank parses don't make them aliases.
            digest = hashlib.sha1(parsed.markdown.encode("utf-8")).hexdigest()
            if parsed.markdown and digest in seen_content:
                log.info("Skipping %s — identical content already saved", final_url)
                continue
            seen_content.add(digest)

            pages.append(Page(url=final_url, depth=depth, content=parsed.markdown))

            if depth < max_depth:
                for link in parsed.links:
                    if link not in queued:
                        queued.add(link)
                        queue.append((link, depth + 1))

            # Politeness pause — but not after the last request of the crawl.
            if delay and queue and len(pages) < max_pages:
                time.sleep(delay)

    log.info(
        "Crawl finished: %d page(s) fetched, %d still queued (limit %d)",
        len(pages),
        len(queue),
        max_pages,
    )
    return pages
