"""Small, standard-library-only persistence helpers for Codex Brain."""
from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def atomic_write_text(path: Path, content: str) -> None:
    atomic_write_bytes(path, content.encode("utf-8"))


def acquire_file_lock(path: Path) -> int | None:
    """Kernel-held lock: released on process exit, with no time-based stealing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if os.name == "nt":
            import msvcrt
            # Windows locks a byte range; keep one byte in the persistent file.
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except OSError as exc:
        os.close(fd)
        if exc.errno in (11, 13, 35, 36):
            return None
        raise


def release_file_lock(fd: int | None) -> None:
    if fd is not None:
        # Do not unlink: another process may already have opened the same inode.
        os.close(fd)


@contextmanager
def exclusive_file_lock(path: Path):
    fd = acquire_file_lock(path)
    if fd is None:
        raise RuntimeError(f"Outra gravação está em andamento: {path}")
    try:
        yield
    finally:
        release_file_lock(fd)
