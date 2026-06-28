import sys
import re
import argparse
from datetime import date
from urllib.parse import urlparse

import httpx

from config import OUTPUT_DIR, MAX_PAGES, MAX_DEPTH
from src.fetcher import fetch, NotHtmlError
from src.parser import parse
from src.crawler import crawl, Page
from src.logger import setup_logging, get_logger

log = get_logger(__name__)

_MAX_SLUG_LEN = 80


def normalize_url(url: str) -> str:
    """Ensure the URL has a scheme so httpx and urlparse behave correctly."""
    if not urlparse(url).scheme:
        return "https://" + url
    return url


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:_MAX_SLUG_LEN].strip("_")


def url_to_filename(url: str) -> str:
    parsed = urlparse(url)
    return f"{_slug(parsed.netloc + parsed.path)}_{date.today()}.md"


def crawl_filename(url: str) -> str:
    return f"{_slug(urlparse(url).netloc)}_crawl_{date.today()}.md"


def combine_pages(pages: list[Page], start_url: str) -> str:
    """Merge crawled pages into a single Markdown document with a table of contents."""
    lines = [f"# Crawl of {urlparse(start_url).netloc}", ""]
    lines.append(f"Source: {start_url}  ")
    lines.append(f"Pages: {len(pages)}  ")
    lines.append(f"Date: {date.today()}")
    lines.append("")
    lines.append("## Contents")
    lines.append("")
    for i, page in enumerate(pages, 1):
        lines.append(f"{i}. {page.url}")
    lines.append("")

    for i, page in enumerate(pages, 1):
        lines.append("\n---\n")
        lines.append(f"# [{i}] {page.url}")
        lines.append("")
        lines.append(page.content or "_(empty page)_")

    return "\n".join(lines) + "\n"


def run_single(url: str) -> int:
    try:
        html = fetch(url)
        content = parse(html)
    except NotHtmlError as exc:
        log.error("%s is not an HTML page (%s)", url, exc)
        return 1
    except httpx.HTTPStatusError as exc:
        log.error("HTTP %s for %s", exc.response.status_code, url)
        return 1
    except httpx.HTTPError as exc:
        log.error("Network error fetching %s: %s", url, exc)
        return 1
    except Exception:
        log.exception("Unexpected failure while processing %s", url)
        return 1

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = OUTPUT_DIR / url_to_filename(url)
    output_file.write_text(content, encoding="utf-8")
    log.info("Saved to %s", output_file)
    return 0


def run_crawl(url: str, max_pages: int, max_depth: int) -> int:
    pages = crawl(url, max_pages=max_pages, max_depth=max_depth)
    if not pages:
        log.error("No pages fetched — nothing to save")
        return 1

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_file = OUTPUT_DIR / crawl_filename(url)
    output_file.write_text(combine_pages(pages, url), encoding="utf-8")
    log.info("Saved %d page(s) to %s", len(pages), output_file)
    return 0


def main() -> int:
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Fetch a web page (or crawl a site) into clean Markdown for AI context."
    )
    parser.add_argument("url", help="URL to fetch (scheme optional, defaults to https)")
    parser.add_argument(
        "--crawl", action="store_true",
        help="Recursively follow same-domain links and save one combined file",
    )
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES,
                        help=f"Max pages to fetch when crawling (default {MAX_PAGES})")
    parser.add_argument("--max-depth", type=int, default=MAX_DEPTH,
                        help=f"Max link depth when crawling (default {MAX_DEPTH})")
    args = parser.parse_args()

    url = normalize_url(args.url)
    if args.crawl:
        return run_crawl(url, args.max_pages, args.max_depth)
    return run_single(url)


if __name__ == "__main__":
    sys.exit(main())
