# lyrics.py — SRT to LRC converter for Bongoo
# by itu-dallasli
#
# Converts .srt subtitle files to .lrc (synchronized lyrics) format.

import re
import os


def srt_time_to_lrc(srt_time):
    """Convert SRT timestamp (HH:MM:SS,mmm) to LRC timestamp [MM:SS.xx]."""
    match = re.match(r'(\d+):(\d+):(\d+)[,.](\d+)', srt_time)
    if not match:
        return None
    h, m, s, ms = int(match[1]), int(match[2]), int(match[3]), int(match[4])
    total_min = h * 60 + m
    centisec = int(ms / 10)  # LRC uses centiseconds
    return f"[{total_min:02d}:{s:02d}.{centisec:02d}]"


def srt_to_lrc(srt_path, lrc_path=None):
    """Convert an .srt file to .lrc format.

    Args:
        srt_path: Path to the .srt file
        lrc_path: Output path (default: same name with .lrc extension)

    Returns:
        Path to the created .lrc file, or None on failure
    """
    if lrc_path is None:
        lrc_path = os.path.splitext(srt_path)[0] + ".lrc"

    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return None

    # Parse SRT blocks: number, timestamp line, text lines
    blocks = re.split(r'\n\s*\n', content.strip())
    lines = []

    for block in blocks:
        block_lines = block.strip().split('\n')
        if len(block_lines) < 3:
            continue

        # Second line has timestamps: 00:01:23,456 --> 00:01:25,789
        time_match = re.match(
            r'(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)',
            block_lines[1]
        )
        if not time_match:
            continue

        lrc_time = srt_time_to_lrc(time_match.group(1))
        if lrc_time is None:
            continue

        # Join remaining text lines (strip HTML tags)
        text = " ".join(block_lines[2:])
        text = re.sub(r'<[^>]+>', '', text).strip()
        if text:
            lines.append(f"{lrc_time}{text}")

    if not lines:
        return None

    with open(lrc_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return lrc_path
