import time
from collections import deque
from dataclasses import dataclass

import httpx

from config import MAX_PAGES, MAX_DEPTH, CRAWL_DELAY
from src.fetcher import fetch, NotHtmlError
from src.parser import parse, extract_links
from src.logger import get_logger

log = get_logger(__name__)


@dataclass
class Page:
    url: str
    depth: int
    content: str


def crawl(
    start_url: str,
    max_pages: int = MAX_PAGES,
    max_depth: int = MAX_DEPTH,
    delay: float = CRAWL_DELAY,
) -> list[Page]:
    """Breadth-first crawl of same-domain pages starting from start_url.

    Follows internal links up to max_depth, fetching at most max_pages pages.
    A failure on a single page is logged and skipped — it does not abort the crawl.
    Returns the successfully fetched pages in visit order.
    """
    queue: deque[tuple[str, int]] = deque([(start_url.rstrip("/"), 0)])
    queued = {start_url.rstrip("/")}  # URLs ever added, to avoid re-queueing
    pages: list[Page] = []

    while queue and len(pages) < max_pages:
        url, depth = queue.popleft()
        log.info("[%d/%d] depth %d: %s", len(pages) + 1, max_pages, depth, url)

        try:
            html = fetch(url)
        except NotHtmlError as exc:
            log.warning("Skipping %s — %s", url, exc)
            continue
        except httpx.HTTPStatusError as exc:
            log.warning("Skipping %s — HTTP %s", url, exc.response.status_code)
            continue
        except httpx.HTTPError as exc:
            log.warning("Skipping %s — network error: %s", url, exc)
            continue

        content = parse(html)
        pages.append(Page(url=url, depth=depth, content=content))

        if depth < max_depth:
            for link in extract_links(html, url):
                if link not in queued:
                    queued.add(link)
                    queue.append((link, depth + 1))

        if delay and queue and len(pages) < max_pages:
            time.sleep(delay)

    log.info(
        "Crawl finished: %d page(s) fetched, %d still queued (limit %d)",
        len(pages),
        len(queue),
        max_pages,
    )
    return pages
