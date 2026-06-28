import os
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import markdownify

from src.logger import get_logger

log = get_logger(__name__)

_NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]
# Containers identified by id/class — cookie/consent banners and similar chrome.
_NOISE_ATTR_RE = re.compile(r"cookie|consent|gdpr|cmplz", re.I)
# Attributes that commonly hold the real (lazy-loaded) image URL.
_LAZY_SRC_ATTRS = ("data-src", "data-lazy-src", "data-original")
# File extensions that are not crawlable HTML pages (images, media, docs, assets).
_SKIP_EXT = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp", ".tiff",
    ".pdf", ".zip", ".gz", ".tar", ".rar", ".7z", ".dmg", ".exe",
    ".mp4", ".webm", ".mov", ".avi", ".mkv", ".mp3", ".wav", ".ogg", ".flac",
    ".css", ".js", ".mjs", ".json", ".xml", ".rss", ".atom",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv",
}


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


def parse(html: str) -> str:
    """Strip noise from HTML and convert the main content to Markdown."""
    soup = BeautifulSoup(html, "lxml")
    _clean(soup)

    body = soup.find("main") or soup.find("article") or soup.body or soup
    log.debug("Content root: <%s>", getattr(body, "name", "document"))

    content = markdownify.markdownify(
        str(body), heading_style="ATX", strip=["a"]
    ).strip()
    log.info("Parsed content: %d characters", len(content))

    if not content:
        log.warning("Parsed content is empty — page may be JS-rendered or blocked")

    return content


def extract_links(html: str, base_url: str) -> list[str]:
    """Return de-duplicated, same-domain links found on the page.

    URLs are resolved against base_url, stripped of fragments and trailing
    slashes, and limited to http(s) links on the same host as base_url.
    Order of first appearance is preserved.
    """
    soup = BeautifulSoup(html, "lxml")
    base_host = urlparse(base_url).netloc

    seen: dict[str, None] = {}
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
