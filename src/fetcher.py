import time

import httpx

from config import HEADERS, TIMEOUT
from src.logger import get_logger

log = get_logger(__name__)


class NotHtmlError(Exception):
    """Raised when a fetched resource is not an HTML document."""


def fetch(url: str) -> str:
    """Fetch the raw HTML of a page.

    Raises httpx.HTTPError on a network/HTTP failure, or NotHtmlError if the
    response is not an HTML document (e.g. an image or PDF).
    """
    log.info("Requesting %s", url)
    start = time.perf_counter()

    with httpx.Client(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
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
        return response.text
