"""Command-line interface: argument parsing and the two run modes."""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

from page_miner import __version__
from page_miner.config import CRAWL_DELAY, MAX_DEPTH, MAX_PAGES, OUTPUT_DIR
from page_miner.crawler import crawl
from page_miner.fetcher import NotHtmlError, create_client, fetch
from page_miner.logging_setup import get_logger, setup_logging
from page_miner.output import combine_pages, crawl_filename, page_filename, save
from page_miner.parser import parse_page

log = get_logger(__name__)


def normalize_url(url: str) -> str:
    """Ensure the URL has a scheme so httpx and urlparse behave correctly."""
    if not urlparse(url).scheme:
        return "https://" + url
    return url


def run_single(url: str, output_dir: Path) -> int:
    """Fetch one page, convert it to Markdown, and save it. Returns an exit code."""
    try:
        with create_client() as client:
            result = fetch(client, url)
        content = parse_page(result.html).markdown
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

    save(content, output_dir, page_filename(url))
    return 0


def run_crawl(url: str, output_dir: Path, max_pages: int, max_depth: int, delay: float) -> int:
    """Crawl a site and save everything as one combined file. Returns an exit code."""
    pages = crawl(url, max_pages=max_pages, max_depth=max_depth, delay=delay)
    if not pages:
        log.error("No pages fetched — nothing to save")
        return 1

    save(combine_pages(pages, url), output_dir, crawl_filename(url))
    log.info("Crawled %d page(s)", len(pages))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="page-miner",
        description="Fetch a web page (or crawl a site) into clean Markdown for AI context.",
    )
    parser.add_argument("url", help="URL to fetch (scheme optional, defaults to https)")
    parser.add_argument(
        "--crawl", action="store_true",
        help="recursively follow same-domain links and save one combined file",
    )
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES,
                        help=f"max pages to fetch when crawling (default {MAX_PAGES})")
    parser.add_argument("--max-depth", type=int, default=MAX_DEPTH,
                        help=f"max link depth when crawling (default {MAX_DEPTH})")
    parser.add_argument("--delay", type=float, default=CRAWL_DELAY,
                        help=f"seconds between requests when crawling (default {CRAWL_DELAY})")
    parser.add_argument("-o", "--output-dir", type=Path, default=OUTPUT_DIR,
                        help=f"where to save results (default {OUTPUT_DIR}/)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="show DEBUG detail on the console too")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    setup_logging(verbose=args.verbose)

    url = normalize_url(args.url)
    if args.crawl:
        return run_crawl(url, args.output_dir, args.max_pages, args.max_depth, args.delay)
    return run_single(url, args.output_dir)


if __name__ == "__main__":
    sys.exit(main())
