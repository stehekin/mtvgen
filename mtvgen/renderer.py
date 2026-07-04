import os
import sys
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
try:
    from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip
except ImportError:
    from moviepy import ImageClip, AudioFileClip, CompositeVideoClip

from mtvgen.config import (
    RESOLUTIONS,
    DEFAULT_FPS,
    DEFAULT_TRANSITION_DURATION,
    MIN_IMAGE_DURATION,
    LYRIC_FONT_SIZE,
    LYRIC_FONT_COLOR,
    LYRIC_OUTLINE_COLOR,
    LYRIC_OUTLINE_WIDTH,
    LYRIC_SHADOW_COLOR,
    LYRIC_SHADOW_OFFSET,
    LYRIC_BOX_PADDING,
    LYRIC_BOX_COLOR,
    LYRIC_BOX_ROUNDING,
    LYRIC_BOTTOM_MARGIN,
    PREFERRED_FONTS
)
from mtvgen.audio_analyzer import detect_beats

def set_clip_duration(clip, duration):
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)

def set_clip_start(clip, start):
    if hasattr(clip, "with_start"):
        return clip.with_start(start)
    return clip.set_start(start)

def set_clip_audio(clip, audio):
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    return clip.set_audio(audio)

def apply_crossfadein(clip, duration):
    if hasattr(clip, "crossfadein"):
        return clip.crossfadein(duration)
    # MoviePy v2 compatibility
    try:
        from moviepy.video.fx import CrossFadeIn
        return clip.with_effects([CrossFadeIn(duration)])
    except ImportError:
        try:
            import moviepy.video.fx.all as vfx
            return clip.with_effects([vfx.crossfadein(duration)])
        except Exception:
            return clip

def apply_crossfadeout(clip, duration):
    if hasattr(clip, "crossfadeout"):
        return clip.crossfadeout(duration)
    # MoviePy v2 compatibility
    try:
        from moviepy.video.fx import CrossFadeOut
        return clip.with_effects([CrossFadeOut(duration)])
    except ImportError:
        try:
            import moviepy.video.fx.all as vfx
            return clip.with_effects([vfx.crossfadeout(duration)])
        except Exception:
            return clip

def apply_fadein(clip, duration):
    if hasattr(clip, "fadein"):
        return clip.fadein(duration)
    # MoviePy v2 compatibility
    try:
        from moviepy.video.fx import FadeIn
        return clip.with_effects([FadeIn(duration)])
    except ImportError:
        try:
            import moviepy.video.fx.all as vfx
            return clip.with_effects([vfx.fadein(duration)])
        except Exception:
            return clip

def apply_fadeout(clip, duration):
    if hasattr(clip, "fadeout"):
        return clip.fadeout(duration)
    # MoviePy v2 compatibility
    try:
        from moviepy.video.fx import FadeOut
        return clip.with_effects([FadeOut(duration)])
    except ImportError:
        try:
            import moviepy.video.fx.all as vfx
            return clip.with_effects([vfx.fadeout(duration)])
        except Exception:
            return clip

def set_clip_position(clip, pos):
    if hasattr(clip, "with_position"):
        return clip.with_position(pos)
    return clip.set_position(pos)

def resize_and_crop(image_path, target_width, target_height):
    """
    Opens an image, crops it from the center to match the target aspect ratio,
    and resizes it to the target resolution (Aspect Fill).
    """
    img = Image.open(image_path)
    if img.mode != "RGB":
        img = img.convert("RGB")
        
    img_w, img_h = img.size
    
    target_aspect = target_width / target_height
    img_aspect = img_w / img_h
    
    if img_aspect > target_aspect:
        new_w = int(img_h * target_aspect)
        left = (img_w - new_w) // 2
        right = left + new_w
        top = 0
        bottom = img_h
    else:
        new_h = int(img_w / target_aspect)
        top = (img_h - new_h) // 2
        bottom = top + new_h
        left = 0
        right = img_w
        
    img_cropped = img.crop((left, top, right, bottom))
    img_resized = img_cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
    return img_resized


