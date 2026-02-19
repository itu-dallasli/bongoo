# 🎵 Bongoo

> YouTube MP3 Downloader by **itu-dallasli**

Download YouTube videos as high-quality **320kbps MP3** files. GUI app + command-line tool.

## Prerequisites

- **Python 3.8+**
- **FFmpeg** — `winget install FFmpeg` (Windows) / `brew install ffmpeg` (macOS) / `sudo apt install ffmpeg` (Linux)

## Setup

```bash
git clone https://github.com/itu-dallasli/mp3downloaderr.git
cd mp3downloaderr
pip install -r requirements.txt
```

## Usage

### GUI App

```bash
python app.py
```

Paste a URL, click Download. Toggle "Download full playlist" for playlists.

### Command Line

```bash
python download.py "https://www.youtube.com/watch?v=VIDEO_ID"
python download.py "https://www.youtube.com/watch?v=VIDEO_ID" -o my_music
```

## Build .exe

```bash
python build.py
```

Output: `dist/Bongoo.exe`

## Features

- 320kbps MP3 conversion
- Album art + metadata embedding
- Playlist support
- Modern dark-themed GUI
- Standalone .exe packaging

## License

[MIT](LICENSE) — itu-dallasli
