"""Small re-entrant advisory file locks for local cross-process serialization."""

from __future__ import annotations

import fcntl
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
def exclusive_file_lock(path: Path) -> Iterator[None]:
    """Serialize one resource across threads and processes; nested calls are safe."""

    resolved = path.resolve(strict=False)
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
        resolved.parent.mkdir(parents=True, exist_ok=True)
        handle = resolved.open("a+b")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            held[key] = (handle, 1)
            yield
        finally:
            held.pop(key, None)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
