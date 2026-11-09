"""Metadata and ID3 tagging module using mutagen.
Embeds track info, artist, album, and high-res cover art for easy identification
in video editing suites (Premiere Pro, DaVinci Resolve, Final Cut Pro).
"""

import os
import re
import urllib.request
from typing import Optional, Dict, Any

import mutagen
from mutagen.id3 import (
    ID3,
    ID3NoHeaderError,
    TIT2,
    TPE1,
    TALB,
    COMM,
    APIC,
    TCON,
    TDRC,
)


def sanitize_filename(filename: str, max_length: int = 180) -> str:
    """
    Sanitize string to be safe for Windows/Linux/macOS file systems.
    Removes characters: < > : " / \\ | ? * and controls characters.
    """
    # Replace illegal characters with empty string or dash
    cleaned = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Strip leading/trailing dots or spaces (Windows hates trailing dots)
    cleaned = cleaned.strip('. ')
    if not cleaned:
        cleaned = "audio_track"
    # Truncate length if needed
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip('. ')
    return cleaned


def parse_title_and_artist(video_title: str, uploader: str) -> Dict[str, str]:
    """
    Extracts artist and clean song title from video title and uploader.
    Handles 'Artist - Song' formats and cleans common noise like '(Official Music Video)'.
    """
    # Clean common YouTube noise
    noise_patterns = [
        r'\[Official\s*(?:Music\s*)?Video\]',
        r'\(Official\s*(?:Music\s*)?Video\)',
        r'\[Official\s*Audio\]',
        r'\(Official\s*Audio\)',
        r'\[Official\s*Lyric\s*Video\]',
        r'\(Official\s*Lyric\s*Video\)',
        r'\[Lyrics?\]',
        r'\(Lyrics?\)',
        r'\[HQ\]',
        r'\(HQ\)',
        r'\[HD\]',
        r'\(HD\)',
        r'\[4K\]',
        r'\(4K\)',
        r'\[Visualizer\]',
        r'\(Visualizer\)',
    ]

    clean_title = video_title
    for pattern in noise_patterns:
        clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE)
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()

    artist = uploader or "Unknown Artist"
    # Remove "- Topic" from YouTube Music artist channels
    artist = re.sub(r'\s*-\s*Topic$', '', artist, flags=re.IGNORECASE).strip()

    # Check for "Artist - Title" in the title
    if " - " in clean_title:
        parts = clean_title.split(" - ", 1)
        potential_artist = parts[0].strip()
        potential_title = parts[1].strip()
        if potential_artist and potential_title:
            artist = potential_artist
            clean_title = potential_title

    return {
        "title": clean_title,
        "artist": artist,
    }


def download_thumbnail(thumbnail_url: str, temp_thumb_path: str) -> bool:
    """Downloads thumbnail image to a local temporary path."""
    if not thumbnail_url:
        return False
    try:
        req = urllib.request.Request(
            thumbnail_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as response, open(temp_thumb_path, 'wb') as out_file:
            out_file.write(response.read())
        return os.path.isfile(temp_thumb_path) and os.path.getsize(temp_thumb_path) > 0
    except Exception:
        return False


def embed_id3_tags(
    mp3_path: str,
    title: str,
    artist: str,
    album: str = "YouTube Audio",
    year: Optional[str] = None,
    genre: str = "Soundtrack",
    comment: str = "Downloaded for video editing (320kbps CBR)",
    thumbnail_path: Optional[str] = None,
) -> None:
    """
    Embeds ID3v2.3 tags and cover art into the target MP3 file.
    ID3v2.3 is used for universal compatibility across Windows Explorer and video editors.
    """
    try:
        tags = ID3(mp3_path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.delete(mp3_path)  # Clear any legacy or partial tags
    tags = ID3()

    tags.add(TIT2(encoding=3, text=title))
    tags.add(TPE1(encoding=3, text=artist))
    tags.add(TALB(encoding=3, text=album))
    tags.add(TCON(encoding=3, text=genre))
    if year:
        tags.add(TDRC(encoding=3, text=str(year)))
    tags.add(COMM(encoding=3, lang='eng', desc='Desc', text=comment))

    # Embed thumbnail as Album Art (APIC)
    if thumbnail_path and os.path.isfile(thumbnail_path):
        try:
            with open(thumbnail_path, 'rb') as img:
                img_data = img.read()

            mime_type = "image/jpeg"
            if thumbnail_path.lower().endswith(".png"):
                mime_type = "image/png"
            elif thumbnail_path.lower().endswith(".webp"):
                mime_type = "image/webp"

            tags.add(
                APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,  # 3 is front cover
                    desc='Front Cover',
                    data=img_data,
                )
            )
        except Exception:
            pass  # Non-fatal if thumbnail fails to embed

    tags.save(mp3_path, v2_version=3)
