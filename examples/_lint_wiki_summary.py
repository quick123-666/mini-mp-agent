"""Backward-compat thin wrapper. Real logic in scripts/wiki_lint.py."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.wiki_lint import main

if __name__ == "__main__":
    sys.exit(main())
