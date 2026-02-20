# Bongoo — YouTube MP3/MP4 Downloader
# by itu-dallasli
#
# A simple desktop app to download YouTube videos as MP3 or MP4.
# Usage: python app.py

import os
import sys
import re
import shutil
import glob
import threading
import subprocess
import customtkinter as ctk
import yt_dlp
from lyrics import srt_to_lrc


# only allow real youtube URLs
ALLOWED_URL = re.compile(
    r'^https?://(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/.+$'
)

MAX_URL_LENGTH = 2048

# Browser priority for cookie auto-detection
_BROWSER_PRIORITY = ["chrome", "edge", "firefox", "brave", "opera", "chromium"]


def detect_cookie_browser():
    """Auto-detect the best browser for cookie extraction.
    Tries each browser in priority order; returns the first one that works,
    or None if no browser cookies are accessible.
    """
    import yt_dlp.cookies
    for browser in _BROWSER_PRIORITY:
        try:
            # Try to open the cookie jar — if it works, the browser is usable
            jar = yt_dlp.cookies.extract_cookies_from_browser(browser)
            if jar is not None:
                return browser
        except Exception:
            continue
    return None


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Bongoo")
        self.geometry("540x640")
        self.minsize(460, 580)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.output_dir = os.path.join(os.getcwd(), "downloads")
        self.downloading = False
        self._last_clipboard = ""

        self.build_ui()

    def build_ui(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=30, pady=20)

        # Title
        ctk.CTkLabel(
            frame, text="Bongoo",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=(10, 5))

        ctk.CTkLabel(
            frame, text="by itu-dallasli",
            font=ctk.CTkFont(size=12), text_color="gray",
        ).pack(pady=(0, 15))

        # URL input
        self.url_entry = ctk.CTkEntry(
            frame, placeholder_text="Paste YouTube URL here...",
            height=45, font=ctk.CTkFont(size=14), corner_radius=10,
        )
        self.url_entry.pack(fill="x", pady=(0, 8))

        # Options row 1 — format selector + folder
        opts1 = ctk.CTkFrame(frame, fg_color="transparent")
        opts1.pack(fill="x", pady=(0, 8))

        self.format_var = ctk.StringVar(value="MP3")
        self.format_selector = ctk.CTkSegmentedButton(
            opts1, values=["MP3", "MP4 360p", "MP4 720p"],
            variable=self.format_var, font=ctk.CTkFont(size=12),
            command=self.on_format_change,
        )
        self.format_selector.pack(side="left")

        ctk.CTkButton(
            opts1, text="📁 Folder", width=100, height=30,
            font=ctk.CTkFont(size=12), fg_color="gray30",
            hover_color="gray40", corner_radius=8,
            command=self.pick_folder,
        ).pack(side="right")

        # Options row 2 — playlist + subtitles
        opts2 = ctk.CTkFrame(frame, fg_color="transparent")
        opts2.pack(fill="x", pady=(0, 8))

        self.playlist_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            opts2, text="Full playlist",
            variable=self.playlist_var, font=ctk.CTkFont(size=12),
        ).pack(side="left")

        self.subtitle_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            opts2, text="📝 Subtitles/Lyrics",
            variable=self.subtitle_var, font=ctk.CTkFont(size=12),
        ).pack(side="right")

        # Options row 3 — trim + clipboard
        trim_frame = ctk.CTkFrame(frame, fg_color="transparent")
        trim_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            trim_frame, text="✂ Trim:",
            font=ctk.CTkFont(size=12), text_color="#aaa",
        ).pack(side="left", padx=(0, 6))

        self.start_entry = ctk.CTkEntry(
            trim_frame, placeholder_text="Start (sec)",
            width=100, height=30, font=ctk.CTkFont(size=12), corner_radius=8,
        )
        self.start_entry.pack(side="left", padx=(0, 6))

        self.end_entry = ctk.CTkEntry(
            trim_frame, placeholder_text="End (sec)",
            width=100, height=30, font=ctk.CTkFont(size=12), corner_radius=8,
        )
        self.end_entry.pack(side="left", padx=(0, 6))

        self.clipboard_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            trim_frame, text="📋 Clipboard",
            variable=self.clipboard_var, font=ctk.CTkFont(size=12),
            command=self.toggle_clipboard,
        ).pack(side="right")

        # Options row 4 — AI features (normalize, analyze, stems)
        ai_frame = ctk.CTkFrame(frame, fg_color="transparent")
        ai_frame.pack(fill="x", pady=(0, 8))

        self.normalize_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            ai_frame, text="🔊 Normalize",
            variable=self.normalize_var, font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 12))

        self.analyze_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            ai_frame, text="🎵 BPM & Key",
            variable=self.analyze_var, font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 12))

        # Options row 5 — stem separation + model selector
        stem_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stem_frame.pack(fill="x", pady=(0, 8))

        self.stems_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            stem_frame, text="🎛 Separate Stems",
            variable=self.stems_var, font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(0, 12))

        self.stem_model_var = ctk.StringVar(value="Open-Unmix")
        self.stem_model_menu = ctk.CTkOptionMenu(
            stem_frame, values=["Open-Unmix", "Demucs"],
            variable=self.stem_model_var, font=ctk.CTkFont(size=12),
            width=130, height=30, fg_color="gray30",
            button_color="gray40", corner_radius=8,
        )
        self.stem_model_menu.pack(side="left")

        # Download button
        self.dl_btn = ctk.CTkButton(
            frame, text="⬇  Download MP3", height=50,
            font=ctk.CTkFont(size=16, weight="bold"), corner_radius=12,
            fg_color="#6C3CE1", hover_color="#5A2FBF",
            command=self.start_download,
        )
        self.dl_btn.pack(fill="x", pady=(0, 12))

        # Progress bar
        self.progress = ctk.CTkProgressBar(frame, height=8, corner_radius=4, progress_color="#6C3CE1")
        self.progress.pack(fill="x", pady=(0, 8))
        self.progress.set(0)

        # Status
        self.status = ctk.CTkLabel(
            frame, text="Ready", font=ctk.CTkFont(size=13),
            text_color="#8a8a8a", anchor="w",
        )
        self.status.pack(fill="x", pady=(0, 5))

        # Log
        self.log = ctk.CTkTextbox(
            frame, height=100, font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8, state="disabled", fg_color="gray14",
        )
        self.log.pack(fill="both", expand=True, pady=(0, 8))

        # Footer
        footer = ctk.CTkFrame(frame, fg_color="transparent")
        footer.pack(fill="x")

        self.folder_label = ctk.CTkLabel(
            footer, text=f"{self.output_dir}",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w",
        )
        self.folder_label.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            footer, text="Open Folder", width=95, height=28,
            font=ctk.CTkFont(size=11), fg_color="gray30",
            hover_color="gray40", corner_radius=6,
            command=self.open_folder,
        ).pack(side="right")

    # -- helpers --

    def write_log(self, msg):
        def _do():
            self.log.configure(state="normal")
            self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.after(0, _do)

    def set_status(self, text, color="#8a8a8a"):
        self.after(0, lambda: self.status.configure(text=text, text_color=color))

    def set_progress(self, val):
        self.after(0, lambda: self.progress.set(val))

    def pick_folder(self):
        folder = ctk.filedialog.askdirectory(title="Choose download folder", initialdir=self.output_dir)
        if folder:
            self.output_dir = folder
            self.folder_label.configure(text=f"📁 {self.output_dir}")

    def open_folder(self):
        os.makedirs(self.output_dir, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(self.output_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self.output_dir])
        else:
            subprocess.Popen(["xdg-open", self.output_dir])

    def on_format_change(self, value):
        if value == "MP3":
            self.dl_btn.configure(text="⬇  Download MP3")
        else:
            self.dl_btn.configure(text=f"⬇  Download {value}")

    # -- clipboard --

    def toggle_clipboard(self):
        if self.clipboard_var.get():
            self._last_clipboard = ""
            self.write_log("📋 Clipboard watch enabled")
            self.poll_clipboard()
        else:
            self.write_log("📋 Clipboard watch disabled")

    def poll_clipboard(self):
        if not self.clipboard_var.get():
            return
        try:
            text = self.clipboard_get().strip()
            if text != self._last_clipboard and ALLOWED_URL.match(text):
                self._last_clipboard = text
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, text)
                self.set_status("📋 YouTube link detected!", "#3498db")
                self.write_log(f"📋 Auto-filled: {text}")
        except Exception:
            pass
        self.after(1500, self.poll_clipboard)

    # -- trim helpers --

    def parse_trim(self):
        start_text = self.start_entry.get().strip()
        end_text = self.end_entry.get().strip()
        start = None
        end = None

        if start_text:
            try:
                start = float(start_text)
                if start < 0:
                    raise ValueError
            except ValueError:
                self.set_status("Invalid start time", "#e74c3c")
                return None, "error"

        if end_text:
            try:
                end = float(end_text)
                if end < 0:
                    raise ValueError
            except ValueError:
                self.set_status("Invalid end time", "#e74c3c")
                return None, "error"

        if start is not None and end is not None and start >= end:
            self.set_status("Start must be less than End", "#e74c3c")
            return None, "error"

        return start, end

    # -- download --

    def get_download_mode(self):
        fmt = self.format_var.get()
        if fmt == "MP4 360p":
            return "mp4_360"
        elif fmt == "MP4 720p":
            return "mp4_720"
        return "mp3"

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self.set_status("Paste a YouTube URL first!", "#e74c3c")
            return

        if len(url) > MAX_URL_LENGTH:
            self.set_status("URL is too long", "#e74c3c")
            return

        if not ALLOWED_URL.match(url):
            self.set_status("Invalid URL — only YouTube links allowed", "#e74c3c")
            self.write_log("Only youtube.com and youtu.be URLs are accepted.")
            return

        if shutil.which("ffmpeg") is None:
            self.set_status("❌  FFmpeg not found — install it first", "#e74c3c")
            self.write_log("Install FFmpeg: winget install FFmpeg")
            return

        start, end = self.parse_trim()
        if end == "error":
            return

        mode = self.get_download_mode()
        ext = "mp4" if mode.startswith("mp4") else "mp3"

        self.downloading = True
        self.dl_btn.configure(text=f"⏳  Downloading {ext.upper()}...", state="disabled", fg_color="gray40")
        self.url_entry.configure(state="disabled")
        self.set_status("🔄  Starting...", "#f39c12")
        self.set_progress(0)

        self.after(0, lambda: (
            self.log.configure(state="normal"),
            self.log.delete("1.0", "end"),
            self.log.configure(state="disabled"),
        ))

        threading.Thread(
            target=self.do_download, args=(url, start, end, mode), daemon=True
        ).start()

    def do_download(self, url, start=None, end=None, mode="mp3"):
        output_dir = os.path.realpath(self.output_dir)
        os.makedirs(output_dir, exist_ok=True)
        subtitles = self.subtitle_var.get()
        normalize = self.normalize_var.get()
        do_analyze = self.analyze_var.get()
        do_stems = self.stems_var.get()
        stem_model = "demucs" if self.stem_model_var.get() == "Demucs" else "openunmix"

        def on_progress(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = done / total
                    self.set_progress(pct)
                    self.set_status(f"⬇️  {pct:.0%} downloaded", "#3498db")
            elif d["status"] == "finished":
                self.set_progress(1.0)
                if mode == "mp3":
                    self.set_status("🔄  Converting to MP3...", "#f39c12")
                    self.write_log("Converting to MP3...")
                else:
                    self.set_status("🔄  Merging video...", "#f39c12")
                    self.write_log("Merging video tracks...")

        ext = "mp4" if mode.startswith("mp4") else "mp3"

        opts = {
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "noplaylist": not self.playlist_var.get(),
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [on_progress],
            # --- Anti-429: retry + backoff ---
            "retries": 10,
            "extractor_retries": 5,
            "retry_sleep_functions": {"http": lambda n: 2 ** n},
            "sleep_interval": 1,
            "max_sleep_interval": 5,
        }

        # --- Anti-429: auto-detect browser cookies ---
        cookie_browser = detect_cookie_browser()
        if cookie_browser:
            opts["cookiesfrombrowser"] = (cookie_browser,)
            self.write_log(f"🍪 Auto-detected {cookie_browser} cookies")
        else:
            self.write_log("🍪 No browser cookies found (may get 429 errors)")

        if mode.startswith("mp4"):
            height = 360 if "360" in mode else 720
            opts["format"] = (
                f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
            )
            opts["merge_output_format"] = "mp4"
            opts["postprocessors"] = [{"key": "FFmpegMetadata"}]
        else:
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

        if subtitles:
            opts["writesubtitles"] = True
            opts["writeautomaticsub"] = True
            opts["subtitleslangs"] = ["en", "tr"]
            opts["subtitlesformat"] = "srt"
            self.write_log("📝 Subtitle download enabled")

        if start is not None or end is not None:
            pp_args = []
            if start is not None:
                pp_args += ["-ss", str(start)]
            if end is not None:
                pp_args += ["-to", str(end)]
            opts["postprocessor_args"] = {"ffmpeg_i1": pp_args}
            self.write_log(f"✂ Trimming: {start or 0}s → {end or 'end'}s")

        if normalize and mode == "mp3":
            opts.setdefault("postprocessor_args", {})
            norm_args = ["-af", "loudnorm=I=-14:TP=-1:LRA=11"]
            if "ffmpeg_o" in opts["postprocessor_args"]:
                opts["postprocessor_args"]["ffmpeg_o"] += norm_args
            else:
                opts["postprocessor_args"]["ffmpeg_o"] = norm_args
            self.write_log("🔊 Audio normalization enabled (-14 LUFS)")

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if "entries" in info:
                    count = sum(1 for _ in info["entries"])
                    self.write_log(f"Downloaded {count} tracks!")
                    self.set_status(f"Done — {count} tracks saved", "#2ecc71")
                else:
                    title = info.get("title", "Unknown")
                    artist = info.get("uploader", info.get("channel", "Unknown"))
                    duration = info.get("duration", 0)

                    self.write_log(f"Saved: {title}.{ext}")
                    self.write_log(f"  Artist:   {artist}")
                    self.write_log(f"  Duration: {int(duration // 60)}:{int(duration % 60):02d}")

                    if subtitles and mode == "mp3":
                        # Only match SRT files for THIS song (not leftover ones)
                        safe_title = glob.escape(title)
                        srt_files = glob.glob(os.path.join(output_dir, f"{safe_title}*.srt"))
                        for srt_file in srt_files:
                            lrc_path = srt_to_lrc(srt_file)
                            if lrc_path:
                                self.write_log(f"  Lyrics:   {os.path.basename(lrc_path)}")

                    # Post-download: BPM & Key analysis
                    if do_analyze and mode == "mp3":
                        mp3_path = os.path.join(output_dir, f"{title}.mp3")
                        if os.path.isfile(mp3_path):
                            self.set_status("🎵 Analyzing BPM & Key...", "#f39c12")
                            try:
                                from analysis import analyze, format_result
                                result = analyze(mp3_path)
                                if result:
                                    self.write_log(f"  Analysis: {format_result(result)}")
                                else:
                                    self.write_log("  Analysis: failed (missing librosa?)")
                            except Exception as e:
                                self.write_log(f"  Analysis error: {e}")

                    # Post-download: Stem separation
                    if do_stems and mode == "mp3":
                        mp3_path = os.path.join(output_dir, f"{title}.mp3")
                        if os.path.isfile(mp3_path):
                            self.set_status(f"🎛 Separating stems ({stem_model})...", "#f39c12")
                            self.write_log(f"  Separating with {stem_model}...")
                            try:
                                from stems import separate
                                stems_result = separate(mp3_path, model=stem_model)
                                if stems_result:
                                    for name, path in stems_result.items():
                                        self.write_log(f"  Stem: {name} → {os.path.basename(path)}")
                                else:
                                    self.write_log("  Stem separation failed")
                            except Exception as e:
                                self.write_log(f"  Stem error: {e}")

                    self.set_status(f"✅ Done — {title}.{ext}", "#2ecc71")

                self.set_progress(1.0)
        except Exception as e:
            self.write_log(f"Error: {e}")
            self.set_status("Download failed", "#e74c3c")
            self.set_progress(0)
        finally:
            self.downloading = False
            fmt_label = self.format_var.get()
            self.after(0, lambda: (
                self.dl_btn.configure(
                    text=f"⬇  Download {fmt_label}",
                    state="normal", fg_color="#6C3CE1"
                ),
                self.url_entry.configure(state="normal"),
            ))


if __name__ == "__main__":
    App().mainloop()
