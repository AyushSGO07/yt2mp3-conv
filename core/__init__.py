"""YouTube to MP3 Core Package.
Provides yt-dlp downloading, pydub audio processing, and ID3 metadata embedding.
"""

import sys

# Ensure Python 3.13 compatibility for pydub
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules["audioop"] = audioop
    except ImportError:
        pass

__version__ = "1.0.0"