def get_font(font_size, is_cjk=False):
    """
    Attempts to load a premium font from preferred font names, checking standard
    system font directories. Falls back to default Pillow font if none found.
    Prioritizes CJK-supporting fonts if is_cjk is True.
    """
    system_paths = []
    if sys.platform.startswith("linux"):
        system_paths = [
            "/usr/share/fonts",
            "/usr/share/fonts/truetype",
            "/usr/share/fonts/TTF",
            "/usr/share/fonts/opentype",  # CJK fonts are often OTF
            os.path.expanduser("~/.local/share/fonts")
        ]
    elif sys.platform == "darwin":  # macOS
        system_paths = [
            "/Library/Fonts",
            "/System/Library/Fonts",
            os.path.expanduser("~/Library/Fonts")
        ]
    elif sys.platform == "win32":
        system_paths = [
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Fonts")
        ]

    cjk_fonts = [
        "wqy-microhei.ttc",
        "wqy-zenhei.ttc",
        "DroidSansFallback.ttf",
        "DroidSansFallbackFull.ttf",
        "NotoSansCJKsc-Regular.otf",
        "NotoSansCJK-Regular.ttc",
        "SourceHanSansCN-Regular.otf",
        "SourceHanSans-Regular.ttc",
        "NotoSansCJK.ttc",
        "NotoSansCJKsc-Bold.otf",
        "SourceHanSansSC-Regular.otf",
        "msyh.ttc",  # Microsoft YaHei
        "simsun.ttc", # SimSun
        "simhei.ttf"  # SimHei
    ]

    search_fonts = cjk_fonts + PREFERRED_FONTS if is_cjk else PREFERRED_FONTS

    for font_name in search_fonts:
        try:
            return ImageFont.truetype(font_name, font_size)
        except IOError:
            pass
            
        for path in system_paths:
            if not os.path.exists(path):
                continue
            for root, dirs, files in os.walk(path):
                if font_name in files:
                    try:
                        return ImageFont.truetype(os.path.join(root, font_name), font_size)
                    except IOError:
                        pass
                for f in files:
                    if f.lower() == font_name.lower():
                        try:
                            return ImageFont.truetype(os.path.join(root, f), font_size)
                        except IOError:
                            pass

    fallback_names = ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf", "Helvetica.ttf"]
    if is_cjk:
        fallback_names = ["wqy-microhei.ttc", "wqy-zenhei.ttc", "DroidSansFallback.ttf"] + fallback_names

    for fallback in fallback_names:
        for path in system_paths:
            if not os.path.exists(path):
                continue
            for root, dirs, files in os.walk(path):
                if fallback in files:
                    try:
                        return ImageFont.truetype(os.path.join(root, fallback), font_size)
                    except IOError:
                        pass

    print("Warning: Could not load any system TrueType fonts. Using default basic font.")
    return ImageFont.load_default()


def get_text_metrics_with_fallback(text, font_western, font_cjk):
    """
    Measures the text line and returns (total_width, visual_height, global_offset_y).
    This ensures pixel-perfect vertical centering by measuring the combined bounding box
    of all characters in the string across the two fallback fonts.
    """
    if not text:
        return 0, 0, 0
        
    total_w = 0
    global_min_y = 9999
    global_max_y = -9999
    
    # Temporary draw context
    draw_temp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    
    for char in text:
        is_char_cjk = ('\u4e00' <= char <= '\u9fff' or 
                       '\u3040' <= char <= '\u30ff' or 
                       '\u1100' <= char <= '\u11ff' or
                       '\uac00' <= char <= '\ud7af' or
                       '\uff00' <= char <= '\uffef')
        font = font_cjk if is_char_cjk else font_western
        
        # Width advance
        if hasattr(font, 'getlength'):
            char_w = int(font.getlength(char))
        else:
            char_w = font.getsize(char)[0]
        total_w += char_w
        
        # Bounding box vertical bounds
        if hasattr(font, 'getbbox'):
            bbox = font.getbbox(char)
        else:
            w, h = draw_temp.textsize(char, font=font)
            bbox = (0, 0, w, h)
            
        if bbox:
            min_y = bbox[1]
            max_y = bbox[3]
            if min_y < global_min_y:
                global_min_y = min_y
            if max_y > global_max_y:
                global_max_y = max_y
                
    if global_min_y == 9999:
        global_min_y = 0
    if global_max_y == -9999:
        global_max_y = 48  # Default estimate
        
    visual_height = global_max_y - global_min_y
    return total_w, visual_height, global_min_y

