"""
MaxTube Pro Studio - Downloader Engine
High-performance, multi-platform media downloader powered by yt-dlp & FFmpeg.
Supports YouTube, Facebook, Instagram Reels, TikTok, Twitter/X, and 1000+ sources.
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import yt_dlp
import config

logger = logging.getLogger("maxtube-pro-studio.downloader")

def sanitize_filename(name: str) -> str:
    """Sanitizes filename for cross-platform filesystem safety."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip().replace("\n", " ").replace("\r", "")
    return name[:150]  # Limit length for OS path constraints

def format_bytes(size: Optional[float]) -> str:
    """Formats bytes into human readable MB/GB."""
    if not size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def format_seconds(seconds: Optional[int]) -> str:
    """Formats seconds into MM:SS or HH:MM:SS."""
    if seconds is None or seconds < 0:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def detect_platform(url: str) -> str:
    """Detects social platform from URL."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "YouTube"
    elif "facebook.com" in url_lower or "fb.watch" in url_lower or "fb.gg" in url_lower:
        return "Facebook"
    elif "instagram.com" in url_lower:
        return "Instagram"
    elif "tiktok.com" in url_lower:
        return "TikTok"
    elif "twitter.com" in url_lower or "x.com" in url_lower:
        return "X (Twitter)"
    elif "soundcloud.com" in url_lower:
        return "SoundCloud"
    elif "vimeo.com" in url_lower:
        return "Vimeo"
    elif "reddit.com" in url_lower:
        return "Reddit"
    return "Universal Video"

class MediaInspector:
    """Inspects URLs and extracts rich metadata without downloading."""

    @staticmethod
    def inspect(url: str) -> Dict[str, Any]:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "nocheckcertificate": True,
            "socket_timeout": 15,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {"success": False, "error": "Could not extract media info."}

                is_playlist = info.get("_type") == "playlist" or "entries" in info

                if is_playlist:
                    entries = info.get("entries", [])
                    playlist_items = []
                    for idx, entry in enumerate(entries[:50]):  # Cap preview at 50 items
                        if entry:
                            playlist_items.append({
                                "index": idx + 1,
                                "id": entry.get("id"),
                                "title": entry.get("title", f"Track {idx + 1}"),
                                "duration": format_seconds(entry.get("duration")),
                                "url": entry.get("url") or entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                                "thumbnail": entry.get("thumbnail") or info.get("thumbnail")
                            })

                    return {
                        "success": True,
                        "is_playlist": True,
                        "platform": detect_platform(url),
                        "id": info.get("id"),
                        "title": info.get("title", "Playlist"),
                        "uploader": info.get("uploader") or info.get("channel", "Unknown Curator"),
                        "item_count": len(entries),
                        "thumbnail": info.get("thumbnail") or (playlist_items[0]["thumbnail"] if playlist_items else None),
                        "entries": playlist_items,
                        "webpage_url": info.get("webpage_url", url)
                    }

                # Single Video / Track
                formats = info.get("formats", [])
                available_resolutions = set()
                for fmt in formats:
                    h = fmt.get("height")
                    if h and isinstance(h, int) and h > 0:
                        available_resolutions.add(h)

                sorted_resolutions = sorted(list(available_resolutions), reverse=True)

                return {
                    "success": True,
                    "is_playlist": False,
                    "platform": detect_platform(url),
                    "id": info.get("id"),
                    "title": info.get("title", "Unknown Title"),
                    "description": (info.get("description") or "")[:200],
                    "uploader": info.get("uploader") or info.get("channel", "Unknown Creator"),
                    "duration": info.get("duration", 0),
                    "duration_str": format_seconds(info.get("duration")),
                    "thumbnail": info.get("thumbnail"),
                    "views": info.get("view_count"),
                    "webpage_url": info.get("webpage_url", url),
                    "available_resolutions": sorted_resolutions,
                    "like_count": info.get("like_count")
                }
        except yt_dlp.utils.DownloadError as e:
            logger.warning(f"DownloadError inspecting {url}: {e}")
            return {"success": False, "error": f"Platform extraction error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error inspecting {url}: {e}", exc_info=True)
            return {"success": False, "error": f"Failed to parse media link: {str(e)}"}


class MediaDownloader:
    """Executes downloads with format conversion, hardware acceleration mapping, and metadata binding."""

    def __init__(self, job_id: str, options: Dict[str, Any], progress_callback: Optional[Callable] = None):
        self.job_id = job_id
        self.options = options
        self.progress_callback = progress_callback
        self.downloaded_files: List[Path] = []
        self.final_file_path: Optional[Path] = None

    def _progress_hook(self, d: Dict[str, Any]):
        """Internal yt-dlp hook mapped to progress callback."""
        if not self.progress_callback:
            return

        status = d.get("status", "unknown")
        if status == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded_bytes = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            eta = d.get("eta")

            percent = 0.0
            if total_bytes > 0:
                percent = round((downloaded_bytes / total_bytes) * 100, 1)

            self.progress_callback({
                "job_id": self.job_id,
                "status": "downloading",
                "percent": percent,
                "downloaded_bytes": downloaded_bytes,
                "downloaded_str": format_bytes(downloaded_bytes),
                "total_bytes": total_bytes,
                "total_str": format_bytes(total_bytes),
                "speed": speed,
                "speed_str": f"{format_bytes(speed)}/s" if speed else "-- KB/s",
                "eta": eta,
                "eta_str": format_seconds(eta),
                "filename": os.path.basename(d.get("filename", "")),
                "step": "Downloading stream..."
            })
        elif status == "finished":
            filename = d.get("filename")
            if filename:
                self.downloaded_files.append(Path(filename))
            self.progress_callback({
                "job_id": self.job_id,
                "status": "postprocessing",
                "percent": 99.0,
                "speed_str": "Processing...",
                "eta_str": "Encoding",
                "step": "Transcoding & embedding metadata (H.264 / AAC / ID3)..."
            })
        elif status == "error":
            self.progress_callback({
                "job_id": self.job_id,
                "status": "error",
                "error": "Error during stream extraction"
            })

    def download(self, url: str) -> Dict[str, Any]:
        mode = self.options.get("mode", "video")  # "video" or "audio"
        resolution = self.options.get("resolution", "best")
        audio_format = self.options.get("audio_format", "mp3")
        audio_bitrate = self.options.get("audio_bitrate", "320")

        platform = detect_platform(url)

        # YouTube strictly keeps your exact original format: Title + [Resolution]
        out_tmpl = str(config.DOWNLOAD_DIR / "%(title)s - [%(height)sp].%(ext)s")
        if mode == "audio":
            out_tmpl = str(config.DOWNLOAD_DIR / f"%(title)s - [{audio_format.upper()}].%(ext)s")

        # Smart Safety Guard for Facebook, Instagram, and TikTok:
        # If title/caption is normal, keep it. If missing or too risky, fallback to ID-based naming.
        if platform in ["Facebook", "Instagram", "TikTok"]:
            try:
                with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True, "nocheckcertificate": True}) as temp_ydl:
                    temp_info = temp_ydl.extract_info(url, download=False)
                    title = temp_info.get("title", "") if temp_info else ""
                    if len(title) > 60 or not title.strip():
                        if mode == "audio":
                            out_tmpl = str(config.DOWNLOAD_DIR / f"%(id)s - [{audio_format.upper()}].%(ext)s")
                        else:
                            out_tmpl = str(config.DOWNLOAD_DIR / "%(id)s - [%(height)sp].%(ext)s")
            except Exception:
                if mode == "audio":
                    out_tmpl = str(config.DOWNLOAD_DIR / f"%(id)s - [{audio_format.upper()}].%(ext)s")
                else:
                    out_tmpl = str(config.DOWNLOAD_DIR / "%(id)s - [%(height)sp].%(ext)s")

        ydl_opts: Dict[str, Any] = {
            "outtmpl": out_tmpl,
            "quiet": False,
            "no_warnings": True,
            "progress_hooks": [self._progress_hook],
            "nocheckcertificate": True,
            "continuedl": True,
            "retries": 10,
            "fragment_retries": 10,
            "socket_timeout": 30,
            "windowsfilenames": True,
            "restrictfilenames": False,
        }

        # Setup Video Download Mode (Supports full 8K, 4K and high resolutions properly)
        if mode == "video":
            if resolution == "best":
                format_selector = (
                    "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/"
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                    "bestvideo+bestaudio/"
                    "best"
                )
            else:
                height = int(resolution) if resolution.isdigit() else 1080
                if height >= 2160:
                    format_selector = (
                        f"bestvideo[height<={height}]+bestaudio/"
                        f"best[height<={height}]/"
                        "bestvideo+bestaudio/"
                        "best"
                    )
                else:
                    format_selector = (
                        f"bestvideo[vcodec^=avc1][height<={height}]+bestaudio[acodec^=mp4a]/"
                        f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                        f"bestvideo[height<={height}]+bestaudio/"
                        f"best[height<={height}]/"
                        f"best"
                    )

            ydl_opts["format"] = format_selector
            ydl_opts["merge_output_format"] = "mp4"

            postprocessors = [
                {
                    "key": "FFmpegVideoRemuxer",
                    "preferedformat": "mp4",
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                }
            ]
            ydl_opts["postprocessors"] = postprocessors
            ydl_opts["postprocessor_args"] = {
                "FFmpegVideoRemuxer": ["-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart"],
                "merger": ["-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart"]
            }

        # Setup Audio Download Mode (Studio Grade)
        elif mode == "audio":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["writethumbnail"] = True

            postprocessors = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": audio_bitrate if audio_bitrate != "0" else None,
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                }
            ]

            if audio_format in ("mp3", "m4a", "flac"):
                postprocessors.append({
                    "key": "EmbedThumbnail",
                    "already_have_thumbnail": False
                })

            ydl_opts["postprocessors"] = postprocessors

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return {"success": False, "error": "Extraction failed: no media found."}

                if "requested_downloads" in info and info["requested_downloads"]:
                    final_path = info["requested_downloads"][0].get("filepath")
                else:
                    final_path = ydl.prepare_filename(info)

                if mode == "audio":
                    base, _ = os.path.splitext(final_path)
                    final_path = f"{base}.{audio_format}"
                elif mode == "video":
                    base, _ = os.path.splitext(final_path)
                    final_path = f"{base}.mp4"

                final_file = Path(final_path)
                
                if not final_file.exists():
                    parent = config.DOWNLOAD_DIR
                    media_id = info.get("id", "")
                    matches = list(parent.glob(f"*{media_id}*"))
                    if matches:
                        final_file = matches[0]

                if not final_file.exists():
                    files = sorted(config.DOWNLOAD_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
                    if files and (files[0].suffix.lower() in [".mp4", ".mp3", ".m4a", ".wav", ".flac"]):
                        final_file = files[0]

                self.final_file_path = final_file

                file_size = final_file.stat().st_size if final_file.exists() else 0

                return {
                    "success": True,
                    "file_path": str(final_file),
                    "filename": final_file.name,
                    "file_size": file_size,
                    "file_size_str": format_bytes(file_size),
                    "title": info.get("title"),
                    "ext": final_file.suffix.replace(".", ""),
                    "thumbnail": info.get("thumbnail")
                }

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"yt-dlp Download Error on {url}: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected download failure on {url}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}