#!/usr/bin/env python3
"""YouTube to MP3 (320kbps) Downloader for Video Editors.

Downloads high-quality audio from YouTube, processes with pydub to true
320kbps CBR MP3 (48kHz SMPTE standard), normalizes peaks, and embeds ID3 tags.
"""

import os
import sys
import argparse
import subprocess
from typing import Optional

# Ensure audioop compatibility for Python 3.13+
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules["audioop"] = audioop
    except ImportError:
        pass

from core.downloader import YouTubeMP3Downloader


def parse_timestamp(ts: Optional[str]) -> Optional[float]:
    """
    Parses timestamp into seconds.
    Supports formats:
      - Raw seconds: '90', '45.5'
      - MM:SS: '1:30', '03:45'
      - HH:MM:SS: '01:15:30'
    """
    if not ts:
        return None
    ts = str(ts).strip()
    if not ts:
        return None
    if ":" not in ts:
        try:
            return float(ts)
        except ValueError:
            return None

    parts = ts.split(":")
    try:
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:  # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return None
    return None


def open_folder(folder_path: str):
    """Opens directory in Windows Explorer / OS file manager."""
    try:
        if sys.platform == "win32":
            os.startfile(os.path.abspath(folder_path))
        elif sys.platform == "darwin":
            subprocess.run(["open", os.path.abspath(folder_path)], check=False)
        else:
            subprocess.run(["xdg-open", os.path.abspath(folder_path)], check=False)
    except Exception as e:
        print(f"Could not open folder automatically: {e}")


