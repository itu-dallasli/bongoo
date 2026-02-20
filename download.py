# Bongoo — YouTube MP3/MP4 Downloader
# by itu-dallasli
#
# Downloads YouTube videos as high-quality MP3 or MP4 files.
# Usage: python download.py <youtube_url>

import sys
import os
import re
import shutil
import argparse
import glob
import time
import yt_dlp
from lyrics import srt_to_lrc


# Supported browsers for cookie auto-detection (tried in order)
_BROWSER_PRIORITY = ["chrome", "edge", "firefox", "brave", "opera", "chromium"]


def detect_cookie_browser():
    """Auto-detect the best browser for cookie extraction."""
    import yt_dlp.cookies
    for browser in _BROWSER_PRIORITY:
        try:
            jar = yt_dlp.cookies.extract_cookies_from_browser(browser)
            if jar is not None:
                return browser
        except Exception:
            continue
    return None


# only allow real youtube URLs — blocks command injection via crafted strings
ALLOWED_URL = re.compile(
    r'^https?://(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/.+$'
)

MAX_URL_LENGTH = 2048


def validate_url(url):
    """Reject anything that isn't a YouTube URL."""
    if len(url) > MAX_URL_LENGTH:
        print("URL is too long.")
        sys.exit(1)
    if not ALLOWED_URL.match(url):
        print("Invalid URL. Only YouTube links are accepted.")
        print("Example: https://www.youtube.com/watch?v=VIDEO_ID")
        sys.exit(1)
    return url


def sanitize_path(path):
    """Block path traversal attacks in output directory."""
    resolved = os.path.realpath(path)
    if ".." in path:
        print("Invalid output path — path traversal not allowed.")
        sys.exit(1)
    return resolved


def validate_seconds(value, name):
    """Ensure a time value is a non-negative number."""
    try:
        val = float(value)
        if val < 0:
            raise ValueError
        return val
    except (ValueError, TypeError):
        print(f"Invalid {name} value: must be a non-negative number.")
        sys.exit(1)


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("FFmpeg is not installed!")
        print("Install it: winget install FFmpeg (Windows)")
        print("            brew install ffmpeg (macOS)")
        print("            sudo apt install ffmpeg (Linux)")
        sys.exit(1)


