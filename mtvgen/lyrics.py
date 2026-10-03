"""Multi-tier lyric retrieval: embedded tags → online (Kugou/NetEase/LRCLIB) → Vocal Separation + Forced Alignment."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

from .aligner import align_lyrics
from .models import LyricLine, LyricWord
from .providers import fetch_kugou_lyrics, fetch_netease_lyrics
from .separator import separate_vocals

logger = logging.getLogger(__name__)

# Matches a leading line tag like [01:23.45], [01:23:45] or [01:23]
_LRC_TAG_RE = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]\s*")
# Matches enhanced LRC word timestamps like <01:23.45>
_LRC_WORD_RE = re.compile(r"<(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?>")


def _lrc_timestamp_to_seconds(minutes: str, seconds: str, centis: Optional[str]) -> float:
    """Convert LRC timestamp components to seconds."""
    m = int(minutes)
    s = int(seconds)
    frac = int(centis) / (10 ** len(centis)) if centis else 0.0
    return m * 60.0 + s + frac


def parse_lrc(lrc_content: str) -> list[LyricLine]:
    """Parse an LRC string into a list of LyricLine objects."""
    lines: list[LyricLine] = []

    for raw_line in lrc_content.strip().splitlines():
        raw_line = raw_line.strip()

        stamps: list[float] = []
        pos = 0
        while True:
            tag = _LRC_TAG_RE.match(raw_line, pos)
            if not tag:
                break
            stamps.append(_lrc_timestamp_to_seconds(*tag.groups()))
            pos = tag.end()
        if not stamps:
            continue

        start = stamps[0]
        text = raw_line[pos:].strip()

        if not text:
            continue

        word_matches = list(_LRC_WORD_RE.finditer(text))
        words: Optional[list[LyricWord]] = None

        if word_matches:
            clean_text_parts = []
            words = []
            segments = _LRC_WORD_RE.split(text)
            idx = 0
            while idx < len(segments):
                word_text = segments[idx].strip()
                if word_text:
                    clean_text_parts.append(word_text)
                    if idx == 0:
                        word_start = start
                    else:
                        word_start = _lrc_timestamp_to_seconds(
                            segments[idx - 3], segments[idx - 2], segments[idx - 1]
                        )
                    if idx + 3 < len(segments):
                        word_end = _lrc_timestamp_to_seconds(
                            segments[idx + 1], segments[idx + 2], segments[idx + 3]
                        )
                    else:
                        word_end = word_start + 1.0
                    words.append(LyricWord(word=word_text, start=word_start, end=word_end))
                idx += 4

            text = " ".join(clean_text_parts)

        lines.append(LyricLine(text=text, start=start, end=0.0, words=words))
        for extra in stamps[1:]:
            lines.append(LyricLine(text=text, start=extra, end=0.0, words=None))

    lines.sort(key=lambda l: l.start)

    for i in range(len(lines)):
        if i + 1 < len(lines):
            lines[i].end = lines[i + 1].start
        else:
            lines[i].end = lines[i].start + 5.0

        if lines[i].words and lines[i].words[-1].end > lines[i].end:
            lines[i].words[-1].end = lines[i].end

    return lines


def _query_variants(title: str, artist: str) -> list[str]:
    variants: list[str] = []
    for q in (f"{title} {artist}", title, f"{artist} {title}"):
        q = q.strip()
        if q and q not in variants:
            variants.append(q)
    return variants


def fetch_online_lyrics(title: str, artist: str) -> Optional[str]:
    try:
        import syncedlyrics
    except ImportError:
        logger.warning("syncedlyrics not installed, skipping aggregator")
        return None

    for search_term in _query_variants(title, artist):
        logger.info(f"Searching online for synced lyrics: '{search_term}'")
        for attempt, enhanced in enumerate((True, False)):
            try:
                lrc = syncedlyrics.search(search_term, enhanced=enhanced)
            except Exception as e:
                logger.warning(f"Online lyrics search failed ({search_term!r}): {e}")
                time.sleep(0.5)
                continue
            if lrc and parse_lrc(lrc):
                logger.info(f"Found synced lyrics online ({len(lrc)} chars)")
                return lrc
            time.sleep(0.3)

    return None


_CACHE_DIR = Path.home() / ".cache" / "mtvgen" / "lyrics"


def _cache_path(title: str, artist: str, duration: Optional[float]) -> Path:
    key = f"{title}|{artist}|{int(duration or 0)}".encode("utf-8")
    return _CACHE_DIR / f"{hashlib.sha1(key).hexdigest()}.lrc"


def _read_cache(title: str, artist: str, duration: Optional[float]) -> Optional[str]:
    path = _cache_path(title, artist, duration)
    try:
        return path.read_text(encoding="utf-8") if path.exists() else None
    except OSError:
        return None


def _write_cache(title: str, artist: str, duration: Optional[float], lrc: str) -> None:
    try:
        path = _cache_path(title, artist, duration)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(lrc, encoding="utf-8")
    except OSError as e:
        logger.debug(f"Could not write lyric cache: {e}")


def extract_lyrics(
    mp3_path: str | Path,
    lrc_path: Optional[str | Path] = None,
    separate_vocals_first: bool = False,
) -> list[LyricLine]:
    """Extract synchronized lyrics using a multi-tier strategy:

    Tier 0: User-provided LRC file
    Tier 1: Embedded SYLT lyrics in MP3 tags
    Tier 2: Online providers (Kugou -> NetEase -> LRCLIB/syncedlyrics -> Cache)
    Tier 3: Plain text + Demucs Vocal Separation + PyTorch Forced Alignment
    """
    from .metadata import get_metadata, get_embedded_lyrics

    mp3_path = Path(mp3_path)

    # Tier 0: User-provided LRC file
    if lrc_path:
        lrc_path = Path(lrc_path)
        logger.info(f"Using provided LRC file: {lrc_path}")
        lrc_content = lrc_path.read_text(encoding="utf-8")
        lines = parse_lrc(lrc_content)
        if lines:
            logger.info(f"✓ Parsed {len(lines)} lines from provided LRC file")
            return lines
        else:
            # If provided file was plain text without timestamps, perform forced alignment on it!
            logger.info("Provided file has no timestamps; proceeding with forced alignment...")
            plain_text_lines = [l.strip() for l in lrc_content.splitlines() if l.strip()]
            vocal_track = separate_vocals(mp3_path) if separate_vocals_first else None
            aligned = align_lyrics(mp3_path, plain_text_lines, vocals_path=vocal_track)
            if aligned:
                return aligned

    meta = get_metadata(mp3_path)
    title = meta["title"]
    artist = meta["artist"]
    duration = meta["duration"]

    # Tier 1: Embedded synced lyrics
    logger.info("Tier 1: Checking embedded lyrics in MP3 tags...")
    embedded = get_embedded_lyrics(mp3_path)
    plain_embedded_text: Optional[str] = None
    if embedded:
        if "synced" in embedded:
            logger.info("✓ Found embedded synced lyrics (SYLT)")
            return embedded["synced"]
        if "unsynced" in embedded:
            plain_embedded_text = embedded["unsynced"]
            logger.info("Found embedded plain text lyrics (USLT)")

    # Tier 2: Disk cache check
    cached = _read_cache(title, artist, duration)
    if cached:
        lines = parse_lrc(cached)
        if lines:
            logger.info(f"✓ Using cached lyrics: {len(lines)} lines")
            return lines

    # Tier 2: Online providers check
    logger.info("Tier 2: Searching online synced lyric providers...")

    # Provider A: Kugou Music
    kugou_lrc = fetch_kugou_lyrics(title, artist, duration)
    if kugou_lrc:
        lines = parse_lrc(kugou_lrc)
        if lines:
            _write_cache(title, artist, duration, kugou_lrc)
            return lines

    # Provider B: NetEase Cloud Music
    netease_lrc = fetch_netease_lyrics(title, artist)
    if netease_lrc:
        lines = parse_lrc(netease_lrc)
        if lines:
            _write_cache(title, artist, duration, netease_lrc)
            return lines

    # Provider C: Syncedlyrics Aggregator (LRCLIB, Musixmatch, Megalobiz, Genius)
    agg_lrc = fetch_online_lyrics(title, artist)
    if agg_lrc:
        lines = parse_lrc(agg_lrc)
        if lines:
            _write_cache(title, artist, duration, agg_lrc)
            return lines

    # Tier 3: Plain text + Vocal Separation + Forced Alignment
    logger.info("Tier 3: No synced lyrics found online. Searching plain text lyrics for alignment...")

    plain_lines: list[str] = []
    if plain_embedded_text:
        plain_lines = [line.strip() for line in plain_embedded_text.splitlines() if line.strip()]

    if plain_lines:
        logger.info(f"Found {len(plain_lines)} plain text lyric lines to align.")
        vocal_track = separate_vocals(mp3_path)
        aligned = align_lyrics(mp3_path, plain_lines, vocals_path=vocal_track)
        if aligned:
            return aligned

    logger.warning("No lyrics could be extracted or aligned from any source")
    return []
