import os

# Video Resolutions
RESOLUTIONS = {
    "landscape": (1280, 720),       # High Definition (Fast default)
    "landscape_1080p": (1920, 1080), # Full HD (Slow master)
    "landscape_720p": (1280, 720),   # HD
    "landscape_480p": (854, 480),    # Standard Definition (Extremely fast)
    
    "portrait": (720, 1280),        # Mobile HD
    "portrait_1080p": (1080, 1920), # Mobile Full HD (Slow)
    "portrait_720p": (720, 1280),
    "portrait_480p": (480, 854),
    
    "square": (720, 720),
    "square_720p": (720, 720),
    "square_480p": (480, 480)
}

# Default Configuration Settings
DEFAULT_RESOLUTION_NAME = "landscape"
DEFAULT_FPS = 15

# Slideshow Settings
DEFAULT_TRANSITION_DURATION = 1.0  # seconds (crossfade)
MIN_IMAGE_DURATION = 2.0          # seconds minimum per image

# Lyric Styling
LYRIC_FONT_SIZE = 56
LYRIC_FONT_COLOR = (255, 255, 255)       # RGB
LYRIC_OUTLINE_COLOR = (0, 0, 0)          # RGB
LYRIC_OUTLINE_WIDTH = 4                  # pixels
LYRIC_SHADOW_COLOR = (0, 0, 0, 150)       # RGBA
LYRIC_SHADOW_OFFSET = (4, 4)             # x, y pixels
LYRIC_BOX_PADDING = (30, 15)             # horizontal, vertical padding inside the box
LYRIC_BOX_COLOR = (0, 0, 0, 100)         # RGBA (frosted glass semi-transparent black)
LYRIC_BOX_ROUNDING = 15                  # px corner radius
LYRIC_BOTTOM_MARGIN = 120                # pixels from bottom of the screen (adjusted for 720p)

# Fallback fonts list to try to load
PREFERRED_FONTS = [
    "Inter-Bold.ttf",
    "Roboto-Bold.ttf",
    "Montserrat-Bold.ttf",
    "Arial.ttf",
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf"
]
