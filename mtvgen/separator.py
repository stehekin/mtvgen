"""Audio stem separation using Demucs to isolate clean vocal tracks."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_VOCALS_DIR = Path.home() / ".cache" / "mtvgen" / "vocals"


def separate_vocals(audio_path: str | Path, force: bool = False) -> Path:
    """Separate vocals from an audio file using Demucs.

    Args:
        audio_path: Path to the input MP3 / audio file.
        force: If True, re-separate even if cached.

    Returns:
        Path to the isolated vocals audio file (WAV), or original file on failure.
    """
    audio_path = Path(audio_path).resolve()
    if not audio_path.exists():
        logger.error(f"Audio file not found: {audio_path}")
        return audio_path

    CACHE_VOCALS_DIR.mkdir(parents=True, exist_ok=True)
    target_vocal_path = CACHE_VOCALS_DIR / f"{audio_path.stem}_vocals.wav"

    if target_vocal_path.exists() and not force:
        logger.info(f"✓ Using cached isolated vocal track: {target_vocal_path}")
        return target_vocal_path

    logger.info(f"Isolating vocals with Demucs (this may take 15-30s)...")

    try:
        # Run demucs separation via subprocess using current Python executable
        cmd = [
            sys.executable,
            "-m",
            "demucs.separate",
            "-n",
            "htdemucs",
            "--two-stems",
            "vocals",
            "-o",
            str(CACHE_VOCALS_DIR),
            str(audio_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.debug(f"Demucs output: {result.stdout}")

        # Demucs output structure: CACHE_VOCALS_DIR / htdemucs / <song_stem> / vocals.wav
        out_vocal = CACHE_VOCALS_DIR / "htdemucs" / audio_path.stem / "vocals.wav"
        if out_vocal.exists():
            # Copy / rename to target_vocal_path
            out_vocal.replace(target_vocal_path)
            logger.info(f"✓ Successfully isolated vocals: {target_vocal_path}")
            return target_vocal_path
        else:
            logger.warning(f"Demucs finished but output vocal file was not found at {out_vocal}")
    except Exception as e:
        logger.warning(f"Vocal separation failed ({e}). Falling back to original audio.")

    return audio_path
