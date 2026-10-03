"""Multi-tier lyric retrieval: embedded tags → online (LRCLIB) → Whisper transcription."""

from __future__ import annotations

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Optional

from .models import LyricLine, LyricWord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LRC Parsing
# ---------------------------------------------------------------------------

# Matches a leading line tag like [01:23.45], [01:23:45] or [01:23]
_LRC_TAG_RE = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]\s*")
# Matches enhanced LRC word timestamps like <01:23.45>
_LRC_WORD_RE = re.compile(r"<(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?>")


def _lrc_timestamp_to_seconds(minutes: str, seconds: str, centis: Optional[str]) -> float:
    """Convert LRC timestamp components to seconds."""
    m = int(minutes)
    s = int(seconds)
    # Fractional part may be absent, or 1-3 digits (tenths/centiseconds/milliseconds)
    frac = int(centis) / (10 ** len(centis)) if centis else 0.0
    return m * 60.0 + s + frac


def parse_lrc(lrc_content: str) -> list[LyricLine]:
    """Parse an LRC string into a list of LyricLine objects.

    Supports both standard LRC (line-level timestamps) and enhanced LRC
    (word-level timestamps with <mm:ss.xx> inline tags).
    """
    lines: list[LyricLine] = []

    for raw_line in lrc_content.strip().splitlines():
        raw_line = raw_line.strip()

        # Collect every leading timestamp (a line may repeat, e.g. [00:10.00][01:20.00]text)
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

        # Check for enhanced LRC word-level timestamps
        word_matches = list(_LRC_WORD_RE.finditer(text))
        words: Optional[list[LyricWord]] = None

        if word_matches:
            # Enhanced LRC: extract word timestamps
            clean_text_parts = []
            words = []
            # Split text by word timestamp markers
            segments = _LRC_WORD_RE.split(text)
            # segments alternates: text, min, sec, centi, text, min, sec, centi, ...
            idx = 0
            while idx < len(segments):
                word_text = segments[idx].strip()
                if word_text:
                    clean_text_parts.append(word_text)
                    # Determine this word's start time
                    if idx == 0:
                        word_start = start
                    else:
                        # Previous group: idx-3=min, idx-2=sec, idx-1=centi
                        word_start = _lrc_timestamp_to_seconds(
                            segments[idx - 3], segments[idx - 2], segments[idx - 1]
                        )
                    # Determine end time: next timestamp or line end
                    if idx + 3 < len(segments):
                        word_end = _lrc_timestamp_to_seconds(
                            segments[idx + 1], segments[idx + 2], segments[idx + 3]
                        )
                    else:
                        word_end = word_start + 1.0  # Placeholder; fixed below
                    words.append(LyricWord(word=word_text, start=word_start, end=word_end))
                idx += 4

            text = " ".join(clean_text_parts)

        lines.append(LyricLine(text=text, start=start, end=0.0, words=words))
        # Repeated timestamps: word timings are absolute, so extra copies are line-level only
        for extra in stamps[1:]:
            lines.append(LyricLine(text=text, start=extra, end=0.0, words=None))

    lines.sort(key=lambda l: l.start)

    # Fix end times: each line ends when the next begins (or + 5s for last)
    for i in range(len(lines)):
        if i + 1 < len(lines):
            lines[i].end = lines[i + 1].start
        else:
            lines[i].end = lines[i].start + 5.0

        # Fix last word end time to match line end
        if lines[i].words and lines[i].words[-1].end > lines[i].end:
            lines[i].words[-1].end = lines[i].end

    return lines


# ---------------------------------------------------------------------------
# Online Lyric Fetching
# ---------------------------------------------------------------------------

def _query_variants(title: str, artist: str) -> list[str]:
    """Search strings to try, most specific first, without duplicates."""
    variants: list[str] = []
    for q in (f"{title} {artist}", title, f"{artist} {title}"):
        q = q.strip()
        if q and q not in variants:
            variants.append(q)
    return variants


