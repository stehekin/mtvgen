import os
import argparse
from mtvgen.aligner import parse_lrc, run_interactive_tapper, generate_vocal_energy_alignment, generate_linear_alignment
from mtvgen.renderer import create_music_video
try:
    from moviepy.editor import AudioFileClip
except ImportError:
    from moviepy import AudioFileClip

VALID_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff")

def find_images(image_input):
    """
    Given a path (directory or list of files), finds and returns all valid image paths.
    """
    image_paths = []
    
    if os.path.isdir(image_input):
        for root, _, files in os.walk(image_input):
            for file in files:
                if file.lower().endswith(VALID_IMAGE_EXTENSIONS):
                    image_paths.append(os.path.join(root, file))
        image_paths.sort()
    elif os.path.isfile(image_input) and image_input.lower().endswith(VALID_IMAGE_EXTENSIONS):
        image_paths = [image_input]
    else:
        parts = image_input.split(",")
        for part in parts:
            part = part.strip()
            if os.path.isfile(part) and part.lower().endswith(VALID_IMAGE_EXTENSIONS):
                image_paths.append(part)
                
    return image_paths


def main():
    parser = argparse.ArgumentParser(
        description="MTVGen: Python-based Music Video Generator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required inputs
    parser.add_argument(
        "-i", "--images",
        required=True,
        help="Path to a directory containing images, or a comma-separated list of image files."
    )
    parser.add_argument(
        "-l", "--lyrics",
        required=True,
        help="Path to the lyrics file (.txt for plain text, .lrc for timed lyrics)."
    )
    parser.add_argument(
        "-s", "--song",
        required=True,
        help="Path to the MP3 song file."
    )
    
    # Outputs & Styling
    parser.add_argument(
        "-o", "--output",
        default="output.mp4",
        help="Path to the output MP4 video file."
    )
    parser.add_argument(
        "-r", "--resolution",
        choices=[
            "landscape", "portrait", "square",
            "landscape_1080p", "landscape_720p", "landscape_480p",
            "portrait_1080p", "portrait_720p", "portrait_480p",
            "square_720p", "square_480p"
        ],
        default="landscape",
        help="Video aspect ratio and resolution preset."
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=15,
        help="Frames per second of the output video."
    )
    parser.add_argument(
        "--transition",
        type=float,
        default=1.0,
        help="Crossfade transition duration between pictures (in seconds)."
    )
    parser.add_argument(
        "--effect",
        choices=["fade", "focus-reveal", "grayscale-reveal", "flash-white", "random"],
        default="random",
        help="Visual transition effect style for background images."
    )
    parser.add_argument(
        "--title",
        help="Song title to display at the beginning of the video (defaults to filename)."
    )
    parser.add_argument(
        "--font",
        help="Path to a custom TTF/OTF font file to use for text rendering."
    )


    parser.add_argument(
        "--no-beat-sync",
        action="store_true",
        help="Disable aligning picture transitions to the song's musical beat."
    )
    parser.add_argument(
        "--preview",
        type=float,
        nargs="?",
        const=10.0,
        default=None,
        help="Generate a short preview video of specified duration in seconds (default: 10.0s)."
    )
    
    # Alignment Modes
    parser.add_argument(
        "-m", "--mode",
        choices=["auto", "tap", "lrc", "energy", "linear"],
        default="auto",
        help=(
            "Lyric alignment mode. 'auto' parses LRC timestamps if present, falling back to 'energy'. "
            "'tap' runs the interactive terminal tapper. 'lrc' parses timestamped LRC. "
            "'energy' uses vocal-range frequency analysis (non-AI). 'linear' spaces lyrics evenly."
        )
    )
    
    args = parser.parse_args()

    # 1. Validate inputs
    if not os.path.exists(args.song):
        print(f"Error: Song file not found: {args.song}")
        return 1
        
    if not os.path.exists(args.lyrics):
        print(f"Error: Lyrics file not found: {args.lyrics}")
        return 1

    image_paths = find_images(args.images)
    if not image_paths:
        print(f"Error: No valid images ({', '.join(VALID_IMAGE_EXTENSIONS)}) found at: {args.images}")
        return 1
        
    print(f"Found {len(image_paths)} images.")

    # 2. Determine song duration
    try:
        audio = AudioFileClip(args.song)
        song_duration = audio.duration
        audio.close()
    except Exception as e:
        print(f"Error loading song duration: {e}")
        return 1

    # 3. Handle Lyric Alignment based on Mode
    aligned_lyrics = []
    
    mode = args.mode
    if mode == "auto":
        if args.lyrics.lower().endswith(".lrc"):
            mode = "lrc"
        else:
            print("\nLyrics file does not end in '.lrc'. Using Vocal Energy Analysis for smart spacing.")
            print("For perfect timing, run with '-m tap' to record timestamps manually.\n")
            mode = "energy"
            
    if mode == "lrc":
        print(f"Parsing timestamped LRC lyrics: {args.lyrics}")
        try:
            aligned_lyrics = parse_lrc(args.lyrics, song_duration)
        except Exception as e:
            print(f"Error parsing LRC file: {e}")
            print("Falling back to Vocal Energy Analysis...")
            mode = "energy"

    if mode == "tap":
        try:
            aligned_lyrics, lrc_file_path = run_interactive_tapper(args.song, args.lyrics)
            print(f"Successfully timed lyrics. Proceeding to rendering.")
        except Exception as e:
            print(f"Error during interactive tapping: {e}")
            print("Falling back to Vocal Energy Analysis.")
            mode = "energy"

    if mode == "energy":
        print("Analyzing vocals to synchronize lyric spacing...")
        try:
            aligned_lyrics = generate_vocal_energy_alignment(args.lyrics, args.song)
        except Exception as e:
            print(f"Vocal energy analysis failed: {e}")
            print("Falling back to basic linear distribution.")
            mode = "linear"

    if mode == "linear":
        print("Generating even linear distribution for lyrics...")
        try:
            aligned_lyrics = generate_linear_alignment(args.lyrics, song_duration)
        except Exception as e:
            print(f"Error generating linear alignment: {e}")
            return 1

    # 4. Determine Song Title for Video Intro
    song_title = args.title
    if not song_title:
        base_name = os.path.basename(args.song)
        name_without_ext, _ = os.path.splitext(base_name)
        song_title = name_without_ext.replace("_", " ").replace("-", " ").title()

    # 5. Run Video Generator
    print("\nStarting video generation process...")
    try:
        create_music_video(
            image_paths=image_paths,
            aligned_lyrics=aligned_lyrics,
            mp3_path=args.song,
            output_path=args.output,
            resolution_name=args.resolution,
            transition_duration=args.transition,
            effect_style=args.effect,
            enable_beat_sync=not args.no_beat_sync,
            song_title=song_title,
            custom_font_path=args.font,
            preview_duration=args.preview,
            fps=args.fps
        )
        print(f"\nSUCCESS! Music video created at: {args.output}")
    except Exception as e:
        print(f"\nError rendering video: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
