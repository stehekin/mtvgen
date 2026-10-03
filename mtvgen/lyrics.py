"""Multi-tier lyric retrieval: embedded tags → online (LRCLIB) → Whisper transcription."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from .models import LyricLine, LyricWord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LRC Parsing
# ---------------------------------------------------------------------------

# Matches lines like [01:23.45] Some lyric text
_LRC_LINE_RE = re.compile(r"\[(\d{1,2}):(\d{2})\.(\d{2,3})\]\s*(.*)")
# Matches enhanced LRC word timestamps like <01:23.45>
_LRC_WORD_RE = re.compile(r"<(\d{1,2}):(\d{2})\.(\d{2,3})>")


def _lrc_timestamp_to_seconds(minutes: str, seconds: str, centis: str) -> float:
    """Convert LRC timestamp components to seconds."""
    m = int(minutes)
    s = int(seconds)
    # Handle both 2-digit (centiseconds) and 3-digit (milliseconds) fractional parts
    if len(centis) == 2:
        frac = int(centis) / 100.0
    else:
        frac = int(centis) / 1000.0
    return m * 60.0 + s + frac


def parse_lrc(lrc_content: str) -> list[LyricLine]:
    """Parse an LRC string into a list of LyricLine objects.

    Supports both standard LRC (line-level timestamps) and enhanced LRC
    (word-level timestamps with <mm:ss.xx> inline tags).
    """
    lines: list[LyricLine] = []

    for raw_line in lrc_content.strip().splitlines():
        match = _LRC_LINE_RE.match(raw_line.strip())
        if not match:
            continue

        start = _lrc_timestamp_to_seconds(match.group(1), match.group(2), match.group(3))
        text = match.group(4).strip()

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
                idx += 1

            text = " ".join(clean_text_parts)

        lines.append(LyricLine(text=text, start=start, end=0.0, words=words))

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

def fetch_online_lyrics(title: str, artist: str) -> Optional[str]:
    """Fetch synchronized lyrics from online sources (LRCLIB, etc.).

    Uses the `syncedlyrics` library which aggregates LRCLIB, NetEase,
    Musixmatch, and other providers.

    Returns:
        LRC string if found, None otherwise
    """
    try:
        import syncedlyrics
    except ImportError:
        logger.warning("syncedlyrics not installed, skipping online search")
        return None

    search_term = f"{title} {artist}"
    logger.info(f"Searching online for synced lyrics: '{search_term}'")

    try:
        lrc = syncedlyrics.search(search_term, enhanced=True)
        if lrc:
            logger.info(f"Found synced lyrics online ({len(lrc)} chars)")
            return lrc
        # Try without enhanced (fallback to line-level)
        lrc = syncedlyrics.search(search_term, enhanced=False)
        if lrc:
            logger.info(f"Found line-level lyrics online ({len(lrc)} chars)")
            return lrc
    except Exception as e:
        logger.warning(f"Online lyrics search failed: {e}")

    return None


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

    # Tier 2: Online search
    logger.info("Tier 2: Searching for lyrics online...")

    # Try syncedlyrics aggregator
    lrc_content = fetch_online_lyrics(title, artist)
    if lrc_content:
        lines = parse_lrc(lrc_content)
        if lines:
            logger.info(f"✓ Found online synced lyrics: {len(lines)} lines")
            return lines

    # Try direct LRCLIB API
    lrc_content = fetch_lrclib_lyrics(title, artist, duration)
    if lrc_content:
        lines = parse_lrc(lrc_content)
        if lines:
            logger.info(f"✓ Found LRCLIB synced lyrics: {len(lines)} lines")
            return lines

    # Tier 3: Whisper transcription
    logger.info("Tier 3: No lyrics found online, falling back to Whisper transcription...")
    lines = transcribe_lyrics(mp3_path, model_size=whisper_model)
    if lines:
        logger.info(f"✓ Transcribed {len(lines)} lines with Whisper")
        return lines

    logger.warning("No lyrics could be extracted from any source")
    return []
