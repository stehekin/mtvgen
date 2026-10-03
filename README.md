# 🎵 MTVGen — Music TV Generator

Generate visually stunning music videos (MTV) from MP3 files with synchronized lyrics.

MTVGen automatically extracts lyrics, synchronizes them to the audio, and renders a cinematic video with audio-reactive visualizations, karaoke-style lyric highlights, and floating particle effects.

## Features

- **Smart Lyric Extraction** — Multi-tier fallback:
  1. Reads embedded lyrics from MP3 ID3 tags (SYLT/USLT)
  2. Searches online via LRCLIB and other providers
  3. Falls back to AI transcription (Whisper) with word-level timestamps
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
git clone https://github.com/youruser/mtvgen.git
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
2. Search for synchronized lyrics online
3. Render an MTV video → `song_mtv.mp4`

### With a pre-made LRC file
```bash
python -m mtvgen song.mp3 --lyrics song.lrc
```

### Specify output path
```bash
python -m mtvgen song.mp3 -o my_video.mp4
```

### Extract lyrics only (no video)
```bash
python -m mtvgen song.mp3 --lyrics-only
```

### Use a larger Whisper model for better transcription
```bash
python -m mtvgen song.mp3 --whisper-model medium
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
| `--lyrics` | None | Path to a pre-made `.lrc` file |
| `--whisper-model` | `base` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `--resolution` | `1920x1080` | Output video resolution |
| `--lyrics-only` | false | Only extract lyrics as JSON, skip video |
| `-v, --verbose` | false | Enable debug logging |

## Architecture

```
MP3 File
  │
  ├─→ [Python] Metadata extraction (mutagen)
  ├─→ [Python] Lyric search (syncedlyrics → LRCLIB → Whisper)
  │     │
  │     └─→ lyrics.json
  │
  └─→ [Remotion] Video rendering
        ├─ Animated gradient background
        ├─ Floating particles
        ├─ 64-band FFT spectrum visualizer
        └─ Synchronized lyric display (karaoke mode)
              │
              └─→ output.mp4
```

## Project Structure

```
mtvgen/
├── mtvgen/                 # Python package
│   ├── cli.py              # CLI entry point
│   ├── metadata.py         # MP3 metadata extraction
│   ├── lyrics.py           # Multi-tier lyric retrieval
│   └── models.py           # Data models (SongData, LyricLine, LyricWord)
├── remotion/               # Remotion video project
│   ├── src/
│   │   ├── Root.tsx        # Composition registration
│   │   ├── MTV.tsx         # Main video composition
│   │   ├── components/
│   │   │   ├── Background.tsx
│   │   │   ├── SpectrumVisualizer.tsx
│   │   │   ├── LyricsDisplay.tsx
│   │   │   └── Particles.tsx
│   │   └── utils/
│   │       └── lyrics.ts   # TypeScript lyric helpers
│   └── public/             # Audio + lyrics placed here at runtime
├── requirements.txt
└── README.md
```

## License

MIT