def interactive_mode():
    """Polished interactive CLI wizard."""
    print("=" * 65)
    print("  YouTube to MP3 Downloader (320 kbps) for Video Editing")
    print("  - Powered by yt-dlp & pydub")
    print("  - SMPTE Video Standard: 48 kHz, Stereo, 320 kbps CBR")
    print("=" * 65)
    print()

    url = input("Enter YouTube URL (Video / Song / Shorts / Playlist): ").strip()
    while not url:
        url = input("Please enter a valid YouTube URL: ").strip()

    output_dir = input("Output folder (press Enter for './downloads'): ").strip()
    if not output_dir:
        output_dir = "downloads"

    downloader = YouTubeMP3Downloader(
        output_dir=output_dir,
        sample_rate=48000,
        bitrate="320k",
        normalize=True,
    )

    print("\nFetching media details from YouTube...")
    try:
        info = downloader.get_info(url)
    except Exception as e:
        print(f"Error fetching video info: {e}")
        return

    if info.get("is_playlist"):
        count = info.get("count", 0)
        title = info.get("title", "Playlist")
        print(f"\nDetected Playlist: '{title}' ({count} items)")
        confirm = input(f"Do you want to download all {count} songs at 320kbps? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Download cancelled.")
            return

        print("\nStarting playlist batch download...")
        results = downloader.download_playlist(url)
        success_count = sum(1 for r in results if "error" not in r)
        print(f"\nFinished! Successfully downloaded {success_count}/{count} songs to '{output_dir}'.")
        open_folder(output_dir)
        return

    print("\n" + "-" * 50)
    print(f"  Title:    {info.get('title')}")
    print(f"  Artist:   {info.get('artist')}")
    print(f"  Duration: {info.get('duration_formatted')}")
    print("-" * 50)

    # Trimming options
    trim_choice = input("\nDo you want to trim this audio? (e.g. download only a specific part) (y/N): ").strip().lower()
    start_sec = None
    end_sec = None
    fade_in_sec = None
    fade_out_sec = None

    if trim_choice == 'y':
        start_input = input("  Start time (e.g. 0:45 or 45, press Enter for beginning): ").strip()
        start_sec = parse_timestamp(start_input)
        end_input = input("  End time (e.g. 2:30 or 150, press Enter for track end): ").strip()
        end_sec = parse_timestamp(end_input)

        fade_choice = input("  Apply smooth fade in / fade out? (y/N): ").strip().lower()
        if fade_choice == 'y':
            fi = input("    Fade in seconds (e.g. 2, press Enter to skip): ").strip()
            fade_in_sec = float(fi) if fi else None
            fo = input("    Fade out seconds (e.g. 3, press Enter to skip): ").strip()
            fade_out_sec = float(fo) if fo else None

    # Normalization
    norm_choice = input("\nNormalize volume for video editing? (Recommended: prevents clipping) (Y/n): ").strip().lower()
    downloader.normalize = (norm_choice != 'n')

    print("\nDownloading and processing audio...")
    print("1. Extracting best stream via yt-dlp...")
    print("2. Resampling & encoding to 320kbps CBR @ 48kHz via pydub...")
    print("3. Embedding ID3 tags and cover art...")

    try:
        result = downloader.download_song(
            url=url,
            start_sec=start_sec,
            end_sec=end_sec,
            fade_in_sec=fade_in_sec,
            fade_out_sec=fade_out_sec,
        )

        print("\n" + "=" * 65)
        print("  DOWNLOAD COMPLETED SUCCESSFULLY!")
        print("=" * 65)
        print(f"  File:       {result['file_name']}")
        print(f"  Saved to:   {result['file_path']}")
        print(f"  Duration:   {result['duration_formatted']}")
        print(f"  Size:       {result['filesize_mb']} MB")
        print(f"  Bitrate:    {result['bitrate']} CBR (Optimized for Video Editing)")
        print(f"  Sample Rate:{result['sample_rate']} Hz (SMPTE Standard)")
        print("=" * 65)

        open_choice = input("\nOpen downloads folder in Windows Explorer? (Y/n): ").strip().lower()
        if open_choice != 'n':
            open_folder(downloader.output_dir)

    except Exception as e:
        print(f"\nError processing song: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Download MP3 songs from YouTube at 320kbps (video editing standard)."
    )
    parser.add_argument("url", nargs="?", help="YouTube video or playlist URL")
    parser.add_argument("-o", "--output", default="downloads", help="Output directory (default: downloads)")
    parser.add_argument("-b", "--bitrate", default="320k", help="Bitrate (default: 320k)")
    parser.add_argument("-r", "--sample-rate", type=int, default=48000, help="Sample rate in Hz (default: 48000 for video editing)")
    parser.add_argument("-s", "--start", help="Trim start time (e.g. '01:15' or '75')")
    parser.add_argument("-e", "--end", help="Trim end time (e.g. '02:40' or '160')")
    parser.add_argument("--fade-in", type=float, help="Fade-in duration in seconds")
    parser.add_argument("--fade-out", type=float, help="Fade-out duration in seconds")
    parser.add_argument("--no-normalize", action="store_true", help="Disable audio peak normalization")
    parser.add_argument("--name", help="Custom output filename (without .mp3)")
    parser.add_argument("--batch", help="Path to text file containing URLs to download (one per line)")
    parser.add_argument("--open", action="store_true", help="Open output folder in file manager when finished")

    args = parser.parse_args()

    # If no URL or batch file is passed, launch interactive wizard
    if not args.url and not args.batch:
        interactive_mode()
        return

    downloader = YouTubeMP3Downloader(
        output_dir=args.output,
        sample_rate=args.sample_rate,
        bitrate=args.bitrate,
        normalize=not args.no_normalize,
    )

    # Batch mode
    if args.batch:
        if not os.path.isfile(args.batch):
            print(f"Batch file not found: {args.batch}")
            sys.exit(1)

        with open(args.batch, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

        print(f"Loaded {len(urls)} URLs from batch file '{args.batch}'.")
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")
            try:
                res = downloader.download_song(url)
                print(f"Saved: {res['file_name']} ({res['duration_formatted']}, {res['filesize_mb']} MB)")
            except Exception as e:
                print(f"Failed {url}: {e}")

        print(f"\nBatch download completed! All files saved to '{os.path.abspath(args.output)}'.")
        if args.open:
            open_folder(args.output)
        return

    # Single URL mode
    start_sec = parse_timestamp(args.start)
    end_sec = parse_timestamp(args.end)

    print(f"Downloading: {args.url}")
    print(f"Target Bitrate: {args.bitrate} | Sample Rate: {args.sample_rate}Hz | Output: {args.output}")

    try:
        # Check if URL is a playlist
        info = downloader.get_info(args.url)
        if info.get("is_playlist"):
            print(f"Playlist detected: {info.get('title')} ({info.get('count')} tracks)")
            downloader.download_playlist(args.url)
        else:
            result = downloader.download_song(
                url=args.url,
                start_sec=start_sec,
                end_sec=end_sec,
                fade_in_sec=args.fade_in,
                fade_out_sec=args.fade_out,
                custom_filename=args.name,
            )
            print("\nDownload Complete!")
            print(f"  Title:     {result['title']}")
            print(f"  Artist:    {result['artist']}")
            print(f"  Duration:  {result['duration_formatted']}")
            print(f"  File:      {result['file_path']}")
            print(f"  Size:      {result['filesize_mb']} MB (320kbps MP3)")

        if args.open:
            open_folder(args.output)

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
