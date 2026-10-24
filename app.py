"""MaxTube Pro Studio - Main Flask Application Server
High-performance, zero-lag media downloader backend with real-time SSE updates,
automated cache cleanup, batch processing, and studio audio/video conversion.
"""

import os
import json
import time
import logging
import threading
from pathlib import Path
from flask import (
    Flask, render_template, request, jsonify,
    Response, send_file, after_this_request, stream_with_context
)

import config
import version
from core.downloader import MediaInspector
from core.queue_manager import QueueManager, JobState
from core.cleanup import CleanupManager
from core.updater import DependencyManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("maxtube-pro-studio.app")

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["APP_NAME"] = version.APP_NAME
app.config["APP_SLUG"] = version.APP_SLUG
app.config["APP_VERSION"] = version.__version__

@app.after_request
def add_version_headers(response):
    """Exposes the official application identity and release version on every API response."""
    response.headers["X-App-Name"] = version.APP_NAME
    response.headers["X-App-Slug"] = version.APP_SLUG
    response.headers["X-App-Version"] = version.__version__
    return response

# Initialize singletons
queue_mgr = QueueManager.get_instance()
cleanup_mgr = CleanupManager.get_instance()
cleanup_mgr.start_background_purger()

@app.route("/")
def index():
    """Renders the MaxTube Pro Studio Dark-Mode Web Interface."""
    return render_template(
        "index.html",
        resolutions=config.RESOLUTIONS,
        audio_formats=config.AUDIO_FORMATS,
        audio_bitrates=config.AUDIO_BITRATES,
        ffmpeg_available=config.FFMPEG_AVAILABLE,
        ytdlp_version=DependencyManager.get_current_version(),
        app_name=version.APP_NAME,
        app_version=version.__version__
    )

@app.route("/api/inspect", methods=["POST"])
def inspect_media():
    """Inspects a media link and extracts metadata, resolutions, and playlist contents."""
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"success": False, "error": "Please provide a valid media URL."}), 400

    info = MediaInspector.inspect(url)
    return jsonify(info)

@app.route("/api/download/start", methods=["POST"])
def start_download():
    """
    Initiates a single, batch, or playlist download task.
    Returns the newly created job_id.
    """
    data = request.get_json(force=True, silent=True) or {}
    urls = data.get("urls", [])
    
    # Support single url field as well
    if isinstance(urls, str):
        urls = [urls]
    elif not urls and "url" in data:
        urls = [data["url"]]

    # Filter empty / whitespace lines
    cleaned_urls = [u.strip() for u in urls if u and isinstance(u, str) and u.strip().startswith("http")]

    if not cleaned_urls:
        return jsonify({"success": False, "error": "No valid URLs provided."}), 400

    options = {
        "mode": data.get("mode", "video"),  # "video" or "audio"
        "resolution": data.get("resolution", "best"),
        "audio_format": data.get("audio_format", "mp3"),
        "audio_bitrate": data.get("audio_bitrate", "320"),
    }

    job_id = queue_mgr.submit_job(cleaned_urls, options)

    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "Download task queued successfully.",
        "item_count": len(cleaned_urls)
    })

@app.route("/api/progress/<job_id>")
def job_progress_sse(job_id: str):
    """
    Server-Sent Events (SSE) stream for real-time progress updates.
    Transmits download speed, percentage, ETA, and transcoding status.
    """
    job = queue_mgr.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    def event_stream():
        # Send initial snapshot immediately
        yield f"data: {json.dumps(job.to_dict())}\n\n"

        while True:
            try:
                # Wait up to 1 second for a new event
                update = job.event_queue.get(timeout=1.0)
                yield f"data: {json.dumps(update)}\n\n"

                if update.get("status") in (JobState.COMPLETED, JobState.ERROR, JobState.CANCELLED):
                    break
            except Exception:
                # Send periodic heartbeat keep-alive
                current_state = job.to_dict()
                yield f"data: {json.dumps(current_state)}\n\n"
                if current_state.get("status") in (JobState.COMPLETED, JobState.ERROR, JobState.CANCELLED):
                    break

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@app.route("/api/job/<job_id>")
def get_job_status(job_id: str):
    """Pollable endpoint for job status."""
    job = queue_mgr.get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job.to_dict())

@app.route("/api/download/file/<job_id>")
def serve_downloaded_file(job_id: str):
    """
    Streams the finished file or batch ZIP to the user.
    Uses try...finally and after_this_request hooks to purge the file after transmission.
    """
    job = queue_mgr.get_job(job_id)
    if not job or not job.final_file_path:
        return jsonify({"error": "File is not ready or has already been retrieved."}), 404

    target_file = Path(job.final_file_path)
    if not target_file.exists():
        return jsonify({"error": "File was purged from temporary storage."}), 410

    # Auto-cleanup hook: schedule file deletion shortly after response completes
    @after_this_request
    def schedule_cleanup(response):
        def _delayed_delete():
            time.sleep(15)  # Allow socket to flush completely
            cleanup_mgr.safe_delete_file(target_file)
            logger.info(f"Auto-purged served file: {target_file.name}")

        threading.Thread(target=_delayed_delete, daemon=True).start()
        return response

    return send_file(
        str(target_file),
        as_attachment=True,
        download_name=job.final_filename or target_file.name
    )

@app.route("/api/updater/check", methods=["GET", "POST"])
def check_updates():
    """Checks PyPI for yt-dlp upgrades."""
    info = DependencyManager.check_for_updates()
    return jsonify(info)

@app.route("/api/updater/upgrade", methods=["POST"])
def upgrade_ytdlp():
    """Triggers background pip update for yt-dlp."""
    result = DependencyManager.update_ytdlp()
    return jsonify(result)

@app.route("/api/system/stats")
def system_stats():
    """Returns storage metrics and engine health."""
    stats = cleanup_mgr.get_storage_stats()
    stats["ffmpeg_installed"] = config.FFMPEG_AVAILABLE
    stats["ytdlp_version"] = DependencyManager.get_current_version()
    stats["app_name"] = version.APP_NAME
    stats["app_version"] = version.__version__
    return jsonify(stats)

@app.route("/api/system/clean", methods=["POST"])
def manual_clean():
    """Forces an immediate sweep of temporary files."""
    purged = cleanup_mgr.purge_expired_files()
    return jsonify({"success": True, "purged_items": purged})

if __name__ == "__main__":
    logger.info(f"Starting {version.APP_NAME} v{version.__version__} on http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, threaded=True)