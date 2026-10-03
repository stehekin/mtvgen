"""Multi-tier lyric retrieval: embedded tags → online (LRCLIB, etc.) → Gemini transcription."""

from __future__ import annotations

import hashlib
import json
import logging
import os
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
# Gemini Transcription (Fallback)
# ---------------------------------------------------------------------------

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"

_GEMINI_PROMPT = """You are transcribing the lyrics of a song from its audio.

Return a JSON array. Each item is one sung line (phrase) of the lyrics:
  - "start": the time the line begins being sung, formatted MM:SS.s (e.g. "01:23.5")
  - "text": the lyrics of that line

Rules:
- Transcribe exactly what is sung, in the original language(s) of the song. Do not translate.
- Chinese/Cantonese lyrics: write the standard Chinese characters of the actual lyrics.
- Skip instrumental sections. Do not output credits, song titles, singer names,
  annotations like [Chorus] or (music), or any text that is not sung.
- If a line is repeated in the song, output it again at its new time.
- Do not invent lyrics. If a part is unintelligible, omit it.
- Timestamps must be increasing and match the audio as precisely as you can.
"""

_GEMINI_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "start": {"type": "STRING"},
            "text": {"type": "STRING"},
        },
        "required": ["start", "text"],
    },
}


def _parse_timestamp(value) -> Optional[float]:
    """Parse 'MM:SS.s', 'H:MM:SS', or a plain number of seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    parts = str(value).strip().replace(",", ".").split(":")
    try:
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60 + float(part)
        return seconds
    except ValueError:
        return None


def transcribe_lyrics(
    mp3_path: str | Path,
    model: str = DEFAULT_GEMINI_MODEL,
    duration: Optional[float] = None,
) -> list[LyricLine]:
    """Transcribe lyrics from audio with Gemini (line-level timestamps).

    Last-resort fallback when no synced lyrics are found elsewhere. Requires
    the GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable.

    Args:
        mp3_path: Path to the MP3 file
        model: Gemini model name
        duration: Song length in seconds, used to drop out-of-range timestamps

    Returns:
        List of LyricLine (line-level timing only), empty on failure
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set; cannot transcribe lyrics with Gemini")
        return []

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.error("google-genai not installed. Install with: pip install google-genai")
        return []

    logger.info(f"Transcribing lyrics with Gemini (model={model})...")
    client = genai.Client(api_key=api_key)

    uploaded = None
    try:
        uploaded = client.files.upload(file=str(mp3_path))
        # Wait until the uploaded audio is ready for use
        for _ in range(60):
            state = getattr(getattr(uploaded, "state", None), "name", None)
            if state != "PROCESSING":
                break
            time.sleep(1.0)
            uploaded = client.files.get(name=uploaded.name)

        response = client.models.generate_content(
            model=model,
            contents=[uploaded, _GEMINI_PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_GEMINI_SCHEMA,
                temperature=0.0,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            ),
        )
        items = json.loads(response.text)
    except Exception as e:
        logger.error(f"Gemini transcription failed: {e}")
        return []
    finally:
        if uploaded is not None:
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass

    entries: list[tuple[float, str]] = []
    for item in items:
        text = str(item.get("text", "")).strip()
        start = _parse_timestamp(item.get("start"))
        if not text or start is None:
            continue
        if duration and start > duration + 1.0:
            logger.debug(f"Dropping out-of-range line at {start:.1f}s: {text}")
            continue
        entries.append((start, text))
    entries.sort(key=lambda e: e[0])

    lines: list[LyricLine] = []
    for i, (start, text) in enumerate(entries):
        end = entries[i + 1][0] if i + 1 < len(entries) else start + 5.0
        lines.append(LyricLine(text=text, start=start, end=end, words=None))

    logger.info(f"Gemini transcribed {len(lines)} lyric lines")
    return lines


# ---------------------------------------------------------------------------
# Main Extraction Pipeline
# ---------------------------------------------------------------------------

def extract_lyrics(
    mp3_path: str | Path,
    lrc_path: Optional[str | Path] = None,
    gemini_model: str = DEFAULT_GEMINI_MODEL,
    force_gemini: bool = False,
) -> list[LyricLine]:
    """Extract synchronized lyrics using a multi-tier fallback strategy.

    Priority:
      1. User-provided LRC file (--lyrics flag)
      2. Embedded synced lyrics (SYLT ID3 tag)
      3. Online search (syncedlyrics → LRCLIB), cached on success
      4. Gemini transcription (fallback; needs GEMINI_API_KEY)

    Args:
        mp3_path: Path to the MP3 file
        lrc_path: Optional path to a pre-made .lrc file
        gemini_model: Gemini model used for the transcription fallback
        force_gemini: Skip all other sources and use Gemini only (for testing)

    Returns:
        List of LyricLine objects
    """
    from .metadata import get_metadata, get_embedded_lyrics

    mp3_path = Path(mp3_path)

    # Debug/evaluation mode: skip every other source and use Gemini only
    if force_gemini:
        logger.info("--force-gemini: skipping LRC/embedded/online sources")
        return transcribe_lyrics(
            mp3_path, model=gemini_model, duration=get_metadata(mp3_path)["duration"]
        )

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

    # Tier 3: Gemini transcription
    logger.info("Tier 3: No synced lyrics found online, falling back to Gemini transcription...")
    lines = transcribe_lyrics(mp3_path, model=gemini_model, duration=duration)
    if lines:
        logger.info(f"✓ Transcribed {len(lines)} lines with Gemini")
        return lines

    logger.warning("No lyrics could be extracted from any source")
    return []
