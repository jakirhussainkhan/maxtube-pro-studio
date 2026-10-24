# MaxTube Pro Studio 🎬⚡

**Version: 1.0.0** · **Repository:** [`maxtube-pro-studio`](https://github.com/jakirhussainkhan/maxtube-pro-studio)

> **Studio-Grade Multi-Platform Media & Audio Extraction Workstation**  
> Powered by Python (Flask), `yt-dlp`, and `FFmpeg`. Zero-lag hardware encoding, real-time SSE progress streaming, batch ZIP bundling, and automatic server storage purging.

---

## 📦 Release Notes — v1.0.0

**Release name:** Initial Stable Release  
**Release date:** 2026-10-24

This is the first stable public release of **MaxTube Pro Studio**.

- ✅ Complete rebrand to **MaxTube Pro Studio** (`maxtube-pro-studio`) across the UI, API, package metadata, and documentation.
- ✅ Version pinned to **1.0.0** in `version.py`, `pyproject.toml`, API response headers, and the web interface.
- ✅ Universal multi-platform video, reel, story, short, and audio extraction.
- ✅ Full resolution spectrum from `144p` through `4320p 8K UHD`.
- ✅ Studio audio exports: MP3, M4A (AAC), WAV, and FLAC with ID3 metadata and cover art.
- ✅ Real-time Server-Sent Events (SSE) progress streaming with speed, ETA, and byte counters.
- ✅ Batch queue processing with automatic ZIP packaging.
- ✅ Automatic temporary-file purging to keep server storage clean.
- ✅ Strict `.gitignore` rules for secrets, virtual environments, dependencies, and build artifacts.

---

## 🚀 Key Features

1. **Universal Multi-Platform Downloader**:
   - Downloads videos, reels, stories, shorts, and tracks from **YouTube, Facebook, Instagram Reels, TikTok (No Watermark), X (Twitter), SoundCloud, Vimeo**, and 1000+ platforms.
   - Built-in dynamic updater routine keeps `yt-dlp` in sync with upstream platform API shifts.

2. **Advanced Video Formats & Hardware Compatibility**:
   - Complete resolution spectrum: `144p`, `240p`, `360p`, `480p`, `720p`, `1080p FHD`, `1440p 2K`, `2160p 4K UHD`, `4320p 8K UHD`.
   - Forces **H.264 video codec (`libx264`)** and **AAC audio (`aac`)** inside an **MP4** container with `+faststart` atom placement for zero-lag hardware playback on mobile phones and TVs.
   - Dynamic filename templating: `Video Title - [1080p].mp4`.

3. **Studio-Grade Audio & Metadata Binding**:
   - Audio formats: **MP3** (64k, 128k, 192k, 256k, 320k Studio Master), **M4A (AAC)**, and lossless **WAV / FLAC**.
   - Automated ID3 metadata tagging (Title, Artist, Album) and high-resolution cover art embedding directly into audio files.

4. **Batch Processing, Queues & ZIP Bundling**:
   - Single links, batch multi-line lists, and playlists.
   - Real-time Server-Sent Events (SSE) streaming download speed, ETA countdown, downloaded bytes, and transcoding steps.
   - Automatic compression of multi-item downloads into a single `.zip` archive for 1-click retrieval.

5. **Server Efficiency & Auto-Cleanup Architecture**:
   - Background daemon sweeps and purges temporary files automatically.
   - Streaming `after_this_request` immediate removal hooks ensure zero server storage bloat or disk locks.

6. **Cyberpunk Studio Dark UI**:
   - Responsive Glassmorphism dark interface built with Bootstrap 5 and custom CSS.
   - Media URL inspector with instant thumbnail, duration, view count, and playlist track accordion.

---

## 🛠️ Prerequisites & Installation

### 1. Install FFmpeg (Required for 1080p+ merging & audio transcoding)

- **Windows**:
  ```powershell
  winget install Gyan.FFmpeg
  ```
  *(Or download from [ffmpeg.org](https://ffmpeg.org/download.html) and add `bin` folder to system PATH)*

- **macOS** (Homebrew):
  ```bash
  brew install ffmpeg
  ```

- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update && sudo apt install ffmpeg -y
  ```

---

### 2. Install Python Dependencies

```powershell
# Clone the repository
git clone https://github.com/jakirhussainkhan/maxtube-pro-studio.git
cd maxtube-pro-studio

# (Optional) Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

---

## 🎯 Running MaxTube Pro Studio

### Option A: Run Locally
```powershell
python run.py
```
Open your browser and navigate to: **`http://localhost:5000`**

---

### Option B: Run on Custom Port
```powershell
python run.py --port 8080
```

---

### Option C: Expose Instantly via Ngrok (External Sharing)
Share your local studio instance securely with anyone across the internet over HTTPS:

```powershell
# Start server and establish Ngrok public tunnel automatically
python run.py --ngrok
```

If you have an Ngrok authentication token:
```powershell
python run.py --ngrok --ngrok-token YOUR_NGROK_AUTHTOKEN
```
The terminal will display your unique public URL (e.g. `https://xxxx-xx-xx.ngrok-free.app`).

---

## 🔌 API Version Headers

Every HTTP response includes the official application identity:

| Header | Value |
| --- | --- |
| `X-App-Name` | `MaxTube Pro Studio` |
| `X-App-Slug` | `maxtube-pro-studio` |
| `X-App-Version` | `1.0.0` |

The version is also available from `version.py`, `pyproject.toml`, and the `/api/system/stats` endpoint.

---

## 📁 Project Architecture

```
maxtube-pro-studio/
├── app.py                      # Flask Application Server (REST APIs & SSE Streams)
├── config.py                   # Central Configurations, Resolutions, & Audio Bitrates
├── version.py                  # Official Application Name & Version (1.0.0)
├── pyproject.toml              # Package Metadata for maxtube-pro-studio v1.0.0
├── run.py                      # Startup Script with Ngrok Tunnel & Environment Checks
├── requirements.txt            # Python Dependencies
├── core/
│   ├── __init__.py
│   ├── downloader.py           # yt-dlp wrapper, H.264/AAC re-encoding, format mapping
│   ├── queue_manager.py        # Thread-safe queue manager & Batch ZIP bundler
│   ├── updater.py              # yt-dlp dependency updater & PyPI checker
│   └── cleanup.py              # Automated cache purger & storage GC
├── templates/
│   └── index.html              # Dark Mode Studio Web Interface
└── static/
    ├── css/
    │   └── style.css           # Glassmorphism, cyber neon accents, responsive styling
    └── js/
        └── app.js              # SSE progress streaming, URL inspect, batch controller
```

---

## 📄 License

Released under the MIT License. See the repository for full details.

**MaxTube Pro Studio v1.0.0** — Initial Stable Release · 2026-10-24
