# 🎵 MTVGen — Music TV Generator

Generate visually stunning music videos (MTV) from MP3 files with synchronized lyrics.

MTVGen automatically extracts lyrics, synchronizes them to the audio, and renders a cinematic video with audio-reactive visualizations, karaoke-style lyric highlights, and floating particle effects.

## Features

- **Multi-Tier Smart Lyric System** — Seamless fallback pipeline:
  1. Reads embedded synced lyrics (SYLT) or provided `.lrc` files
  2. Searches top Chinese & global synced lyric services (**Kugou**, **NetEase**, **LRCLIB**, **Musixmatch**, **Genius**)
  3. **Demucs Vocal Separation** + **PyTorch MMS Forced Alignment** for plain text lyrics
- **Selectable Themes & Visual Effects** — Choose between 6 distinct visual themes and mix-and-match overlay effects (`particles`, `spectrum`, `waveform`)
- **Audio-Reactive Visuals** — Real-time FFT spectrum analyzer & oscilloscope waveform visualizers
- **Karaoke-Style Lyrics** — Smooth, jitter-free lyric highlighting & frame-deterministic spring animations
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

### Choose Themes and Effects
```bash
# Sunset theme with waveform visualizer
python -m mtvgen song.mp3 --theme sunset --effects waveform -o sunset_mtv.mp4

# Northern Lights Aurora theme with floating particles
python -m mtvgen song.mp3 --theme aurora --effects particles -o aurora_mtv.mp4

# Midnight theme with both spectrum bars and particles
python -m mtvgen song.mp3 --theme midnight --effects "particles,spectrum" -o midnight_mtv.mp4

# Minimalist dark theme without overlay effects
python -m mtvgen song.mp3 --theme minimal --effects none -o minimal_mtv.mp4
```

### With a pre-made LRC file or plain text lyrics
```bash
# Synced LRC file
python -m mtvgen song.mp3 --lyrics song.lrc

# Plain text file (automatically aligned with MMS Forced Alignment)
python -m mtvgen song.mp3 --lyrics lyrics.txt --separate-vocals
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
| `--theme` | `neon` | Visual theme: `neon`, `minimal`, `cosmic`, `sunset`, `aurora`, `midnight` |
| `--effects` | `all` | Overlay effects: `all`, `none`, or comma-separated e.g. `'particles,spectrum,waveform'` |
| `--lyrics` | None | Path to a pre-made `.lrc` file or plain text file |
| `--separate-vocals` | false | Isolate vocal track using Demucs before forced alignment |
| `--resolution` | `1920x1080` | Output video resolution |
| `--lyrics-only` | false | Only extract lyrics as JSON, skip video |
| `--allow-no-lyrics` | false | Render even if no lyrics were found |
| `-v, --verbose` | false | Enable debug logging |

## License

MIT
