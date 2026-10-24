"""
MaxTube Pro Studio - Launcher & Tunnel Manager
Runs the Flask server locally and provides instant public sharing via Ngrok.
"""

import sys
import os
import argparse
import shutil
import logging

def print_banner():
    banner = r"""
  __  __              _____     _           ___            _ _      
 |  \/  |__ ___  _ __|_   _|  _| |__  ___  / __| |_ _  _ _| (_)___  
 | |\/| / _` \ \/ / _ \| | | || | '_ \/ -_) \__ \  _| || / _` | / _ \ 
 |_|  |_\__,_/>_<  ___/|_|  \_,_|_.__/\___| |___/\__|\_,_\__,_|_|\___/
                                                                     
    >> High-Fidelity Multi-Platform Media & Audio Extraction Workstation <<
    """
    print("\033[96m" + banner + "\033[0m")

def check_environment():
    """Validates system tools and dependencies."""
    print("\033[90m[*] Checking system environment...\033[0m")
    
    # FFmpeg verification
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"\033[92m[✓] FFmpeg Detected:\033[0m {ffmpeg_path}")
    else:
        print("\033[93m[!] WARNING: FFmpeg was not detected on your system PATH.\033[0m")
        print("\033[93m    High-res video merging (1080p/4K/8K) and audio transcoding require FFmpeg.\033[0m")
        print("\033[93m    Install via: winget install Gyan.FFmpeg (Windows) or brew install ffmpeg (Mac)\033[0m\n")

    # yt-dlp verification
    try:
        import yt_dlp
        version = getattr(yt_dlp.version, "__version__", "unknown")
        print(f"\033[92m[✓] yt-dlp Engine Loaded:\033[0m v{version}")
    except ImportError:
        print("\033[91m[✗] ERROR: yt-dlp is not installed. Run: pip install -r requirements.txt\033[0m")
        sys.exit(1)

def start_server(host: str, port: int, use_ngrok: bool = False, ngrok_token: str = None):
    """Starts the Flask server with optional Ngrok public tunnel."""
    public_url = None

    if use_ngrok:
        try:
            from pyngrok import ngrok, conf

            if ngrok_token:
                ngrok.set_auth_token(ngrok_token)
                print("\033[92m[✓] Ngrok Auth Token configured.\033[0m")

            print("\033[94m[*] Establishing secure Ngrok public tunnel...\033[0m")
            tunnel = ngrok.connect(port, "http")
            public_url = tunnel.public_url
            print("\n" + "=" * 60)
            print(f"\033[92m★ PUBLIC NGROK URL: \033[1m{public_url}\033[0m")
            print(f"\033[96m★ LOCAL ACCESS URL: \033[1mhttp://localhost:{port}\033[0m")
            print("=" * 60 + "\n")
        except Exception as e:
            print(f"\033[91m[!] Failed to start Ngrok tunnel: {e}\033[0m")
            print("\033[90mContinuing with local server...\033[0m")
    else:
        print("\n" + "=" * 60)
        print(f"\033[92m★ LOCAL STUDIO SERVER: \033[1mhttp://localhost:{port}\033[0m")
        print(f"\033[96m★ NETWORK ACCESS:      \033[1mhttp://{host}:{port}\033[0m")
        print("=" * 60 + "\n")

    # Import and run app
    from app import app
    try:
        app.run(host=host, port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n\033[93m[*] Shutting down MaxTube Pro Studio...\033[0m")
        if use_ngrok:
            try:
                from pyngrok import ngrok
                ngrok.kill()
            except Exception:
                pass
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MaxTube Pro Studio - Media Downloader Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host IP to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Port to run on (default: 5000)")
    parser.add_argument("--ngrok", action="store_true", help="Launch a public Ngrok tunnel")
    parser.add_argument("--ngrok-token", default=os.environ.get("NGROK_AUTHTOKEN"), help="Ngrok auth token")

    args = parser.parse_args()

    print_banner()
    check_environment()
    start_server(host=args.host, port=args.port, use_ngrok=args.ngrok, ngrok_token=args.ngrok_token)