import os
import shutil
from pathlib import Path

import version

# Application Identity & Version
APP_NAME = version.APP_NAME
APP_SLUG = version.APP_SLUG
APP_VERSION = version.__version__

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
TEMP_DIR = BASE_DIR / "temp"
ZIP_DIR = BASE_DIR / "temp_zips"

# Ensure runtime directories exist
for directory in (DOWNLOAD_DIR, TEMP_DIR, ZIP_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Application Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "maxtube-pro-studio-super-secret-key-2026")
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1", "yes")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 5000))

# Cleanup Settings
FILE_TTL_SECONDS = 900  # 15 minutes before temporary files are purged
CLEANUP_INTERVAL_SECONDS = 180  # Run garbage collector every 3 minutes

# Supported Video Resolutions
RESOLUTIONS = [
    {"label": "Best Available", "value": "best", "desc": "Highest quality available"},
    {"label": "8K Ultra HD (4320p)", "value": "4320", "desc": "7680x4320 8K UHD"},
    {"label": "4K Ultra HD (2160p)", "value": "2160", "desc": "3840x2160 4K UHD"},
    {"label": "2K Quad HD (1440p)", "value": "1440", "desc": "2560x1440 2K QHD"},
    {"label": "Full HD (1080p)", "value": "1080", "desc": "1920x1080 FHD 60/30fps"},
    {"label": "HD (720p)", "value": "720", "desc": "1280x720 Standard HD"},
    {"label": "Standard (480p)", "value": "480", "desc": "854x480 SD"},
    {"label": "Low (360p)", "value": "360", "desc": "640x360 Data Saver"},
    {"label": "Economy (240p)", "value": "240", "desc": "426x240 Mobile Saver"},
    {"label": "Ultra Low (144p)", "value": "144", "desc": "256x144 Lowest Bitrate"},
]

# Supported Audio Options
AUDIO_FORMATS = [
    {"id": "mp3", "name": "MP3 (MPEG Audio Layer III)", "ext": "mp3", "lossless": False},
    {"id": "m4a", "name": "M4A (AAC Audio - Apple High Quality)", "ext": "m4a", "lossless": False},
    {"id": "wav", "name": "WAV (Lossless PCM Uncompressed)", "ext": "wav", "lossless": True},
    {"id": "flac", "name": "FLAC (Free Lossless Audio Codec)", "ext": "flac", "lossless": True},
]

AUDIO_BITRATES = [
    {"label": "Original / Best", "value": "0"},
    {"label": "320 kbps (Studio Master)", "value": "320"},
    {"label": "256 kbps (High Fidelity)", "value": "256"},
    {"label": "192 kbps (Standard High)", "value": "192"},
    {"label": "128 kbps (Good Quality)", "value": "128"},
    {"label": "64 kbps (Voice / Economy)", "value": "64"},
]

# Hardware-accelerated / Zero-lag video output settings
DEFAULT_VIDEO_CONTAINER = "mp4"
DEFAULT_VIDEO_VCODEC = "libx264"
DEFAULT_VIDEO_ACODEC = "aac"

# FFmpeg check
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
FFPROBE_AVAILABLE = shutil.which("ffprobe") is not None
