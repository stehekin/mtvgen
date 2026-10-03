"""CLI entry point for mtvgen — generate Music TV videos from MP3 files."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__
from .lyrics import extract_lyrics
from .metadata import get_metadata
from .models import SongData

logger = logging.getLogger(__name__)

# Path to the Remotion project relative to this file
REMOTION_DIR = Path(__file__).parent.parent / "remotion"


def setup_logging(verbose: bool = False) -> None:
    """Configure logging output."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def check_prerequisites() -> bool:
    """Check that required external tools are available."""
    ok = True

    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        logger.info(f"Node.js: {result.stdout.strip()}")
    except FileNotFoundError:
        logger.error("Node.js is not installed. Please install Node.js >= 18.")
        ok = False

    # Check npx
    try:
        subprocess.run(["npx", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        logger.error("npx is not available. Please install Node.js >= 18.")
        ok = False

    # Check ffmpeg (needed by Remotion for rendering)
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        first_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
        logger.info(f"FFmpeg: {first_line}")
    except FileNotFoundError:
        logger.error("FFmpeg is not installed. Please install ffmpeg.")
        ok = False

    # Check Remotion project exists
    if not (REMOTION_DIR / "package.json").exists():
        logger.error(f"Remotion project not found at {REMOTION_DIR}")
        ok = False

    return ok


def ensure_remotion_deps() -> None:
    """Ensure Remotion project dependencies are installed."""
    node_modules = REMOTION_DIR / "node_modules"
    if not node_modules.exists():
        logger.info("Installing Remotion dependencies (first run)...")
        subprocess.run(
            ["npm", "install"],
            cwd=str(REMOTION_DIR),
            check=True,
        )
    else:
        logger.debug("Remotion node_modules found, skipping install")


def render_video(
    song_data: SongData,
    mp3_path: Path,
    output_path: Path,
    resolution: str = "1920x1080",
) -> None:
    """Invoke Remotion to render the MTV video.

    Args:
        song_data: Song metadata and lyrics
        mp3_path: Path to the input MP3 file
        output_path: Desired output MP4 path
        resolution: Video resolution (e.g. '1920x1080')
    """
    ensure_remotion_deps()

    # Copy audio to Remotion public directory
    public_dir = REMOTION_DIR / "public"
    public_dir.mkdir(exist_ok=True)
    audio_dest = public_dir / "audio.mp3"
    shutil.copy2(str(mp3_path), str(audio_dest))
    logger.info(f"Copied audio to {audio_dest}")

    # Write lyrics JSON to Remotion public directory
    lyrics_dest = public_dir / "lyrics.json"
    song_data.save_json(str(lyrics_dest))
    logger.info(f"Wrote lyrics data to {lyrics_dest}")

    # Build input props for Remotion
    input_props = {
        "audioFile": "audio.mp3",
        "songData": song_data.to_dict(),
    }
    props_json = json.dumps(input_props)

    # Parse resolution
    try:
        width, height = resolution.split("x")
        width, height = int(width), int(height)
    except ValueError:
        width, height = 1920, 1080

    # Invoke Remotion render
    logger.info(f"Rendering MTV video ({width}x{height})...")
    logger.info("This may take several minutes depending on song length and hardware.")

    render_cmd = [
        "npx", "remotion", "render",
        "MTV",
        str(output_path.resolve()),
        "--props", props_json,
        "--log", "verbose",
    ]

    logger.debug(f"Render command: {' '.join(render_cmd)}")

    try:
        result = subprocess.run(
            render_cmd,
            cwd=str(REMOTION_DIR),
            check=True,
        )
        logger.info(f"✓ Video rendered successfully: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Remotion render failed with exit code {e.returncode}")
        raise


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="mtvgen",
        description="Generate a Music TV video from an MP3 file with synchronized lyrics.",
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to the input MP3 file",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output MP4 file path (default: <input_name>_mtv.mp4)",
    )
    parser.add_argument(
        "--lyrics",
        type=str,
        default=None,
        help="Path to an LRC file with pre-made synchronized lyrics",
    )
    parser.add_argument(
        "--whisper-model",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper model size for transcription fallback (default: base)",
    )
    parser.add_argument(
        "--resolution",
        type=str,
        default="1920x1080",
        help="Output video resolution (default: 1920x1080)",
    )
    parser.add_argument(
        "--lyrics-only",
        action="store_true",
        help="Only extract lyrics and save as JSON (skip video rendering)",
    )
    parser.add_argument(
        "--force-whisper",
        action="store_true",
        help="Ignore LRC/embedded/online lyrics and transcribe with Whisper only (for testing)",
    )
    parser.add_argument(
        "--allow-no-lyrics",
        action="store_true",
        help="Render the video even if no lyrics could be found",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    # Validate input file
    mp3_path = Path(args.input).resolve()
    if not mp3_path.exists():
        logger.error(f"Input file not found: {mp3_path}")
        return 1
    if not mp3_path.suffix.lower() == ".mp3":
        logger.warning(f"Input file may not be an MP3: {mp3_path.suffix}")

    # Default output path
    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = mp3_path.parent / f"{mp3_path.stem}_mtv.mp4"

    logger.info(f"Input:  {mp3_path}")
    logger.info(f"Output: {output_path}")

    # Step 1: Extract metadata
    logger.info("=" * 50)
    logger.info("Step 1: Reading MP3 metadata...")
    meta = get_metadata(mp3_path)
    logger.info(f"  Title:    {meta['title']}")
    logger.info(f"  Artist:   {meta['artist']}")
    logger.info(f"  Duration: {meta['duration']:.1f}s")

    # Step 2: Extract lyrics
    logger.info("=" * 50)
    logger.info("Step 2: Extracting lyrics...")
    lyrics = extract_lyrics(
        mp3_path,
        lrc_path=args.lyrics,
        whisper_model=args.whisper_model,
        force_whisper=args.force_whisper,
    )
    logger.info(f"  Found {len(lyrics)} lyric lines")

    if not lyrics and not args.allow_no_lyrics:
        logger.error(
            "No lyrics could be found from any source. Provide an LRC file with "
            "--lyrics, retry later (online providers may be down), or pass "
            "--allow-no-lyrics to render without lyrics."
        )
        return 2

    if lyrics:
        # Show first few lines as preview
        for line in lyrics[:3]:
            logger.info(f"    [{line.start:.1f}s] {line.text}")
        if len(lyrics) > 3:
            logger.info(f"    ... and {len(lyrics) - 3} more lines")

    # Build song data
    song_data = SongData(
        title=meta["title"],
        artist=meta["artist"],
        duration=meta["duration"],
        lyrics=lyrics,
    )

    # Lyrics-only mode
    if args.lyrics_only:
        json_path = output_path.with_suffix(".json")
        song_data.save_json(str(json_path))
        logger.info(f"✓ Lyrics saved to: {json_path}")
        return 0

    # Step 3: Check prerequisites for video rendering
    logger.info("=" * 50)
    logger.info("Step 3: Checking prerequisites...")
    if not check_prerequisites():
        logger.error("Missing prerequisites. Please install the required tools.")
        return 1

    # Step 4: Render video
    logger.info("=" * 50)
    logger.info("Step 4: Rendering MTV video...")
    try:
        render_video(song_data, mp3_path, output_path, args.resolution)
    except Exception as e:
        logger.error(f"Video rendering failed: {e}")
        return 1

    logger.info("=" * 50)
    logger.info(f"✓ Done! MTV video saved to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