def draw_text_with_fallback(draw, text, x, y, font_western, font_cjk, fill, global_offset_y, stroke_width=0, stroke_fill=None):
    """
    Renders text character-by-character, dynamically choosing between a Western font
    and a CJK font. Keeps characters perfectly aligned on the typographical baseline.
    Spaces are bypassed and only cursor-advanced to prevent Pillow space outline bugs.
    """
    curr_x = x
    for char in text:
        is_char_cjk = ('\u4e00' <= char <= '\u9fff' or 
                       '\u3040' <= char <= '\u30ff' or 
                       '\u1100' <= char <= '\u11ff' or
                       '\uac00' <= char <= '\ud7af' or
                       '\uff00' <= char <= '\uffef')
        font = font_cjk if is_char_cjk else font_western
        
        if hasattr(font, 'getlength'):
            char_w = int(font.getlength(char))
        else:
            char_w = font.getsize(char)[0]
        
        # Space characters: bypass drawing completely, just advance cursor to avoid outlines
        if char in (" ", "\u3000", "\t"):
            curr_x += char_w
            continue
            
        # Draw character at aligned baseline
        draw.text(
            (curr_x, y - global_offset_y),
            char,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill
        )
        curr_x += char_w

def render_lyric_frame(width, height, active_text, font_western, font_cjk, start_time):
    """
    Renders the lyric box as a small transparent PIL image (only the current sentence),
    and calculates its position on the main screen. Avoids overlapping with the intro title
    card by shifting early lyrics to the bottom. Uses pixel-exact offset compensation
    and font fallback to align and render the text perfectly.
    """
    active_w, active_h, global_offset_y = get_text_metrics_with_fallback(active_text, font_western, font_cjk)
    
    box_w = active_w + (LYRIC_BOX_PADDING[0] * 2)
    box_h = active_h + (LYRIC_BOX_PADDING[1] * 2)
    
    # Cap box width at 90% of screen width to prevent overflow
    max_box_w = int(width * 0.9)
    if box_w > max_box_w:
        box_w = max_box_w

    # Create box image of exact dimensions (cropped)
    box_img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(box_img)
    
    if active_text:
        if hasattr(draw, "rounded_rectangle"):
            draw.rounded_rectangle(
                [0, 0, box_w, box_h],
                radius=LYRIC_BOX_ROUNDING,
                fill=LYRIC_BOX_COLOR
            )
        else:
            draw.rectangle(
                [0, 0, box_w, box_h],
                fill=LYRIC_BOX_COLOR
            )

    active_y = LYRIC_BOX_PADDING[1]
    active_x = (box_w - active_w) // 2
    
    if active_text:
        # Draw Drop shadow (with offset)
        draw_text_with_fallback(
            draw, active_text, 
            active_x + LYRIC_SHADOW_OFFSET[0], active_y + LYRIC_SHADOW_OFFSET[1], 
            font_western, font_cjk, 
            LYRIC_SHADOW_COLOR,
            global_offset_y
        )
        # Draw Main text with outline
        draw_text_with_fallback(
            draw, active_text, 
            active_x, active_y, 
            font_western, font_cjk, 
            LYRIC_FONT_COLOR,
            global_offset_y,
            stroke_width=LYRIC_OUTLINE_WIDTH,
            stroke_fill=LYRIC_OUTLINE_COLOR
        )

    # Position calculations: center horizontally
    x_pos = (width - box_w) // 2
    
    # If the lyric falls during the intro title card (first 5.0 seconds), 
    # position it at the bottom to avoid overlapping with the centered title card.
    if start_time < 5.0:
        y_pos = height - 100 - box_h  # Bottom third
    else:
        y_pos = (height - box_h) // 2 # Centered
        
    return box_img, x_pos, y_pos

