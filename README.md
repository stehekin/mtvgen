# MTVGen: Python Music Video Generator

MTVGen is a high-performance, non-AI Python application that compiles images, an audio track, and lyrics into a synchronized music video. It features automatic Chinese/Japanese/Korean typography rendering, beat-synchronized slideshow transitions, and fast GPU-like transitions that compile in seconds on standard CPUs.

---

## 1. Installation Guide

Modern Linux distributions restrict global Python package installations (PEP 668) to protect the operating system. To install and run MTVGen, you must use a Python **Virtual Environment (`venv`)**.

### System Prerequisites
Ensure you have the Python 3 virtual environment package installed:
- **Ubuntu/Debian**: `sudo apt install python3-venv python3-full`
- **Fedora/RHEL**: `sudo dnf install python3-devel`
- **Arch Linux**: Included by default in `python`.

### Setup Steps
Run these commands in your project terminal:

```bash
# 1. Create a virtual environment named 'venv' in your project root
python3 -m venv venv

# 2. Activate the virtual environment
source venv/bin/activate

# 3. Install the dependencies inside the virtual environment
pip install -r requirements.txt
```

> [!NOTE]
> When the virtual environment is active, your terminal prompt will show `(venv)`. You can exit the virtual environment at any time by running:
> ```bash
> deactivate
> ```

---

## 2. Quick Start: Testing the Installation

We have included a script to generate mock files (solid-color pictures, a 15-second WAV synth song, and test lyrics) so you can test the program instantly.

### 1. Generate Test Assets
```bash
python3 /home/qiang/.gemini/antigravity/brain/15946ce4-f695-4016-af6f-124d4ccf1659/scratch/test_setup.py
```
This creates a `test_assets/` folder in your workspace containing mock assets.

### 2. Generate a Video
```bash
python3 main.py -i test_assets -l test_assets/lyrics.lrc -s test_assets/song.wav -o output.mp4 -m lrc
```
This will compile a video named `output.mp4` using the pre-timed LRC file.

---

## 3. Usage Manual

### Command Structure
```bash
python3 main.py -i <images_input> -l <lyrics_file> -s <audio_file> [options]
```

### Required Arguments:
- `-i, --images`: Path to a directory containing images, or a comma-separated list of image files.
- `-l, --lyrics`: Path to the lyrics file (either a plain `.txt` file or a timed `.lrc` file).
- `-s, --song`: Path to the audio file (`.wav` or `.mp3`).

### Optional Customization Arguments:
- `-o, --output`: Name of the output video file (default: `output.mp4`).
- `-r, --resolution`: Video aspect ratio and resolution preset (choices: `landscape` (720p), `portrait` (720p), `square` (720p), `landscape_1080p`, `landscape_720p`, `landscape_480p`, `portrait_1080p`, `portrait_720p`, `portrait_480p`, `square_720p`, `square_480p`; default: `landscape`).
- `-m, --mode`: Alignment strategy (choices: `auto`, `tap`, `lrc`, `energy`, `linear`; default: `auto`).
- `--effect`: Slide transition style (choices: `fade`, `focus-reveal`, `grayscale-reveal`, `flash-white`, `random`; default: `random`).
- `--title`: Song title to display at the beginning of the video (defaults to extracting from audio filename).
- `--font`: Path to a custom TrueType/OpenType font file (e.g. `.ttf` or `.otf`) to use for video text rendering.
- `--font-size`: Font size for the lyric text overlay (default: `56`).
- `--title-size`: Font size for the song title card (default: `110`).
- `--font-color`: Text color (supports standard names like `white`, `yellow`, `red`, hex codes like `#FFCC00`, or comma-separated RGB integers like `255,204,0`; default: `white`).
- `--box-color`: Bounding box background color (supports RGBA comma-separated values like `0,0,0,100` or hex like `#00000064`; default: semi-transparent black `0,0,0,100`).
- `--shadow-color`: Text drop shadow color (supports RGBA comma-separated values like `0,0,0,150` or hex like `#00000096`; default: dark shadow `0,0,0,150`).
- `--lyric-pos`: Screen position of the lyrics (choices: `dynamic` (bottom in first 5s, center thereafter), `top`, `center`, `bottom`; default: `dynamic`).
- `--preview [DURATION]`: Generate a short preview video of the specified length in seconds. Defaults to `10.0` seconds if `--preview` is specified without a value (e.g., `--preview 15.5` to compile a 15.5-second preview).
- `--transition`: Overlap transition duration in seconds (default: `1.0`).
- `--fps`: Frame rate of output video (default: `15`). Pass `--fps 12` to compile even faster.
- `--no-beat-sync`: Disables aligning slide transitions to the drum beats in the song.

---

## 4. Lyric Alignment Modes (`-m`)

MTVGen supports four distinct lyric alignment techniques depending on your timing requirements:

| Mode | Input Required | Computation | Best For |
| :--- | :--- | :--- | :--- |
| **`lrc`** | Timed `.lrc` file | Instant | Perfect, frame-accurate synchronization with zero CPU overhead. |
| **`tap`** | Plain `.txt` lyrics | Manual Tapping | Fast, simple timing setup. Play the song in the terminal and press `Enter` to stamp when each line starts. Automatically generates a `.lrc` file for future runs. |
| **`energy`** | Plain `.txt` lyrics | <1s DSP analysis | Fully automated alignment without manual work or heavy AI dependencies. Uses a Butterworth bandpass filter to isolate vocal frequencies (200Hz - 2000Hz) and maps lyrics only to active singing segments. |
| **`linear`** | Plain `.txt` lyrics | Instant | Evenly distributes lyric lines across the song's duration (ignoring intros/solos). |

---

## 5. Transition Effects (`--effect`)

To make the video feel professional, MTVGen uses high-performance transition effects that run instantly without GPU overhead:

- **`fade`**: Classic, elegant crossfade between slides. The video automatically fades in from black at the beginning and fades out to black at the end.
- **`focus-reveal`**: The slide starts out heavily blurred (bokeh focus effect) and resolves into crisp focus over 1.5 seconds.
- **`grayscale-reveal`**: The slide starts in black & white and fades into full color over 1.5 seconds.
- **`flash-white`**: A quick, 0.4-second white camera flash that highlights the moment of transition.
- **`random`**: Randomly chooses one of the available transitions (`fade`, `focus-reveal`, `grayscale-reveal`, or `flash-white`) for each slide transition.

---

## 6. Premium Layout & Design System

The app's design aesthetics are managed centrally in `mtvgen/config.py`:
- **Glassmorphic Bounding Box**: Lyrics are rendered inside a semi-transparent black pill box (acrylic overlay) positioned in the bottom third of the screen.
- **Auto CJK Font Loading**: The app scans your lyrics for Chinese, Japanese, or Korean characters. If found, it automatically bypasses Western fonts and loads CJK-compatible fonts (like Droid Sans Fallback or WenQuanYi Micro Hei) to prevent characters from showing as blank rectangles.
- **High-Readability Typography**: Features text outlines and drop shadows, ensuring text is legible on bright or busy background images.
