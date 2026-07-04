"""HTML → Markdown conversion and same-domain link extraction.

parse_page() is the single entry point: it builds one BeautifulSoup tree and
does both jobs on it, in the right order — links must be extracted *before*
cleaning, because cleaning removes <nav>/<header>/<footer>, which is exactly
where most internal links live.
"""

import os
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import markdownify
from bs4 import BeautifulSoup

from page_miner.logging_setup import get_logger

log = get_logger(__name__)

# Tags that never carry article content.
_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]

# Containers identified by id/class — cookie/consent banners and similar chrome.
_NOISE_ATTR_RE = re.compile(r"cookie|consent|gdpr|cmplz", re.I)

# Attributes that commonly hold the real (lazy-loaded) image URL.
_LAZY_SRC_ATTRS = ("data-src", "data-lazy-src", "data-original")

# Invisible characters that survive into Markdown (zero-width space/joiners, BOM).
_INVISIBLE_RE = re.compile("[\u200b\u200c\u200d\ufeff]")

# Lines that are pure page chrome once links/images are stripped: carousel
# arrows, stray separators.
_ARTIFACT_LINES = {"›", "‹", ";", "|"}

# File extensions that are not crawlable HTML pages (images, media, docs, assets).
_SKIP_EXT = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp", ".tiff",
    ".pdf", ".zip", ".gz", ".tar", ".rar", ".7z", ".dmg", ".exe",
    ".mp4", ".webm", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".ogg", ".flac",
    ".css", ".js", ".mjs", ".json", ".xml", ".rss", ".atom",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv",
}


@dataclass(frozen=True)
class ParsedPage:
    """The useful output of one HTML page."""

    markdown: str
    links: list[str] = field(default_factory=list)  # same-domain, deduplicated


def parse_page(html: str, base_url: str | None = None) -> ParsedPage:
    """Convert a page to Markdown and (optionally) collect its internal links.

    Pass base_url to also get same-domain links resolved against it; without
    it, links is empty. The HTML is parsed exactly once.
    """
    soup = BeautifulSoup(html, "lxml")

    # Order matters: _clean() decomposes nav/header/footer, so links must be
    # harvested from the intact tree first.
    links = _extract_links(soup, base_url) if base_url else []

    _clean(soup)
    _unwrap_layout_tables(soup)
    markdown = _to_markdown(soup)

    if not markdown:
        log.warning("Parsed content is empty — page may be JS-rendered or blocked")

    return ParsedPage(markdown=markdown, links=links)


def _extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Return de-duplicated, same-domain links found on the page.

    URLs are resolved against base_url, stripped of fragments and trailing
    slashes, and limited to http(s) links on the same host as base_url.
    Order of first appearance is preserved.
    """
    base_host = urlparse(base_url).netloc

    seen: dict[str, None] = {}  # dict as an ordered set
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"]).split("#")[0].rstrip("/")
        parsed = urlparse(href)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc != base_host:
            continue
        if os.path.splitext(parsed.path)[1].lower() in _SKIP_EXT:
            continue
        seen.setdefault(href, None)

    log.debug("Found %d same-domain link(s)", len(seen))
    return list(seen)


def _clean(soup: BeautifulSoup) -> None:
    """Remove noise tags, cookie/consent banners and base64 placeholder images in place."""
    removed = 0
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
        removed += 1

    for tag in soup.find_all(attrs={"class": _NOISE_ATTR_RE}) + soup.find_all(attrs={"id": _NOISE_ATTR_RE}):
        tag.decompose()
        removed += 1
    log.debug("Removed %d noise/banner element(s)", removed)

    # Replace base64 placeholder images with their real lazy-loaded URL, or drop them.
    swapped = dropped = 0
    for img in soup.find_all("img"):
        if not (img.get("src") or "").startswith("data:"):
            continue
        real = next((img.get(a) for a in _LAZY_SRC_ATTRS if img.get(a)), None)
        if real:
            img["src"] = real
            swapped += 1
        else:
            img.decompose()
            dropped += 1
    log.debug("Images: %d data-URI swapped to real src, %d dropped", swapped, dropped)


def _unwrap_layout_tables(soup: BeautifulSoup) -> None:
    """Flatten tables used for page layout (not data) into plain blocks.

    Old templates put whole articles inside <table> cells; markdownify would
    render those as one enormous, unreadable table row. A table counts as
    layout when it has no <th> and either at most two rows or a single column
    — real data tables have headers or a grid of rows and columns.
    """
    unwrapped = 0
    for table in soup.find_all("table"):
        if table.find("th"):
            continue
        rows = table.find_all("tr")
        single_column = all(len(tr.find_all(["td", "th"], recursive=False)) <= 1 for tr in rows)
        if len(rows) > 2 and not single_column:
            continue

        # Turn each cell into a block element, then dissolve the table markup.
        for cell in table.find_all("td"):
            cell.name = "div"
        for wrapper in table.find_all(["tr", "thead", "tbody", "tfoot"]):
            wrapper.unwrap()
        table.unwrap()
        unwrapped += 1
    log.debug("Unwrapped %d layout table(s)", unwrapped)


def _to_markdown(soup: BeautifulSoup) -> str:
    """Convert the main content of a cleaned tree to Markdown."""
    # Prefer semantic content containers; fall back to <body>, then the document.
    body = soup.find("main") or soup.find("article") or soup.body or soup
    log.debug("Content root: <%s>", getattr(body, "name", "document"))

    content = markdownify.markdownify(
        str(body), heading_style="ATX", strip=["a"]
    ).strip()
    content = _polish(content)
    log.info("Parsed content: %d characters", len(content))
    return content


def _polish(markdown: str) -> str:
    """Final text cleanup: invisible characters, artifact lines, excess blank lines."""
    markdown = _INVISIBLE_RE.sub("", markdown)
    lines = [line for line in markdown.split("\n") if line.strip() not in _ARTIFACT_LINES]
    markdown = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", markdown).strip()
