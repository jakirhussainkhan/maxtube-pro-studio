"""
MaxTube Pro Studio - Server Efficiency & Auto-Cleanup Architecture
Guarantees zero storage overhead and eliminates host machine disk bloat.
"""

import os
import time
import shutil
import logging
import threading
from pathlib import Path
from typing import List, Optional
import config

logger = logging.getLogger("maxtube-pro-studio.cleanup")

class CleanupManager:
    _instance = None
    _thread: Optional[threading.Thread] = None
    _stop_event = threading.Event()

    def __init__(self):
        self.watch_dirs: List[Path] = [
            config.DOWNLOAD_DIR,
            config.TEMP_DIR,
            config.ZIP_DIR
        ]
        self.ttl = config.FILE_TTL_SECONDS
        self.interval = config.CLEANUP_INTERVAL_SECONDS

    @classmethod
    def get_instance(cls) -> "CleanupManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_background_purger(self):
        """Starts the periodic cleanup daemon."""
        if self._thread and self._thread.is_alive():
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_purger_loop, daemon=True, name="StoragePurgerDaemon")
        self._thread.start()
        logger.info(f"Background Storage Purger started. TTL: {self.ttl}s, Interval: {self.interval}s")

    def stop_background_purger(self):
        """Stops the daemon."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run_purger_loop(self):
        while not self._stop_event.is_set():
            try:
                self.purge_expired_files()
            except Exception as e:
                logger.error(f"Error during scheduled cleanup: {e}", exc_info=True)
            self._stop_event.wait(self.interval)

    def purge_expired_files(self) -> int:
        """
        Scans watched directories and deletes files older than TTL.
        Returns count of purged files.
        """
        now = time.time()
        purged_count = 0

        for target_dir in self.watch_dirs:
            if not target_dir.exists():
                continue

            for entry in target_dir.iterdir():
                try:
                    # Check age
                    stat = entry.stat()
                    file_age = now - max(stat.st_mtime, stat.st_ctime)
                    
                    if file_age > self.ttl:
                        if entry.is_file() or entry.is_symlink():
                            self.safe_delete_file(entry)
                            purged_count += 1
                        elif entry.is_dir():
                            shutil.rmtree(entry, ignore_errors=True)
                            purged_count += 1
                except Exception as e:
                    logger.debug(f"Could not inspect or delete {entry.name}: {e}")

        if purged_count > 0:
            logger.info(f"Auto-cleanup purged {purged_count} expired items from storage.")
        return purged_count

    @staticmethod
    def safe_delete_file(file_path: Path, max_retries: int = 4, delay: float = 0.5) -> bool:
        """
        Attempts to delete a file safely with retries to account for Windows OS file locks.
        """
        if not file_path or not file_path.exists():
            return True

        for attempt in range(max_retries):
            try:
                if file_path.is_file() or file_path.is_symlink():
                    file_path.unlink(missing_ok=True)
                elif file_path.is_dir():
                    shutil.rmtree(file_path, ignore_errors=True)
                return True
            except PermissionError:
                # Windows might briefly keep the file handle locked
                time.sleep(delay * (attempt + 1))
            except Exception as e:
                logger.debug(f"Failed deleting {file_path}: {e}")
                time.sleep(delay)

        logger.warning(f"Could not delete {file_path} after {max_retries} retries. Scheduled for next sweep.")
        return False

    @staticmethod
    def purge_directory(target_dir: Path):
        """Purges all files in a specific directory immediately."""
        if not target_dir.exists():
            return
        for item in target_dir.iterdir():
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink(missing_ok=True)
                elif item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
            except Exception as e:
                logger.debug(f"Could not purge {item}: {e}")

    def get_storage_stats(self) -> dict:
        """Returns statistics on server storage usage."""
        total_size = 0
        total_files = 0

        for target_dir in self.watch_dirs:
            if target_dir.exists():
                for item in target_dir.rglob("*"):
                    if item.is_file():
                        total_files += 1
                        try:
                            total_size += item.stat().st_size
                        except Exception:
                            pass

        return {
            "temp_files_count": total_files,
            "temp_size_bytes": total_size,
            "temp_size_mb": round(total_size / (1024 * 1024), 2),
            "ttl_seconds": self.ttl
        }
