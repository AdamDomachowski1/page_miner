"""Backwards-compatible entry point — the real code lives in page_miner.cli.

Prefer `python -m page_miner` or the installed `page-miner` command.
"""

import sys

from page_miner.cli import main

if __name__ == "__main__":
    sys.exit(main())
