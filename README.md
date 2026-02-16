# TubeSwift Downloader

TubeSwift Downloader is a modern, GUI-based application for downloading YouTube videos and playlists efficiently. Built with Python and `tkinter`, it leverages the powerful `yt-dlp` library to ensure reliable downloads with support for high speeds and various quality settings.

## Features

- **Modern GUI**: A clean, dark-themed interface built with `tkinter` and `ttk`.
- **Quality Control**: Select your preferred maximum video resolution (360p, 480p, 720p, 1080p).
- **Fast Mode**: Optimizes download settings with parallel chunk downloading for maximum bandwidth usage.
- **Aria2c Integration**: Automatically detects and uses `aria2c` (if installed) as an external downloader for significantly faster speeds.
- **Live Monitoring**: Real-time progress bar, download speed, and ETA tracking.
- **Playlist Support**: Seamlessly handles individual videos and full playlists.
- **Logging**: Built-in log window to view download details and status updates.

## Prerequisites

- **Python 3.x**
- **ffmpeg**: Required so yt-dlp can merge/recode downloads into MP4.
- **aria2** (Optional): Highly recommended for the "Fast mode" to work at its best.

## Installation

1.  **Clone or download** this repository.

2.  **Create a virtual environment**:
    ```bash
    python -m venv env
    ```

3.  **Activate the virtual environment**:
    ```bash
    # Windows (PowerShell):
    ./scripts/activate
    # Windows (cmd):
    .\env\Scripts\activate.bat
    # macOS/Linux:
    source env/bin/activate
    ```

4.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: `tkinter` is included with standard Python installations on Windows/macOS. On Linux, you may need to install `python3-tk`)*.

5.  **Install ffmpeg**:
    -   **Windows**: Install from `ffmpeg.org` (or via `winget install Gyan.FFmpeg`) and add it to PATH.
    -   **Linux**: `sudo apt install ffmpeg`
    -   **macOS**: `brew install ffmpeg`

6.  **Install Aria2 (Optional but Recommended)**:
    -   **Windows**: Download `aria2` from github.com/aria2/aria2, extract it, and add the folder containing `aria2c.exe` to your system's PATH environment variable.
    -   **Linux**: `sudo apt install aria2`
    -   **macOS**: `brew install aria2`

    *The app will automatically detect `aria2c` if it is available in your PATH.*

## Usage

1.  Run the application:
    ```bash
    python download.py
    ```

2.  **Paste URL**: Enter a YouTube video or playlist link.
3.  **Select Output**: Choose a destination folder (defaults to `downloaded-videos` in the current directory).
4.  **Settings**: Pick your max quality and toggle "Fast mode".
5.  **Download**: Click "Start Download" and wait for completion.

## License

This project is open-source and free to use.
