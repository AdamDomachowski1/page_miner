"""HTTP layer: a shared keep-alive client and a fetch() that validates HTML.

The client is created once and reused across a whole crawl, so repeated
requests to the same host share a TCP/TLS connection instead of paying the
handshake cost per page.
"""

import time
from dataclasses import dataclass

import httpx

from page_miner.config import HEADERS, TIMEOUT
from page_miner.logging_setup import get_logger

log = get_logger(__name__)


class NotHtmlError(Exception):
    """Raised when a fetched resource is not an HTML document."""


@dataclass(frozen=True)
class FetchResult:
    """A successfully fetched HTML page.

    final_url may differ from the requested URL when redirects were followed —
    the crawler uses it to avoid fetching the same page twice under two names.
    """

    final_url: str
    html: str


def create_client() -> httpx.Client:
    """Build the shared HTTP client. Use as a context manager to close it."""
    return httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)


def fetch(client: httpx.Client, url: str) -> FetchResult:
    """Fetch the raw HTML of a page using the shared client.

    Raises httpx.HTTPError on a network/HTTP failure, or NotHtmlError if the
    response is not an HTML document (e.g. an image or PDF).
    """
    log.info("Requesting %s", url)
    start = time.perf_counter()

    response = client.get(url)

    elapsed = time.perf_counter() - start
    content_type = response.headers.get("content-type", "")
    log.debug(
        "Response %s in %.2fs (%d bytes, %s, final URL: %s)",
        response.status_code,
        elapsed,
        len(response.content),
        content_type or "no content-type",
        response.url,
    )

    response.raise_for_status()
    if "html" not in content_type.lower():
        raise NotHtmlError(f"Non-HTML content-type: {content_type or 'unknown'}")

    return FetchResult(final_url=str(response.url), html=response.text)
