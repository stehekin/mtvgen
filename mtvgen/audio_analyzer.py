import os
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
try:
    from moviepy.editor import AudioFileClip
except ImportError:
    from moviepy import AudioFileClip

def load_audio_data(mp3_path, target_fs=22050):
    """
    Loads an audio file using MoviePy, extracts its sound samples as a NumPy array,
    converts it to mono, and resamples to target_fs.
    """
    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"Audio file not found: {mp3_path}")
        
    print(f"Extracting audio samples from {os.path.basename(mp3_path)}...")
    clip = AudioFileClip(mp3_path)
    duration = clip.duration
    
    # Extract sound array. Specifying fps resamples the audio
    sound_array = clip.to_soundarray(fps=target_fs)
    clip.close()
    
    # Convert stereo to mono by taking the mean of left and right channels
    if sound_array.ndim > 1:
        mono_data = sound_array.mean(axis=1)
    else:
        mono_data = sound_array
        
    return mono_data, target_fs, duration


def butter_bandpass_filter(data, lowcut, highcut, fs, order=4):
    """
    Applies a zero-phase Butterworth bandpass filter to the audio data.
    """
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    # Use filtfilt for zero-phase distortion (no phase delay/time shift in audio)
    y = filtfilt(b, a, data)
    return y


def detect_vocal_segments(mp3_path, frame_duration=0.2, threshold_ratio=0.12, min_vocal_len=0.6, max_gap_len=1.6):
    """
    Extracts vocal frequency bands (200Hz - 2000Hz), calculates moving RMS volume,
    thresholds active frames, and merges them into segments of singing.
    """
    # 1. Load Audio
    data, fs, duration = load_audio_data(mp3_path, target_fs=22050)
    
    # 2. Apply Butterworth Bandpass Filter to isolate vocals (200Hz to 2000Hz)
    filtered = butter_bandpass_filter(data, lowcut=200, highcut=2000, fs=fs, order=4)
    
    # 3. Compute short-time RMS envelope
    frame_size = int(frame_duration * fs)
    num_frames = len(filtered) // frame_size
    
    rms_envelope = []
    for i in range(num_frames):
        start_idx = i * frame_size
        end_idx = start_idx + frame_size
        window = filtered[start_idx:end_idx]
        rms = np.sqrt(np.mean(window ** 2))
        rms_envelope.append(rms)
        
    rms_envelope = np.array(rms_envelope)
    
    # Avoid divide by zero
    max_val = np.max(rms_envelope)
    if max_val == 0:
        max_val = 1.0
        
    # Normalize envelope
    rms_norm = rms_envelope / max_val
    
    # 4. Binary classification based on threshold
    active_frames = (rms_norm > threshold_ratio).astype(int)
    
    # 5. Hysteresis Smoothing: Merge short gaps and prune short spikes
    gap_frames_limit = int(max_gap_len / frame_duration)
    vocal_frames_limit = int(min_vocal_len / frame_duration)
    
    # Merge gaps (fill small silent intervals inside singing)
    gap_count = 0
    in_gap = False
    for i in range(len(active_frames)):
        if active_frames[i] == 0:
            if i > 0 and active_frames[i-1] == 1:
                in_gap = True
                gap_count = 1
            elif in_gap:
                gap_count += 1
        else:
            if in_gap:
                if gap_count <= gap_frames_limit:
                    # Fill the gap
                    active_frames[i - gap_count : i] = 1
                in_gap = False
                gap_count = 0
                
    # Prune spikes (remove short momentary noises/transients)
    active_count = 0
    in_active = False
    for i in range(len(active_frames)):
        if active_frames[i] == 1:
            if i == 0 or active_frames[i-1] == 0:
                in_active = True
                active_count = 1
            elif in_active:
                active_count += 1
        else:
            if in_active:
                if active_count < vocal_frames_limit:
                    # Clear the spike
                    active_frames[i - active_count : i] = 0
                in_active = False
                active_count = 0
                
    # 6. Extract Start & End Times
    segments = []
    in_segment = False
    start_time = 0.0
    
    for i in range(len(active_frames)):
        t = i * frame_duration
        if active_frames[i] == 1 and not in_segment:
            in_segment = True
            start_time = t
        elif active_frames[i] == 0 and in_segment:
            in_segment = False
            segments.append({"start": start_time, "end": t})
            
    # Handle end of song boundary
    if in_segment:
        segments.append({"start": start_time, "end": duration})
        
    # Post-process: If no segments found, default to entire song
    if not segments:
        print("Warning: No vocal segments detected with current threshold. Defaulting to single song-wide block.")
        segments = [{"start": 0.0, "end": duration}]
        
    return segments, duration


def detect_beats(mp3_path, min_interval=0.45):
    """
    Detects beat onsets by filtering low frequencies (sub-150Hz) and finding peaks
    in the envelope increase rate (spectral flux derivative).
    """
    # 1. Load Audio
    data, fs, duration = load_audio_data(mp3_path, target_fs=11025) # Lower sample rate is fine for bass
    
    # 2. Lowpass filter to keep bass (kick drum, bass guitar < 150 Hz)
    nyq = 0.5 * fs
    low_cutoff = 150.0
    b, a = butter(4, low_cutoff / nyq, btype='low')
    bass_data = filtfilt(b, a, data)
    
    # 3. Compute absolute amplitude envelope in 50ms windows
    window_duration = 0.05
    window_size = int(window_duration * fs)
    num_windows = len(bass_data) // window_size
    
    envelope = []
    for i in range(num_windows):
        start_idx = i * window_size
        end_idx = start_idx + window_size
        window = bass_data[start_idx:end_idx]
        envelope.append(np.mean(np.abs(window)))
        
    envelope = np.array(envelope)
    
    # 4. Compute envelope derivative (onset strength)
    # Only keep positive changes (onsets)
    diff = np.diff(envelope)
    onset_strength = np.maximum(0, diff)
    
    # Normalize
    max_onset = np.max(onset_strength)
    if max_onset == 0:
        max_onset = 1.0
    onset_strength = onset_strength / max_onset
    
    # 5. Peak Finding
    # min_interval translates to distance in windows
    min_distance_windows = int(min_interval / window_duration)
    
    peaks, _ = find_peaks(
        onset_strength,
        height=0.15,                       # minimum intensity threshold
        distance=min_distance_windows      # spacing between beats
    )
    
    beat_times = [p * window_duration for p in peaks]
    
    # If no beats found, generate periodic placeholders (e.g. every 2 seconds)
    if not beat_times:
        print("Warning: No beats detected. Generating fallback grid.")
        beat_times = list(np.arange(2.0, duration, 2.0))
        
    return beat_times
