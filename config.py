import logging
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PageFetcher/1.0)"
}

# Crawler defaults
MAX_PAGES = 60       # hard cap on pages fetched per crawl
MAX_DEPTH = 3        # 0 = start page only, 1 = + its links, etc.
CRAWL_DELAY = 0.5    # seconds to wait between requests (politeness)

# Logging
LOG_LEVEL = logging.INFO
LOG_FILE = LOGS_DIR / "page_fetcher.log"
LOG_MAX_BYTES = 1_000_000  # rotate at ~1 MB
LOG_BACKUP_COUNT = 3       # keep 3 old log files
