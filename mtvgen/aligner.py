import re
import os
import time
from mtvgen.audio_analyzer import detect_vocal_segments

def parse_lrc(lrc_path, song_duration=None):
    """
    Parses a standard LRC file and returns a list of lyric segments:
    [(start_time, end_time, lyric_text), ...]
    """
    if not os.path.exists(lrc_path):
        raise FileNotFoundError(f"LRC file not found: {lrc_path}")

    # Standard LRC tag: [mm:ss.xx] or [mm:ss:xx] or [mm:ss]
    pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
    
    events = []
    with open(lrc_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Find all timestamps in the line
            matches = list(pattern.finditer(line))
            if not matches:
                continue
            
            last_match = matches[-1]
            text = line[last_match.end():].strip()
            
            for m in matches:
                minutes = int(m.group(1))
                seconds = float(m.group(2))
                total_seconds = minutes * 60 + seconds
                events.append((total_seconds, text))

    # Sort events by timestamp
    events.sort(key=lambda x: x[0])
    
    if not events:
        raise ValueError(f"No valid lyric timestamps found in LRC file: {lrc_path}")

    aligned_lyrics = []
    for i in range(len(events)):
        start_time = events[i][0]
        text = events[i][1]
        
        # End time is the start of the next line, or start + 5 seconds (capped at song_duration)
        if i < len(events) - 1:
            end_time = events[i+1][0]
        else:
            end_time = start_time + 5.0
            if song_duration:
                end_time = min(end_time, song_duration)
        
        aligned_lyrics.append({
            "start": start_time,
            "end": end_time,
            "text": text
        })
        
    return aligned_lyrics


def run_interactive_tapper(mp3_path, lyrics_path, output_lrc_path=None):
    """
    Plays the MP3 file using pygame.mixer and prompts the user to tap
    Enter in the terminal to capture timestamps for each lyric line.
    Saves the result to output_lrc_path.
    """
    import pygame
    
    if not os.path.exists(lyrics_path):
        raise FileNotFoundError(f"Lyrics file not found: {lyrics_path}")
    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"MP3 song file not found: {mp3_path}")

    # Load lyrics
    with open(lyrics_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        raise ValueError("Lyrics file is empty.")

    print("\n" + "="*60)
    print("           MTVGen - Interactive Lyric Tapper")
    print("="*60)
    print("Instructions:")
    print("1. The song will play shortly after you press Enter to start.")
    print("2. Listen to the song. As soon as you hear the line displayed,")
    print("   press Enter to record its start timestamp.")
    print("3. There will be a final press at the end to stamp the end of the last line.")
    print("="*60)
    
    input("Press Enter to initialize audio and start...")

    # Initialize Pygame Mixer
    pygame.mixer.init()
    pygame.mixer.music.load(mp3_path)
    
    print("\nPlaying audio...")
    pygame.mixer.music.play()
    
    timestamps = []
    
    for i, line in enumerate(lines):
        print(f"\n---> ACTIVE LINE ({i+1}/{len(lines)}):")
        print(f"     \033[1;32;40m{line}\033[0m")
        if i + 1 < len(lines):
            print(f"     Next: {lines[i+1]}")
        else:
            print("     Next: [End of Song]")
            
        input("[Press ENTER to stamp]")
        
        pos_ms = pygame.mixer.music.get_pos()
        pos_sec = pos_ms / 1000.0
        timestamps.append((pos_sec, line))
        print(f"Stamped at {pos_sec:.2f} seconds.")

    print("\n---> FINAL STAMP (End of last line / Outro start):")
    input("[Press ENTER to stamp final lyric end]")
    final_pos_sec = pygame.mixer.music.get_pos() / 1000.0
    timestamps.append((final_pos_sec, "[End]"))
    
    pygame.mixer.music.stop()
    pygame.mixer.quit()

    # Create LRC content
    lrc_lines = []
    for i in range(len(timestamps) - 1):
        t_sec = timestamps[i][0]
        text = timestamps[i][1]
        
        minutes = int(t_sec // 60)
        seconds = t_sec % 60
        timestamp_str = f"[{minutes:02d}:{seconds:05.2f}]"
        lrc_lines.append(f"{timestamp_str} {text}")
        
    if not output_lrc_path:
        base, _ = os.path.splitext(lyrics_path)
        output_lrc_path = base + ".lrc"
        
    with open(output_lrc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lrc_lines) + "\n")
        
    print(f"\nSuccess! Timestamps saved to: {output_lrc_path}")
    print("="*60)
    
    aligned_lyrics = []
    for i in range(len(timestamps) - 1):
        aligned_lyrics.append({
            "start": timestamps[i][0],
            "end": timestamps[i+1][0],
            "text": timestamps[i][1]
        })
        
    return aligned_lyrics, output_lrc_path


def generate_vocal_energy_alignment(lyrics_path, mp3_path):
    """
    Finds active singing segments using DSP frequency band analysis,
    then distributes lyrics proportionally within those blocks.
    """
    if not os.path.exists(lyrics_path):
        raise FileNotFoundError(f"Lyrics file not found: {lyrics_path}")
        
    print("Analyzing audio files for singing segments...")
    segments, song_duration = detect_vocal_segments(mp3_path)
    
    with open(lyrics_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
        
    if not lines:
        raise ValueError("Lyrics file is empty.")
        
    num_lines = len(lines)
    num_segments = len(segments)
    
    print(f"Distributing {num_lines} lyric lines across {num_segments} detected vocal blocks.")
    
    seg_durations = [seg["end"] - seg["start"] for seg in segments]
    total_active_time = sum(seg_durations)
    
    if total_active_time < 1.0:
        print("Warning: Active vocal duration too short. Spacing lines linearly.")
        return generate_linear_alignment(lyrics_path, song_duration)
        
    # Allocate lines to segments proportionally (greedy distribution)
    if num_lines >= num_segments:
        assigned_counts = [1] * num_segments
        remaining = num_lines - num_segments
    else:
        assigned_counts = [0] * num_segments
        for i in range(num_lines):
            assigned_counts[i] = 1
        remaining = 0
        
    if remaining > 0:
        weights = [d / total_active_time for d in seg_durations]
        for _ in range(remaining):
            proportions = [assigned_counts[i] / num_lines for i in range(num_segments)]
            deficits = [weights[i] - proportions[i] for i in range(num_segments)]
            best_idx = deficits.index(max(deficits))
            assigned_counts[best_idx] += 1
            
    # Generate timestamps for each line within its segment
    aligned_lyrics = []
    line_idx = 0
    for seg_idx, seg in enumerate(segments):
        count = assigned_counts[seg_idx]
        if count == 0:
            continue
            
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_dur = seg_end - seg_start
        
        line_dur = seg_dur / count
        for c in range(count):
            if line_idx >= num_lines:
                break
            l_start = seg_start + c * line_dur
            l_end = l_start + line_dur
            aligned_lyrics.append({
                "start": l_start,
                "end": l_end,
                "text": lines[line_idx]
            })
            line_idx += 1
            
    return aligned_lyrics


def generate_linear_alignment(lyrics_path, song_duration):
    """
    Fallback method: Evenly distributes lyric lines across the song duration.
    Assumes a 3-second intro and a 3-second outro buffer.
    """
    if not os.path.exists(lyrics_path):
        raise FileNotFoundError(f"Lyrics file not found: {lyrics_path}")

    with open(lyrics_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        raise ValueError("Lyrics file is empty.")

    intro_duration = 3.0
    outro_duration = 3.0
    
    usable_duration = max(2.0, song_duration - intro_duration - outro_duration)
    line_duration = usable_duration / len(lines)
    
    aligned_lyrics = []
    for i, line in enumerate(lines):
        start = intro_duration + i * line_duration
        end = start + line_duration
        aligned_lyrics.append({
            "start": start,
            "end": end,
            "text": line
        })
        
    return aligned_lyrics
