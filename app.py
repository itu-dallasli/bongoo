# Bongoo — YouTube MP3 Downloader
# by itu-dallasli
#
# A simple desktop app to download YouTube videos as MP3.
# Usage: python app.py

import os
import sys
import shutil
import threading
import subprocess
import customtkinter as ctk
import yt_dlp


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Bongoo — itu-dallasli")
        self.geometry("540x460")
        self.minsize(460, 400)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.output_dir = os.path.join(os.getcwd(), "downloads")
        self.downloading = False

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

        # Options row
        opts = ctk.CTkFrame(frame, fg_color="transparent")
        opts.pack(fill="x", pady=(0, 12))

        self.playlist_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            opts, text="Download full playlist",
            variable=self.playlist_var, font=ctk.CTkFont(size=12),
        ).pack(side="left")

        ctk.CTkButton(
            opts, text="📁 Folder", width=100, height=30,
            font=ctk.CTkFont(size=12), fg_color="gray30",
            hover_color="gray40", corner_radius=8,
            command=self.pick_folder,
        ).pack(side="right")

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
            frame, height=90, font=ctk.CTkFont(family="Consolas", size=11),
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

    # -- download --

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self.set_status("⚠️  Paste a YouTube URL first!", "#e74c3c")
            return

        if shutil.which("ffmpeg") is None:
            self.set_status("❌  FFmpeg not found — install it first", "#e74c3c")
            self.write_log("Install FFmpeg: winget install FFmpeg")
            return

        # disable button
        self.downloading = True
        self.dl_btn.configure(text="⏳  Downloading...", state="disabled", fg_color="gray40")
        self.url_entry.configure(state="disabled")
        self.set_status("🔄  Starting...", "#f39c12")
        self.set_progress(0)

        # clear log
        self.after(0, lambda: (
            self.log.configure(state="normal"),
            self.log.delete("1.0", "end"),
            self.log.configure(state="disabled"),
        ))

        threading.Thread(target=self.do_download, args=(url,), daemon=True).start()

    def do_download(self, url):
        os.makedirs(self.output_dir, exist_ok=True)

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
                self.set_status("🔄  Converting to MP3...", "#f39c12")
                self.write_log("Converting to MP3...")

        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
            "writethumbnail": True,
            "noplaylist": not self.playlist_var.get(),
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [on_progress],
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

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

                if "entries" in info:
                    count = sum(1 for _ in info["entries"])
                    self.write_log(f"Downloaded {count} tracks!")
                    self.set_status(f"Done — {count} tracks saved", "#2ecc71")
                else:
                    title = info.get("title", "Unknown")
                    self.write_log(f"Saved: {title}.mp3")
                    self.set_status(f" Done — {title}.mp3", "#2ecc71")

                self.set_progress(1.0)
        except Exception as e:
            self.write_log(f"Error: {e}")
            self.set_status("Download failed", "#e74c3c")
            self.set_progress(0)
        finally:
            self.downloading = False
            self.after(0, lambda: (
                self.dl_btn.configure(text="⬇  Download MP3", state="normal", fg_color="#6C3CE1"),
                self.url_entry.configure(state="normal"),
            ))


if __name__ == "__main__":
    App().mainloop()
