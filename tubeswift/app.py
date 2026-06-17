import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .downloader import DownloadCancelled, DownloadEngine
from .ffmpeg import discover_ffmpeg
from .models import DownloadSettings
from .preflight import PreflightError, ensure_ffmpeg, ensure_output_dir, validate_youtube_url


class DownloaderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("TubeSwift Downloader")
        self.root.geometry("1180x760")
        self.root.minsize(1020, 680)
        self.root.configure(bg="#08101a")

        self.log_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.is_downloading = False
        self.cancel_requested = False

        self._build_style()
        self._build_ui()
        self._poll_log_queue()

    def _build_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("App.TFrame", background="#08101a")
        style.configure("Card.TFrame", background="#101d2d")
        style.configure("Panel.TFrame", background="#0c1826")

        style.configure(
            "Hero.TLabel",
            background="#08101a",
            foreground="#e8f4ff",
            font=("Avenir Next Demi Bold", 28),
        )
        style.configure(
            "HeroSub.TLabel",
            background="#08101a",
            foreground="#7fa0be",
            font=("Avenir Next", 11),
        )

        style.configure(
            "CardTitle.TLabel",
            background="#101d2d",
            foreground="#9fd8ff",
            font=("Avenir Next Demi Bold", 12),
        )
        style.configure(
            "Label.TLabel",
            background="#101d2d",
            foreground="#dce9f4",
            font=("Avenir Next", 11),
        )
        style.configure(
            "Meta.TLabel",
            background="#0c1826",
            foreground="#a8c2d8",
            font=("Avenir Next", 10),
        )
        style.configure(
            "Value.TLabel",
            background="#0c1826",
            foreground="#ecf7ff",
            font=("Avenir Next Demi Bold", 11),
        )
        style.configure(
            "Status.TLabel",
            background="#0c1826",
            foreground="#63ffd9",
            font=("Avenir Next Demi Bold", 11),
        )

        style.configure(
            "Primary.TButton",
            font=("Avenir Next Demi Bold", 11),
            padding=(16, 10),
            background="#00b7ff",
            foreground="#03101f",
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#4dd2ff"), ("disabled", "#225a75")],
            foreground=[("disabled", "#9bc3d8")],
        )

        style.configure(
            "Secondary.TButton",
            font=("Avenir Next Demi Bold", 10),
            padding=(12, 9),
            background="#1b3147",
            foreground="#d2e8f7",
            borderwidth=0,
        )
        style.map("Secondary.TButton", background=[("active", "#284763")])

        style.configure(
            "Neon.Horizontal.TProgressbar",
            troughcolor="#14243a",
            background="#00d9ff",
            bordercolor="#14243a",
            lightcolor="#00d9ff",
            darkcolor="#00d9ff",
        )

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, style="App.TFrame")
        container.pack(fill="both", expand=True, padx=18, pady=16)

        header = ttk.Frame(container, style="App.TFrame")
        header.pack(fill="x", pady=(0, 12))

        ttk.Label(header, text="TubeSwift // HyperDownload", style="Hero.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text=(
                "Modern YouTube ingestion pipeline with adaptive throughput tuning, "
                "live telemetry, and fail-safe transfer controls."
            ),
            style="HeroSub.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(container, style="App.TFrame")
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, style="Card.TFrame")
        left.pack(side="left", fill="both", expand=False, padx=(0, 12))

        right = ttk.Frame(body, style="App.TFrame")
        right.pack(side="left", fill="both", expand=True)

        self._build_controls(left)
        self._build_telemetry(right)

    def _build_controls(self, parent: ttk.Frame) -> None:
        controls = ttk.Frame(parent, style="Card.TFrame", padding=18)
        controls.pack(fill="both", expand=True)

        ttk.Label(controls, text="Mission Control", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(controls, text="YouTube URL", style="Label.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        self.url_var = tk.StringVar()
        ttk.Entry(controls, textvariable=self.url_var, width=58).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(0, 14)
        )

        ttk.Label(controls, text="Output Folder", style="Label.TLabel").grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        self.output_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        ttk.Entry(controls, textvariable=self.output_var).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(0, 14), padx=(0, 8)
        )
        ttk.Button(controls, text="Browse", style="Secondary.TButton", command=self._browse_folder).grid(
            row=4, column=2, sticky="ew", pady=(0, 14)
        )

        ttk.Label(controls, text="Max Resolution", style="Label.TLabel").grid(row=5, column=0, sticky="w")
        ttk.Label(controls, text="Performance Profile", style="Label.TLabel").grid(row=5, column=1, sticky="w")
        ttk.Label(controls, text="Output Strategy", style="Label.TLabel").grid(row=5, column=2, sticky="w")

        self.max_height_var = tk.StringVar(value="1080")
        ttk.Combobox(
            controls,
            textvariable=self.max_height_var,
            values=["360", "480", "720", "1080"],
            state="readonly",
            width=10,
        ).grid(row=6, column=0, sticky="ew", pady=(6, 14), padx=(0, 8))

        self.profile_var = tk.StringVar(value="Turbo")
        profile_box = ttk.Combobox(
            controls,
            textvariable=self.profile_var,
            values=["Balanced", "Turbo", "Extreme"],
            state="readonly",
            width=14,
        )
        profile_box.grid(row=6, column=1, sticky="ew", pady=(6, 14), padx=(0, 8))
        profile_box.bind("<<ComboboxSelected>>", lambda _e: self._update_profile_hint())

        self.output_mode_var = tk.StringVar(value="Fastest")
        output_box = ttk.Combobox(
            controls,
            textvariable=self.output_mode_var,
            values=["Fastest", "MP4 Compatible"],
            state="readonly",
            width=16,
        )
        output_box.grid(row=6, column=2, sticky="ew", pady=(6, 14))
        output_box.bind("<<ComboboxSelected>>", lambda _e: self._update_profile_hint())

        ttk.Label(controls, text="Download Type", style="Label.TLabel").grid(row=8, column=0, sticky="w", pady=(10, 6))
        self.download_type_var = tk.StringVar(value="Video")
        download_type_box = ttk.Combobox(
            controls,
            textvariable=self.download_type_var,
            values=["Video", "MP3"],
            state="readonly",
            width=16,
        )
        download_type_box.grid(row=8, column=1, columnspan=2, sticky="ew", pady=(10, 6))
        download_type_box.bind("<<ComboboxSelected>>", lambda _e: self._update_profile_hint())

        self.profile_hint_var = tk.StringVar(value="Turbo + Fastest targets peak throughput and minimal post-processing.")
        ttk.Label(controls, textvariable=self.profile_hint_var, style="Meta.TLabel", wraplength=430).grid(
            row=9, column=0, columnspan=3, sticky="w", pady=(0, 16)
        )

        actions = ttk.Frame(controls, style="Card.TFrame")
        actions.grid(row=10, column=0, columnspan=3, sticky="ew")

        self.download_button = ttk.Button(
            actions, text="Start Hyper Download", style="Primary.TButton", command=self.start_download
        )
        self.download_button.pack(side="left")

        self.cancel_button = ttk.Button(
            actions,
            text="Cancel",
            style="Secondary.TButton",
            command=self.cancel_download,
            state="disabled",
        )
        self.cancel_button.pack(side="left", padx=(8, 0))

        ttk.Label(controls, text="Live Status", style="CardTitle.TLabel").grid(
            row=11, column=0, sticky="w", pady=(20, 8)
        )

        status_panel = ttk.Frame(controls, style="Panel.TFrame", padding=10)
        status_panel.grid(row=12, column=0, columnspan=3, sticky="ew")

        ttk.Label(status_panel, text="State", style="Meta.TLabel").grid(row=0, column=0, sticky="w")
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(status_panel, textvariable=self.status_var, style="Status.TLabel").grid(
            row=1, column=0, sticky="w", pady=(2, 6)
        )

        ttk.Label(status_panel, text="Transfer", style="Meta.TLabel").grid(row=2, column=0, sticky="w")
        self.meta_var = tk.StringVar(value="Speed: -- | Avg: -- | ETA: --")
        ttk.Label(status_panel, textvariable=self.meta_var, style="Value.TLabel", wraplength=420).grid(
            row=3, column=0, sticky="w", pady=(2, 0)
        )

        for idx in range(3):
            controls.columnconfigure(idx, weight=1)
        status_panel.columnconfigure(0, weight=1)


    def _build_telemetry(self, parent: ttk.Frame) -> None:
        top_panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        top_panel.pack(fill="x", pady=(0, 12))

        ttk.Label(top_panel, text="Telemetry", style="CardTitle.TLabel").pack(anchor="w")

        self.progress = ttk.Progressbar(
            top_panel,
            style="Neon.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        self.progress.pack(fill="x", pady=(10, 8))

        self.progress_caption = tk.StringVar(value="Awaiting launch...")
        ttk.Label(top_panel, textvariable=self.progress_caption, style="Meta.TLabel").pack(anchor="w")

        log_panel = ttk.Frame(parent, style="Panel.TFrame", padding=16)
        log_panel.pack(fill="both", expand=True)

        ttk.Label(log_panel, text="Transfer Log", style="CardTitle.TLabel").pack(anchor="w")

        text_wrap = ttk.Frame(log_panel, style="Panel.TFrame")
        text_wrap.pack(fill="both", expand=True, pady=(10, 0))

        self.log_box = tk.Text(
            text_wrap,
            bg="#08101a",
            fg="#bcecff",
            insertbackground="#bcecff",
            bd=0,
            padx=12,
            pady=10,
            font=("Menlo", 11),
            wrap="word",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#15324f",
            highlightcolor="#00d9ff",
        )
        self.log_box.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(text_wrap, orient="vertical", command=self.log_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_box.configure(yscrollcommand=scrollbar.set)

    def _update_profile_hint(self) -> None:
        profile = self.profile_var.get()
        mode = self.output_mode_var.get()

        hints = {
            ("Balanced", "Fastest"): "Balanced network pressure with quick muxed stream preference.",
            ("Balanced", "MP4 Compatible"): "Balanced speed with compatibility-focused MP4 remuxing.",
            ("Turbo", "Fastest"): "Turbo + Fastest targets peak throughput and minimal post-processing.",
            ("Turbo", "MP4 Compatible"): "Turbo transfer with MP4 compatibility at a small finalize cost.",
            ("Extreme", "Fastest"): "Extreme pushes aggressive concurrency; best on high-bandwidth stable networks.",
            ("Extreme", "MP4 Compatible"): "Extreme transfer speed with aggressive settings and MP4 remuxing.",
        }
        self.profile_hint_var.set(hints.get((profile, mode), "Adaptive transfer profile selected."))

    def _browse_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_var.get() or str(Path.cwd()))
        if selected:
            self.output_var.set(selected)

    def _poll_log_queue(self) -> None:
        while not self.log_queue.empty():
            kind, data = self.log_queue.get_nowait()
            if kind == "log":
                self.log_box.insert("end", f"{data}\n")
                self.log_box.see("end")
            elif kind == "progress":
                self.progress["value"] = data.percent
                self.status_var.set(data.status)
                self.progress_caption.set(f"{data.percent:.1f}% complete")
                self.meta_var.set(data.meta)
            elif kind == "done":
                self._finish_state("Completed")
            elif kind == "cancelled":
                self._finish_state("Cancelled")
                self.log_queue.put(("log", "Download cancelled."))
            elif kind == "error":
                self._finish_state("Failed")
                messagebox.showerror("Download Failed", str(data))

        self.root.after(120, self._poll_log_queue)

    def _finish_state(self, status: str) -> None:
        self.is_downloading = False
        self.cancel_requested = False
        self.download_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.status_var.set(status)

    def _get_settings(self) -> DownloadSettings:
        url = self.url_var.get().strip()
        output_path = self.output_var.get().strip()
        max_height = self.max_height_var.get().strip()
        performance_profile = self.profile_var.get().strip()
        output_mode = self.output_mode_var.get().strip()
        download_type = self.download_type_var.get().strip()

        if not url:

            raise PreflightError("Please enter a YouTube video or playlist URL.")
        if not output_path:
            raise PreflightError("Please choose an output folder.")

        validate_youtube_url(url)

        try:
            max_height_int = int(max_height)
        except ValueError as exc:
            raise PreflightError("Invalid quality selected.") from exc

        if performance_profile not in {"Balanced", "Turbo", "Extreme"}:
            raise PreflightError("Invalid performance profile selected.")
        if output_mode not in {"Fastest", "MP4 Compatible"}:
            raise PreflightError("Invalid output mode selected.")
        if download_type not in {"Video", "MP3"}:
            raise PreflightError("Invalid download type selected.")

        output_dir = Path(output_path)
        ensure_output_dir(output_dir)
        ensure_ffmpeg()

        return DownloadSettings(
            url=url,
            output_dir=output_dir,
            max_height=max_height_int,
            performance_profile=performance_profile,
            output_mode=output_mode,
            download_type=download_type.lower(),
        )


    def start_download(self) -> None:
        if self.is_downloading:
            return

        try:
            settings = self._get_settings()
        except PreflightError as exc:
            messagebox.showwarning("Cannot Start Download", str(exc))
            return

        self.progress["value"] = 0
        self.progress_caption.set("Initializing transfer...")
        self.status_var.set("Starting...")
        self.meta_var.set("Speed: -- | Avg: -- | ETA: --")
        self.log_box.delete("1.0", "end")
        self.log_queue.put(("log", f"Source: {settings.url}"))
        self.log_queue.put(("log", f"Output: {settings.output_dir}"))
        self.log_queue.put(("log", f"Resolution Cap: {settings.max_height}p"))
        self.log_queue.put(("log", f"Performance Profile: {settings.performance_profile}"))
        self.log_queue.put(("log", f"Output Strategy: {settings.output_mode}"))
        self.log_queue.put(("log", f"Download Type: {settings.download_type}"))
        self.log_queue.put(("log", f"ffmpeg: {discover_ffmpeg() or 'not found'}"))


        self.is_downloading = True
        self.cancel_requested = False
        self.download_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")

        worker = threading.Thread(target=self._run_download, args=(settings,), daemon=True)
        worker.start()

    def cancel_download(self) -> None:
        if self.is_downloading:
            self.cancel_requested = True
            self.status_var.set("Cancelling...")
            self.log_queue.put(("log", "Cancellation requested. Waiting for current fragment..."))

    def _run_download(self, settings: DownloadSettings) -> None:
        engine = DownloadEngine(
            settings=settings,
            on_log=lambda msg: self.log_queue.put(("log", msg)),
            on_progress=lambda update: self.log_queue.put(("progress", update)),
            should_cancel=lambda: self.cancel_requested,
        )

        try:
            engine.run()
            self.log_queue.put(("done", None))
        except DownloadCancelled:
            self.log_queue.put(("cancelled", None))
        except Exception as exc:
            self.log_queue.put(("error", str(exc)))
            self.log_queue.put(("log", f"Error: {exc}"))


def main() -> None:
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