def fetch_online_lyrics(title: str, artist: str) -> Optional[str]:
    """Fetch synchronized lyrics from online sources (LRCLIB, etc.).

    Uses the `syncedlyrics` library which aggregates LRCLIB, NetEase,
    Musixmatch, and other providers. Because providers are flaky (and the
    library swallows their errors), each query variant is tried twice:
    first for enhanced (word-level) LRC, then for line-level LRC.

    Returns:
        LRC string if found, None otherwise
    """
    try:
        import syncedlyrics
    except ImportError:
        logger.warning("syncedlyrics not installed, skipping online search")
        return None

    for search_term in _query_variants(title, artist):
        logger.info(f"Searching online for synced lyrics: '{search_term}'")
        for attempt, enhanced in enumerate((True, False)):
            try:
                lrc = syncedlyrics.search(search_term, enhanced=enhanced)
            except Exception as e:
                logger.warning(f"Online lyrics search failed ({search_term!r}): {e}")
                time.sleep(1.0 + attempt)
                continue
            if lrc and parse_lrc(lrc):
                logger.info(f"Found synced lyrics online ({len(lrc)} chars)")
                return lrc
            time.sleep(0.5)

    return None


# ---------------------------------------------------------------------------
# Lyric cache (so a once-successful lookup survives flaky providers)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Direct LRCLIB API Fallback
# ---------------------------------------------------------------------------

def fetch_lrclib_lyrics(title: str, artist: str, duration: Optional[float] = None) -> Optional[str]:
    """Fetch synchronized lyrics directly from LRCLIB API.

    This is a fallback when `syncedlyrics` doesn't find results.
    """
    try:
        import requests
    except ImportError:
        logger.warning("requests not installed, skipping LRCLIB")
        return None

    url = "https://lrclib.net/api/get"
    headers = {"User-Agent": "MTVGen/1.0 (github.com/mtvgen)"}
    params = {"track_name": title, "artist_name": artist}
    if duration:
        params["duration"] = int(duration)

    logger.info(f"Querying LRCLIB API: title='{title}', artist='{artist}'")

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            synced = data.get("syncedLyrics")
            if synced:
                logger.info(f"Found synced lyrics from LRCLIB ({len(synced)} chars)")
                return synced
            plain = data.get("plainLyrics")
            if plain:
                logger.info("Found plain lyrics from LRCLIB (no timestamps)")
                # Can't use plain text without alignment, return None
                return None
        else:
            logger.debug(f"LRCLIB returned status {resp.status_code}")
    except Exception as e:
        logger.warning(f"LRCLIB API request failed: {e}")

    return None


# ---------------------------------------------------------------------------
# Whisper Transcription (Fallback)
# ---------------------------------------------------------------------------