def render_title_frame(width, height, title_text, font_title_w, font_title_c):
    """
    Renders a transparent frame containing the large centered song title.
    """
    frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)

    # Calculate title size
    title_w, title_h, title_offset_y = get_text_metrics_with_fallback(title_text, font_title_w, font_title_c)
    
    # Center title vertically
    title_x = (width - title_w) // 2
    title_y = (height - title_h) // 2
    
    # Draw Main Song Title
    title_x = (width - title_w) // 2
    draw_text_with_fallback(
        draw, title_text, 
        title_x + 4, title_y + 4, 
        font_title_w, font_title_c, 
        LYRIC_SHADOW_COLOR,
        title_offset_y
    )
    draw_text_with_fallback(
        draw, title_text, 
        title_x, title_y, 
        font_title_w, font_title_c, 
        LYRIC_FONT_COLOR,
        title_offset_y,
        stroke_width=LYRIC_OUTLINE_WIDTH,
        stroke_fill=LYRIC_OUTLINE_COLOR
    )
    
    # Draw a thin decorative line below (gap of 25px)
    line_w = int(title_w * 1.2)
    if line_w > width * 0.8:
        line_w = int(width * 0.8)
    line_x1 = (width - line_w) // 2
    line_x2 = line_x1 + line_w
    line_y = title_y + title_h + 25
    
    # Draw line with shadow
    draw.line([line_x1 + 2, line_y + 2, line_x2 + 2, line_y + 2], fill=(0, 0, 0, 100), width=3)
    draw.line([line_x1, line_y, line_x2, line_y], fill=(255, 255, 255, 180), width=3)
    
    return frame

