# Bongoo — YouTube MP3 Downloader
# by itu-dallasli
#
# Downloads YouTube videos as high-quality 320kbps MP3 files.
# Usage: python download.py <youtube_url>

import sys
import os
import re
import shutil
import argparse
import yt_dlp


# only allow real youtube URLs — blocks command injection via crafted strings
ALLOWED_URL = re.compile(
    r'^https?://(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/.+$'
)


def validate_url(url):
    """Reject anything that isn't a YouTube URL."""
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


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("FFmpeg is not installed!")
        print("Install it: winget install FFmpeg (Windows)")
        print("            brew install ffmpeg (macOS)")
        print("            sudo apt install ffmpeg (Linux)")
        sys.exit(1)


def download(url, output_dir="downloads"):
    url = validate_url(url)
    output_dir = sanitize_path(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "writethumbnail": True,
        "quiet": False,
        "no_warnings": False,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            },
            {"key": "EmbedThumbnail"},
            {"key": "FFmpegMetadata"},
        ],
    }

    print(f"\nDownloading: {url}")
    print(f"Saving to: {os.path.abspath(output_dir)}\n")

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "Unknown")
            print(f"\nDone! Saved: {title}.mp3")
    except Exception as e:
        print(f"\nFailed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bongoo — YouTube MP3 Downloader by itu-dallasli")
    parser.add_argument("url", help="YouTube video or playlist URL")
    parser.add_argument("-o", "--output", default="downloads", help="Output folder (default: downloads)")
    args = parser.parse_args()

    check_ffmpeg()
    download(args.url, args.output)
