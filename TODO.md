# TubeSwift MP3 Download Enhancement - TODO

- [x] Update `tubeswift/models.py` to add `download_type` (video/mp3) into `DownloadSettings`.

- [x] Update GUI `tubeswift/app.py` to add a “Download Type” selector and pass it into `DownloadSettings`.

- [x] Update CLI `tubeswift/cli.py` to add `--download-type {video,mp3}` and pass it into `DownloadSettings`.

- [x] Update `tubeswift/downloader.py` to implement MP3 mode using yt-dlp postprocessor `FFmpegExtractAudio`.

- [x] Update Hosted API `tubeswift/hosted_api.py` to accept/validate `download_type` and pass it into `DownloadSettings`.

- [x] Update `README.md` with GUI + CLI usage examples for MP3.

- [x] Run `python -m py_compile` on touched modules to sanity-check syntax.



