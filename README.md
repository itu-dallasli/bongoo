# 🎵 Bongoo

> YouTube MP3/MP4 Downloader by **itu-dallasli**

Download YouTube videos as high-quality **320kbps MP3** or **MP4 (360p/720p)** files.  
GUI app + command-line tool — open source, no ads, no tracking.

---

## Features

| Feature | Description |
|---------|-------------|
| 🎵 **MP3 320kbps** | Lossless-quality audio conversion |
| 🎬 **MP4 Video** | 360p / 720p video download |
| ✂ **Trim** | Download only a specific time range |
| 📝 **Subtitles & Lyrics** | `.srt` for video, `.lrc` synchronized lyrics for MP3 |
| 📋 **Clipboard Watch** | Auto-detects copied YouTube links |
| 🎛 **Stem Separation** | Isolate vocals and backing track (Open-Unmix / Demucs) |
| 🎵 **BPM & Key** | Detect tempo and musical key via AI |
| 🔊 **Normalize** | Standardize audio levels (loudnorm -14 LUFS) |
| 🔒 **Secure** | URL validation, path sanitization, no shell execution |
| 🍪 **Auto Cookie Auth** | Bypasses YouTube rate-limiting automatically |
| 📦 **Playlist Support** | Download entire playlists |
| 🖥 **Standalone .exe** | Package as portable Windows executable |

---

## Prerequisites

| Tool | Install |
|------|---------|
| **Python 3.8+** | [python.org](https://www.python.org/downloads/) |
| **FFmpeg** | `winget install FFmpeg` (Win) · `brew install ffmpeg` (Mac) · `sudo apt install ffmpeg` (Linux) |

### Verify FFmpeg

```bash
ffmpeg -version
```

## Setup

```bash
git clone https://github.com/itu-dallasli/bongoo.git
cd bongoo
pip install -r requirements.txt
```

> **Note:** AI features (stem separation, BPM analysis) require PyTorch (~2 GB).  
> Core features (download, trim, subtitles) work without it.

## Usage

### GUI App

```bash
python app.py
```

Paste a URL → pick format → click Download. All options are toggle switches.

### Command Line

```bash
# MP3 download
python download.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Custom output folder
python download.py "URL" -o my_music

# Trim (seconds)
python download.py "URL" --start 30 --end 90

# MP4 720p video
python download.py "URL" --video --quality 720

# Subtitles / Lyrics
python download.py "URL" --subtitles

# Normalize audio
python download.py "URL" --normalize

# BPM & Key analysis
python download.py "URL" --analyze

# Stem separation
python download.py "URL" --stems --stem-model openunmix
python download.py "URL" --stems --stem-model demucs
```

## Build .exe

```bash
python build.py
```

Output: `dist/Bongoo.exe` — FFmpeg must be in PATH or same folder.

## Project Structure

```
bongoo/
├── app.py           # GUI application (customtkinter)
├── download.py      # CLI downloader + core logic
├── lyrics.py        # SRT → LRC subtitle converter
├── stems.py         # AI stem separation (Open-Unmix / Demucs)
├── analysis.py      # BPM & key detection (librosa)
├── build.py         # PyInstaller build script
├── requirements.txt # Python dependencies
└── README.md
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "FFmpeg not found" | Install: `winget install FFmpeg` |
| "Invalid URL" | Only `youtube.com`, `youtu.be`, `music.youtube.com` accepted |
| 429 Too Many Requests | Cookies are auto-detected; make sure you're logged into YouTube in a browser |
| Download fails | Update yt-dlp: `pip install -U yt-dlp` |
| Stem separation fails | Install PyTorch: `pip install torch torchaudio soundfile` |
| Subtitles missing | Not all videos have subtitles available |

## Security

- **URL whitelist** — regex-based, YouTube domains only
- **Path sanitization** — blocks `..` traversal
- **URL length limit** — max 2048 characters
- **No shell execution** — all downloads use yt-dlp Python API

## License

[MIT](LICENSE) — itu-dallasli