def transcribe_lyrics(mp3_path: str | Path, model_size: str = "base") -> list[LyricLine]:
    """Transcribe lyrics from audio using faster-whisper with word timestamps.

    This is the last-resort fallback when no lyrics are found online.

    Args:
        mp3_path: Path to the MP3 file
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large-v3')

    Returns:
        List of LyricLine with word-level timestamps
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.error("faster-whisper not installed. Install with: pip install faster-whisper")
        return []

    mp3_path = str(mp3_path)
    logger.info(f"Transcribing with faster-whisper (model={model_size})...")

    # Detect device
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
    except ImportError:
        device = "cpu"
        compute_type = "int8"

    logger.info(f"Using device={device}, compute_type={compute_type}")

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    segments, info = model.transcribe(
        mp3_path,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    segments = list(segments)
    if not segments:
        # VAD often treats sung vocals over instruments as non-speech; retry without it
        logger.warning("Whisper found no speech with VAD; retrying without VAD filter...")
        segments, info = model.transcribe(mp3_path, word_timestamps=True, vad_filter=False)
        segments = list(segments)

    logger.info(f"Detected language: {info.language} (probability={info.language_probability:.2f})")

    lines: list[LyricLine] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue

        words = None
        if segment.words:
            words = [
                LyricWord(word=w.word.strip(), start=w.start, end=w.end)
                for w in segment.words
                if w.word.strip()
            ]

        lines.append(LyricLine(
            text=text,
            start=segment.start,
            end=segment.end,
            words=words,
        ))

    logger.info(f"Transcribed {len(lines)} lyric lines")
    return lines


# ---------------------------------------------------------------------------
# Main Extraction Pipeline
# ---------------------------------------------------------------------------

def extract_lyrics(
    mp3_path: str | Path,
    lrc_path: Optional[str | Path] = None,
    whisper_model: str = "base",
    force_whisper: bool = False,
) -> list[LyricLine]:
    """Extract synchronized lyrics using a multi-tier fallback strategy.

    Priority:
      1. User-provided LRC file (--lyrics flag)
      2. Embedded synced lyrics (SYLT ID3 tag)
      3. Online search (syncedlyrics → LRCLIB)
      4. Whisper transcription (fallback)

    Args:
        mp3_path: Path to the MP3 file
        lrc_path: Optional path to a pre-made .lrc file
        whisper_model: Whisper model size for transcription fallback

    Returns:
        List of LyricLine objects
    """
    from .metadata import get_metadata, get_embedded_lyrics

    mp3_path = Path(mp3_path)

    # Debug/evaluation mode: skip every other source and use Whisper only
    if force_whisper:
        logger.info("--force-whisper: skipping LRC/embedded/online sources")
        return transcribe_lyrics(mp3_path, model_size=whisper_model)

    # Tier 0: User-provided LRC file
    if lrc_path:
        lrc_path = Path(lrc_path)
        logger.info(f"Using provided LRC file: {lrc_path}")
        lrc_content = lrc_path.read_text(encoding="utf-8")
        lines = parse_lrc(lrc_content)
        if lines:
            logger.info(f"Parsed {len(lines)} lines from LRC file")
            return lines
        logger.warning("Provided LRC file yielded no lines, falling through")

    # Get metadata for online search
    meta = get_metadata(mp3_path)
    title = meta["title"]
    artist = meta["artist"]
    duration = meta["duration"]

    # Tier 1: Embedded lyrics in MP3 tags
    logger.info("Tier 1: Checking embedded lyrics in MP3 tags...")
    embedded = get_embedded_lyrics(mp3_path)
    if embedded:
        if "synced" in embedded:
            logger.info("✓ Found embedded synced lyrics (SYLT)")
            return embedded["synced"]
        # Plain text lyrics can't be used without alignment
        logger.info("Found embedded plain lyrics (USLT) but no timestamps")

    # Tier 2: Cache, then online search
    cached = _read_cache(title, artist, duration)
    if cached:
        lines = parse_lrc(cached)
        if lines:
            logger.info(f"✓ Using cached lyrics: {len(lines)} lines")
            return lines

    logger.info("Tier 2: Searching for lyrics online...")

    # Try syncedlyrics aggregator
    lrc_content = fetch_online_lyrics(title, artist)
    if lrc_content:
        lines = parse_lrc(lrc_content)
        if lines:
            logger.info(f"✓ Found online synced lyrics: {len(lines)} lines")
            _write_cache(title, artist, duration, lrc_content)
            return lines

    # Try direct LRCLIB API (with retries; the server sometimes returns 503)
    for attempt in range(3):
        lrc_content = fetch_lrclib_lyrics(title, artist, duration)
        if lrc_content:
            break
        time.sleep(1.0 + attempt)
    if lrc_content:
        lines = parse_lrc(lrc_content)
        if lines:
            logger.info(f"✓ Found LRCLIB synced lyrics: {len(lines)} lines")
            _write_cache(title, artist, duration, lrc_content)
            return lines

    # Tier 3: Whisper transcription
    logger.info("Tier 3: No lyrics found online, falling back to Whisper transcription...")
    lines = transcribe_lyrics(mp3_path, model_size=whisper_model)
    if lines:
        logger.info(f"✓ Transcribed {len(lines)} lines with Whisper")
        return lines

    logger.warning("No lyrics could be extracted from any source")
    return []
