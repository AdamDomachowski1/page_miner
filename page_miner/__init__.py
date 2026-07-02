"""page_miner — fetch a web page (or crawl a site) into clean Markdown.

Public API:
    fetch_page()  — grab and convert a single page
    crawl()       — breadth-first, same-domain crawl
"""

from page_miner.crawler import Page, crawl
from page_miner.fetcher import FetchResult, NotHtmlError, create_client, fetch
from page_miner.parser import ParsedPage, parse_page

__version__ = "1.0.0"

__all__ = [
    "Page",
    "crawl",
    "FetchResult",
    "NotHtmlError",
    "create_client",
    "fetch",
    "ParsedPage",
    "parse_page",
    "__version__",
]
