"""
MaxTube Pro Studio - Dependency & yt-dlp Auto-Updater Routine
Ensures yt-dlp stays in sync with rapidly changing platform APIs.
"""

import sys
import subprocess
import logging
import threading
import importlib
import requests

logger = logging.getLogger("maxtube-pro-studio.updater")

class DependencyManager:
    _lock = threading.Lock()
    _is_updating = False
    _last_check_info = None

    @classmethod
    def get_current_version(cls) -> str:
        """Returns the currently loaded yt-dlp version."""
        try:
            import yt_dlp
            return getattr(yt_dlp.version, "__version__", "unknown")
        except Exception as e:
            logger.error(f"Failed to get yt-dlp version: {e}")
            return "not_installed"

    @classmethod
    def check_for_updates(cls) -> dict:
        """
        Checks PyPI for the latest published yt-dlp release.
        """
        current_version = cls.get_current_version()
        info = {
            "current_version": current_version,
            "latest_version": current_version,
            "update_available": False,
            "error": None
        }

        try:
            response = requests.get("https://pypi.org/pypi/yt-dlp/json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("info", {}).get("version", current_version)
                info["latest_version"] = latest_version
                info["update_available"] = (current_version != latest_version and current_version != "unknown")
            else:
                info["error"] = f"PyPI returned status {response.status_code}"
        except Exception as e:
            logger.warning(f"Failed to check for yt-dlp update: {e}")
            info["error"] = str(e)

        cls._last_check_info = info
        return info

    @classmethod
    def update_ytdlp(cls) -> dict:
        """
        Executes pip install --upgrade yt-dlp to update the dependency cleanly.
        """
        with cls._lock:
            if cls._is_updating:
                return {"success": False, "message": "An update is already in progress."}
            cls._is_updating = True

        def _do_update():
            try:
                logger.info("Starting yt-dlp update via pip...")
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=120
                )
                if result.returncode == 0:
                    logger.info("yt-dlp upgraded successfully.")
                    try:
                        import yt_dlp
                        importlib.reload(yt_dlp)
                    except Exception:
                        pass
                else:
                    logger.error(f"yt-dlp update failed: {result.stderr}")
            except Exception as e:
                logger.error(f"Exception during yt-dlp update: {e}")
            finally:
                with cls._lock:
                    cls._is_updating = False

        thread = threading.Thread(target=_do_update, daemon=True)
        thread.start()

        return {
            "success": True,
            "message": "yt-dlp update initiated in background."
        }

    @classmethod
    def is_updating(cls) -> bool:
        return cls._is_updating
