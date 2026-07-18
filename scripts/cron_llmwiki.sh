#!/usr/bin/env bash
# cron_llmwiki.sh — single OpenClaw cron entry point.
#
# Run by OpenClaw cron every 3h. Wraps the four ingest sources:
#   - cron-full: scan all session JSONL files (mtime delta vs state)
#   - mem:       scan MEMORY.md for new paragraphs
#   - lint:      always (cheap, no LLM)
#
# This script is bash (not PowerShell) because OpenClaw cron on Windows ships
# Git Bash. Uses PYTHONPATH to find the mini-mp-agent repo.
#
# Crontab entry (OpenClaw cron add):
#   schedule: every 3h
#   command : bash /path/to/scripts/cron_llmwiki.sh
#
# Exit codes:
#   0 = OK
#   1 = ingest/lint failed (caller should retry)
#   2 = setup error (cron should alert)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
HOUR="$(date +%H)"

WIKI_ROOT="${REPO_ROOT}/llmwiki"

# Decide which ingest sources to run this cycle.
# 23:xx (23:00-23:59 local) gets the heavy "cron-full" pass to catch the
# day's full backlog; other hours use the lighter "auto" path which still
# processes new session files but without re-scanning everything.
SOURCES=("mem")
if [[ "${HOUR}" == "23" ]]; then
    SOURCES+=("cron-full")
fi

echo "[cron_llmwiki] repo=${REPO_ROOT} wiki=${WIKI_ROOT} hour=${HOUR} sources=${SOURCES[*]}"

for SRC in "${SOURCES[@]}"; do
    echo "--- ingest source: ${SRC} ---"
    if ! python "${REPO_ROOT}/scripts/wiki_ingest.py" \
            --wiki-root "${WIKI_ROOT}" \
            --source "${SRC}"; then
        echo "[cron_llmwiki] ingest ${SRC} failed" >&2
        exit 1
    fi
done

echo "--- lint ---"
if ! python "${REPO_ROOT}/scripts/wiki_lint.py" \
        --wiki-root "${WIKI_ROOT}" \
        --stale-days 90; then
    echo "[cron_llmwiki] lint failed" >&2
    exit 1
fi

echo "[cron_llmwiki] OK"
