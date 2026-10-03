# 🎵 MTVGen — Music TV Generator

Generate visually stunning music videos (MTV) from MP3 files with synchronized lyrics.

MTVGen automatically extracts lyrics, synchronizes them to the audio, and renders a cinematic video with audio-reactive visualizations, karaoke-style lyric highlights, and floating particle effects.

## Features

- **Multi-Tier Smart Lyric System** — Seamless fallback pipeline:
  1. Reads embedded synced lyrics (SYLT) or provided `.lrc` files
  2. Searches top Chinese & global synced lyric services (**Kugou**, **NetEase**, **LRCLIB**, **Musixmatch**, **Genius**)
  3. **Demucs Vocal Separation** + **PyTorch MMS Forced Alignment** for plain text lyrics
- **Audio-Reactive Visuals** — 64-band FFT spectrum analyzer that pulses with the music
- **Karaoke-Style Lyrics** — Words highlight progressively as they're sung
- **Cinematic Background** — Animated gradients with floating particles
- **1080p Output** — High-quality MP4 video at 30fps

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for Remotion video rendering)
- **FFmpeg** (for video encoding)

## Installation

```bash
# Clone the repo
git clone https://github.com/stehekin/mtvgen.git
cd mtvgen

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install Remotion dependencies (auto-installed on first run)
cd remotion && npm install && cd ..
```

## Usage

### Basic usage
```bash
python -m mtvgen song.mp3
```

This will:
1. Extract the song's metadata (title, artist)
2. Search for synchronized lyrics across Kugou, NetEase, LRCLIB, and global databases
3. Render an MTV video → `song_mtv.mp4`

### With a pre-made LRC file or plain text lyrics
```bash
# Synced LRC file
python -m mtvgen song.mp3 --lyrics song.lrc

# Plain text file (automatically aligned with MMS Forced Alignment)
python -m mtvgen song.mp3 --lyrics lyrics.txt --separate-vocals
```

### Specify output path
```bash
python -m mtvgen song.mp3 -o my_video.mp4
```

### Extract lyrics only (no video)
```bash
python -m mtvgen song.mp3 --lyrics-only
```

### Preview in Remotion Studio (interactive)
```bash
cd remotion
npx remotion studio
```

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `input` | (required) | Path to the input MP3 file |
| `-o, --output` | `<input>_mtv.mp4` | Output MP4 file path |
| `--lyrics` | None | Path to a pre-made `.lrc` file or plain text file |
| `--separate-vocals` | false | Isolate vocal track using Demucs before forced alignment |
| `--resolution` | `1920x1080` | Output video resolution |
| `--lyrics-only` | false | Only extract lyrics as JSON, skip video |
| `--allow-no-lyrics` | false | Render even if no lyrics were found |
| `-v, --verbose` | false | Enable debug logging |

## Architecture

```
MP3 File
  │
  ├─→ [Python] Metadata extraction (mutagen)
  ├─→ [Python] Lyric retrieval:
  │     ├─ Tier 1: Embedded SYLT ID3 tags / LRC file
  │     ├─ Tier 2: Chinese & Global APIs (Kugou → NetEase → LRCLIB / Musixmatch)
  │     └─ Tier 3: Demucs Vocal Separation + PyTorch MMS Forced Alignment
  │           │
  │           └─→ lyrics.json
  │
  └─→ [Remotion] Video rendering
        ├─ Animated gradient background
        ├─ Floating particles
        ├─ 64-band FFT spectrum visualizer
        └─ Synchronized lyric display (karaoke mode)
              │
              └─→ output.mp4
```

## License

MIT