def download(url, output_dir="downloads", start=None, end=None,
             mode="mp3", quality="720", subtitles=False,
             normalize=False, on_progress=None):
    """Download a YouTube video as MP3 or MP4.

    Args:
        url:        YouTube URL
        output_dir: Folder to save to
        start:      Trim start in seconds (or None)
        end:        Trim end in seconds (or None)
        mode:       "mp3", "mp4_360", or "mp4_720"
        quality:    Video quality (360 or 720)
        subtitles:  Download subtitles/lyrics
        normalize:  Apply audio normalization (loudnorm)
        on_progress: Optional callback(dict) for progress hooks
    """
    url = validate_url(url)
    output_dir = sanitize_path(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

    opts = {
        "outtmpl": outtmpl,
        "quiet": False,
        "no_warnings": False,
        # --- Anti-429: retry + backoff ---
        "retries": 10,
        "extractor_retries": 5,
        "retry_sleep_functions": {"http": lambda n: 2 ** n},  # exponential backoff
        "sleep_interval": 1,       # wait 1s before each download
        "max_sleep_interval": 5,   # random 1-5s between playlist items
    }

    # --- Anti-429: auto-detect browser cookies ---
    cookie_browser = detect_cookie_browser()
    if cookie_browser:
        opts["cookiesfrombrowser"] = (cookie_browser,)
        print(f"🍪 Using {cookie_browser} cookies")

    # ---------- Format selection ----------
    if mode.startswith("mp4"):
        height = 360 if "360" in mode else 720
        opts["format"] = (
            f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
        )
        opts["merge_output_format"] = "mp4"
        opts["postprocessors"] = [{"key": "FFmpegMetadata"}]
    else:
        # MP3 mode
        opts["format"] = "bestaudio/best"
        opts["writethumbnail"] = True
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            },
            {"key": "EmbedThumbnail"},
            {"key": "FFmpegMetadata"},
        ]

    # ---------- Subtitles ----------
    if subtitles:
        opts["writesubtitles"] = True
        opts["writeautomaticsub"] = True
        opts["subtitleslangs"] = ["en", "tr"]
        opts["subtitlesformat"] = "srt"

    # ---------- Trim (time interval) ----------
    if start is not None or end is not None:
        pp_args = []
        if start is not None:
            pp_args += ["-ss", str(start)]
        if end is not None:
            pp_args += ["-to", str(end)]
        opts["postprocessor_args"] = {"ffmpeg_i1": pp_args}

    # ---------- Audio normalization ----------
    if normalize and mode == "mp3":
        opts.setdefault("postprocessor_args", {})
        # loudnorm filter: -14 LUFS target, -1 dBTP true peak
        norm_args = ["-af", "loudnorm=I=-14:TP=-1:LRA=11"]
        if "ffmpeg_o" in opts["postprocessor_args"]:
            opts["postprocessor_args"]["ffmpeg_o"] += norm_args
        else:
            opts["postprocessor_args"]["ffmpeg_o"] = norm_args

    # ---------- Progress hook ----------
    if on_progress:
        opts["progress_hooks"] = [on_progress]

    ext = "mp4" if mode.startswith("mp4") else "mp3"
    print(f"\nDownloading: {url}")
    print(f"Format: {ext.upper()}" + (f" ({mode.split('_')[1]}p)" if "mp4" in mode else " (320kbps)"))
    print(f"Saving to: {os.path.abspath(output_dir)}")
    if start is not None or end is not None:
        print(f"Trimming: {start or 0}s → {end or 'end'}s")
    if subtitles:
        print("Subtitles: enabled")
    if normalize:
        print("Normalization: enabled (loudnorm -14 LUFS)")
    print()

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "Unknown")

            # Convert .srt to .lrc for MP3 downloads
            if subtitles and mode == "mp3":
                srt_files = glob.glob(os.path.join(output_dir, "*.srt"))
                for srt_file in srt_files:
                    lrc_path = srt_to_lrc(srt_file)
                    if lrc_path:
                        print(f"Lyrics saved: {os.path.basename(lrc_path)}")

            print(f"\nDone! Saved: {title}.{ext}")
            return info
    except Exception as e:
        print(f"\nFailed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Bongoo — YouTube MP3/MP4 Downloader by itu-dallasli"
    )
    parser.add_argument("url", help="YouTube video or playlist URL")
    parser.add_argument("-o", "--output", default="downloads",
                        help="Output folder (default: downloads)")
    parser.add_argument("--start", type=float, default=None,
                        help="Trim start time in seconds")
    parser.add_argument("--end", type=float, default=None,
                        help="Trim end time in seconds")
    parser.add_argument("--video", action="store_true",
                        help="Download as MP4 video instead of MP3")
    parser.add_argument("--quality", choices=["360", "720"], default="720",
                        help="Video quality (default: 720)")
    parser.add_argument("--subtitles", action="store_true",
                        help="Download subtitles (.srt for video, .lrc for MP3)")
    parser.add_argument("--normalize", action="store_true",
                        help="Normalize audio levels (loudnorm -14 LUFS)")
    parser.add_argument("--stems", action="store_true",
                        help="Separate audio into stems after download")
    parser.add_argument("--stem-model", choices=["openunmix", "demucs"],
                        default="openunmix",
                        help="Stem separation model (default: openunmix)")
    parser.add_argument("--analyze", action="store_true",
                        help="Detect BPM and musical key")

    args = parser.parse_args()

    # validate trim values
    if args.start is not None:
        validate_seconds(args.start, "start")
    if args.end is not None:
        validate_seconds(args.end, "end")
    if args.start is not None and args.end is not None and args.start >= args.end:
        print("Error: --start must be less than --end")
        sys.exit(1)

    mode = f"mp4_{args.quality}" if args.video else "mp3"

    check_ffmpeg()
    info = download(args.url, args.output, start=args.start, end=args.end,
                    mode=mode, subtitles=args.subtitles, normalize=args.normalize)

    # Post-download: stem separation
    if args.stems and mode == "mp3" and info:
        from stems import separate
        title = info.get("title", "Unknown")
        mp3_path = os.path.join(args.output, f"{title}.mp3")
        if os.path.isfile(mp3_path):
            print(f"\nSeparating stems ({args.stem_model})...")
            result = separate(mp3_path, model=args.stem_model)
            if result:
                print("Stems saved:")
                for name, path in result.items():
                    print(f"  {name}: {os.path.basename(path)}")
            else:
                print("Stem separation failed.")

    # Post-download: BPM/key analysis
    if args.analyze and mode == "mp3" and info:
        from analysis import analyze, format_result
        title = info.get("title", "Unknown")
        mp3_path = os.path.join(args.output, f"{title}.mp3")
        if os.path.isfile(mp3_path):
            print(f"\nAnalyzing BPM and key...")
            result = analyze(mp3_path)
            if result:
                print(f"  {format_result(result)}")
            else:
                print("Analysis failed.")
