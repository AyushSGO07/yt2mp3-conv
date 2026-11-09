"""YouTube Downloader module using yt-dlp, pydub, and mutagen.
Downloads high-fidelity audio streams from YouTube and delivers pristine 320kbps MP3s
optimized for video editing timelines.
"""

import os
import shutil
import tempfile
from typing import Optional, Dict, Any, Callable, List

import yt_dlp

from .audio_processor import AudioProcessor
from .metadata import (
    sanitize_filename,
    parse_title_and_artist,
    download_thumbnail,
    embed_id3_tags,
)


class YouTubeMP3Downloader:
    """Orchestrates YouTube extraction via yt-dlp and 320kbps processing via pydub."""

    def __init__(
        self,
        output_dir: str = "downloads",
        sample_rate: int = 48000,
        bitrate: str = "320k",
        normalize: bool = True,
        headroom_db: float = 0.5,
    ):
        """
        Initialize downloader.
        
        Args:
            output_dir: Directory where final MP3s will be saved.
            sample_rate: Audio sample rate (48000 Hz recommended for video editors).
            bitrate: Output MP3 bitrate (default '320k').
            normalize: Whether to normalize peaks to prevent clipping on timeline.
            headroom_db: Headroom in dB below 0 dBFS when normalizing.
        """
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.bitrate = bitrate
        self.normalize = normalize
        self.headroom_db = headroom_db
        self.processor = AudioProcessor(sample_rate=sample_rate, channels=2)

    def get_info(self, url: str) -> Dict[str, Any]:
        """
        Extracts metadata for a single video or playlist without downloading.
        Useful for UI preview and validation.
        """
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        if shutil.which("node"):
            ydl_opts['js_runtimes'] = {'node': {}}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        if not info:
            raise ValueError(f"Could not retrieve video information for URL: {url}")

        is_playlist = 'entries' in info and info['entries'] is not None

        if is_playlist:
            entries = []
            for entry in info.get('entries', []):
                if entry:
                    entries.append({
                        "id": entry.get("id"),
                        "title": entry.get("title", "Untitled"),
                        "duration": entry.get("duration", 0),
                        "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                    })
            return {
                "is_playlist": True,
                "title": info.get("title", "YouTube Playlist"),
                "count": len(entries),
                "entries": entries,
            }
        else:
            duration = info.get("duration", 0)
            mins = int(duration // 60)
            secs = int(duration % 60)
            parsed = parse_title_and_artist(
                info.get("title", "Unknown Title"),
                info.get("uploader", "Unknown Artist")
            )
            return {
                "is_playlist": False,
                "id": info.get("id"),
                "title": info.get("title", "Unknown Title"),
                "clean_title": parsed["title"],
                "artist": parsed["artist"],
                "uploader": info.get("uploader", "Unknown Artist"),
                "duration": duration,
                "duration_formatted": f"{mins:02d}:{secs:02d}",
                "thumbnail": info.get("thumbnail"),
                "webpage_url": info.get("webpage_url", url),
            }

    def download_song(
        self,
        url: str,
        start_sec: Optional[float] = None,
        end_sec: Optional[float] = None,
        fade_in_sec: Optional[float] = None,
        fade_out_sec: Optional[float] = None,
        custom_filename: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Downloads the YouTube audio stream, processes it with pydub to 320kbps MP3,
        embeds ID3 metadata and thumbnail, and returns completion stats.
        
        Args:
            url: YouTube video URL.
            start_sec: Trim start in seconds (optional).
            end_sec: Trim end in seconds (optional).
            fade_in_sec: Fade in in seconds (optional).
            fade_out_sec: Fade out in seconds (optional).
            custom_filename: Optional custom output filename (without .mp3).
            progress_callback: Callback function receiving status dict.
            
        Returns:
            Dict containing output file path, title, artist, duration, and metadata.
        """
        with tempfile.TemporaryDirectory(prefix="yt_mp3_") as temp_dir:
            temp_audio_template = os.path.join(temp_dir, "%(id)s.%(ext)s")
            temp_thumb_path = os.path.join(temp_dir, "thumb.jpg")

            def ytdl_hook(d):
                if progress_callback and d.get('status') == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes') or 0
                    percent = (downloaded / total * 100) if total > 0 else 0
                    progress_callback({
                        "status": "downloading",
                        "percent": round(percent, 1),
                        "speed": d.get('speed', 0),
                        "eta": d.get('eta', 0),
                    })

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': temp_audio_template,
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [ytdl_hook],
            }
            if shutil.which("node"):
                ydl_opts['js_runtimes'] = {'node': {}}

            if progress_callback:
                progress_callback({"status": "extracting_metadata", "percent": 0})

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)

            if not os.path.isfile(downloaded_file):
                # Search for any downloaded file in the temp directory if extension changed
                found_files = [
                    os.path.join(temp_dir, f)
                    for f in os.listdir(temp_dir)
                    if not f.startswith("thumb") and os.path.isfile(os.path.join(temp_dir, f))
                ]
                if not found_files:
                    raise FileNotFoundError("Audio stream could not be downloaded by yt-dlp.")
                downloaded_file = found_files[0]

            if progress_callback:
                progress_callback({"status": "processing_audio", "percent": 75})

            # Determine Title and Artist
            raw_title = info.get("title", "Audio Track")
            raw_uploader = info.get("uploader", "Unknown Artist")
            parsed = parse_title_and_artist(raw_title, raw_uploader)
            clean_title = parsed["title"]
            clean_artist = parsed["artist"]

            # Construct output filename
            if custom_filename:
                base_name = sanitize_filename(custom_filename)
            else:
                base_name = sanitize_filename(f"{clean_artist} - {clean_title}")

            output_mp3_path = os.path.join(self.output_dir, f"{base_name}.mp3")

            # Avoid accidental overwrite if file exists with same name
            counter = 1
            original_base = base_name
            while os.path.exists(output_mp3_path):
                base_name = f"{original_base} ({counter})"
                output_mp3_path = os.path.join(self.output_dir, f"{base_name}.mp3")
                counter += 1

            # Process with pydub: 320kbps, 48kHz, normalization, trim, fade
            proc_result = self.processor.process_and_export(
                input_path=downloaded_file,
                output_path=output_mp3_path,
                bitrate=self.bitrate,
                normalize=self.normalize,
                headroom_db=self.headroom_db,
                start_sec=start_sec,
                end_sec=end_sec,
                fade_in_sec=fade_in_sec,
                fade_out_sec=fade_out_sec,
            )

            if progress_callback:
                progress_callback({"status": "embedding_metadata", "percent": 90})

            # Download and embed thumbnail if available
            thumb_url = info.get("thumbnail")
            has_thumb = False
            if thumb_url:
                has_thumb = download_thumbnail(thumb_url, temp_thumb_path)

            upload_year = None
            upload_date = info.get("upload_date")
            if upload_date and len(upload_date) >= 4:
                upload_year = upload_date[:4]

            embed_id3_tags(
                mp3_path=output_mp3_path,
                title=clean_title,
                artist=clean_artist,
                album=info.get("channel", "YouTube Audio"),
                year=upload_year,
                genre="Soundtrack",
                comment=f"Video Editing 320kbps Audio | {url}",
                thumbnail_path=temp_thumb_path if has_thumb else None,
            )

            if progress_callback:
                progress_callback({"status": "completed", "percent": 100})

            return {
                "file_path": output_mp3_path,
                "file_name": os.path.basename(output_mp3_path),
                "title": clean_title,
                "artist": clean_artist,
                "raw_title": raw_title,
                "uploader": raw_uploader,
                "duration_formatted": proc_result["duration_formatted"],
                "duration_sec": proc_result["duration_sec"],
                "filesize_mb": proc_result["filesize_mb"],
                "bitrate": self.bitrate,
                "sample_rate": proc_result["sample_rate"],
                "normalized": proc_result["normalized"],
                "trimmed": proc_result["trimmed"],
                "thumbnail_url": thumb_url,
                "url": url,
            }

    def download_playlist(
        self,
        playlist_url: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Downloads all videos from a playlist as 320kbps MP3s."""
        info = self.get_info(playlist_url)
        if not info.get("is_playlist"):
            # Single video fallback
            return [self.download_song(playlist_url, progress_callback=progress_callback)]

        entries = info.get("entries", [])
        total = len(entries)
        results = []

        for idx, entry in enumerate(entries, 1):
            entry_url = entry["url"]
            if progress_callback:
                progress_callback({
                    "status": "playlist_item",
                    "current": idx,
                    "total": total,
                    "title": entry.get("title", ""),
                })
            try:
                res = self.download_song(entry_url)
                results.append(res)
            except Exception as e:
                results.append({
                    "url": entry_url,
                    "title": entry.get("title", ""),
                    "error": str(e),
                })

        return results
