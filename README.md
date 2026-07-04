# ⛏️ page-miner

**Turn any website into clean Markdown — ready to paste into an AI context window.**

Fetch a single page or crawl a whole site: page-miner strips the noise (scripts, navigation, cookie banners, base64 placeholder images) and saves what's left as tidy `.md` files.

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐
│ fetcher │ →  │ parser  │ →  │ crawler │ →  │  output  │
│  HTTP   │    │ HTML→MD │    │   BFS   │    │ .md file │
└─────────┘    └─────────┘    └─────────┘    └──────────┘
```

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -e .

.venv/bin/page-miner example.com
```

That's it — the page lands in `output/example_com_<date>.md`. A bare host without a scheme is automatically upgraded to `https://`.

## Usage

### Single page

```bash
page-miner <url>
```

### Crawl a whole site

Recursively follows same-domain links (breadth-first) and merges everything into **one** combined file with a table of contents:

```bash
page-miner <url> --crawl
```

```
output/<domain>_crawl_<date>.md
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--crawl` | off | Recursively crawl instead of fetching a single page |
| `--max-pages N` | `60` | Hard cap on how many pages are fetched |
| `--max-depth N` | `3` | How deep to follow links (`0` = start page only) |
| `--delay S` | `0.5` | Politeness pause between requests (seconds) |
| `-o, --output-dir DIR` | `output/` | Where to save results |
| `-v, --verbose` | off | Show `DEBUG` detail on the console |
| `--version` | | Print the version and exit |

Example — crawl up to 200 pages, 2 levels deep:

```bash
page-miner rumbomundo.com --crawl --max-pages 200 --max-depth 2
```

> `python -m page_miner <url>` and `python main.py <url>` work too, if you prefer not to install the entry point.

## How it works

The package is a small pipeline, one module per responsibility:

| Module | Responsibility |
|---|---|
| `page_miner/fetcher.py` | HTTP: one shared keep-alive client, redirect tracking, HTML validation |
| `page_miner/parser.py` | One-pass HTML → Markdown conversion **and** same-domain link extraction |
| `page_miner/crawler.py` | Breadth-first crawl with depth/page caps and redirect deduplication |
| `page_miner/output.py` | Safe filenames, the combined crawl document, saving to disk |
| `page_miner/cli.py` | Argument parsing and the two run modes |
| `page_miner/config.py` | Every tunable default in one place |

Details worth knowing:

- **One HTTP client per crawl** — connections are kept alive, so a 60-page crawl doesn't pay 60 TLS handshakes.
- **One parse per page** — links are extracted and Markdown is generated from a single BeautifulSoup tree. Links are harvested *before* cleaning, because `<nav>`/`<header>`/`<footer>` (which cleaning removes) is where most internal links live.
- **Double dedup** — pages are keyed by their *final* URL (so `/page` and `/page/` redirecting to the same place are saved once; off-domain redirects are skipped) *and* by a hash of their content (so a language-switch URL that re-renders the homepage isn't saved twice).
- **Boilerplate stripping** — when combining a crawl, any Markdown block repeated verbatim on 3+ pages (menus, footers, contact boxes — common on sites without semantic `<nav>`/`<footer>` markup) is kept once on the first page and dropped everywhere else.
- **Layout tables flattened** — tables without headers used for page layout (old div-less templates) become plain paragraphs instead of one enormous Markdown table row; real data tables are preserved.
- **Noise removal** — drops `script`, `style`, `nav`, `footer`, `header`, `aside`, cookie/consent banners (matched by `cookie|consent|gdpr|cmplz` in id/class), swaps base64 placeholder images for their real lazy-loaded URL, and scrubs zero-width characters and carousel-arrow artifacts.
- **Resilient crawling** — a failed page (HTTP error, non-HTML, network hiccup) is logged and skipped; it never aborts the crawl.

## Configuration

Defaults live in [`page_miner/config.py`](page_miner/config.py):

| Parameter | Default | Description |
|---|---|---|
| `TIMEOUT` | `15` | HTTP request timeout (seconds) |
| `HEADERS` | Mozilla UA | HTTP headers sent with each request |
| `OUTPUT_DIR` | `./output` | Default output folder |
| `MAX_PAGES` | `60` | Default page cap for `--crawl` |
| `MAX_DEPTH` | `3` | Default link depth for `--crawl` |
| `CRAWL_DELAY` | `0.5` | Default delay between requests (seconds) |
| `LOG_LEVEL` | `INFO` | Console log level |

## Logging

Every run logs to two places:

- **Console** — concise `INFO`+ messages (add `-v` for full detail)
- **`logs/page_miner.log`** — always full `DEBUG`: timestamps, response codes, timings, byte counts. Rotates at ~1 MB, keeps 3 old files.

When something breaks, check the log file first — it records the failing URL, the error type, and full tracebacks for unexpected errors.

## Development

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
```

The test suite (`tests/`) covers parsing, link extraction, filenames, the combined document, and the crawler — all offline, with a faked HTTP layer.
