#!/usr/bin/env python3
"""
Shared utility functions for the Strict Translation Engine.
Provides atomic I/O, JSON helpers, logging, file locking, and
Dichtrung-specific path resolution.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

# ─── Dichtrung Mono-repo Constants ──────────────────────────────────────────

DICHTRUNG_ROOT = Path(r"D:\Dichtrung")
SOURCE_SPLIT_DIR = DICHTRUNG_ROOT / "Source" / "Source split"
OUTPUT_DIR = DICHTRUNG_ROOT / "Output"
GLOBAL_STATE_DIR = DICHTRUNG_ROOT / "Global State"

# Chapter filename patterns used in Dichtrung
# Source: "0001 - 第1章 一切的开始.md"
SOURCE_CHAPTER_RE = re.compile(r"^(\d{4})\s*-\s*(.+)\.md$")
# Output: "Chương 0001 - Sự khởi đầu của tất cả.md"
OUTPUT_CHAPTER_RE = re.compile(r"^Chương\s+(\d{4})\s*-\s*(.+)\.md$")


# ─── Time Helpers ───────────────────────────────────────────────────────────

def now_iso() -> str:
    """Return current time in ISO 8601 format with timezone."""
    return datetime.now().astimezone().isoformat()


# ─── Directory Helpers ──────────────────────────────────────────────────────

def ensure_dir(path: str | Path) -> Path:
    """Create directory (and parents) if it doesn't exist."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ─── Text I/O ───────────────────────────────────────────────────────────────

def read_text(path: str | Path, encoding: str = "utf-8") -> str:
    """Read entire file as text."""
    return Path(path).read_text(encoding=encoding)


def write_text_atomic(path: str | Path, text: str, encoding: str = "utf-8") -> None:
    """Write text to file atomically (write tmp then rename)."""
    target = Path(path)
    ensure_dir(target.parent)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, encoding=encoding,
        dir=str(target.parent), suffix=".tmp"
    ) as tmp:
        tmp.write(text)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, target)


# ─── JSON I/O ───────────────────────────────────────────────────────────────

def load_json(path: str | Path, default: Any = None) -> Any:
    """Load JSON from file, returning default if file doesn't exist."""
    p = Path(path)
    if not p.exists():
        return default
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json_atomic(path: str | Path, payload: Any) -> None:
    """Write JSON to file atomically with pretty-print."""
    write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2))


# ─── Hash ───────────────────────────────────────────────────────────────────

def sha256_text(text: str) -> str:
    """Return SHA-256 hex digest of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ─── Logging ────────────────────────────────────────────────────────────────

def get_logger(
    name: str,
    log_file: str | Path | None = None,
    level: int = logging.INFO
) -> logging.Logger:
    """Create or retrieve a named logger with stream and optional file handler."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file:
        log_path = Path(log_file)
        ensure_dir(log_path.parent)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# ─── File Locking ───────────────────────────────────────────────────────────

@contextmanager
def file_lock(
    lock_path: str | Path,
    timeout: float = 30.0,
    poll_interval: float = 0.2
) -> Iterator[None]:
    """Simple file-based lock using exclusive creation."""
    path = Path(lock_path)
    ensure_dir(path.parent)
    start = time.time()
    fd: int | None = None

    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("utf-8"))
            break
        except FileExistsError:
            if time.time() - start >= timeout:
                raise TimeoutError(f"Could not acquire lock: {path}")
            time.sleep(poll_interval)

    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


# ─── Collection Helpers ─────────────────────────────────────────────────────

def unique_by_key(items: list[dict], key: str) -> tuple[bool, list[str]]:
    """Check uniqueness of a key across a list of dicts.
    Returns (is_unique, list_of_duplicates)."""
    seen: set[str] = set()
    dupes: list[str] = []
    for item in items:
        value = str(item.get(key, "")).strip()
        if not value:
            continue
        if value in seen:
            dupes.append(value)
        seen.add(value)
    return len(dupes) == 0, dupes


# ─── Dichtrung Path Resolution ─────────────────────────────────────────────

def resolve_branch_dir(branch_name: str) -> Path:
    """Resolve a project branch directory under Output/."""
    return OUTPUT_DIR / branch_name


def resolve_source_dir(branch_name: str) -> Path:
    """Resolve source split directory for a branch.
    Falls back to branch_name if no source_ref in config."""
    branch_dir = resolve_branch_dir(branch_name)
    config = load_json(branch_dir / "translation_config.json")
    if config and config.get("source_ref", {}).get("split"):
        rel = config["source_ref"]["split"]
        return DICHTRUNG_ROOT / rel
    return SOURCE_SPLIT_DIR / branch_name


def list_source_chapters(branch_name: str) -> list[Path]:
    """List sorted source chapter files for a branch."""
    source_dir = resolve_source_dir(branch_name)
    return sorted(source_dir.glob("*.md"))


def get_source_chapter_path(branch_name: str, chapter: int) -> Path | None:
    """Get the source chapter file for a specific chapter number.
    Source files use format: '0001 - 第1章 xxx.md'"""
    source_dir = resolve_source_dir(branch_name)
    prefix = f"{chapter:04d}"
    for f in source_dir.iterdir():
        if f.name.startswith(prefix) and f.suffix == ".md":
            return f
    return None


def get_output_chapter_path(branch_name: str, chapter: int, title: str = "") -> Path:
    """Build output chapter file path.
    Output format: 'Chương 0001 - Title.md'"""
    branch_dir = resolve_branch_dir(branch_name)
    if title:
        filename = f"Chương {chapter:04d} - {title}.md"
    else:
        filename = f"Chương {chapter:04d}.md"
    return branch_dir / "output" / filename


def chapter_number_from_source(filename: str) -> int | None:
    """Extract chapter number from source filename like '0123 - ...'"""
    m = SOURCE_CHAPTER_RE.match(filename)
    return int(m.group(1)) if m else None


def chapter_number_from_output(filename: str) -> int | None:
    """Extract chapter number from output filename like 'Chương 0123 - ...'"""
    m = OUTPUT_CHAPTER_RE.match(filename)
    return int(m.group(1)) if m else None


def list_branches() -> list[str]:
    """List all project branch names under Output/."""
    if not OUTPUT_DIR.exists():
        return []
    return sorted([
        d.name for d in OUTPUT_DIR.iterdir()
        if d.is_dir() and (d / "translation_config.json").exists()
    ])
