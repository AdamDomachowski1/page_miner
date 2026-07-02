"""Central configuration — every tunable default lives here.

Paths are relative to the current working directory (not the package), so the
tool behaves the same whether run from a checkout or installed via pip.
"""

import logging
from pathlib import Path

# Where results and logs land, relative to where the tool is invoked.
OUTPUT_DIR = Path("output")
LOGS_DIR = Path("logs")

# HTTP
TIMEOUT = 15  # seconds per request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PageMiner/1.0)",
}

# Crawler defaults (overridable via CLI flags)
MAX_PAGES = 60     # hard cap on pages fetched per crawl
MAX_DEPTH = 3      # 0 = start page only, 1 = + its links, etc.
CRAWL_DELAY = 0.5  # seconds to wait between requests (politeness)

# Logging
LOG_LEVEL = logging.INFO           # console verbosity; the file always gets DEBUG
LOG_FILE = LOGS_DIR / "page_miner.log"
LOG_MAX_BYTES = 1_000_000          # rotate at ~1 MB
LOG_BACKUP_COUNT = 3               # keep 3 rotated files
