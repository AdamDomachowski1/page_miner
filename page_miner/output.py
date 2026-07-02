"""Output layer: filenames, the combined crawl document, and saving to disk."""

import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from page_miner.crawler import Page
from page_miner.logging_setup import get_logger

log = get_logger(__name__)

_MAX_SLUG_LEN = 80


def _slug(text: str) -> str:
    """Turn arbitrary text into a safe, bounded filename fragment."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")[:_MAX_SLUG_LEN].strip("_")


def page_filename(url: str) -> str:
    """Filename for a single fetched page: host + path + today's date."""
    parsed = urlparse(url)
    return f"{_slug(parsed.netloc + parsed.path)}_{date.today()}.md"


def crawl_filename(url: str) -> str:
    """Filename for a combined crawl file: host + today's date."""
    return f"{_slug(urlparse(url).netloc)}_crawl_{date.today()}.md"


# Boilerplate detection: a Markdown block repeated verbatim on at least this
# many pages is considered site chrome (menu, footer, contact box). The count
# is per page (not per occurrence), so a block quoted twice on one article
# doesn't qualify. Kept low on purpose: multilingual sites repeat each
# language's menu only on that language's subset of pages.
_BOILERPLATE_MIN_PAGES = 3


def _strip_boilerplate(pages: list[Page]) -> list[str]:
    """Return each page's Markdown with cross-page boilerplate removed.

    Sites without semantic <nav>/<footer> markup repeat their menu and footer
    in the extracted content of every page. Any block (blank-line-separated
    chunk) that appears on _BOILERPLATE_MIN_PAGES+ pages is kept only on the
    first page — so the information survives once — and dropped everywhere else.
    """
    if len(pages) < _BOILERPLATE_MIN_PAGES:
        return [p.content for p in pages]

    page_blocks = [p.content.split("\n\n") for p in pages]

    # Count on how many pages each distinct block appears (not occurrences).
    counts: Counter[str] = Counter()
    for blocks in page_blocks:
        counts.update({b.strip() for b in blocks if b.strip()})

    boilerplate = {block for block, n in counts.items() if n >= _BOILERPLATE_MIN_PAGES}
    if not boilerplate:
        return [p.content for p in pages]

    # First page keeps everything; the rest lose the repeated blocks.
    stripped = [pages[0].content]
    removed_chars = 0
    for blocks in page_blocks[1:]:
        kept = [b for b in blocks if b.strip() not in boilerplate]
        removed_chars += sum(len(b) for b in blocks if b.strip() in boilerplate)
        stripped.append("\n\n".join(kept).strip())

    log.info(
        "Boilerplate: %d repeated block(s) removed from %d page(s) (%d chars saved)",
        len(boilerplate), len(pages) - 1, removed_chars,
    )
    return stripped


def combine_pages(pages: list[Page], start_url: str) -> str:
    """Merge crawled pages into one Markdown document with a table of contents.

    Blocks repeated across most pages (menus, footers) are kept only on the
    first page — see _strip_boilerplate().
    """
    contents = _strip_boilerplate(pages)

    lines = [
        f"# Crawl of {urlparse(start_url).netloc}",
        "",
        f"Source: {start_url}  ",
        f"Pages: {len(pages)}  ",
        f"Date: {date.today()}",
        "",
        "## Contents",
        "",
    ]
    for i, page in enumerate(pages, 1):
        lines.append(f"{i}. {page.url}")
    lines.append("")

    for i, (page, content) in enumerate(zip(pages, contents), 1):
        lines.append("\n---\n")
        lines.append(f"# [{i}] {page.url}")
        lines.append("")
        lines.append(content or "_(empty page)_")

    return "\n".join(lines) + "\n"


def save(content: str, directory: Path, filename: str) -> Path:
    """Write content into directory/filename (creating the directory) and return the path."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    log.info("Saved to %s", path)
    return path
