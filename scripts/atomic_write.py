"""Atomic file write with retry + per-file locking.

Phase 3 ship (2026-07-17 23:30).

Design (M-AtomicWrite-001 [imp=0.7]):
  1. write content to <path>.tmp.<rand8> (avoid partial file)
  2. acquire per-file lock via msvcrt.locking (Windows) / fcntl.flock (Unix)
  3. os.replace(tmp, final) — atomic on NTFS/ext4
  4. retry 5 times with backoff if lock contention

mp already has this in meta-planner file_lock.py (D-091); fork + adapt.
"""
from __future__ import annotations

import os
import random
import string
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Union

LOCK_RETRIES = 5
LOCK_BACKOFF_BASE_MS = 50
TMP_RAND_LEN = 8


def _tmp_path(target: Path) -> Path:
    """Generate <target>.tmp.<rand8>."""
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=TMP_RAND_LEN))
    suffix = target.suffix + f".tmp.{rand}"
    return target.with_name(target.name + suffix)


@contextmanager
def file_lock(target: Path, retries: int = LOCK_RETRIES):
    """Acquire per-file lock. Works on Windows (msvcrt) and Unix (fcntl).

    Yields inside lock; releases after block exits.
    Raises OSError if all retries fail.
    """
    lock_path = target.with_suffix(target.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.touch(exist_ok=True)

    if sys.platform == "win32":
        import msvcrt
        fd = None
        try:
            fd = open(lock_path, "r+b")
            for attempt in range(retries):
                try:
                    msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if attempt < retries - 1:
                        time.sleep((LOCK_BACKOFF_BASE_MS * (attempt + 1)) / 1000)
                    else:
                        raise
            yield
        finally:
            if fd is not None:
                try:
                    fd.seek(0)
                    msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
                fd.close()
    else:
        import fcntl
        fd = None
        try:
            fd = open(lock_path, "r+b")
            for attempt in range(retries):
                try:
                    fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if attempt < retries - 1:
                        time.sleep((LOCK_BACKOFF_BASE_MS * (attempt + 1)) / 1000)
                    else:
                        raise
            yield
        finally:
            if fd is not None:
                try:
                    fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
                fd.close()


def atomic_write(
    target: Union[str, Path],
    content: Union[str, bytes],
    retries: int = LOCK_RETRIES,
    encoding: str = "utf-8",
) -> Path:
    """Atomically write content to target. Returns Path on success.

    Raises OSError if all retries fail (lock contention).
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(content, str):
        content_bytes = content.encode(encoding)
    else:
        content_bytes = content

    tmp = _tmp_path(target)
    last_err = None

    for attempt in range(retries):
        try:
            with file_lock(target, retries=1):
                tmp.write_bytes(content_bytes)
                os.replace(tmp, target)
                return target
        except (OSError, IOError) as e:
            last_err = e
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if attempt < retries - 1:
                time.sleep((LOCK_BACKOFF_BASE_MS * (attempt + 1)) / 1000)

    raise OSError(f"atomic_write failed after {retries} retries: {last_err}")


def atomic_read(target: Union[str, Path], encoding: str = "utf-8") -> str:
    """Read file with shared lock (allows concurrent reads)."""
    target = Path(target)
    with file_lock(target):
        return target.read_text(encoding=encoding)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python -m mini_mp_agent.scripts.atomic_write <file> <content>")
        sys.exit(1)
    target = Path(sys.argv[1])
    content = sys.argv[2]
    print(f"Writing {len(content)} bytes to {target}")
    atomic_write(target, content)
    print(f"OK: read back = {atomic_read(target)!r}")
