"""Backward-compat thin wrapper. The real logic moved to scripts/wiki_ingest.py.

Run as before:
  PYTHONPATH=. python examples/wiki_from_session.py --limit 5

For cron use, prefer scripts/cron_llmwiki.sh.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.wiki_ingest import main

if __name__ == "__main__":
    sys.exit(main())
