import os
import queue
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import yt_dlp


class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TubeSwift Downloader")
        self.root.geometry("900x620")
        self.root.minsize(840, 560)
        self.root.configure(bg="#0e1116")

        self.log_queue = queue.Queue()
        self.is_downloading = False

        self._build_style()
        self._build_ui()
        self._poll_log_queue()

    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Card.TFrame", background="#151a22")
        style.configure("Header.TLabel", background="#0e1116", foreground="#f5f7fa", font=("Segoe UI Semibold", 20))
        style.configure("SubHeader.TLabel", background="#0e1116", foreground="#8b95a7", font=("Segoe UI", 10))
        style.configure("Label.TLabel", background="#151a22", foreground="#d8deea", font=("Segoe UI", 10))
        style.configure("Value.TLabel", background="#151a22", foreground="#f5f7fa", font=("Segoe UI Semibold", 10))
        style.configure("Primary.TButton", font=("Segoe UI Semibold", 10), padding=(14, 8), background="#1f6feb", foreground="white")
        style.map("Primary.TButton", background=[("active", "#2b7cff"), ("disabled", "#2a2f3b")])
        style.configure("Secondary.TButton", font=("Segoe UI", 10), padding=(10, 7), background="#262c39", foreground="#e5e9f0")
        style.map("Secondary.TButton", background=[("active", "#333b4b")])
        style.configure("Modern.Horizontal.TProgressbar", troughcolor="#1f2531", background="#1f6feb", bordercolor="#1f2531", lightcolor="#1f6feb", darkcolor="#1f6feb")

    def _build_ui(self):
        header = ttk.Frame(self.root, style="Card.TFrame")
        header.pack(fill="x", padx=16, pady=(16, 10))

        title_block = ttk.Frame(self.root)
        title_block.pack(fill="x", padx=16, pady=(0, 8))
        ttk.Label(title_block, text="TubeSwift Downloader", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            title_block,
            text="Fast YouTube and playlist downloads with live progress and reliability tuning.",
            style="SubHeader.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        content = ttk.Frame(self.root, style="Card.TFrame")
        content.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        form = ttk.Frame(content, style="Card.TFrame")
        form.pack(fill="x", padx=16, pady=16)

        ttk.Label(form, text="YouTube URL", style="Label.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 6))
        self.url_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.url_var, width=90).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 14))

        ttk.Label(form, text="Output Folder", style="Label.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=(0, 6))
        self.output_var = tk.StringVar(value=str(Path.cwd() / "downloaded-videos"))
        ttk.Entry(form, textvariable=self.output_var).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 14), padx=(0, 10))
        ttk.Button(form, text="Browse", style="Secondary.TButton", command=self._browse_folder).grid(row=3, column=2, sticky="ew", pady=(0, 14))

        self.max_height_var = tk.StringVar(value="720")
        ttk.Label(form, text="Max Quality", style="Label.TLabel").grid(row=4, column=0, sticky="w", pady=(0, 6))
        quality = ttk.Combobox(form, textvariable=self.max_height_var, values=["360", "480", "720", "1080"], state="readonly", width=12)
        quality.grid(row=5, column=0, sticky="w", pady=(0, 12))

        self.fast_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            form,
            text="Fast mode (more parallel chunks, best speed for stable internet)",
            variable=self.fast_mode_var
        ).grid(row=5, column=1, columnspan=2, sticky="w", pady=(0, 12))

        for idx in range(3):
            form.columnconfigure(idx, weight=1)

        action_row = ttk.Frame(content, style="Card.TFrame")
        action_row.pack(fill="x", padx=16)

        self.download_button = ttk.Button(action_row, text="Start Download", style="Primary.TButton", command=self.start_download)
        self.download_button.pack(side="left")

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(action_row, textvariable=self.status_var, style="Value.TLabel").pack(side="right")

        self.progress = ttk.Progressbar(content, style="Modern.Horizontal.TProgressbar", orient="horizontal", mode="determinate", maximum=100)
        self.progress.pack(fill="x", padx=16, pady=(12, 8))

        self.meta_var = tk.StringVar(value="Speed: -- | ETA: --")
        ttk.Label(content, textvariable=self.meta_var, style="SubHeader.TLabel").pack(anchor="w", padx=16)

        log_wrap = ttk.Frame(content, style="Card.TFrame")
        log_wrap.pack(fill="both", expand=True, padx=16, pady=(10, 16))

        self.log_box = tk.Text(
            log_wrap,
            bg="#0f131b",
            fg="#c8d1dd",
            insertbackground="#c8d1dd",
            bd=0,
            padx=10,
            pady=10,
            font=("Consolas", 10),
            wrap="word",
        )
        self.log_box.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=scrollbar.set)

    def _browse_folder(self):
        selected = filedialog.askdirectory(initialdir=self.output_var.get() or str(Path.cwd()))
        if selected:
            self.output_var.set(selected)

    def _poll_log_queue(self):
        while not self.log_queue.empty():
            kind, data = self.log_queue.get_nowait()
            if kind == "log":
                self.log_box.insert("end", f"{data}\n")
                self.log_box.see("end")
            elif kind == "progress":
                self.progress["value"] = data.get("percent", 0.0)
                self.status_var.set(data.get("status", "Downloading..."))
                self.meta_var.set(data.get("meta", "Speed: -- | ETA: --"))
            elif kind == "done":
                self.is_downloading = False
                self.download_button.configure(state="normal")
                self.status_var.set("Completed")
            elif kind == "error":
                self.is_downloading = False
                self.download_button.configure(state="normal")
                self.status_var.set("Failed")
                messagebox.showerror("Download Failed", data)
        self.root.after(120, self._poll_log_queue)

    @staticmethod
    def _fmt_bytes_per_sec(speed):
        if not speed:
            return "--"
        units = ["B/s", "KB/s", "MB/s", "GB/s"]
        value = float(speed)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}"
            value /= 1024
        return "--"

    @staticmethod
    def _fmt_eta(seconds):
        if seconds in (None, "N/A"):
            return "--"
        try:
            seconds = int(seconds)
        except (ValueError, TypeError):
            return "--"
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {sec}s"
        if minutes > 0:
            return f"{minutes}m {sec}s"
        return f"{sec}s"

    def _build_ydl_options(self, output_path, max_height):
        aria2_available = shutil.which("aria2c") is not None
        parallel_fragments = 8 if self.fast_mode_var.get() else 4

        ydl_opts = {
            "outtmpl": os.path.join(output_path, "%(title)s.%(ext)s"),
            "format": f"bv*[height<={max_height}]+ba/b[height<={max_height}]",
            "noplaylist": False,
            "continuedl": True,
            "overwrites": False,
            "retries": 10,
            "fragment_retries": 10,
            "concurrent_fragment_downloads": parallel_fragments,
            "buffersize": 1024 * 1024,
            "http_chunk_size": 10 * 1024 * 1024 if self.fast_mode_var.get() else 4 * 1024 * 1024,
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        if aria2_available:
            ydl_opts["external_downloader"] = "aria2c"
            ydl_opts["external_downloader_args"] = [
                "-x", "16",
                "-s", "16",
                "-k", "1M",
                "--min-split-size=1M",
                "--summary-interval=1",
            ]
            self.log_queue.put(("log", "Using aria2c accelerator for faster segmented downloads."))
        else:
            self.log_queue.put(("log", "aria2c not found; using yt-dlp parallel fragments."))

        return ydl_opts

    def _progress_hook(self, d):
        status = d.get("status", "")
        if status == "downloading":
            downloaded = d.get("downloaded_bytes", 0)
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            percent = (downloaded / total * 100) if total else 0.0

            speed = self._fmt_bytes_per_sec(d.get("speed"))
            eta = self._fmt_eta(d.get("eta"))
            meta = f"Speed: {speed} | ETA: {eta}"

            title = d.get("info_dict", {}).get("title", "Downloading...")
            self.log_queue.put(("progress", {"percent": percent, "status": f"Downloading: {title}", "meta": meta}))
        elif status == "finished":
            self.log_queue.put(("log", "Download finished. Processing final file..."))
            self.log_queue.put(("progress", {"percent": 100.0, "status": "Finalizing...", "meta": "Speed: -- | ETA: 0s"}))

    def start_download(self):
        if self.is_downloading:
            return

        url = self.url_var.get().strip()
        output_path = self.output_var.get().strip()
        max_height = self.max_height_var.get().strip()

        if not url:
            messagebox.showwarning("Missing URL", "Please enter a YouTube video or playlist URL.")
            return
        if not output_path:
            messagebox.showwarning("Missing Output Folder", "Please choose an output folder.")
            return

        Path(output_path).mkdir(parents=True, exist_ok=True)

        self.progress["value"] = 0
        self.status_var.set("Starting...")
        self.meta_var.set("Speed: -- | ETA: --")
        self.log_box.delete("1.0", "end")
        self.log_queue.put(("log", f"Source: {url}"))
        self.log_queue.put(("log", f"Output: {output_path}"))
        self.log_queue.put(("log", f"Quality cap: {max_height}p"))

        self.is_downloading = True
        self.download_button.configure(state="disabled")

        worker = threading.Thread(target=self._run_download, args=(url, output_path, max_height), daemon=True)
        worker.start()

    def _run_download(self, url, output_path, max_height):
        try:
            ydl_opts = self._build_ydl_options(output_path, max_height)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.log_queue.put(("done", None))
            self.log_queue.put(("log", "All downloads completed successfully."))
        except Exception as exc:
            self.log_queue.put(("error", str(exc)))
            self.log_queue.put(("log", f"Error: {exc}"))


def main():
    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
