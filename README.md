# YouTube to MP3 Downloader (320 kbps) for Video Editors

A dedicated, high-fidelity audio downloading and mastering tool built with `yt-dlp` and `pydub`. Specifically optimized for video editors (Adobe Premiere Pro, DaVinci Resolve, Final Cut Pro, CapCut, After Effects, Vegas Pro).

---

## Why This Tool is Built for Video Editors

Most generic YouTube downloaders produce inconsistent variable-bitrate (VBR) audio with non-standard sample rates (44.1 kHz, 22 kHz) that cause **audio drift**, **desync**, **clipping**, or **resampling artifacts** when imported into video editing timelines.

This tool solves those issues:

1. **True 320 kbps Constant Bitrate (CBR)**:
   - Uses `yt-dlp` to pull the highest-quality raw audio stream (Opus/AAC).
   - Re-encodes with `pydub` and `libmp3lame` at an uncompromised 320 kbps CBR with clean Xing headers.
2. **48,000 Hz (48 kHz) Video Editing Standard**:
   - Conforms all audio to 48 kHz (SMPTE industry standard for 24, 25, 30, and 60 fps timelines).
   - Eliminates real-time resampling load and audio glitching in Premiere Pro and DaVinci Resolve.
3. **Peak Normalization (-0.5 dBFS Headroom)**:
   - Automatically normalizes tracks so quiet songs are brought up and loud songs don't clip your master audio bus.
4. **Precision Trimming & Fading**:
   - Download only the specific section you need (e.g. intro, chorus, background hook) with optional fade-in and fade-out.
5. **Embedded Cover Art & ID3 Metadata**:
   - Automatically downloads the YouTube video thumbnail and embeds it as high-res album art (`APIC`) into the MP3.
   - Files display thumbnails directly in **Windows Explorer**, **DaVinci Resolve Media Pool**, and **Adobe Premiere Project Panel**.
6. **Two Interfaces Included**:
   - **Modern Web Studio (Streamlit)**: Visual player, trimming controls, progress bars, and folder opener.
   - **Interactive & CLI Tool**: Fast command-line interface with single-command or batch-file downloads.

---

## Quick Start

### 1. Requirements

- **Python 3.10+** (Fully compatible with Python 3.13 via `audioop-lts`)
- **FFmpeg** (Installed on system or in PATH)
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

---

## Method 1: Web Studio (Recommended)

Double-click `run_gui.bat` or run:
```bash
streamlit run app.py
```

### Features:
- **Instant Track Inspection**: Paste URL to see thumbnail, artist, title, and duration.
- **Audio Trimming**: Enter start and end timestamps (e.g. `0:30` to `2:15`) or set fade-in/fade-out in seconds.
- **In-Browser Audio Player**: Preview the 320kbps MP3 immediately in your browser before dragging it into your NLE.
- **Batch Tab**: Paste a list of URLs to download an entire project's soundtrack in one click.
- **One-Click Folder Reveal**: Opens the output directory directly in Windows Explorer.

---

## Method 2: Command Line (CLI)

### Interactive Mode (No Arguments)
Double-click `run_cli.bat` or run:
```bash
python downloader.py
```
This launches a guided wizard asking for your URL, optional trimming timestamps, volume normalization, and opens the output folder upon completion.

### Direct CLI Commands

#### 1. Download a single song (320 kbps CBR @ 48 kHz)
```bash
python downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

#### 2. Download with custom output folder & reveal in Explorer
```bash
python downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -o "downloads" --open
```

#### 3. Trim a specific section (e.g. from 0:45 to 2:30) with 2s fade-in and 3s fade-out
```bash
python downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --start 0:45 --end 2:30 --fade-in 2 --fade-out 3
```

#### 4. Batch download from a text file
```bash
python downloader.py --batch urls_example.txt -o downloads
```

#### 5. Download a full YouTube Playlist
```bash
python downloader.py "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

---

## CLI Options Reference

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `url` | Positional | YouTube video, music, shorts, or playlist URL | None (interactive) |
| `--output` | `-o` | Target directory for MP3 files | `downloads` |
| `--bitrate` | `-b` | MP3 audio bitrate | `320k` |
| `--sample-rate`| `-r` | Target audio sample rate | `48000` (48 kHz) |
| `--start` | `-s` | Trim start time (`MM:SS` or seconds) | Start of song |
| `--end` | `-e` | Trim end time (`MM:SS` or seconds) | End of song |
| `--fade-in` | | Fade in duration in seconds | None |
| `--fade-out` | | Fade out duration in seconds | None |
| `--no-normalize`| | Disable peak volume normalization | Normalized |
| `--name` | | Custom output filename (without `.mp3`) | `Artist - Title` |
| `--batch` | | Path to a `.txt` file with URLs (one per line)| None |
| `--open` | | Automatically reveal folder in Windows Explorer | False |

---

## Project Architecture

```
yt2mp3-conv/
├── core/
│   ├── __init__.py           # Python 3.13 audioop compatibility layer
│   ├── audio_processor.py    # pydub audio mastering (320k CBR, 48kHz conform, trim, fade, normalize)
│   ├── downloader.py         # yt-dlp stream extraction & download orchestrator
│   └── metadata.py           # ID3v2.3 tagger & high-res thumbnail cover-art embedder
├── downloads/                # Default folder for downloaded MP3s
├── app.py                    # Streamlit Web Studio
├── downloader.py             # CLI & interactive wizard
├── run_gui.bat               # Windows 1-click launcher for Web Studio
├── run_cli.bat               # Windows 1-click launcher for CLI
├── urls_example.txt          # Batch download template
├── requirements.txt          # Package dependencies
└── README.md                 # Documentation
```

---

## Best Practices for Video Editors

1. **Timeline Resampling**: Never mix 44.1 kHz and 48 kHz tracks on the same sequence if you can avoid it. Keeping all imported audio at **48 kHz** prevents subtle sync drift on long edits.
2. **Audio Levels**: All tracks processed with default settings are peak-normalized to **-0.5 dBFS**. This guarantees maximum fidelity without clipping your master meter.
3. **Cover Art in Media Pools**: The embedded ID3 artwork allows you to switch your Premiere Project Panel or DaVinci Media Pool to "Icon / Thumbnail View" for instant visual organization.