def create_music_video(
    image_paths,
    aligned_lyrics,
    mp3_path,
    output_path,
    resolution_name="landscape",
    transition_duration=DEFAULT_TRANSITION_DURATION,
    effect_style="random",
    enable_beat_sync=True,
    song_title=None,
    custom_font_path=None,
    font_color=None,
    box_color=None,
    shadow_color=None,
    preview_duration=None,
    fps=DEFAULT_FPS
):
    """
    Builds the slideshow video (optionally beat-synced), renders transparent lyric overlays,
    composites them, adds audio, and outputs the final MP4.
    """
    if not image_paths:
        raise ValueError("Must provide at least one image path.")
    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"MP3 file not found: {mp3_path}")

    # Override visual style from parameters if provided
    global LYRIC_FONT_COLOR, LYRIC_BOX_COLOR, LYRIC_SHADOW_COLOR
    if font_color is not None:
        LYRIC_FONT_COLOR = font_color
    if box_color is not None:
        LYRIC_BOX_COLOR = box_color
    if shadow_color is not None:
        LYRIC_SHADOW_COLOR = shadow_color

    # 1. Load Audio and determine video duration
    print("Loading audio track...")
    audio_clip = AudioFileClip(mp3_path)
    total_duration = audio_clip.duration
    
    if preview_duration is not None and preview_duration > 0:
        total_duration = min(total_duration, float(preview_duration))
        audio_clip = audio_clip.subclip(0, total_duration)
        print(f"PREVIEW MODE: Capping video duration to first {total_duration:.2f} seconds.")
    else:
        print(f"Song duration: {total_duration:.2f} seconds")

    target_w, target_h = RESOLUTIONS.get(resolution_name, RESOLUTIONS["landscape"])
    print(f"Target video resolution: {target_w}x{target_h} ({resolution_name})")

    # 2. Setup Slideshow Timelines
    num_images = len(image_paths)
    image_timings = [] # List of tuples: (start_time, end_time)
    
    if enable_beat_sync and num_images > 1:
        try:
            print("Detecting beat onsets for transition synchronization...")
            beat_times = detect_beats(mp3_path)
            print(f"Detected {len(beat_times)} beats in audio.")
            
            # Distribute images on beats
            beats_per_image = max(1, round(len(beat_times) / num_images))
            
            transition_timestamps = [0.0]
            for i in range(1, num_images):
                beat_idx = min(len(beat_times) - 1, i * beats_per_image)
                transition_timestamps.append(beat_times[beat_idx])
            transition_timestamps.append(total_duration)
            
            for i in range(num_images):
                image_timings.append((transition_timestamps[i], transition_timestamps[i+1]))
                
            print("Beat-synced slide transition timings generated.")
        except Exception as e:
            print(f"Beat detection failed ({e}). Falling back to uniform spacing.")
            enable_beat_sync = False

    if not enable_beat_sync or num_images <= 1:
        # Uniform distribution
        base_img_duration = total_duration / num_images
        current_time = 0.0
        for i in range(num_images):
            end_time = current_time + base_img_duration
            if i == num_images - 1:
                end_time = total_duration
            image_timings.append((current_time, end_time))
            current_time = end_time
            
        print("Uniform slide transition timings generated.")

    # 3. Build Background Slideshow
    print("Building background slideshow...")
    bg_clips = []
    
    for i in range(num_images):
        start, end = image_timings[i]
        clip_duration = end - start
        
        display_duration = clip_duration
        if i < num_images - 1:
            display_duration += transition_duration
            
        if start + display_duration > total_duration:
            display_duration = total_duration - start

        if display_duration <= 0:
            continue

        print(f"  Processing Background Image {i+1}/{num_images}: {os.path.basename(image_paths[i])} ({clip_duration:.2f}s) [Effect: {effect_style}]")
        
        pil_img = resize_and_crop(image_paths[i], target_w, target_h)
        np_img = np.array(pil_img)

        # Base ImageClip creation
        img_clip = set_clip_duration(ImageClip(np_img), display_duration)
        img_clip = set_clip_start(img_clip, start)

        # Select a random effect style if "random" is chosen
        current_effect = effect_style
        if effect_style == "random":
            current_effect = random.choice(["fade", "focus-reveal", "grayscale-reveal", "flash-white"])
            print(f"    Selected random effect for slide: {current_effect}")

        # Flat composition: append sub-clips to the main list directly to avoid slow nested CompositeVideoClips
        if current_effect == "focus-reveal" and display_duration > 1.5:
            # Pre-blur the image and crossfade from blurred to sharp over 1.5s
            pil_blur = pil_img.filter(ImageFilter.GaussianBlur(radius=15))
            np_blur = np.array(pil_blur)
            
            blur_clip = set_clip_duration(ImageClip(np_blur), display_duration)
            blur_clip = set_clip_start(blur_clip, start)
            
            sharp_clip = apply_crossfadein(img_clip, 1.5)
            
            bg_clips.append(blur_clip)
            bg_clips.append(sharp_clip)
            
        elif current_effect == "grayscale-reveal" and display_duration > 1.5:
            pil_gray = pil_img.convert("L").convert("RGB")
            np_gray = np.array(pil_gray)
            
            gray_clip = set_clip_duration(ImageClip(np_gray), display_duration)
            gray_clip = set_clip_start(gray_clip, start)
            
            color_clip = apply_crossfadein(img_clip, 1.5)
            
            bg_clips.append(gray_clip)
            bg_clips.append(color_clip)
            
        elif current_effect == "flash-white" and display_duration > 0.4:
            # Overlay a brief white flash at the start of the slide transition
            white_img = np.ones_like(np_img) * 255
            white_clip = set_clip_duration(ImageClip(white_img), 0.4)
            white_clip = set_clip_start(white_clip, start)
            white_clip = apply_fadeout(white_clip, 0.4)
            
            if i > 0 and transition_duration > 0:
                img_clip = apply_crossfadein(img_clip, transition_duration)
                
            bg_clips.append(img_clip)
            bg_clips.append(white_clip)
            
        else: # Standard "fade"
            if i > 0 and transition_duration > 0:
                img_clip = apply_crossfadein(img_clip, transition_duration)
                
            bg_clips.append(img_clip)

    slideshow_video = CompositeVideoClip(bg_clips, size=(target_w, target_h))
    
    # Apply global fade-in and fade-out to the entire slideshow background
    print("Applying global fade-in and fade-out transitions...")
    slideshow_video = apply_fadein(slideshow_video, 1.5)
    slideshow_video = apply_fadeout(slideshow_video, 1.5)

    # 4. Create Lyric & Title Overlays
    print("Generating lyric and title overlays...")
    is_cjk = False
    
    # Check lyrics for CJK
    for item in aligned_lyrics:
        for char in item.get("text", ""):
            if ('\u4e00' <= char <= '\u9fff' or 
                '\u3040' <= char <= '\u30ff' or 
                '\u1100' <= char <= '\u11ff' or
                '\uac00' <= char <= '\ud7af' or
                '\uff00' <= char <= '\uffef'):
                is_cjk = True
                break
        if is_cjk:
            break
            
    # Check title for CJK
    if song_title:
        for char in song_title:
            if ('\u4e00' <= char <= '\u9fff' or 
                '\u3040' <= char <= '\u30ff' or 
                '\u1100' <= char <= '\u11ff' or
                '\uac00' <= char <= '\ud7af' or
                '\uff00' <= char <= '\uffef'):
                is_cjk = True
                break
            
    if is_cjk:
        print("CJK characters detected in text. Prioritizing Chinese/Japanese/Korean system fonts.")
        
    # Verify and load custom user font if specified
    if custom_font_path:
        if os.path.exists(custom_font_path):
            try:
                # Test load to verify TTF integrity
                test_font = ImageFont.truetype(custom_font_path, LYRIC_FONT_SIZE)
                print(f"Using custom user-specified font: {custom_font_path}")
            except Exception as e:
                print(f"Error loading custom font '{custom_font_path}' ({e}). Falling back to system fonts.")
                custom_font_path = None
        else:
            print(f"Custom font path not found: '{custom_font_path}'. Falling back to system fonts.")
            custom_font_path = None

    if custom_font_path:
        font_w = ImageFont.truetype(custom_font_path, LYRIC_FONT_SIZE)
        font_c = ImageFont.truetype(custom_font_path, LYRIC_FONT_SIZE)
    else:
        font_w = get_font(LYRIC_FONT_SIZE, is_cjk=False)
        font_c = get_font(LYRIC_FONT_SIZE, is_cjk=is_cjk)
    
    lyric_clips = []
    
    # Render song title card at the start of the video
    if song_title and total_duration > 5.0:
        print(f"Creating intro title card overlay: '{song_title}'")
        if custom_font_path:
            font_title_w = ImageFont.truetype(custom_font_path, 110)
            font_title_c = ImageFont.truetype(custom_font_path, 110)
        else:
            font_title_w = get_font(110, is_cjk=False)
            font_title_c = get_font(110, is_cjk=is_cjk)
        
        title_pil = render_title_frame(
            target_w, target_h, song_title, 
            font_title_w, font_title_c
        )
        title_np = np.array(title_pil)
        
        # Display title for the first 5 seconds, fading in/out
        title_clip = set_clip_duration(ImageClip(title_np), 5.0)
        title_clip = set_clip_start(title_clip, 0.0)
        title_clip = apply_crossfadein(title_clip, 1.0)
        title_clip = apply_crossfadeout(title_clip, 1.0)
        
        lyric_clips.append(title_clip)
    for i, item in enumerate(aligned_lyrics):
        start = item["start"]
        end = item["end"]
        text = item["text"]
        
        if not text.strip():
            continue
            
        if start >= total_duration:
            continue
        end = min(end, total_duration)
        duration = end - start
        if duration <= 0:
            continue
            
        frame_pil, x_pos, y_pos = render_lyric_frame(target_w, target_h, text, font_w, font_c, start)
        frame_np = np.array(frame_pil)
        
        # Create a small ImageClip positioned at calculated coordinates, saving 90% blending pixel computations
        lyric_clip = set_clip_duration(ImageClip(frame_np), duration)
        lyric_clip = set_clip_start(lyric_clip, start)
        lyric_clip = set_clip_position(lyric_clip, (x_pos, y_pos))
        
        if duration > 0.6:
            lyric_clip = apply_crossfadein(lyric_clip, 0.2)
            lyric_clip = apply_crossfadeout(lyric_clip, 0.2)
            
        lyric_clips.append(lyric_clip)

    # 5. Assemble Final Composition
    print("Compositing video track and audio track...")
    final_video = CompositeVideoClip([slideshow_video] + lyric_clips, size=(target_w, target_h))
    final_video = set_clip_duration(final_video, total_duration)
    final_video = set_clip_audio(final_video, audio_clip)

    # 6. Render Output File
    num_threads = os.cpu_count() or 2
    print(f"Rendering final music video using {num_threads} CPU threads (preset: ultrafast)...")
    final_video.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        threads=num_threads,
        preset="ultrafast"
    )
    
    audio_clip.close()
    final_video.close()
    print("Rendering complete!")
