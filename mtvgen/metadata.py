"""Extract metadata and embedded lyrics from MP3 files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from mutagen import File as MutagenFile
from mutagen.id3 import ID3, USLT, SYLT
from mutagen.mp3 import MP3

from .models import LyricLine, LyricWord

logger = logging.getLogger(__name__)


def get_metadata(mp3_path: str | Path) -> dict:
    """Extract title, artist, album, and duration from an MP3 file.

    Returns:
        dict with keys: title, artist, album, duration (seconds)
    """
    mp3_path = Path(mp3_path)

    # Read tags
    audio = MutagenFile(str(mp3_path), easy=True)
    title = None
    artist = None
    album = None

    if audio:
        title = audio.get("title", [None])[0]
        artist = audio.get("artist", [None])[0]
        album = audio.get("album", [None])[0]

    # Fallback: use filename as title
    if not title:
        title = mp3_path.stem
        logger.info(f"No title tag found, using filename: {title}")

    if not artist:
        artist = "Unknown Artist"
        logger.info("No artist tag found, using 'Unknown Artist'")

    # Get duration via mutagen
    duration = 0.0
    try:
        mp3_info = MP3(str(mp3_path))
        duration = mp3_info.info.length
    except Exception:
        raw_audio = MutagenFile(str(mp3_path))
        duration = raw_audio.info.length if raw_audio and raw_audio.info else 0.0

    return {
        "title": title,
        "artist": artist,
        "album": album,
        "duration": duration,
    }


def get_embedded_lyrics(mp3_path: str | Path) -> Optional[dict]:
    """Check for embedded lyrics in MP3 ID3 tags.

    Returns:
        dict with keys:
          - 'synced': list[LyricLine] if SYLT tag found
          - 'plain': str if USLT tag found
          - None if no lyrics embedded
    """
    mp3_path = str(mp3_path)
    result = {}

    try:
        id3 = ID3(mp3_path)
    except Exception:
        logger.debug(f"No ID3 tags found in {mp3_path}")
        return None

    # Check SYLT (Synchronized Lyrics) — best case
    for sylt in id3.getall("SYLT"):
        if sylt.text:
            lines: list[LyricLine] = []
            for i, (text, timestamp_ms) in enumerate(sylt.text):
                start = timestamp_ms / 1000.0
                # End time is the start of the next entry, or start + 5s for the last
                if i + 1 < len(sylt.text):
                    end = sylt.text[i + 1][1] / 1000.0
                else:
                    end = start + 5.0
                text = text.strip()
                if text:
                    lines.append(LyricLine(text=text, start=start, end=end))
            if lines:
                result["synced"] = lines
                logger.info(f"Found SYLT embedded lyrics: {len(lines)} lines")
                return result

    # Check USLT (Unsynchronized Lyrics)
    for uslt in id3.getall("USLT"):
        if uslt.text and uslt.text.strip():
            result["plain"] = uslt.text.strip()
            logger.info(f"Found USLT embedded lyrics ({len(uslt.text)} chars)")
            return result

    return None
