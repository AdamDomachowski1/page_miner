# page_fetcher

Fetches a web page — or crawls a whole site — and saves the content as clean `.md`, ready to use as context for AI.

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

### Single page

```bash
.venv/bin/python main.py <url>
```

Saves one file to the `output/` folder:

```
output/github_com_anthropics_anthropic-sdk-python_2026-06-27.md
```

### Crawl a site

Recursively follows same-domain links and merges everything into **one** combined file:

```bash
.venv/bin/python main.py <url> --crawl
```

```
output/<domain>_crawl_2026-06-27.md
```

| Flag | Default | Description |
|---|---|---|
| `--crawl` | off | Enable recursive crawling instead of fetching a single page |
| `--max-pages N` | `60` | Hard cap on how many pages are fetched |
| `--max-depth N` | `3` | How deep to follow links (`0` = start page only) |

Example — crawl up to 200 pages, 2 levels deep:

```bash
.venv/bin/python main.py rumbomundo.com --crawl --max-pages 200 --max-depth 2
```

The combined file starts with a table of contents, then one section per page (`# [n] <url>`).

## How it works

1. `fetcher.py` — downloads the page HTML over HTTP
2. `parser.py` — strips noise and converts content to Markdown:
   - removes `script`, `style`, `nav`, `footer`, `header`, `aside`
   - removes cookie/consent banners (by `cookie`/`consent`/`gdpr`/`cmplz` id/class)
   - replaces base64 placeholder images with their real lazy-loaded URL (or drops them)
   - also exposes `extract_links()` for same-domain link discovery
3. `crawler.py` — breadth-first, same-domain crawl; a failed page is logged and skipped, never aborting the whole crawl
4. `main.py` — saves a single page, or a combined crawl file, to `output/`

A bare host without a scheme (e.g. `example.com`) is automatically upgraded to `https://`.

## Logging

Every run logs to two places:

- **Console** — concise `INFO`+ messages (what was fetched, parsed, saved, or what failed)
- **`logs/page_fetcher.log`** — full `DEBUG` detail: timestamps, module names, response codes, timings, byte counts. Rotates at ~1 MB, keeps 3 old files.

When something breaks, check the log file first — it records the failing URL, the error type (HTTP status, network/DNS, or unexpected), and full tracebacks for unexpected errors.

Adjust `LOG_LEVEL` and rotation settings in `config.py`.

## Configuration

Edit `config.py` to change defaults:

| Parameter | Default | Description |
|---|---|---|
| `TIMEOUT` | `15` | HTTP request timeout (seconds) |
| `HEADERS` | Mozilla UA | HTTP headers sent with the request |
| `OUTPUT_DIR` | `./output` | Output folder |
| `MAX_PAGES` | `60` | Default page cap for `--crawl` |
| `MAX_DEPTH` | `3` | Default link depth for `--crawl` |
| `CRAWL_DELAY` | `0.5` | Delay between requests when crawling (seconds) |
