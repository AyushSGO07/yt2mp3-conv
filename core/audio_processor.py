"""Audio processing module using pydub.
Handles high-quality 320kbps MP3 conversion, normalization, trimming, fading,
and sample rate alignment for video editing workflows.
"""

import os
import sys
from typing import Optional, Tuple, Dict, Any

# Ensure audioop compatibility for Python 3.13+
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules["audioop"] = audioop
    except ImportError:
        pass

from pydub import AudioSegment, effects


class AudioProcessor:
    """Processes downloaded audio files for video editing standards using pydub."""

    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        """
        Initialize AudioProcessor.
        
        Args:
            sample_rate: Target sample rate in Hz. Default 48000 Hz (SMPTE video standard).
            channels: Target audio channels (2 = Stereo, 1 = Mono). Default 2.
        """
        self.sample_rate = sample_rate
        self.channels = channels

    def inspect(self, input_path: str) -> Dict[str, Any]:
        """Inspects an audio file and returns its technical audio properties."""
        audio = AudioSegment.from_file(input_path)
        duration_sec = len(audio) / 1000.0
        mins = int(duration_sec // 60)
        secs = duration_sec % 60
        
        return {
            "duration_ms": len(audio),
            "duration_sec": duration_sec,
            "duration_formatted": f"{mins:02d}:{secs:05.2f}",
            "sample_rate": audio.frame_rate,
            "channels": audio.channels,
            "sample_width": audio.sample_width,
            "max_dBFS": round(audio.max_dBFS, 2),
            "dBFS": round(audio.dBFS, 2),
        }

    def process_and_export(
        self,
        input_path: str,
        output_path: str,
        bitrate: str = "320k",
        normalize: bool = True,
        headroom_db: float = 0.5,
        start_sec: Optional[float] = None,
        end_sec: Optional[float] = None,
        fade_in_sec: Optional[float] = None,
        fade_out_sec: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Processes the input audio file with pydub and exports as a 320kbps MP3.
        
        Args:
            input_path: Path to source audio file downloaded by yt-dlp.
            output_path: Destination path for the 320kbps MP3 file.
            bitrate: Output bitrate (default '320k').
            normalize: Whether to normalize peak levels (prevents clipping in video editors).
            headroom_db: Target headroom below 0 dBFS when normalizing (default 0.5 dB).
            start_sec: Optional start trim time in seconds.
            end_sec: Optional end trim time in seconds.
            fade_in_sec: Optional fade in duration in seconds.
            fade_out_sec: Optional fade out duration in seconds.
            
        Returns:
            Dict containing processing summary and file stats.
        """
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Input audio file not found: {input_path}")

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # 1. Load audio with pydub
        audio = AudioSegment.from_file(input_path)
        original_length_ms = len(audio)

        # 2. Trim audio if specified
        start_ms = int(start_sec * 1000) if start_sec is not None and start_sec > 0 else 0
        end_ms = int(end_sec * 1000) if end_sec is not None and end_sec > 0 else len(audio)

        # Bound checks
        start_ms = max(0, min(start_ms, len(audio)))
        end_ms = max(start_ms, min(end_ms, len(audio)))

        if start_ms > 0 or end_ms < len(audio):
            audio = audio[start_ms:end_ms]

        # 3. Apply Fade In / Fade Out if specified
        if fade_in_sec and fade_in_sec > 0:
            fade_in_ms = int(min(fade_in_sec * 1000, len(audio) / 2))
            audio = audio.fade_in(fade_in_ms)

        if fade_out_sec and fade_out_sec > 0:
            fade_out_ms = int(min(fade_out_sec * 1000, len(audio) / 2))
            audio = audio.fade_out(fade_out_ms)

        # 4. Normalize volume (Crucial for video editing: avoids quiet tracks and prevents clipping)
        if normalize:
            # effects.normalize peaks to 0 dBFS minus headroom
            audio = effects.normalize(audio, headroom=headroom_db)

        # 5. Conform sample rate and channels to video editing standard
        # Video editing standard: 48,000 Hz, 2 Channels (Stereo)
        if audio.frame_rate != self.sample_rate:
            audio = audio.set_frame_rate(self.sample_rate)

        if audio.channels != self.channels:
            audio = audio.set_channels(self.channels)

        # 6. Export to MP3 with CBR 320 kbps using libmp3lame
        export_parameters = [
            "-codec:a", "libmp3lame",
            "-b:a", bitrate,
            "-ar", str(self.sample_rate),
            "-ac", str(self.channels),
            "-write_xing", "0",  # Clean CBR frame headers preferred by video NLEs
        ]

        audio.export(
            output_path,
            format="mp3",
            bitrate=bitrate,
            parameters=export_parameters,
        )

        final_size_bytes = os.path.getsize(output_path)
        final_duration_sec = len(audio) / 1000.0

        return {
            "output_path": output_path,
            "filesize_bytes": final_size_bytes,
            "filesize_mb": round(final_size_bytes / (1024 * 1024), 2),
            "duration_sec": final_duration_sec,
            "duration_formatted": f"{int(final_duration_sec // 60):02d}:{final_duration_sec % 60:05.2f}",
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bitrate": bitrate,
            "normalized": normalize,
            "trimmed": (start_ms > 0 or end_ms < original_length_ms),
        }
