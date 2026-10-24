"""
MaxTube Pro Studio - Batch Processing, Queue & Download Control
Thread-safe background job execution, SSE progress streaming, and Batch ZIP packaging.
"""

import os
import time
import uuid
import queue
import zipfile
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

import config
from core.downloader import MediaDownloader, sanitize_filename
from core.cleanup import CleanupManager

logger = logging.getLogger("maxtube-pro-studio.queue_manager")

class JobState:
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"

class DownloadJob:
    def __init__(self, job_id: str, urls: List[str], options: Dict[str, Any], is_batch: bool = False):
        self.job_id = job_id
        self.urls = urls
        self.options = options
        self.is_batch = is_batch
        self.status = JobState.QUEUED
        self.created_at = time.time()
        self.updated_at = time.time()
        
        # Single job metrics
        self.percent = 0.0
        self.downloaded_str = "0 B"
        self.total_str = "0 B"
        self.speed_str = "-- KB/s"
        self.eta_str = "--:--"
        self.step_message = "Waiting in queue..."
        self.error_message: Optional[str] = None
        
        # Batch metrics
        self.total_items = len(urls)
        self.completed_items = 0
        self.failed_items = 0
        self.current_item_index = 0
        self.current_item_title = ""
        self.items_status: List[Dict[str, Any]] = []

        # Result files
        self.downloaded_files: List[Path] = []
        self.final_file_path: Optional[str] = None
        self.final_filename: Optional[str] = None
        self.final_file_size: int = 0
        self.is_zip: bool = False

        # SSE Event Stream Queue
        self.event_queue = queue.Queue(maxsize=100)

    def push_update(self, data: Dict[str, Any]):
        self.updated_at = time.time()
        payload = self.to_dict()
        payload.update(data)
        try:
            self.event_queue.put_nowait(payload)
        except queue.Full:
            try:
                self.event_queue.get_nowait()
                self.event_queue.put_nowait(payload)
            except Exception:
                pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "is_batch": self.is_batch,
            "percent": self.percent,
            "downloaded_str": self.downloaded_str,
            "total_str": self.total_str,
            "speed_str": self.speed_str,
            "eta_str": self.eta_str,
            "step_message": self.step_message,
            "error_message": self.error_message,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "failed_items": self.failed_items,
            "current_item_index": self.current_item_index,
            "current_item_title": self.current_item_title,
            "final_filename": self.final_filename,
            "final_file_size": self.final_file_size,
            "is_zip": self.is_zip,
            "download_url": f"/api/download/file/{self.job_id}" if self.status == JobState.COMPLETED else None
        }


class QueueManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, max_workers: int = 3):
        self.jobs: Dict[str, DownloadJob] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="Worker")
        self.cleanup_mgr = CleanupManager.get_instance()

    @classmethod
    def get_instance(cls) -> "QueueManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def submit_job(self, urls: List[str], options: Dict[str, Any]) -> str:
        """Creates and enqueues a new download job."""
        job_id = str(uuid.uuid4())[:12]
        is_batch = len(urls) > 1
        job = DownloadJob(job_id=job_id, urls=urls, options=options, is_batch=is_batch)
        
        with self._lock:
            self.jobs[job_id] = job

        self.executor.submit(self._execute_job, job)
        return job_id

    def get_job(self, job_id: str) -> Optional[DownloadJob]:
        with self._lock:
            return self.jobs.get(job_id)

    def _execute_job(self, job: DownloadJob):
        """Worker function executing single or batch downloads."""
        job.status = JobState.DOWNLOADING
        job.push_update({"status": JobState.DOWNLOADING, "step_message": "Initializing download streams..."})

        downloaded_paths: List[Path] = []

        try:
            for idx, url in enumerate(job.urls):
                job.current_item_index = idx + 1
                job.step_message = f"Processing item {idx + 1} of {len(job.urls)}..."
                job.push_update({"step_message": job.step_message, "current_item_index": idx + 1})

                def progress_callback(progress_data: Dict[str, Any]):
                    if job.status == JobState.CANCELLED:
                        raise Exception("Job cancelled by user.")

                    # Calculate blended progress for batch
                    item_pct = progress_data.get("percent", 0.0)
                    if job.is_batch:
                        total_pct = round(((idx * 100.0) + item_pct) / len(job.urls), 1)
                    else:
                        total_pct = item_pct

                    job.percent = total_pct
                    job.downloaded_str = progress_data.get("downloaded_str", job.downloaded_str)
                    job.total_str = progress_data.get("total_str", job.total_str)
                    job.speed_str = progress_data.get("speed_str", job.speed_str)
                    job.eta_str = progress_data.get("eta_str", job.eta_str)
                    job.step_message = progress_data.get("step", job.step_message)
                    job.push_update({})

                downloader = MediaDownloader(
                    job_id=job.job_id,
                    options=job.options,
                    progress_callback=progress_callback
                )

                result = downloader.download(url)

                if result.get("success"):
                    file_path = Path(result["file_path"])
                    if file_path.exists():
                        downloaded_paths.append(file_path)
                        job.completed_items += 1
                        job.current_item_title = result.get("title", file_path.name)
                else:
                    job.failed_items += 1
                    logger.warning(f"Item failed in job {job.job_id} ({url}): {result.get('error')}")

            if not downloaded_paths:
                job.status = JobState.ERROR
                job.error_message = "All download attempts failed. Check the media links or platform availability."
                job.push_update({"status": JobState.ERROR, "error_message": job.error_message})
                return

            # If single file download
            if len(downloaded_paths) == 1 and not job.is_batch:
                single_file = downloaded_paths[0]
                job.final_file_path = str(single_file)
                job.final_filename = single_file.name
                job.final_file_size = single_file.stat().st_size
                job.is_zip = False
                job.status = JobState.COMPLETED
                job.percent = 100.0
                job.step_message = "Download ready!"
                job.push_update({"status": JobState.COMPLETED, "percent": 100.0})
            else:
                # Multiple files -> Bundle into ZIP Archive
                job.step_message = "Bundling batch downloads into ZIP archive..."
                job.push_update({"step_message": job.step_message})

                zip_filename = f"MaxTube_Pro_Studio_Batch_{job.job_id}.zip"
                zip_path = config.ZIP_DIR / zip_filename

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for fpath in downloaded_paths:
                        if fpath.exists():
                            zipf.write(fpath, arcname=fpath.name)

                # Remove original single files after archiving into zip to save disk
                for fpath in downloaded_paths:
                    self.cleanup_mgr.safe_delete_file(fpath)

                job.final_file_path = str(zip_path)
                job.final_filename = zip_filename
                job.final_file_size = zip_path.stat().st_size
                job.is_zip = True
                job.status = JobState.COMPLETED
                job.percent = 100.0
                job.step_message = f"Batch completed! {len(downloaded_paths)} items archived in ZIP."
                job.push_update({"status": JobState.COMPLETED, "percent": 100.0})

        except Exception as e:
            logger.error(f"Job execution failed for {job.job_id}: {e}", exc_info=True)
            job.status = JobState.ERROR
            job.error_message = str(e)
            job.push_update({"status": JobState.ERROR, "error_message": str(e)})

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            job = self.jobs.get(job_id)
            if job:
                job.status = JobState.CANCELLED
                job.push_update({"status": JobState.CANCELLED, "step_message": "Job cancelled."})
                return True
        return False
