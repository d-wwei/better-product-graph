"""Small re-entrant advisory file locks for local cross-process serialization."""

from __future__ import annotations

import fcntl
import os
import stat
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


_registry_guard = threading.Lock()
_process_locks: dict[str, threading.RLock] = {}
_held = threading.local()


def _process_lock(key: str) -> threading.RLock:
    with _registry_guard:
        return _process_locks.setdefault(key, threading.RLock())


@contextmanager
def exclusive_file_lock(path: Path, *, create: bool = True) -> Iterator[None]:
    """Serialize one resource; ``create=False`` is a strictly non-creating read lock."""

    resolved = (
        path.resolve(strict=False)
        if create
        else path.parent.resolve(strict=True) / path.name
    )
    key = str(resolved)
    local_lock = _process_lock(key)
    with local_lock:
        held: dict[str, tuple[object, int]] = getattr(_held, "locks", {})
        _held.locks = held
        existing = held.get(key)
        if existing is not None:
            handle, count = existing
            held[key] = (handle, count + 1)
            try:
                yield
            finally:
                held[key] = (handle, count)
            return
        if create:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            handle = resolved.open("a+b")
        else:
            descriptor = os.open(
                resolved,
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            )
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                os.close(descriptor)
                raise OSError(f"existing lock is not a regular file: {resolved}")
            handle = os.fdopen(descriptor, "rb")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            held[key] = (handle, 1)
            yield
        finally:
            held.pop(key, None)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
